"""
control methods for the mount.
"""

import threading
from functools import partial
import time
import traceback
import os

import psutil
import random

# from sstutil import ProfileTimer as PT

import datetime
from astropy.coordinates import EarthLocation, AltAz, TETE, ICRS
from skyconv_hadec import HADec
from astropy.time import Time as AstroTime
import astropy.units as u
import math
import socket
import json
import stepper_control
import pointing_model
import pendulum
import subprocess

from timezonefinder import TimezoneFinder

import skyconv
import settings
import motion
import typing
import simple_pid

version = "0.0.37"
version_short = "0.0"
version_date_str = "Apr 26 2021"

SIDEREAL_RATE = 0.004178074568511751  # 15.041"/s
AXIS_RA = 1
AXIS_DEC = 2

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
DEFAULT_PARK = {'az': 180, 'alt': 0}
slew_lock = threading.RLock()
set_last_slew_lock = threading.RLock()
manual_lock = threading.RLock()
time_location_lock = threading.RLock()
status_interval = None
inited = False
slewing = False
stepper: typing.Optional[stepper_control.StepperControl] = None

park_sync = False

cancel_slew = False
last_status: typing.Optional[dict] = None
last_target = {'ra': None, 'dec': None, 'ha': None, 'alt': None, 'az': None, 'frame': None, 'parking': False}

ra_encoder_error = None
dec_encoder_error = None

encoder_logging_enabled = False
encoder_logging_file: typing.Optional[typing.TextIO] = None
encoder_logging_clear = False
encoder_logging_interval = None

# Last sync or slew info, if tracking sets radec, else altaz.
last_slew: typing.Dict[str, typing.Union[None, TETE, ICRS, AltAz]] = {'tete': None, 'icrs': None, 'altaz': None}

pointing_logger = settings.get_logger('pointing')

calibration_log = []


