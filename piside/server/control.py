"""
control methods for the mount.
Terminology


Pointing:

1) desired ra/dec
2) if atmospheric refraction correction is enabled
       convert to altaz accounting for atmospheric refraction
   else
       convert to altaz without accounting for atmospheric refraction

3) if altaz inside a 3 point sync area, get nearest three points
        altaz_cal = transform altaz with affine from 3 point sync area
        ra_dec_cal = altaz_cal to ra dec
   elif find nearest 2 point sync
        altaz_cal = transform altaz with affine from 2 point sync
        ra_dec_cal = altaz_cal to ra_dec
   elif use nearest 1 point sync
        ra_dec_cal = altaz to ra dec

4) steps = ra_dec_cal to steps using degree delta and settings steps/degree
   goto steps

"""

import threading
from functools import partial
import time
import traceback
import sys
import os
import psutil

# from sstutil import ProfileTimer as PT

import datetime
from astropy.coordinates import EarthLocation, SkyCoord
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

version = "0.0.28"
version_short = "0.0"
version_date_str = "Aug 31 2020"

SIDEREAL_RATE = 0.004178074568511751  # 15.041"/s
AXIS_RA = 1
AXIS_DEC = 2

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
DEFAULT_PARK = {'az': 180, 'alt': 0}
slew_lock = threading.RLock()
set_last_slew_lock = threading.RLock()
manual_lock = threading.RLock()
status_interval = None
inited = False
slewing = False
stepper = None

park_sync = False

cancel_slew = False
last_status = None

ra_encoder_error = None
dec_encoder_error = None

encoder_logging_enabled = False
encoder_logging_file = None
encoder_logging_clear = False
encoder_logging_interval = None

# Last sync or slew info, if tracking sets radec, else altaz.
last_slew = {'radec': None, 'altaz': None}

pointing_logger = settings.get_logger('pointing')

calibration_log = []


def set_last_slew(coord, obstime=None):
    if not obstime:
        obstime = AstroTime.now()
    with set_last_slew_lock:
        if not coord:
            last_slew['radec'] = None
            last_slew['altaz'] = None
        else:
            if hasattr(coord, 'ra'):
                if settings.runtime_settings['tracking']:
                    last_slew['radec'] = coord
                    last_slew['altaz'] = None
                else:
                    altaz = skyconv.icrs_to_altaz(coord, obstime=obstime, atmo_refraction=True)
                    last_slew['radec'] = None
                    last_slew['altaz'] = altaz
            else:
                if settings.runtime_settings['tracking']:
                    icrs = skyconv.altaz_to_icrs(coord, obstime=obstime, atmo_refraction=True)
                    last_slew['radec'] = icrs
                    last_slew['altaz'] = None
                else:
                    last_slew['radec'] = None
                    last_slew['altaz'] = coord


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


