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

import skyconv

import settings

version = "0.0.17"
version_short = "0.0"
version_date_str = "Jun 21 2019"

SIDEREAL_RATE = 0.004178074568511751  # 15.041"/s
AXIS_RA = 1
AXIS_DEC = 2

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
DEFAULT_PARK = {'alt': 180, 'az': 10}
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

# Last sync or slew info, if tracking sets radec, else altaz.
last_slew = {'radec': None, 'altaz': None}

pointing_logger = settings.get_logger('pointing')


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


def sync(coord):
    """
    :param coord:
    :return:
    """
    global park_sync
    status = calc_status(stepper.get_status())
    obstime = AstroTime.now()
    set_last_slew(coord, obstime=obstime)
    if hasattr(coord, 'ra'):
        coord = skyconv.icrs_to_hadec(coord, obstime=obstime, atmo_refraction=True)
    elif hasattr(coord, 'alt'):
        coord = skyconv.altaz_to_icrs(coord, obstime=obstime, atmo_refraction=False)
        coord = skyconv.icrs_to_hadec(coord, obstime=obstime, atmo_refraction=False)

    if settings.settings['pointing_model'] != 'single' and not park_sync and skyconv.model_real_stepper and \
            skyconv.model_real_stepper.size() > 0:
        stepper_coord = skyconv.steps_to_coord({'ha': status['rep'], 'dec': status['dep']},
                                               frame=skyconv.model_real_stepper.frame(), obstime=obstime)
        if skyconv.model_real_stepper.frame() == 'hadec':
            model_real_stepper.add_point(coord, stepper_coord)
        else:  # AltAz model frame
            coord = skyconv.hadec_to_altaz(coord, obstime=obstime)
            model_real_stepper.add_point(coord, stepper_coord)
    else:
        park_sync = False
        sync_info = {'steps': {'ha': status['rep'], 'dec': status['dep']}, 'coord': coord}
        settings.runtime_settings['sync_info'] = sync_info
        if settings.settings['pointing_model'] in ['single', 'buie']:
            if not isinstance(skyconv.model_real_stepper, pointing_model.PointingModelBuie):
                skyconv.model_real_stepper = pointing_model.PointingModelBuie()
            skyconv.model_real_stepper.clear()
            skyconv.model_real_stepper.add_point(coord, coord)
        else:  # affine model
            if not isinstance(skyconv.model_real_stepper, pointing_model.PointingModelAffine):
                skyconv.model_real_stepper = pointing_model.PointingModelBuie()
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