def synchronized(lock):
    """ Synchronization decorator. """

    def wrap(f):
        def newFunction(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()

        return newFunction

    return wrap


def set_last_slew(coord):
    with set_last_slew_lock:
        if not coord:
            last_slew['tete'] = None
            last_slew['altaz'] = None
        else:
            if settings.runtime_settings['tracking']:
                tete = skyconv.to_tete(coord, overwrite_time=True, obstime=AstroTime.now())
                icrs = skyconv.to_icrs(tete)
                last_slew['tete'] = tete
                last_slew['icrs'] = icrs
                last_slew['altaz'] = None
            else:
                altaz = skyconv.to_altaz(coord)
                last_slew['tete'] = None
                last_slew['icrs'] = None
                last_slew['altaz'] = altaz


sls_debounce = None


def _set_last_slew_none_run():
    global sls_debounce
    # print('Running set_last_slew(None)')
    set_last_slew(None)
    sls_debounce = None


def set_last_slew_none():
    global sls_debounce
    if sls_debounce is None:
        sls_debounce = threading.Timer(0.5, _set_last_slew_none_run)
        sls_debounce.start()


def _ra_aminpsec_to_stppsec(arcmin_per_second):
    """
    arcmin/second to steps/second for RA
    :param arcmin_per_second:
    :return:
    """
    steps_per_degree = settings.settings['ra_ticks_per_degree']
    return steps_per_degree * arcmin_per_second / 60.0


def _ra_asecpsec_to_stppsec(arcsec_per_second):
    """
    arcsec/second to steps/second for RA
    :param arcmin_per_second:
    :return:
    """
    steps_per_degree = settings.settings['ra_ticks_per_degree']
    return steps_per_degree * arcsec_per_second / (60.0 * 60.0)


def _dec_aminpsec_to_stppsec(arcmin_per_second):
    """
    arcmin/second to steps/second for Dec
    :param arcmin_per_second:
    :return:
    """
    steps_per_degree = settings.settings['dec_ticks_per_degree']
    return steps_per_degree * arcmin_per_second / 60.0


def _dec_asecpsec_to_stppsec(arcsec_per_second):
    """
    arcmin/second to steps/second for Dec
    :param arcmin_per_second:
    :return:
    """
    steps_per_degree = settings.settings['dec_ticks_per_degree']
    return steps_per_degree * arcsec_per_second / (60.0 * 60.0)


def sync(coord):
    """
    :param coord:
    :return:
    """
    global park_sync
    status = calc_status(stepper.get_status())
    obstime = AstroTime.now()
    with set_last_slew_lock:
        set_last_slew(coord)
        hadec = skyconv.to_hadec(coord, obstime=obstime)


        if settings.settings['pointing_model'] != 'single' and not park_sync and skyconv.model_real_stepper and \
                skyconv.model_real_stepper.size() > 0:
            stepper_coord = skyconv.steps_to_coord({'ha': status['rep'], 'dec': status['dep']},
                                                   frame=skyconv.model_real_stepper.frame(), obstime=obstime)
            if skyconv.model_real_stepper.frame() == 'hadec':
                skyconv.model_real_stepper.add_point(hadec, stepper_coord)
            else:  # AltAz model frame
                print(hadec, stepper_coord)
                altaz = skyconv.to_altaz(hadec)
                skyconv.model_real_stepper.add_point(altaz, stepper_coord)
            if settings.settings['pointing_model_remember']:
                settings.save_pointing_model(skyconv.model_real_stepper)
        else:
            park_sync = False
            sync_info = {'steps': {'ha': status['rep'], 'dec': status['dep']}, 'coord': hadec}
            print('Setting sync_info', sync_info)
            settings.runtime_settings['sync_info'] = sync_info
            if settings.settings['pointing_model'] in ['single', 'buie']:
                print(settings.settings['pointing_model'], 'sync')
                if not isinstance(skyconv.model_real_stepper, pointing_model.PointingModelBuie):
                    skyconv.model_real_stepper = pointing_model.PointingModelBuie(max_points=settings.settings['pointing_model_points'])
                skyconv.model_real_stepper.clear()
                if settings.settings['pointing_model_remember']:
                    try:
                        skyconv.model_real_stepper = settings.load_pointing_model()
                    except:
                        pass
                skyconv.model_real_stepper.add_point(hadec, hadec)
            else:  # affine model
                print('affine sync')
                if not isinstance(skyconv.model_real_stepper, pointing_model.PointingModelAffine):
                    skyconv.model_real_stepper = pointing_model.PointingModelAffine(max_points=settings.settings['pointing_model_points'])
                altaz = skyconv.to_altaz(hadec)
                skyconv.model_real_stepper.clear()
                if settings.settings['pointing_model_remember']:
                    try:
                        skyconv.model_real_stepper = settings.load_pointing_model()
                    except:
                        pass
                skyconv.model_real_stepper.add_point(altaz, altaz)


def slew(coord, parking=False):
    """
    Slews after going through model
    :param coord: HaDec, ICRS, TETE, AltAz astropy.coordinates or dictionary with ha, dec steps
    :param parking: True if parking slew
    :return:
    """
    global cancel_slew
    if settings.runtime_settings is None or 'sync_info' not in settings.runtime_settings or \
            settings.runtime_settings['sync_info'] is None:
        raise NotSyncedException('Not Synced')
    settings.not_parked()
    cancel_slew = True
    # If not TETE altaz or step lets make this ICRS so it recalculated every loop
    thread = threading.Thread(target=move_to_coord_threadf, args=(coord, parking))
    thread.start()


def _move_to_coord_threadf(wanted_skycoord, axis='ra', parking=False, close_enough=1):
    steps = False
    if type(wanted_skycoord) is dict and 'ha' in wanted_skycoord:
        need_step_position = {'ha': wanted_skycoord['ha'], 'dec': wanted_skycoord['dec']}
        # close_enough = 1
        steps = True
    elif wanted_skycoord.name in ['hadec', 'altaz']:
        need_step_position = skyconv.to_steps(wanted_skycoord)
        # close_enough = 1
        steps = True
    else:
        need_step_position = skyconv.to_steps(wanted_skycoord)
    count = 0
    close_timer = None
    while not cancel_slew:
        # print('_move_to_coord_threadf', axis)
        if close_timer is not None and (time.time() - close_timer) > 10.0:
            # For some reason we are never getting there
            # print('WARNING: close_time slew giving up', file=sys.stderr)
            break
        count += 1
        if not steps and count != 1 and not parking:
            need_step_position = skyconv.to_steps(wanted_skycoord)
            if settings.is_simulation():
                time.sleep(0.2 + random.random() / 10.0)
        loop_start = datetime.datetime.now()
        status = calc_status(stepper.get_status())

        if axis == 'ra':
            delta = need_step_position['ha'] - status['rep']
            status_pos_key = 'rep'
        else:
            delta = need_step_position['dec'] - status['dep']
            status_pos_key = 'dep'

        if abs(round(delta)) <= 10.0 * close_enough and close_timer is None:
            close_timer = time.time()

        if abs(round(delta)) <= close_enough:
            break

        if axis == 'ra':
            pos = 0
            if delta > 0:
                pos = 1
            settle_speed = math.copysign((pos + 4) * settings.settings['ra_track_rate'], delta)
            settle_thresh = 10 * settings.settings['ra_track_rate']
        else:
            settle_speed = math.copysign(4 * settings.settings['dec_ticks_per_degree'] * SIDEREAL_RATE, delta)
            settle_thresh = 10 * settings.settings['dec_ticks_per_degree'] * SIDEREAL_RATE

        if abs(delta) < settle_thresh:
            # print('Settle Threshold', axis)
            if axis == 'ra':
                stepper.set_speed_ra(settle_speed)
            else:
                stepper.set_speed_dec(settle_speed)
            if axis == 'ra':
                sp = need_step_position['ha']
            else:
                sp = need_step_position['dec']
            pid = simple_pid.PID(0.5, 0.1, 0.1, setpoint=sp)
            pid.output_limits = (-abs(settle_speed), abs(settle_speed))
            pid.sample_time = 0.1
            pid.auto_mode = False
            pid.set_auto_mode(True, last_output=settle_speed)
            error = delta
            last_output = -9999999999
            settling_start = time.time()
            while abs(error) > close_enough and not cancel_slew and time.time() - settling_start < 5:
                status = calc_status(stepper.get_status())
                if axis == 'ra':
                    pv = status['rep']
                else:
                    pv = status['dep']
                if not steps and axis == 'ra' and not parking:
                    new_sp = sp + ((datetime.datetime.now() - loop_start).total_seconds() + 0.1) * \
                             settings.settings['ra_track_rate']
                    pid.setpoint = new_sp
                else:
                    new_sp = sp
                output = pid(pv)
                if output != last_output:
                    last_output = output
                    # print('pid output:', axis, output)
                    if axis == 'ra':
                        stepper.set_speed_ra(output)
                    else:
                        stepper.set_speed_dec(output)
                error = new_sp - pv
            # print('End Settle Loop', axis)
        else:
            if axis == 'ra':
                if not parking and settings.runtime_settings['tracking']:
                    v_track = settings.settings['ra_track_rate']
                else:
                    v_track = 0

                times = motion.calc_speed_sleeps(
                    delta,
                    settings.settings['micro']['ra_accel_tpss'],
                    status['rs'],
                    _ra_aminpsec_to_stppsec(settings.settings['ra_slew_fastest']),
                    v_track, 'ra')
            else:
                times = motion.calc_speed_sleeps(
                    delta,
                    settings.settings['micro']['dec_accel_tpss'],
                    status['ds'],
                    _dec_aminpsec_to_stppsec(settings.settings['dec_slew_fastest']),
                    0, 'dec'
                )

            # print('dec_times', dec_times)

            for t in times:
                if t['speed'] is not None:
                    if axis == 'ra':
                        stepper.set_speed_ra(t['speed'])
                    else:
                        stepper.set_speed_dec(t['speed'])
                st = t['sleep']
                while st > 2.0:
                    st -= 2.0
                    time.sleep(2)
                    if cancel_slew:
                        break
                if cancel_slew:
                    break
                time.sleep(st)

    if axis == 'ra':
        rspeed = 0
        if not parking and settings.runtime_settings['tracking']:
            rspeed = settings.settings['ra_track_rate']
        stepper.set_speed_ra(rspeed)
    else:
        stepper.set_speed_dec(0.0)


def move_to_coord_threadf(wanted_skycoord, parking=False):
    global cancel_slew, slewing

    ha_close_enough = settings.settings['ra_track_rate']
    #dec_close_enough = 3.0
    dec_close_enough = settings.settings['dec_ticks_per_degree'] * SIDEREAL_RATE

    try:
        slew_lock.acquire()
        stepper.autoguide_disable()
        slewing = True
        cancel_slew = False

        # Threads
        ra_thread = threading.Thread(target=_move_to_coord_threadf,
                                     args=(wanted_skycoord, 'ra', parking, ha_close_enough))
        ra_thread.start()
        dec_thread = threading.Thread(target=_move_to_coord_threadf,
                                      args=(wanted_skycoord, 'dec', parking, dec_close_enough))
        dec_thread.start()

        ra_thread.join()
        dec_thread.join()

        rspeed = 0
        if settings.runtime_settings['tracking']:
            rspeed = settings.settings['ra_track_rate']
        stepper.set_speed_ra(rspeed)
        stepper.set_speed_dec(0.0)
        time.sleep(0.25)
    except:
        traceback.print_exc()
        raise
    finally:
        try:
            stepper.autoguide_enable()
            if parking and not cancel_slew:
                settings.parked()
            else:
                settings.not_parked()
            if cancel_slew or type(wanted_skycoord) is dict and 'ha' in wanted_skycoord:
                set_last_slew(None)
            else:
                set_last_slew(wanted_skycoord)
        finally:
            slewing = False
            slew_lock.release()


class SimpleInterval:
    def __init__(self, func, sec):
        # print('Simple Interval')
        self._func = func
        self._sec = sec
        self._timer = threading.Timer(self._sec, self._run)
        self._timer.start()

    def cancel(self):
        self._timer.cancel()
        self._timer = None
        self._func = None
        self._sec = None

    def _run(self):
        self._timer = threading.Timer(self._sec, self._run)
        self._timer.start()
        self._func()


# TODO: Should we really use hadec's DEC instead of tete for dec?
def below_horizon_limit(altaz, tete):
    """
    If horizon limit is enabled and earth location is set, it will set if coordinates are below the horizon limits set.
    :param altaz: altaz coordinate
    :type altaz: AltAz
    :param tete: tete coordinate to check dec limit.
    :type tete: TETE
    :return: true if below horizon limit
    :rtype: bool
    """
    az = altaz.az.deg
    alt = altaz.alt.deg
    dec = tete.dec.deg
    if settings.settings['horizon_limit_enabled']:
        dec_gt = settings.settings['horizon_limit_dec']['greater_than']
        dec_lt = settings.settings['horizon_limit_dec']['less_than']
        # print('below_horizon_limit', dec, dec_lt, dec_gt)
        if dec > dec_lt or dec < dec_gt:
            return True
        if 'horizon_limit_points' in settings.settings and \
                settings.settings['horizon_limit_points']:
            if len(settings.settings['horizon_limit_points']) == 1:
                if alt <= settings.settings['horizon_limit_points'][0]['alt']:
                    return True
                else:
                    return False
            else:
                for i in range(len(settings.settings['horizon_limit_points']) - 1):
                    point1 = settings.settings['horizon_limit_points'][i]
                    if i + 1 < len(settings.settings['horizon_limit_points']):
                        point2 = settings.settings['horizon_limit_points'][i + 1]
                    else:
                        point2 = settings.settings['horizon_limit_points'][0]
                    p1az = point1['az']
                    if point2['az'] < p1az or len(settings.settings['horizon_limit_points']) == 1:
                        p1az -= 360.0

                    point2 = settings.settings['horizon_limit_points'][i + 1]
                    if p1az <= az < point2['az']:
                        m = (point2['alt'] - point1['alt']) / (point2['az'] - p1az)
                        b = point1['alt']
                        if alt < (m * (az - p1az) + b):
                            return True
                        else:
                            return False
    return False


def slewtocheck(coord):
    """
    Check if skycoordinate okay to slew or is below horizon limit.
    :param coord:
    :return: true is okay to slew
    :rtype: bool
    """
    if coord is None:
        return False
    tete = skyconv.to_tete(coord)
    altaz = skyconv.to_altaz(coord)
    if below_horizon_limit(altaz, tete):
        return False
    else:
        return True


# We are going to sync based on altaz coordinates, this will be the default location if not set. We'll
# sync on pretend altaz locations.
DEFAULT_ELEVATION_M = 405.0
DEFAULT_LAT_DEG = 0
DEFAULT_LON_DEG = 0


def update_location(from_gps=False):
    """
    Takes current location set in settings and sets runtime earth location.
    """
    # only do altaz sync if after first init
    do_altaz_sync = settings.runtime_settings['earth_location'] is not None
    if do_altaz_sync:
        send_status()
        alt = last_status['alt']
        az = last_status['az']
    # print(settings.settings['location'])
    if 'location' not in settings.settings or not settings.settings['location'] or \
            not settings.settings['location']['lat']:
        settings.runtime_settings['earth_location'] = EarthLocation(lat=DEFAULT_LAT_DEG * u.deg,
                                                                    lon=DEFAULT_LON_DEG * u.deg,
                                                                    height=DEFAULT_ELEVATION_M * u.m)
        return
    if 'elevation' not in settings.settings['location']:
        elevation = DEFAULT_ELEVATION_M
    else:
        elevation = settings.settings['location']['elevation']
    el = EarthLocation(lat=settings.settings['location']['lat'] * u.deg,
                       lon=settings.settings['location']['long'] * u.deg,
                       height=elevation * u.m)
    settings.runtime_settings['earth_location'] = el
    settings.runtime_settings['earth_location_from_gps'] = from_gps
    if do_altaz_sync:
        set_sync(alt=alt, az=az, frame='altaz')
    try:
        settings.runtime_settings['last_locationtz'] = TimezoneFinder().timezone_at(lng=el.lon.deg, lat=el.lat.deg)
    except:
        print('Error getting timezone from location.')
        traceback.print_exc()


def calc_status(status):
    """
    Takes re (ra encoder count), ri (ra steps between encoder), rp (ra step counts) to make a authoritative rep
    count based on settings.
    :param status: Should have keys ri, re, rp, di, de, dp
    :rtype status: dict
    :return: Updates status but also returns it.
    """
    global cancel_slew, ra_encoder_error, dec_encoder_error
    if settings.settings['ra_use_encoder']:
        ra_steps_per_encoder = settings.settings['ra_ticks_per_degree'] / settings.settings[
            'ra_encoder_pulse_per_degree']
        ri = status['ri']
        if settings.settings['limit_encoder_step_fillin']:
            if abs(status['ri']) > abs(ra_steps_per_encoder):
                ri = math.copysign(ri, ra_steps_per_encoder)
            if abs(status['ri']) > abs(10 * settings.settings['ra_ticks_per_degree']):
                # Something wrong with encoder/motor
                cancel_slew = True
                ra_encoder_error = 'Movement not detected by RA Encoder'
                stepper.update_settings({'ra_disable': True})
            else:
                ra_encoder_error = None
        rep = status['re'] * ra_steps_per_encoder + ri
    else:
        ra_encoder_error = None
        rep = status['rp']

    if settings.settings['dec_use_encoder']:
        dec_steps_per_encoder = settings.settings['dec_ticks_per_degree'] / settings.settings[
            'dec_encoder_pulse_per_degree']
        di = status['di']
        if settings.settings['limit_encoder_step_fillin']:
            if abs(status['di']) > abs(dec_steps_per_encoder):
                di = math.copysign(di, dec_steps_per_encoder)
            if abs(status['di']) > abs(10 * settings.settings['dec_ticks_per_degree']):
                # Something wrong with encoder/motor
                cancel_slew = True
                dec_encoder_error = 'Movement not detected by DEC Encoder'
                stepper.update_settings({'dec_disable': True})
            else:
                dec_encoder_error = None
        dep = status['de'] * dec_steps_per_encoder + di
    else:
        dec_encoder_error = None
        dep = status['dp']
    status['rep'] = rep
    status['dep'] = dep
    return status


def start_stop_encoder_logger(enabled):
    global encoder_logging_file, encoder_logging_interval, encoder_logging_enabled
    if enabled and not encoder_logging_enabled:
        encoder_logging_enabled = True
        encoder_logging_file = open('/home/pi/logs/stepper_encoder.csv', 'w')
        encoder_logging_file.write('Time,step_ra,step_dec,enc_ra,enc_dec,ra_over_raenc,dec_over_decenc\n')
        encoder_logging_interval = SimpleInterval(encoder_log, 0.25)
    elif not enabled and encoder_logging_enabled:
        encoder_logging_enabled = False
        if encoder_logging_file:
            encoder_logging_file.close()
            encoder_logging_file = None
        if encoder_logging_interval:
            encoder_logging_interval.cancel()
            encoder_logging_interval = None


def encoder_log():
    global encoder_logging_clear
    if encoder_logging_clear:
        start_stop_encoder_logger(False)
        start_stop_encoder_logger(True)
        encoder_logging_clear = False
    s = stepper.get_status()
    rp_over_re = s['rl']
    dp_over_de = s['dl']
    encoder_logging_file.write(
        '%f,%d,%d,%d,%d,%.2f,%.2f\n' % (time.time(), s['rp'], s['dp'], s['re'], s['de'], rp_over_re, dp_over_de))
    encoder_logging_file.flush()


def get_cpustats():
    ret = {'tempc': 0.0, 'tempf': 0.0, 'load_percent': 0.0, 'memory_percent_usage': 0.0}
    if not settings.is_simulation():
        tempc = subprocess.run(['/usr/bin/vcgencmd', 'measure_temp'],
                               stdout=subprocess.PIPE).stdout.decode().strip().split('=')[1].split("'")[0]
    else:
        tempc = 20.0
    tempc = float(tempc)
    tempf = 32 + tempc * 9. / 5
    load_percent = psutil.cpu_percent()
    tot_m, used_m, free_m = map(int, os.popen('/usr/bin/free -t -m').readlines()[-1].split()[1:])
    memory_percent_usage = 100 * float(used_m) / tot_m
    ret['tempc'] = tempc
    ret['tempf'] = tempf
    ret['load_percent'] = load_percent
    ret['memory_percent_usage'] = memory_percent_usage
    return ret


def send_status():
    """
    Calculates and sets last_status global
    :return:
    """
    import handpad_server
    global slewing, last_status, last_slew, cancel_slew, ra_encoder_error, dec_encoder_error
    try:
        status = calc_status(stepper.get_status())
        status['ra'] = None
        status['dec'] = None
        status['alt'] = None
        status['az'] = None
        status['hostname'] = socket.gethostname()
        status['started_parked'] = settings.runtime_settings['started_parked']
        st = skyconv.get_sidereal_time().hms
        status['sidereal_time'] = '%02d:%02d:%02d' % (int(st.h), int(st.m), int(st.s))
        status['synced'] = settings.runtime_settings['sync_info'] is not None
        status['cpustats'] = get_cpustats()
        if not handpad_server.handpad_server:  # If server has not started yet
            status['handpad'] = False
        else:
            status['handpad'] = handpad_server.handpad_server.serial is not None
        if status['synced']:
            obstime = AstroTime.now()
            with set_last_slew_lock:
                if slewing or (settings.runtime_settings['tracking'] and not last_slew['tete']) or (
                        not settings.runtime_settings['tracking'] and not last_slew['altaz']):
                    icrs = skyconv.steps_to_coord({'ha': status['rep'], 'dec': status['dep']}, frame='icrs',
                                                  obstime=obstime)
                    tete = skyconv.to_tete(icrs, obstime=obstime)
                    hadec = skyconv.to_hadec(icrs, obstime=obstime)
                    # print('After steps_to_coord', radec)
                    altaz = skyconv.to_altaz(tete)
                    if not slewing:
                        set_last_slew(tete)
                else:
                    # Use last slew data if tracking
                    if settings.runtime_settings['tracking']:
                        tete = last_slew['tete']
                        icrs = skyconv.to_icrs(tete)
                        hadec = skyconv.to_hadec(icrs, obstime=obstime)
                        altaz = skyconv.to_altaz(icrs, obstime=obstime)
                    else:
                        altaz = last_slew['altaz']
                        tete = skyconv.to_tete(altaz, obstime=obstime, overwrite_time=True)
                        icrs = skyconv.to_icrs(tete)
                        hadec = skyconv.to_hadec(icrs, obstime=obstime)
            status['ra'] = tete.ra.deg
            status['dec'] = tete.dec.deg
            status['tete_ra'] = tete.ra.deg
            status['tete_dec'] = tete.dec.deg
            status['icrs_ra'] = icrs.ra.deg
            status['icrs_dec'] = icrs.dec.deg
            status['hadec_ha'] = hadec.ha.deg
            status['hadec_dec'] = hadec.dec.deg
            status['time'] = obstime.iso + 'Z'
            # print('earth_location', settings.runtime_settings['earth_location'])
            status['alt'] = altaz.alt.deg
            status['az'] = altaz.az.deg
            status['last_target'] = last_target
            below_horizon = below_horizon_limit(altaz, tete)
            if below_horizon and settings.runtime_settings['tracking']:
                cancel_slew = True
                settings.runtime_settings['tracking'] = False
                stepper.set_speed_ra(0)
                set_last_slew(altaz)
                status['alert'] = 'In horizon limit, tracking stopped'
            # print(altaz)
        if ra_encoder_error:
            status['alert'] = ra_encoder_error
            # Hack to make the error keep coming up
            if ra_encoder_error[-1] == ' ':
                ra_encoder_error = ra_encoder_error.strip()
            else:
                ra_encoder_error = ra_encoder_error + ' '
        elif dec_encoder_error:
            status['alert'] = dec_encoder_error
            # Hack to make the error keep coming up
            if dec_encoder_error[-1] == ' ':
                dec_encoder_error = dec_encoder_error.strip()
            else:
                dec_encoder_error = dec_encoder_error + ' '
        status['slewing'] = slewing
        status['tracking'] = settings.runtime_settings['tracking']
        last_status = status
        # socketio.emit('status', status)
    except:
        traceback.print_exc()


# TMOVE: stepper_control
def micro_update_settings():
    """
    Updates microcontroller runtime values with what is in settings.
    """
    key_values = {'ra_max_tps': _ra_aminpsec_to_stppsec(settings.settings['ra_slew_fastest']),
                  'ra_guide_rate': _ra_asecpsec_to_stppsec(settings.settings['micro']['ra_guide_rate']),
                  'ra_direction': settings.settings['micro']['ra_direction'],
                  'dec_max_tps': _dec_aminpsec_to_stppsec(settings.settings['dec_slew_fastest']),
                  'dec_guide_rate': _dec_asecpsec_to_stppsec(settings.settings['micro']['dec_guide_rate']),
                  'dec_direction': settings.settings['micro']['dec_direction'],
                  'dec_disable': settings.settings['micro']['dec_disable'],
                  'ra_disable': settings.settings['micro']['ra_disable'],
                  'ra_accel_tpss': settings.settings['micro']['ra_accel_tpss'],
                  'dec_accel_tpss': settings.settings['micro']['dec_accel_tpss'],
                  'ra_run_current': settings.settings['micro']['ra_run_current'],
                  'dec_run_current': settings.settings['micro']['dec_run_current'],
                  'ra_med_current': settings.settings['micro']['ra_med_current'],
                  'ra_med_current_threshold': settings.settings['micro']['ra_med_current_threshold'],
                  'dec_med_current': settings.settings['micro']['dec_med_current'],
                  'dec_med_current_threshold': settings.settings['micro']['dec_med_current_threshold'],
                  'ra_hold_current': settings.settings['micro']['ra_hold_current'],
                  'dec_hold_current': settings.settings['micro']['dec_hold_current'],
                  'dec_backlash': settings.settings['micro']['dec_backlash'],
                  'dec_backlash_speed': settings.settings['micro']['dec_backlash_speed'],
                  'ra_backlash': settings.settings['micro']['ra_backlash'],
                  'ra_backlash_speed': settings.settings['micro']['ra_backlash_speed'],
                  }
    stepper.update_settings(key_values)
    if settings.runtime_settings['tracking']:
        stepper.set_speed_ra(settings.settings['ra_track_rate'])
    else:
        stepper.set_speed_ra(0)
    stepper.set_speed_dec(0)


def init():
    """
    Init point for this module.
    :return:
    """
    global stepper, status_interval, inited, park_sync, encoder_logging_file
    if inited:
        return
    inited = True
    # NTP can screw up unparking
    if not settings.is_simulation():
        subprocess.run(['/usr/bin/sudo', '/bin/systemctl', 'stop', 'ntp'])
    # print('Inited')
    # Load settings file
    # Open serial port
    stepper = stepper_control.StepperControl(settings.settings['microserial']['port'],
                                             settings.settings['microserial']['baud'])
    skyconv.model_real_stepper = pointing_model.PointingModelBuie()
    # Handpad will set time/location from GPS eventually
    update_location()
    micro_update_settings()

    frame_args = skyconv.get_frame_init_args('altaz')
    if settings.settings['park_position']:
        settings.runtime_settings['started_parked'] = True
        altaz = AltAz(alt=settings.settings['park_position']['alt'] * u.deg,
                      az=settings.settings['park_position']['az'] * u.deg, **frame_args)
        coord = skyconv.to_icrs(altaz)
    else:
        altaz = AltAz(alt=DEFAULT_PARK['alt'] * u.deg,
                      az=DEFAULT_PARK['az'] * u.deg, frame='altaz', **frame_args)
        coord = skyconv.to_icrs(altaz)
    settings.not_parked()
    sync(coord)
    park_sync = True
    send_status()
    status_interval = SimpleInterval(send_status, 1)
    SimpleInterval(alive_check, 3)
    time.sleep(0.5)


def guide_control(direction, time_ms):
    """

    :param direction: 'n', 's', 'e', or 'w'
    :type direction: str
    :param time_ms:
    :type time_ms: float
    :return:
    """
    # TODO: Not when manual slewing
    # TODO: Different locks for e or w ?
    got_lock = slew_lock.acquire(blocking=False)
    if not got_lock:
        return
    try:
        status = calc_status(stepper.get_status())
        if direction == 'n':
            stepper.set_speed_dec(status['ds'] + _dec_asecpsec_to_stppsec(settings.settings['micro']['dec_guide_rate']))
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_dec, status['ds']))
        elif direction == 's':
            stepper.set_speed_dec(status['ds'] - _dec_asecpsec_to_stppsec(settings.settings['micro']['dec_guide_rate']))
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_dec, status['ds']))
        elif direction == 'w':
            stepper.set_speed_ra(status['rs'] + _ra_asecpsec_to_stppsec(settings.settings['micro']['ra_guide_rate']))
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_ra, status['rs']))
        elif direction == 'e':
            stepper.set_speed_ra(status['rs'] - _ra_asecpsec_to_stppsec(settings.settings['micro']['ra_guide_rate']))
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_ra, status['rs']))
    except:
        traceback.print_exc()
        raise
    finally:
        slew_lock.release()