def sync(coord):
    """
    :param coord:
    :return:
    """
    global park_sync
    status = calc_status(stepper.get_status())
    obstime = AstroTime.now()
    with set_last_slew_lock:
        set_last_slew(coord, obstime=obstime)
        if hasattr(coord, 'ra'):
            coord = skyconv.icrs_to_hadec(coord, obstime=obstime, atmo_refraction=True)
        elif hasattr(coord, 'alt'):
            # print(coord)
            coord = skyconv.altaz_to_icrs(coord, obstime=obstime, atmo_refraction=False)
            # print(coord)
            coord = skyconv.icrs_to_hadec(coord, obstime=obstime, atmo_refraction=False)
            # print(coord)

        if settings.settings['pointing_model'] != 'single' and not park_sync and skyconv.model_real_stepper and \
                skyconv.model_real_stepper.size() > 0:
            stepper_coord = skyconv.steps_to_coord({'ha': status['rep'], 'dec': status['dep']},
                                                   frame=skyconv.model_real_stepper.frame(), inverse_model=True,
                                                   obstime=obstime)
            if skyconv.model_real_stepper.frame() == 'hadec':
                skyconv.model_real_stepper.add_point(coord, stepper_coord)
            else:  # AltAz model frame
                print(coord, stepper_coord)
                coord = skyconv.hadec_to_altaz(coord, obstime=obstime)
                skyconv.model_real_stepper.add_point(coord, stepper_coord)
        else:
            park_sync = False
            sync_info = {'steps': {'ha': status['rep'], 'dec': status['dep']}, 'coord': coord}
            print('Setting sync_info', sync_info)
            settings.runtime_settings['sync_info'] = sync_info
            if settings.settings['pointing_model'] in ['single', 'buie']:
                print(settings.settings['pointing_model'], 'sync')
                if not isinstance(skyconv.model_real_stepper, pointing_model.PointingModelBuie):
                    skyconv.model_real_stepper = pointing_model.PointingModelBuie()
                skyconv.model_real_stepper.clear()
                skyconv.model_real_stepper.add_point(coord, coord)
            else:  # affine model
                print('affine sync')
                if not isinstance(skyconv.model_real_stepper, pointing_model.PointingModelAffine):
                    skyconv.model_real_stepper = pointing_model.PointingModelAffine()
                coord = skyconv.hadec_to_altaz(coord, obstime=obstime)
                skyconv.model_real_stepper.clear()
                skyconv.model_real_stepper.add_point(coord, coord)


def slew(coord, parking=False):
    """
    Slews after going through model
    :param coord: RADec or AltAz astropy.coordinates or dictionary with
    :param parking: True if parking slew
    :return:
    """
    global cancel_slew
    if settings.runtime_settings is None or 'sync_info' not in settings.runtime_settings or \
            settings.runtime_settings['sync_info'] is None:
        raise NotSyncedException('Not Synced')
    settings.not_parked()
    cancel_slew = True
    thread = threading.Thread(target=move_to_coord_threadf, args=(coord, parking))
    thread.start()


def _move_to_coord_threadf(wanted_skycoord, axis='ra', parking=False, close_enough=0):
    steps = False
    if type(wanted_skycoord) is dict and 'ha' in wanted_skycoord:
        need_step_position = {'ha': wanted_skycoord['ha'], 'dec': wanted_skycoord['dec']}
        close_enough = 0
        steps = True
    else:
        need_step_position = skyconv.coord_to_steps(wanted_skycoord, atmo_refraction=True)
    count = 0
    close_timer = None
    while not cancel_slew:
        if close_timer is not None and (time.time() - close_timer) > 10.0:
            # For some reason we are never getting there
            break
        count += 1
        if not steps and count != 1 and not parking:
            need_step_position = skyconv.coord_to_steps(wanted_skycoord, atmo_refraction=True)
        status = calc_status(stepper.get_status())

        if axis == 'ra':
            delta = need_step_position['ha'] - status['rep']
            status_pos_key = 'rep'
        else:
            delta = need_step_position['dec'] - status['dep']
            status_pos_key = 'dep'

        if abs(round(delta)) <= 10.0*close_enough and close_timer is None:
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
            # Settling
            start = datetime.datetime.now()
            status = calc_status(stepper.get_status())
            target = status[status_pos_key] + delta
            if axis == 'ra':
                stepper.set_speed_ra(settle_speed)
            else:
                stepper.set_speed_dec(settle_speed)
            while abs(status[status_pos_key] - target) < close_enough:
                status = calc_status(stepper.get_status())
                time.sleep(0.1)
                if axis == 'ra' and not parking and settings.runtime_settings['tracking']:
                    target += (datetime.datetime.now() - start).total_seconds() * settings.settings['ra_track_rate']
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
                    settings.settings['ra_slew_fastest'],
                    v_track, 'ra')
            else:
                times = motion.calc_speed_sleeps(
                    delta,
                    settings.settings['micro']['dec_accel_tpss'],
                    status['ds'],
                    settings.settings['dec_slew_fastest'],
                    0, 'dec'
                )

            # print('dec_times', dec_times)

            for t in times:
                # print(t)
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

    ha_close_enough = 3.0
    ha_close_enough = 2.5 * settings.settings['ra_track_rate']
    dec_close_enough = 3.0

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

        status = stepper.get_status()
        while not math.isclose(status['rs'], rspeed, rel_tol=0.02) and math.isclose(status['ds'], 0, rel_tol=0.02):
            time.sleep(0.25)
            status = stepper.get_status()
    finally:
        if parking and not cancel_slew:
            settings.parked()
        else:
            settings.not_parked()
        if cancel_slew or type(wanted_skycoord) is dict and 'ha' in wanted_skycoord:
            set_last_slew(None)
        else:
            set_last_slew(wanted_skycoord)
        stepper.autoguide_enable()
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