def move_to_coord_threadf(wanted_skycoord, parking=False):
    global cancel_slew, slewing
    # sleep_time must be < 1
    sleep_time = 0.1
    loops_to_full_speed = 10.0

    ha_close_enough = 3.0
    dec_close_enough = 3.0

    data = {'time': [], 'rpv': [], 'dpv': [], 'rsp': [], 'dsp': [], 'rv': [], 'dv': [], 'era': [], 'edec': []}

    try:
        slew_lock.acquire()
        stepper.autoguide_disable()
        slewing = True
        cancel_slew = False
        if type(wanted_skycoord) is dict and 'ha' in wanted_skycoord:
            need_step_position = {'ha': wanted_skycoord['ha'], 'dec': wanted_skycoord['dec']}
            ha_close_enough = 0
            dec_close_enough = 0
        else:
            need_step_position = skyconv.coord_to_steps(wanted_skycoord, atmo_refraction=True)
        last_datetime = datetime.datetime.now()
        started_slewing = last_datetime
        total_time = 0.0
        first = True
        while not cancel_slew:
            if not parking:
                need_step_position = skyconv.coord_to_steps(wanted_skycoord, atmo_refraction=True)
            now = datetime.datetime.now()
            status = calc_status(stepper.get_status())
            if first:
                dt = sleep_time
                first = False
            else:
                dt = (now - last_datetime).total_seconds()
            last_datetime = now
            total_time += dt

            ra_delta = need_step_position['ha'] - status['rep']
            dec_delta = need_step_position['dec'] - status['dep']
            # print(ra_delta, dec_delta)
            if abs(round(ra_delta)) <= ha_close_enough and abs(round(dec_delta)) <= dec_close_enough:
                break

            if abs(ra_delta) <= ha_close_enough:
                if not parking and settings.runtime_settings['tracking']:
                    ra_speed = settings.settings['ra_track_rate']
                else:
                    ra_speed = 0
            elif abs(ra_delta) < 4 * math.ceil(settings.settings['ra_track_rate']):
                if not parking and settings.runtime_settings['tracking']:
                    # ra_speed = settings.settings['ra_track_rate'] + ((1.0-sleep_time)/sleep_time) * ra_delta
                    ra_speed = settings.settings['ra_track_rate'] + ra_delta / dt
                else:
                    # ra_speed = ((1.0-sleep_time)/sleep_time) * ra_delta
                    ra_speed = ra_delta / dt
            elif abs(ra_delta) < settings.settings['ra_slew_fastest'] / 2.0:
                if not parking and settings.runtime_settings['tracking']:
                    ra_speed = settings.settings['ra_track_rate'] + 2.0 * ra_delta
                else:
                    ra_speed = 2.0 * ra_delta
                # Short slew otherwise we are slowing down
                if abs(ra_speed) > abs(status['rs']):
                    ra_speed = status['rs'] + ra_speed / loops_to_full_speed
                    if abs(ra_speed) > abs(status['rs']):
                        ra_speed = ra_delta
                        # speed = ((1.0-sleep_time)/sleep_time) * ra_delta
                        # speed2 = math.copysign(settings.settings['ra_slew_fastest']*(1.0-sleep_time), ra_delta)
                        # if abs(speed2) < abs(speed):
                        #     speed = speed2
                        # ra_speed = speed
            else:
                speed = (total_time ** 2.0) * math.copysign(settings.settings['ra_slew_fastest'] / 9.0, ra_delta)
                if abs(speed) > settings.settings['ra_slew_fastest']:
                    speed = math.copysign(settings.settings['ra_slew_fastest'], ra_delta)
                ra_speed = speed

            if abs(dec_delta) < dec_close_enough:
                dec_speed = 0.0
            # In case model has dec constantly moving.
            elif abs(dec_delta) < 4 * settings.settings['dec_ticks_per_degree'] * SIDEREAL_RATE:
                dec_speed = dec_delta / dt
            elif abs(dec_delta) < settings.settings['dec_slew_fastest'] / 2.0:
                dec_speed = dec_delta * 2.0
                if abs(dec_speed) > abs(status['ds']):
                    dec_speed = status['ds'] + dec_speed / loops_to_full_speed
                    if abs(dec_speed) > abs(status['ds']):
                        dec_speed = dec_delta

                        # speed = ((1.0-sleep_time)/sleep_time) * dec_delta
                        # speed2 = math.copysign(settings.settings['dec_slew_fastest'] * (1.0-sleep_time), dec_delta)
                        # if abs(speed2) < abs(speed):
                        #    speed = speed2
                        # dec_speed = speed
            else:
                speed = status['ds'] + math.copysign(settings.settings['dec_slew_fastest'] / loops_to_full_speed,
                                                     dec_delta)
                if abs(speed) > settings.settings['dec_slew_fastest']:
                    speed = math.copysign(settings.settings['dec_slew_fastest'], dec_delta)
                dec_speed = speed

            if not math.isclose(status['rs'], ra_speed, rel_tol=0.02):
                stepper.set_speed_ra(ra_speed)
            if not math.isclose(status['ds'], dec_speed, rel_tol=0.02):
                stepper.set_speed_dec(dec_speed)

            data['time'].append((now - started_slewing).total_seconds())
            data['rpv'].append(status['rep'])
            data['dpv'].append(status['dep'])
            data['rsp'].append(need_step_position['ha'])
            data['dsp'].append(need_step_position['dec'])
            data['rv'].append(ra_speed)
            data['dv'].append(dec_speed)
            data['era'].append(need_step_position['ha'] - status['rep'])
            data['edec'].append(need_step_position['dec'] - status['dep'])

            time.sleep(sleep_time)

        if settings.runtime_settings['tracking']:
            stepper.set_speed_ra(settings.settings['ra_track_rate'])
        else:
            stepper.set_speed_ra(0)
        stepper.set_speed_dec(0.0)
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