# Alive is to make sure we don't have a runaway mount incase there is a network disconnection
alive_check_flag = {}
is_alive = {}


def set_alive(client_id):
    alive_check_flag[client_id] = True
    is_alive[client_id] = True


def alive_check():
    for key in alive_check_flag:
        if not alive_check_flag[key]:
            is_alive[key] = False
        else:
            is_alive[key] = True
        alive_check_flag[key] = False


compliment_direction = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}


def manual_control(direction, speed, client_id):
    global slew_lock, manual_lock
    settings.not_parked()
    # print(direction, speed)
    with manual_lock:
        got_lock = slew_lock.acquire(blocking=False)
        if not got_lock:
            for direction in ['left', 'right', 'up', 'down']:
                if direction in timers:
                    timers[direction].cancel()
                    del timers[direction]
            return
        try:
            if direction not in ['left', 'right', 'up', 'down']:
                return
            # If not currently slewing somewhere else
            if direction in timers:
                timers[direction].cancel()
                del timers[direction]
            comp = compliment_direction[direction]
            if comp in timers:
                timers[comp].cancel()
                del timers[comp]
            # print(is_alive, speed)
            if not is_alive[client_id] or not speed:
                status = stepper.get_status()
                recall = False
                if direction in ['left', 'right']:
                    if settings.runtime_settings['tracking']:
                        sspeed = settings.settings['ra_track_rate']
                    else:
                        sspeed = 0
                    stepper.set_speed_ra(sspeed)
                    if not math.isclose(status['rs'], sspeed, rel_tol=0.02):
                        # print('manual stop recall', status['rs'], sspeed)
                        recall = True
                else:
                    stepper.set_speed_dec(0)
                    if status['ds'] != 0:
                        recall = True
                # Keep calling until we are settled
                if recall:
                    timers[direction] = threading.Timer(1, partial(manual_control, direction, speed, client_id))
                    timers[direction].start()
            else:
                # If not current manually going other direction
                if OPPOSITE_MANUAL[direction] in timers:
                    return
                if direction == 'left':
                    stepper.set_speed_ra(-1.0 * _ra_aminpsec_to_stppsec(settings.settings['ra_slew_' + speed]))
                elif direction == 'right':
                    stepper.set_speed_ra(_ra_aminpsec_to_stppsec(settings.settings['ra_slew_' + speed]))
                elif direction == 'up':
                    stepper.set_speed_dec(_dec_aminpsec_to_stppsec(settings.settings['dec_slew_' + speed]))
                elif direction == 'down':
                    stepper.set_speed_dec(-_dec_aminpsec_to_stppsec(settings.settings['dec_slew_' + speed]))
                # We call this periodically if not alive it will cancel the slewing, if alive it will continue at
                # speed we are at.
                timers[direction] = threading.Timer(1, partial(manual_control, direction, speed, client_id))
                timers[direction].start()
        except:
            traceback.print_exc()
            raise
        finally:
            set_last_slew_none()
            # TODO: none it after 5 seconds if slow acceleration, really should we wait for speed to settle?
            threading.Timer(5, set_last_slew_none)
            threading.Timer(10, set_last_slew_none)
            slew_lock.release()