def below_horizon_limit(altaz, radec):
    """
    If horizon limit is enabled and earth location is set, it will set if coordinates are below the horizon limits set.
    :param altaz: SkyCoord in altaz frame.
    :type altaz: astropy.coordinates.SkyCoord.
    :return: true if below horizon limit
    :rtype: bool
    """
    az = altaz.az.deg
    alt = altaz.alt.deg
    dec = radec.dec.deg
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


def slewtocheck(skycoord):
    """
    Check if skycoordinate okay to slew or is below horizon limit.
    :param skycoord:
    :type skycoord: astropy.coordinates.SkyCoord
    :return: true is okay to slew
    :rtype: bool
    """
    if skycoord is None:
        return False
    if hasattr(skycoord, 'ra'):
        altaz = skyconv.icrs_to_altaz(skycoord, atmo_refraction=True)
        radec = skycoord
    else:  # already AltAz
        altaz = skycoord
        radec = skyconv.altaz_to_icrs(skycoord, atmo_refraction=True)
    if below_horizon_limit(altaz, radec):
        return False
    else:
        return True


# We are going to sync based on altaz coordinates, this will be the default location if not set. We'll
# sync on pretend altaz locations.
DEFAULT_ELEVATION_M = 405.0
DEFAULT_LAT_DEG = 0
DEFAULT_LON_DEG = 0


def update_location():
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
        settings.runtime_settings['earth_location_set'] = False
        return
    if 'elevation' not in settings.settings['location']:
        elevation = DEFAULT_ELEVATION_M
    else:
        elevation = settings.settings['location']['elevation']
    el = EarthLocation(lat=settings.settings['location']['lat'] * u.deg,
                       lon=settings.settings['location']['long'] * u.deg,
                       height=elevation * u.m)
    settings.runtime_settings['earth_location_set'] = True
    settings.runtime_settings['earth_location'] = el
    if do_altaz_sync:
        set_sync(alt=alt, az=az)
    try:
        settings.runtime_settings['last_locationtz'] = TimezoneFinder().timezone_at(lng=el.lon.deg, lat=el.lat.deg)
    except:
        pass


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
    tempc = subprocess.run(['/usr/bin/vcgencmd', 'measure_temp'],
                           stdout=subprocess.PIPE).stdout.decode().strip().split('=')[1].split("'")[0]
    tempc = float(tempc)
    tempf = 32 + tempc * 9. / 5
    load_percent = psutil.cpu_percent()
    tot_m, used_m, free_m = map(int, os.popen('/usr/bin/free -t -m').readlines()[-1].split()[1:])
    memory_percent_usage = 100*float(used_m)/tot_m
    ret['tempc'] = tempc
    ret['tempf'] = tempf
    ret['load_percent'] = load_percent
    ret['memory_percent_usage'] = memory_percent_usage
    return ret