def below_horizon_limit(altaz):
    """
    If horizon limit is enabled and earth location is set, it will set if coordinates are below the horizon limits set.
    :param altaz: SkyCoord in altaz frame.
    :type altaz: astropy.coordinates.SkyCoord.
    :return: true if below horizon limit
    :rtype: bool
    """
    az = altaz.az.deg
    alt = altaz.alt.deg
    if settings.settings['horizon_limit_enabled'] and 'horizon_limit_points' in settings.settings and \
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
    :return: true not slewing to a limit
    :rtype: bool
    """
    if skycoord is None:
        return False
    if hasattr(skycoord, 'ra'):
        altaz = skyconv.icrs_to_altaz(skycoord, atmo_refraction=True)
    else:  # already AltAz
        altaz = skycoord
    if below_horizon_limit(altaz):
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


def calc_status(status):
    """
    Takes re (ra encoder count), ri (ra steps between encoder), rp (ra step counts) to make a authoritative rep
    count based on settings.
    :param status: Should have keys ri, re, rp, di, de, dp
    :rtype status: dict
    :return: Updates status but also returns it.
    """
    if settings.settings['use_encoders']:
        ra_steps_per_encoder = settings.settings['ra_ticks_per_degree'] / settings.settings[
            'ra_encoder_pulse_per_degree']
        dec_steps_per_encoder = settings.settings['dec_ticks_per_degree'] / settings.settings[
            'dec_encoder_pulse_per_degree']
        ri = status['ri']
        di = status['di']
        if settings.settings['limit_encoder_step_fillin']:
            if abs(status['ri']) > ra_steps_per_encoder:
                ri = int(ra_steps_per_encoder)
            if abs(status['di']) > dec_steps_per_encoder:
                di = int(dec_steps_per_encoder)
        rep = status['re'] * ra_steps_per_encoder + ri
        dep = status['de'] * dec_steps_per_encoder + di
    else:
        rep = status['rp']
        dep = status['dp']
    status['rep'] = rep
    status['dep'] = dep
    return status


def send_status():
    """
    Sets last_status global and sends last_status to socket.
    :return:
    """
    global slewing, last_status, last_slew
    status = calc_status(stepper.get_status())
    status['ra'] = None
    status['dec'] = None
    status['alt'] = None
    status['az'] = None
    status['hostname'] = socket.gethostname()
    status['started_parked'] = settings.runtime_settings['started_parked']
    status['time'] = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    status['time_been_set'] = settings.runtime_settings['time_been_set']
    status['synced'] = settings.runtime_settings['sync_info'] is not None
    if status['synced']:
        obstime = AstroTime.now()
        with set_last_slew_lock:
            if slewing or (settings.runtime_settings['tracking'] and not last_slew['radec']) or (
                    not settings.runtime_settings['tracking'] and not last_slew['altaz']):
                # TODO: If this takes a long time, we should do this in another thread and use the last time we did it.
                radec = skyconv.steps_to_coord({'ha': status['rep'], 'dec': status['dep']}, frame='icrs',
                                               obstime=obstime,
                                               atmo_refraction=True, inverse_model=True)
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
        below_horizon = below_horizon_limit(altaz)
        if below_horizon and settings.runtime_settings['tracking']:
            settings.runtime_settings['tracking'] = False
            stepper.set_speed_ra(0)
            set_last_slew(altaz, obstime=obstime)
            status['alert'] = 'In horizon limit, tracking stopped'
        # print(altaz)
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
                  'dec_direction': settings.settings['micro']['dec_direction']}
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
    global stepper, status_interval, inited, park_sync, model_real_stepper
    if inited:
        return
    inited = True
    # print('Inited')
    # Load settings file
    # Open serial port
    stepper = stepper_control.StepperControl(settings.settings['microserial']['port'],
                                             settings.settings['microserial']['baud'])
    model_real_stepper = pointing_model.PointingModelBuie()
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
    status_interval = SimpleInterval(send_status, 1)


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


def manual_control(direction, speed, persistant=False):
    global slew_lock, manual_lock
    # print('manual_control', direction, speed)
    settings.not_parked()
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
            if not speed:
                if direction in ['left', 'right']:
                    done = False
                    status = calc_status(stepper.get_status())
                    # print(status)
                    if (settings.runtime_settings['tracking'] and status['rs'] != settings.settings['ra_track_rate']) or \
                            status['rs'] != 0:
                        sspeed = status['rs'] - math.copysign(settings.settings['ra_slew_fastest'] / 10.0,
                                                              status['rs'])
                        if status['rs'] == 0 or abs(sspeed) < settings.settings['ra_track_rate'] or \
                                sspeed / status['rs'] < 0:
                            if settings.runtime_settings['tracking']:
                                sspeed = settings.settings['ra_track_rate']
                            else:
                                sspeed = 0
                            done = True
                        # print(sspeed)
                        stepper.set_speed_ra(sspeed)
                    else:
                        done = True
                    if not done:
                        # print('timer')
                        timers[direction] = threading.Timer(0.1, partial(manual_control, direction, None))
                        timers[direction].start()
                else:
                    done = False
                    status = calc_status(stepper.get_status())
                    if status['ds'] != 0:
                        # print(status)
                        sspeed = status['ds'] - math.copysign(settings.settings['dec_slew_fastest'] / 10.0,
                                                              status['ds'])
                        if status['ds'] == 0 or sspeed / status['ds'] < 0:
                            sspeed = 0
                            done = True
                        # print(sspeed)
                        stepper.set_speed_dec(sspeed)
                    else:
                        done = True
                    if not done:
                        timers[direction] = threading.Timer(0.1, partial(manual_control, direction, None))
                        timers[direction].start()
            else:
                # If not current manually going other direction
                status = calc_status(stepper.get_status())
                # print(status)
                if OPPOSITE_MANUAL[direction] in timers:
                    return
                if direction == 'left':
                    sspeed = status['rs'] - settings.settings['ra_slew_' + speed] / 10.0
                    # print('ra_slew_'+speed, settings.settings['ra_slew_'+speed]/10.0)
                    if abs(sspeed) > settings.settings['ra_slew_' + speed]:
                        sspeed = -settings.settings['ra_slew_' + speed]
                    # print(sspeed)
                    stepper.set_speed_ra(sspeed)
                elif direction == 'right':
                    sspeed = status['rs'] + settings.settings['ra_slew_' + speed] / 10.0
                    if abs(sspeed) > settings.settings['ra_slew_' + speed]:
                        sspeed = settings.settings['ra_slew_' + speed]
                    # print(sspeed)
                    stepper.set_speed_ra(sspeed)
                elif direction == 'up':
                    # print('--------------- dec up %.1f' % settings.settings['dec_slew_' + speed])
                    sspeed = status['ds'] + settings.settings['dec_slew_' + speed] / 10.0
                    if abs(sspeed) > settings.settings['dec_slew_' + speed]:
                        sspeed = settings.settings['dec_slew_' + speed]
                    # print(sspeed)
                    stepper.set_speed_dec(sspeed)
                elif direction == 'down':
                    sspeed = status['ds'] - settings.settings['dec_slew_' + speed] / 10.0
                    if abs(sspeed) > settings.settings['dec_slew_' + speed]:
                        sspeed = -settings.settings['dec_slew_' + speed]
                    # print('--------------- dec down -%.1f' % settings.settings['dec_slew_' + speed])
                    # print(sspeed)
                    stepper.set_speed_dec(sspeed)
                if not persistant:
                    timers[direction] = threading.Timer(0.5, partial(manual_control, direction, None))
                    timers[direction].start()
        finally:
            set_last_slew(None)
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
        d = d + (datetime.datetime.now() - s)
        time_s = d.isoformat()
        daterun = subprocess.run(['/usr/bin/sudo', '/bin/date', '-s', time_s])
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
        print(e)
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
        return Exception('Slew position is below horizon or in keep-out area.')
    else:
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