class NotSyncedException(Exception):
    pass


# TMOVE: stepper_control
def cancel_slews():
    """
    Stop any current slews.
    :return:
    """
    global cancel_slew
    cancel_slew = True
    time.sleep(0.25)
    while not cancel_slew:
        cancel_slew = True
        time.sleep(0.25)


def clear_sync():
    """
    Clears sync_info and sync points.
    """
    global park_sync
    if settings.runtime_settings['tracking']:
        frame_args = skyconv.get_frame_init_args('tete')
        scord = TETE(ra=last_status['ra'] * u.deg, dec=last_status['dec'] * u.deg, ** frame_args)
    else:
        frame_args = skyconv.get_frame_init_args('altaz')
        scord = AltAz(alt=last_status['alt'] * u.deg, az=last_status['az'] * u.deg, **frame_args)
    pointing_logger.debug(json.dumps({'func': 'control.clear_sync'}))
    settings.rm_pointing_model()
    park_sync = True
    sync(scord)
    park_sync = True


def stop_tracking():
    """
    Stops tracking.
    :return:
    """
    settings.runtime_settings['tracking'] = False
    stepper.set_speed_ra(0)
    set_last_slew(last_slew['tete'])


def start_tracking():
    """
    Starts tracking
    :return:
    """
    settings.not_parked()
    settings.runtime_settings['tracking'] = True
    stepper.set_speed_ra(settings.settings['ra_track_rate'])
    set_last_slew(last_slew['altaz'])