def send_status():
    """
    Sets last_status global and sends last_status to socket.
    :return:
    """
    import handpad_server
    global slewing, last_status, last_slew, cancel_slew, ra_encoder_error, dec_encoder_error
    status = calc_status(stepper.get_status())
    status['ra'] = None
    status['dec'] = None
    status['alt'] = None
    status['az'] = None
    status['hostname'] = socket.gethostname()
    status['started_parked'] = settings.runtime_settings['started_parked']
    status['time'] = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    st = skyconv.get_sidereal_time(earth_location=settings.runtime_settings['earth_location']).hms
    status['sidereal_time'] = '%02d:%02d:%02d' % (int(st.h), int(st.m), int(st.s))
    status['time_been_set'] = settings.runtime_settings['time_been_set']
    status['synced'] = settings.runtime_settings['sync_info'] is not None
    status['cpustats'] = get_cpustats()
    if not handpad_server.handpad_server:  #If server has not started yet
        status['handpad'] = False
    else:
        status['handpad'] = handpad_server.handpad_server.serial is not None
    if status['synced']:
        obstime = AstroTime.now()
        with set_last_slew_lock:
            if slewing or (settings.runtime_settings['tracking'] and not last_slew['radec']) or (
                    not settings.runtime_settings['tracking'] and not last_slew['altaz']):
                # TODO: If this takes a long time, we should do this in another thread and use the last time we did it.
                radec = skyconv.steps_to_coord({'ha': status['rep'], 'dec': status['dep']}, frame='icrs',
                                               obstime=obstime,
                                               atmo_refraction=True, inverse_model=True)
                # print('After steps_to_coord', radec)
                altaz = skyconv.icrs_to_altaz(radec, obstime=obstime, atmo_refraction=True)
                if not slewing:
                    set_last_slew(radec, obstime=obstime)
            else:
                # Use last slew data if tracking
                if settings.runtime_settings['tracking']:
                    radec = last_slew['radec']
                    altaz = skyconv.icrs_to_altaz(radec, obstime=obstime, atmo_refraction=True)
                else:
                    altaz = last_slew['altaz']
                    radec = skyconv.altaz_to_icrs(altaz, obstime=obstime, atmo_refraction=True)
        status['ra'] = radec.ra.deg
        status['dec'] = radec.dec.deg
        # print('earth_location', settings.runtime_settings['earth_location'])
        status['alt'] = altaz.alt.deg
        status['az'] = altaz.az.deg
        # if settings.runtime_settings['earth_location_set']:
        below_horizon = below_horizon_limit(altaz, radec)
        if below_horizon and settings.runtime_settings['tracking']:
            cancel_slew = True
            settings.runtime_settings['tracking'] = False
            stepper.set_speed_ra(0)
            set_last_slew(altaz, obstime=obstime)
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