def park_scope():
    stop_tracking()
    frame_args = skyconv.get_frame_init_args('altaz')
    if not settings.settings['park_position']:
        coord = AltAz(alt=DEFAULT_PARK['alt'] * u.deg,
                      az=DEFAULT_PARK['az'] * u.deg, **frame_args)
    else:
        coord = AltAz(alt=settings.settings['park_position']['alt'] * u.deg,
                      az=settings.settings['park_position']['az'] * u.deg, **frame_args)
    slew(coord, parking=True)


@synchronized(time_location_lock)
def set_time(iso_timestr, from_gps=False):
    """
    Will not overwrite if higher priority has previously set. Priorities: 1) GPS 2) NTP 3) Everything else
    :param iso_timestr:
    :type iso_timestr: str
    :return: bool, status_str  True if it set date or didn't need to set date, false if failed. status_str is info
    about what it did.
    :rtype: (bool, str)
    """
    if not from_gps and settings.runtime_settings['time_from_gps']:
        return True, 'Already Set by GPS'
    s = datetime.datetime.now()
    d = pendulum.parse(iso_timestr)
    if settings.is_simulation():
        return True, 'Date Set'
    ntpstat = subprocess.run(['/usr/bin/ntpstat'])
    if from_gps or ntpstat.returncode != 0:
        send_status()
        alt = last_status['alt']
        az = last_status['az']
        d = d + (datetime.datetime.now() - s)
        time_s = d.isoformat()
        daterun = subprocess.run(['/usr/bin/sudo', '/bin/date', '-s', time_s])
        set_sync(alt=alt, az=az)
        if daterun.returncode == 0:
            settings.runtime_settings['time_from_gps'] = from_gps
            return True, 'Date Set'
        else:
            return False, 'Failed to set date'
    return True, 'NTP Set'


@synchronized(time_location_lock)
def set_location(lat, long, elevation, name, from_gps=False):
    """
    Set the mount earth location. Will not overwrite if previously set with higher priority.
    Priority: 1) GPS 2) Everything else
    :param lat: Latitude in degrees
    :type lat: float
    :param long: Longitude in degrees
    :type long: float
    :param elevation: Elevation in meters
    :type elevation: float
    :param name: Name to set location as.
    :type name: str
    :param from_gps: If location was obtained through GPS
    :type from_gps: bool
    :return: None
    """
    if not from_gps and settings.runtime_settings['earth_location_from_gps']:
        return
    location = {'lat': lat, 'long': long, 'elevation': elevation, 'name': name}
    old_location = settings.settings['location']
    settings.settings['location'] = location
    try:
        update_location(from_gps)
    except Exception:
        settings.settings['location'] = old_location
        traceback.print_exc()
        update_location(old_location)
        raise
    settings.write_settings(settings.settings)


def set_sync(ra=None, dec=None, alt=None, az=None, ha=None, frame='icrs'):
    """
    Sync the mount to coordinates given acceptable parameters and defined frame.
    :param ra: RA in degrees
    :type ra: float
    :param dec: Dec in degrees
    :type dec: float
    :param alt: in degrees
    :type alt: float
    :param az: in degrees
    :type az: float
    :param ha: in degrees
    :type ha: float
    :param frame: defaults 'icrs'. which frame, needs to go with parameters, 'icrs', 'tete', 'altaz', 'hadec'
    :type frame: str
    :return: Model point size.
    :rtype: int
    """
    if alt is not None and az is not None:
        frame_args = skyconv.get_frame_init_args('altaz')
        coord = AltAz(alt=alt * u.deg, az=az * u.deg, **frame_args)
    elif ra is not None and dec is not None:
        if frame == 'icrs':
            coord = ICRS(ra=ra * u.deg, dec=dec * u.deg)
        else:  # TETE JNow
            frame_args = skyconv.get_frame_init_args('tete')
            coord = TETE(ra=ra * u.deg, dec=dec * u.deg, **frame_args)
    elif ha is not None:
        frame_args = skyconv.get_frame_init_args('hadec')
        coord = HADec(ha=ha * u.deg, dec=dec * u.deg, **frame_args)
    else:
        raise Exception('Missing Coordinates')
    if settings.runtime_settings['calibration_logging'] and len(calibration_log) > 0:
        calibration_log[-1]['sync'] = coord
    sync(coord)
    return skyconv.model_real_stepper.size()