# TMOVE: stepper_control
def micro_update_settings():
    """
    Updates microcontroller runtime values with what is in settings.
    """
    key_values = {'ra_max_tps': settings.settings['ra_slew_fastest'],
                  'ra_guide_rate': settings.settings['micro']['ra_guide_rate'],
                  'ra_direction': settings.settings['micro']['ra_direction'],
                  'dec_max_tps': settings.settings['dec_slew_fastest'],
                  'dec_guide_rate': settings.settings['micro']['dec_guide_rate'],
                  'dec_direction': settings.settings['micro']['dec_direction'],
                  'dec_disable': settings.settings['micro']['dec_disable'],
                  'ra_disable': settings.settings['micro']['ra_disable'],
                  'ra_accel_tpss': settings.settings['micro']['ra_accel_tpss'],
                  'dec_accel_tpss': settings.settings['micro']['dec_accel_tpss']}
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
    subprocess.run(['/usr/bin/sudo', '/bin/systemctl', 'stop', 'ntp'])
    # print('Inited')
    # Load settings file
    # Open serial port
    stepper = stepper_control.StepperControl(settings.settings['microserial']['port'],
                                             settings.settings['microserial']['baud'])
    skyconv.model_real_stepper = pointing_model.PointingModelBuie()
    #TODO: Lets get time/location from GPS if we can
    update_location()
    micro_update_settings()

    if settings.settings['park_position'] and settings.runtime_settings['earth_location_set'] and \
            settings.last_parked():
        settings.runtime_settings['started_parked'] = True
        coord = SkyCoord(alt=settings.settings['park_position']['alt'] * u.deg,
                         az=settings.settings['park_position']['az'] * u.deg, frame='altaz',
                         obstime=AstroTime.now(),
                         location=settings.runtime_settings['earth_location']).icrs
    elif settings.settings['park_position']:
        coord = SkyCoord(alt=settings.settings['park_position']['alt'] * u.deg,
                         az=settings.settings['park_position']['az'] * u.deg, frame='altaz',
                         obstime=AstroTime.now(),
                         location=settings.runtime_settings['earth_location']).icrs
    else:
        coord = SkyCoord(alt=DEFAULT_PARK['alt'] * u.deg,
                         az=DEFAULT_PARK['az'] * u.deg, frame='altaz',
                         obstime=AstroTime.now(),
                         location=settings.runtime_settings['earth_location']).icrs
    settings.not_parked()
    sync(coord)
    park_sync = True
    send_status()
    status_interval = SimpleInterval(send_status, 1)
    SimpleInterval(alive_check, 3)
    ntpthread = threading.Thread(target=ntp_syncer)
    ntpthread.start()
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
            stepper.set_speed_dec(status['ds'] + settings.settings['micro']['dec_guide_rate'])
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_dec, status['ds']))
        elif direction == 's':
            stepper.set_speed_dec(status['ds'] - settings.settings['micro']['dec_guide_rate'])
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_dec, status['ds']))
        elif direction == 'w':
            stepper.set_speed_ra(status['rs'] + settings.settings['micro']['ra_guide_rate'])
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_ra, status['rs']))
        elif direction == 'e':
            stepper.set_speed_ra(status['rs'] - settings.settings['micro']['ra_guide_rate'])
            threading.Timer(time_ms / 1000.0, partial(stepper.set_speed_ra, status['rs']))
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
                    stepper.set_speed_ra(-1.0 * settings.settings['ra_slew_' + speed])
                elif direction == 'right':
                    stepper.set_speed_ra(settings.settings['ra_slew_' + speed])
                elif direction == 'up':
                    stepper.set_speed_dec(settings.settings['dec_slew_' + speed])
                elif direction == 'down':
                    stepper.set_speed_dec(-settings.settings['dec_slew_' + speed])
                # We call this periodically if not alive it will cancel the slewing, if alive it will continue at
                # speed we are at.
                timers[direction] = threading.Timer(1, partial(manual_control, direction, speed, client_id))
                timers[direction].start()
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


def clear_sync():
    """
    Clears sync_info and sync points.
    """
    global park_sync
    if settings.runtime_settings['tracking']:
        scord = SkyCoord(ra=last_status['ra'] * u.deg, dec=last_status['dec'] * u.deg, frame='icrs')
    else:
        scord = SkyCoord(alt=last_status['alt'] * u.deg, az=last_status['az'] * u.deg, frame='altaz')
    pointing_logger.debug(json.dumps({'func': 'control.clear_sync'}))
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
    set_last_slew(last_slew['radec'])


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
    if not settings.settings['park_position']:
        coord = SkyCoord(alt=DEFAULT_PARK['alt'] * u.deg,
                         az=DEFAULT_PARK['az'] * u.deg, frame='altaz')
    else:
        coord = SkyCoord(alt=settings.settings['park_position']['alt'] * u.deg,
                         az=settings.settings['park_position']['az'] * u.deg, frame='altaz')
    slew(coord, parking=True)


def ntp_syncer():
    # If ntp changes the time after init, we'll sync to last alt,az position
    # Detect this by having a jump in time
    alt = last_status['alt']
    az = last_status['az']
    ntpstat = subprocess.run(['/usr/bin/ntpstat'])
    if ntpstat.returncode == 0:
        return
    now = datetime.datetime.now()
    lastnow = datetime.datetime.now()
    while (now-lastnow).total_seconds() < 3600:
        alt = last_status['alt']
        az = last_status['az']
        lastnow = now
        time.sleep(1)
        now = datetime.datetime.now()
    set_sync(alt=alt, az=az)


def set_time(iso_timestr):
    """
    Try to set the system time
    :param iso_timestr:
    :type iso_timestr: str
    :return: bool, status_str  True if it set date or didn't need to set date, false if failed. status_str is info
    about what it did.
    """
    # if runtime_settings['time_been_set'] and not overwrite:
    #    return 'Already Set', 200
    s = datetime.datetime.now()
    d = pendulum.parse(iso_timestr)
    if settings.is_simulation():
        settings.runtime_settings['time_been_set'] = True
        return True, 'Date Set'
    ntpstat = subprocess.run(['/usr/bin/ntpstat'])
    if ntpstat.returncode != 0:
        send_status()
        alt = last_status['alt']
        az = last_status['az']
        d = d + (datetime.datetime.now() - s)
        time_s = d.isoformat()
        daterun = subprocess.run(['/usr/bin/sudo', '/bin/date', '-s', time_s])
        set_sync(alt=alt, az=az)
        if daterun.returncode == 0:
            settings.runtime_settings['time_been_set'] = True
            return True, 'Date Set'
        else:
            return False, 'Failed to set date'
    settings.runtime_settings['time_been_set'] = True
    return True, 'NTP Set'


def set_location(lat, long, elevation, name):
    """
    Set the mount earth location.
    :param lat: Latitude in degrees
    :type lat: float
    :param long: Longitude in degrees
    :type long: float
    :param elevation: Elevation in meters
    :type elevation: float
    :param name: Name to set location as.
    :type name: str
    :return: None
    """
    location = {'lat': lat, 'long': long, 'elevation': elevation, 'name': name}
    old_location = settings.settings['location']
    settings.settings['location'] = location
    try:
        update_location()
    except Exception as e:
        settings.settings['location'] = old_location
        traceback.print_exc(file=sys.stdout)
        raise
    settings.write_settings(settings.settings)


def set_sync(ra=None, dec=None, alt=None, az=None):
    """
    Sync the mount to coordinates using ra-dec or alt-az.
    :param ra: RA in degrees
    :type ra: float
    :param dec: DEC in degrees
    :type dec: float
    :param alt: deg
    :param az: deg
    :return:
    """
    if alt is not None and az is not None:
        coord = SkyCoord(alt=alt * u.deg, az=az * u.deg, frame='altaz')
    elif ra is not None and dec is not None:
        coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    else:
        raise Exception('Missing Coordinates')
    if settings.runtime_settings['calibration_logging'] and len(calibration_log) > 0:
        calibration_log[-1]['sync'] = coord
    sync(coord)
    return skyconv.model_real_stepper.size()


def set_slew(ra=None, dec=None, alt=None, az=None, ra_steps=None, dec_steps=None, parking=False):
    """
    Slew to ra-dec, alt-az or, ra_steps-dec_steps.
    :param ra: RA in degrees
    :param dec: DEC in degrees
    :param alt: Altitude in degrees
    :param az: Azimuth in degrees
    :param ra_steps: RA Stepper steps
    :type ra_steps: int
    :param dec_steps: DEC Stepper steps
    :type dec_steps: int
    :param parking: True if parking slew
    :type parking: bool
    :return:
    """
    if ra_steps is not None and dec_steps is not None:
        slew({'ha': ra_steps, 'dec': dec_steps})
        return
    elif alt is not None and az is not None:
        coord = SkyCoord(alt=float(alt) * u.deg, az=float(az) * u.deg, frame='altaz')
    else:
        ra = float(ra)
        dec = float(dec)
        coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    if not slewtocheck(coord):
        # print('NNNNNNNNNNNNNNNNNNNNNNNOOOOOOOOOOOOOOOOOTTTT')
        raise Exception('Slew position is below horizon or in keep-out area.')
    else:
        if settings.runtime_settings['calibration_logging']:
            calibration_log.append({
                'slewfrom': SkyCoord(ra=last_status['ra']*u.deg, dec=last_status['dec']*u.deg, frame='icrs'),
                'slewto': coord})
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
        coord = SkyCoord(ra=last_status['ra'] * u.deg, dec=last_status['dec'] * u.deg, frame='icrs')
        altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
        settings.settings['park_position'] = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
    else:
        settings.settings['park_position'] = {'alt': last_status['alt'], 'az': last_status['az']}
    settings.write_settings(settings.settings)