def set_slew(ra=None, dec=None, alt=None, az=None, ra_steps=None, dec_steps=None, parking=False, ha=None, frame='icrs'):
    """
    Slew to ra-dec, alt-az or, ra_steps-dec_steps.
    :param ra: RA in degrees
    :type ra: float
    :param dec: DEC in degrees
    :type dec: float
    :param alt: Altitude in degrees
    :type alt: float
    :param az: Azimuth in degrees
    :type az: float
    :param ra_steps: RA Stepper steps
    :type ra_steps: int
    :param dec_steps: DEC Stepper steps
    :type dec_steps: int
    :param parking: True if parking slew
    :type parking: bool
    :param ha: HA in degrees
    :type ha: float
    :param frame: Frame given defaults 'icrs'
    :type frame: str
    :return:
    """
    global last_target
    target = locals()
    if parking:
        target['frame'] = 'parking'
    if ra_steps is not None and dec_steps is not None:
        last_target = target
        slew({'ha': ra_steps, 'dec': dec_steps})
        return
    elif alt is not None and az is not None:
        frame_args = skyconv.get_frame_init_args('altaz')
        coord = AltAz(alt=float(alt) * u.deg, az=float(az) * u.deg, **frame_args)
    elif ha is not None:
        frame_args = skyconv.get_frame_init_args('hadec')
        coord = HADec(ha=ha * u.deg, dec=dec * u.deg, **frame_args)
    else:
        ra = float(ra)
        dec = float(dec)
        if frame == 'icrs':
            coord = ICRS(ra=ra * u.deg, dec=dec * u.deg)
        else:
            frame_args = skyconv.get_frame_init_args('tete')
            coord = TETE(ra=ra * u.deg, dec=dec * u.deg, **frame_args)
    if not slewtocheck(coord):
        # print('NNNNNNNNNNNNNNNNNNNNNNNOOOOOOOOOOOOOOOOOTTTT')
        raise Exception('Slew position is below horizon or in keep-out area.')
    else:
        if settings.runtime_settings['calibration_logging']:
            frame_args = skyconv.get_frame_init_args('tete', obstime=AstroTime(last_status['time']))
            calibration_log.append({
                'slewfrom': TETE(ra=last_status['ra'] * u.deg, dec=last_status['dec'] * u.deg, **frame_args),
                'slewto': coord})
        last_target = target
        slew(coord, parking)


def set_shutdown():
    """
    Stops motors and shuts down the mount.
    :return:
    """
    stepper.set_speed_ra(0.0)
    stepper.set_speed_dec(0.0)
    time.sleep(0.25)
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])


def set_park_position_here():
    """
    Sets current position to park position.
    """
    if settings.runtime_settings['tracking']:
        frame_args = skyconv.get_frame_init_args('tete', obstime=AstroTime(last_status['time']))
        coord = TETE(ra=last_status['ra'] * u.deg, dec=last_status['dec'] * u.deg, **frame_args)
        altaz = skyconv.to_altaz(coord)
        settings.settings['park_position'] = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
    else:
        settings.settings['park_position'] = {'alt': last_status['alt'], 'az': last_status['az']}
    settings.write_settings(settings.settings)
