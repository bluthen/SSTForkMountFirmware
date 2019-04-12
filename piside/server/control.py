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

from sstutil import ProfileTimer as PT

import datetime
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, ICRS
from astropy.time import Time as AstroTime
import astropy.units as u
import astropy.units.si as usi
import math
import socket
import json
import stepper_control
import pointing_model

import settings

SIDEREAL_RATE = 0.004178074568511751  # 15.041"/s
AXIS_RA = 1
AXIS_DEC = 2

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
slew_lock = threading.RLock()
manual_lock = threading.RLock()
status_interval = None
socketio = None
inited = False
runtime_settings = None
slewing = False
stepper = None

park_sync = False

cancel_slew = False
last_status = None

pm_real_stepper = None
pm_stepper_real = None

pointing_logger = settings.get_logger('pointing')


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
        altaz = convert_to_altaz(skycoord)
    elif hasattr(skycoord, 'alt'):
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
    # print(settings.settings['location'])
    if 'location' not in settings.settings or not settings.settings['location'] or \
            not settings.settings['location']['lat']:
        runtime_settings['earth_location'] = EarthLocation(lat=DEFAULT_LAT_DEG * u.deg, lon=DEFAULT_LON_DEG * u.deg,
                                                           height=DEFAULT_ELEVATION_M * u.m)
        runtime_settings['earth_location_set'] = False
        return
    if 'elevation' not in settings.settings['location']:
        elevation = DEFAULT_ELEVATION_M
    else:
        elevation = settings.settings['location']['elevation']
    el = EarthLocation(lat=settings.settings['location']['lat'] * u.deg,
                       lon=settings.settings['location']['long'] * u.deg,
                       height=elevation * u.m)
    runtime_settings['earth_location_set'] = True
    runtime_settings['earth_location'] = el


def convert_to_altaz(coord, earth_location=None, obstime=None, atmo_refraction=False):
    """
    Convert a skycoordinate to altaz frame.
    :param coord: The coordinates you would want to covert to altaz, probably icrs frame.
    :type coord: astropy.coordinates.SkyCoord
    :param earth_location: Location to base altaz on, defaults runtime_settings['earth_location']
    :type earth_location: astropy.coordinates.EarthLocation
    :param obstime: The observation time to get altaz coordinates, defaults to astropy.time.Time.now()
    :type obstime: astropy.time.Time
    :param atmo_refraction: if should adjust for atmospheric refraction
    :type atmo_refraction: bool
    :return: SkyCoord in altaz or None if unable to compute (missing earth_location)
    :rtype: astropy.coordinates.SkyCoord
    :Example:
        >>> import control
        >>> from astropy.coordinates import EarthLocation, SkyCoord
        >>> import astropy.units as u
        >>> from astropy.time import Time
        >>> t = Time('2018-12-26T22:55:32.281', format='isot', scale='utc')
        >>> earth_location = EarthLocation(lat=38.9369*u.deg, lon= -95.242*u.deg, height=266.0*u.m)
        >>> radec = SkyCoord(ra=30*u.deg, dec=45*u.deg, frame='icrs')
        >>> altaz = control.convert_to_altaz(radec, earth_location, t)
        >>> altaz.alt.deg, altaz.az.deg
        (55.558034184006516, 64.41850865846912)
    """
    if obstime is None:
        obstime = AstroTime.now()
    if earth_location is None:
        earth_location = runtime_settings['earth_location']
    if earth_location is not None:
        pressure = None
        if atmo_refraction and runtime_settings['earth_location_set']:
            pressure = earth_location_to_pressure(earth_location)
        altaz = coord.transform_to(AltAz(obstime=obstime, location=earth_location, pressure=pressure))
        return altaz
    else:
        return None


def clean_altaz(altaz):
    return SkyCoord(alt=altaz.alt.deg * u.deg, az=altaz.az.deg * u.deg, frame='altaz')


def send_status():
    global slewing, last_status
    status = stepper.get_status()
    status['ra'] = None
    status['dec'] = None
    status['alt'] = None
    status['az'] = None
    status['hostname'] = socket.gethostname()
    status['time'] = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    status['time_been_set'] = runtime_settings['time_been_set']
    status['synced'] = runtime_settings['sync_info'] is not None
    if status['synced']:
        coord = steps_to_skycoord(runtime_settings['sync_info'], {'ra': status['rp'], 'dec': status['dp']},
                                  AstroTime.now(), settings.settings['ra_ticks_per_degree'],
                                  settings.settings['dec_ticks_per_degree'])
        stepper_altaz = convert_to_altaz(coord, atmo_refraction=False)
        stepper_altaz = clean_altaz(stepper_altaz)
        real_altaz = pm_stepper_real.transform_point(stepper_altaz)
        radec = convert_to_icrs(real_altaz, atmo_refraction=settings.settings['atmos_refract'])

        status['ra'] = radec.ra.deg
        status['dec'] = radec.dec.deg
        # print('earth_location', runtime_settings['earth_location'])
        status['alt'] = None
        status['az'] = None
        if runtime_settings['earth_location_set']:
            altaz = real_altaz
            below_horizon = below_horizon_limit(altaz)
            if below_horizon and runtime_settings['tracking']:
                runtime_settings['tracking'] = False
                stepper.set_speed_ra(0)
                status['alert'] = 'In horizon limit, tracking stopped'
            # print(altaz)
            status['alt'] = altaz.alt.deg
            status['az'] = altaz.az.deg
    status['slewing'] = slewing
    status['tracking'] = runtime_settings['tracking']
    last_status = status
    socketio.emit('status', status)


# TMOVE: stepper_control
def micro_update_settings():
    key_values = {'ra_max_tps': settings.settings['ra_slew_fastest'],
                  'ra_guide_rate': settings.settings['micro']['ra_guide_rate'],
                  'ra_direction': settings.settings['micro']['ra_direction'],
                  'dec_max_tps': settings.settings['dec_slew_fastest'],
                  'dec_guide_rate': settings.settings['micro']['dec_guide_rate'],
                  'dec_direction': settings.settings['micro']['dec_direction']}
    stepper.update_settings(key_values)
    if runtime_settings['tracking']:
        stepper.set_speed_ra(settings.settings['ra_track_rate'])
    else:
        stepper.set_speed_ra(0)
    stepper.set_speed_dec(0)


def init(osocketio, fruntime_settings):
    global stepper, status_interval, socketio, inited, runtime_settings, pm_real_stepper, pm_stepper_real, park_sync
    if inited:
        return
    inited = True
    # print('Inited')
    runtime_settings = fruntime_settings
    socketio = osocketio
    # Load settings file
    # Open serial port
    stepper = stepper_control.StepperControl(settings.settings['microserial']['port'],
                                             settings.settings['microserial']['baud'])
    pm_real_stepper = pointing_model.PointingModel(True, 'pm_real_stepper')
    pm_stepper_real = pointing_model.PointingModel()
    update_location()
    if settings.settings['park_position'] and runtime_settings['earth_location_set'] and settings.last_parked():
        settings.not_parked()
        coord = SkyCoord(alt=settings.settings['park_position']['alt'] * u.deg,
                         az=settings.settings['park_position']['az'] * u.deg, frame='altaz',
                         obstime=AstroTime.now(),
                         location=runtime_settings['earth_location']).icrs
        sync(coord)
        park_sync = True
    settings.not_parked()
    micro_update_settings()
    status_interval = SimpleInterval(send_status, 1)


def manual_control(direction, speed):
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
                    status = stepper.get_status()
                    # print(status)
                    if (runtime_settings['tracking'] and status['rs'] != settings.settings['ra_track_rate']) or \
                            status['rs'] != 0:
                        sspeed = status['rs'] - math.copysign(settings.settings['ra_slew_fastest'] / 10.0,
                                                              status['rs'])
                        if status['rs'] == 0 or abs(sspeed) < settings.settings['ra_track_rate'] or \
                                sspeed / status['rs'] < 0:
                            if runtime_settings['tracking']:
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
                    status = stepper.get_status()
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
                status = stepper.get_status()
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
                timers[direction] = threading.Timer(0.5, partial(manual_control, direction, None))
                timers[direction].start()
        finally:
            slew_lock.release()


# TMOVE: stepper_control
def move_to_skycoord_threadf(sync_info, wanted_skycoord, parking=False):
    global cancel_slew, slewing
    # sleep_time must be < 1
    sleep_time = 0.1
    loops_to_full_speed = 10.0

    ra_close_enough = 3.0
    dec_close_enough = 3.0

    data = {'time': [], 'rpv': [], 'dpv': [], 'rsp': [], 'dsp': [], 'rv': [], 'dv': [], 'era': [], 'edec': []}

    try:
        slew_lock.acquire()
        stepper.autoguide_disable()
        slewing = True
        cancel_slew = False
        if type(wanted_skycoord) is dict and 'ra_steps' in wanted_skycoord:
            need_step_position = {'ra': wanted_skycoord['ra_steps'], 'dec': wanted_skycoord['dec_steps']}
            ra_close_enough = 0
            dec_close_enough = 0
        else:
            need_step_position = skycoord_to_steps(sync_info, wanted_skycoord, AstroTime.now(),
                                                   settings.settings['ra_ticks_per_degree'],
                                                   settings.settings['dec_ticks_per_degree'])
        last_datetime = datetime.datetime.now()
        started_slewing = last_datetime
        total_time = 0.0
        first = True
        while not cancel_slew:
            if not parking:
                need_step_position = skycoord_to_steps(sync_info, wanted_skycoord, AstroTime.now(),
                                                       settings.settings['ra_ticks_per_degree'],
                                                       settings.settings['dec_ticks_per_degree'])
            now = datetime.datetime.now()
            status = stepper.get_status()
            if first:
                dt = sleep_time
                first = False
            else:
                dt = (now - last_datetime).total_seconds()
            last_datetime = now
            total_time += dt

            ra_delta = need_step_position['ra'] - status['rp']
            dec_delta = need_step_position['dec'] - status['dp']
            # print(ra_delta, dec_delta)
            if abs(round(ra_delta)) <= ra_close_enough and abs(round(dec_delta)) <= dec_close_enough:
                break

            if abs(ra_delta) < math.ceil(settings.settings['ra_track_rate']):
                if not parking and runtime_settings['tracking']:
                    # ra_speed = settings.settings['ra_track_rate'] + ((1.0-sleep_time)/sleep_time) * ra_delta
                    ra_speed = settings.settings['ra_track_rate'] + ra_delta / dt
                else:
                    # ra_speed = ((1.0-sleep_time)/sleep_time) * ra_delta
                    ra_speed = ra_delta / dt
            elif abs(ra_delta) < settings.settings['ra_slew_fastest'] / 2.0:
                if not parking and runtime_settings['tracking']:
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
            data['rpv'].append(status['rp'])
            data['dpv'].append(status['dp'])
            data['rsp'].append(need_step_position['ra'])
            data['dsp'].append(need_step_position['dec'])
            data['rv'].append(ra_speed)
            data['dv'].append(dec_speed)
            data['era'].append(need_step_position['ra'] - status['rp'])
            data['edec'].append(need_step_position['dec'] - status['dp'])

            time.sleep(sleep_time)

        if runtime_settings['tracking']:
            stepper.set_speed_ra(settings.settings['ra_track_rate'])
        else:
            stepper.set_speed_ra(0)
        stepper.set_speed_dec(0.0)
    finally:
        if parking and not cancel_slew:
            settings.parked()
        else:
            settings.not_parked()
        stepper.autoguide_enable()
        slewing = False
        slew_lock.release()


class NotSyncedException(Exception):
    pass


def earth_location_to_pressure(earth_location=None):
    """
    Gives you expected absolute pressure at elevation.
    :param earth_location: astropy.coordinates.EarthLocation defaults to runtime_settings['earth_location']
    :return: pressure astropy.units.Quantity
    :Example:
        >>> import control
        >>> from astropy.coordinates import EarthLocation
        >>> import astropy.units as u
        >>> from astropy.units import si as usi
        >>> earth_location = EarthLocation(lat=38.9369*u.deg, lon= -95.242*u.deg, height=266.0*u.m)
        >>> control.earth_location_to_pressure(earth_location).to_value(usi.Pa)
        98170.13549856932
    """
    if earth_location is None:
        earth_location = runtime_settings['earth_location']
    height = earth_location.height.to_value(u.m)
    # https://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
    return 101325.0 * ((1.0 - 2.2557e-5 * height) ** 5.25588) * usi.Pa


# TMOVE: stepper_control
def slew_to_steps(ra_steps, dec_steps):
    """

    :param ra_steps: steps
    :param dec_steps: steps
    :return:
    """
    wanted_skycoord = {'ra_steps': ra_steps, 'dec_steps': dec_steps}
    move_to_skycoord(runtime_settings['sync_info'], wanted_skycoord, True)


# TMOVE: stepper_control
def move_to_skycoord(sync_info, wanted_skycoord, parking=False):
    """
    Slew to position
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord,
    'steps': {'ra': int, 'dec': int}
    :param wanted_skycoord: astropy.coordinates.SkyCoord
    :param parking: boolean if shouldn't recalculate because of earth location, parking or altaz
    :return:
    """
    global cancel_slew
    cancel_slew = True
    thread = threading.Thread(target=move_to_skycoord_threadf, args=(sync_info, wanted_skycoord, parking))
    thread.start()


# TMOVE: stepper_control
def cancel_slews():
    global cancel_slew
    cancel_slew = True


def calc_speed(a, v0, t):
    # TMOVE: stepper_control
    return 2 * a * t + v0


# TMOVE: stepper_control
def steps_needed_to_deaccelerate(a, v0, vi):
    a = float(a)
    v0 = float(v0)
    vi = float(vi)
    t = (vi - v0) / (2.0 * a)
    return a * t * t + v0 * t


def elevation_to_pressure(elevation):
    """
    Gives you expected absolute pressure at elevation.
    :param elevation: in meters
    :return: pressure in Pa
    :Example:
        >>> import control
        >>> control.elevation_to_pressure(10000)
        26437.48946505586
    """
    # https://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
    return 101325.0 * ((1.0 - 2.2557e-5 * elevation) ** 5.25588)


def clean_deg(deg, dec=False):
    """
    Cleans up dec or ra as degree when outside range [-90, 90], [0, 360].
    :param deg: The degree to cleanup.
    :type deg: float
    :param dec: True if dec, false if ra.
    :type dec: bool
    :return: Cleaned up value. Second argument exists only when dec is True.
    :rtype: float, (int)
    :Example:
        >>> import control
        >>> control.clean_deg(91.0, True)
        (89.0, 1)

        >>> import control
        >>> control.clean_deg(-91.0, True)
        (-89.0, 1)

        >>> import control
        >>> control.clean_deg(-190.0, True)
        (10.0, 1)

        >>> import control
        >>> control.clean_deg(190.0, True)
        (-10.0, 1)

        >>> import control
        >>> control.clean_deg(390.0, True)
        (30.0, 2)

        >>> import control
        >>> control.clean_deg(390.0, False)
        30.0

        >>> import control
        >>> control.clean_deg(-390.0, False)
        330.0

        >>> import control
        >>> control.clean_deg(20.0, False)
        20.0
    """
    if dec:
        pole_count = 0
        while deg > 90 or deg < -90:
            if deg > 90:
                pole_count += 1
                deg = 90 - (deg - 90)
            if deg < -90:
                pole_count += 1
                deg = -90 - (deg + 90)
        return deg, pole_count
    else:
        if deg < 0:
            while deg < 0:
                deg += 360.0
        elif deg > 360.0:
            deg = deg % 360
        return deg


def ra_deg_time2(ra_deg, time1, time2):
    """
    Gives RA in degrees at time2 if we didn't track since time1.
    :param ra_deg: In degrees
    :type ra_deg: float
    :param time1: Time with ra_deg was taken
    :type time1: astropy.time.Time
    :param time2: Second time after time1.
    :type time2: astropy.time.Time
    :return: adjusted ra
    :rtype: float
    :Example:
        >>> import control
        >>> from astropy.time import Time as AstroTime
        >>> from astropy.time import TimeDelta as AstroTimeDelta
        >>> time1 = AstroTime("2018-01-01T01:01:01Z", format='isot')
        >>> ra1 = control.ra_deg_time2(1.0, time1, AstroTime("2018-01-01T01:01:02Z", format='isot'))
        >>> td = AstroTimeDelta(23.9344699*60.0*60.0, format='sec')
        >>> ra2 = control.ra_deg_time2(1.0, time1, time1 + td)
        >>> ra1, ra2
        (1.0041780745685391, 1.0000000000000568)
    """
    td = time2 - time1
    td.format = 'sec'
    ra_deg = ra_deg + (td.value * SIDEREAL_RATE)
    ra_deg = clean_deg(ra_deg)
    return ra_deg


# TMOVE: stepper_control
def get_stepper_altaz(status, obstime=AstroTime.now()):
    if runtime_settings['sync_info']:
        coord = steps_to_skycoord(runtime_settings['sync_info'], {'ra': status['rp'], 'dec': status['dp']},
                                  obstime, settings.settings['ra_ticks_per_degree'],
                                  settings.settings['dec_ticks_per_degree'])
        altaz = convert_to_altaz(coord)
        return altaz
    return None


def clear_sync():
    """
    Clears sync_info and sync points.
    """
    pointing_logger.debug(json.dumps({'func': 'control.clear_sync'}))
    pm_real_stepper.clear()
    pm_stepper_real.clear()
    runtime_settings['sync_info'] = None


def sync(coord):
    """
    Sync telescope position
    :param coord: Telescope position
    :type coord: astropy.coordinates.SkyCord
    :return:
    """
    global park_sync
    pt = PT('control.sync')
    status = stepper.get_status()

    # coord to altaz
    obstime = AstroTime.now()
    if hasattr(coord, 'alt'):
        altaz = coord
    else:
        altaz = convert_to_altaz(coord, obstime=obstime, atmo_refraction=settings.settings['atmos_refract'])

    if settings.settings['pointing_model'] != 'single' and not park_sync and pm_real_stepper.size() > 0:
        altaz = clean_altaz(altaz)
        pt.mark('control.sync 1a')
        stepper_altaz = get_stepper_altaz(status, obstime)
        stepper_altaz = clean_altaz(stepper_altaz)
        pt.mark('control.sync 1b')
        pm_real_stepper.add_point(altaz, stepper_altaz)
        pt.mark('control.sync 1c')
        pm_stepper_real.add_point(stepper_altaz, altaz)
        pointing_logger.debug(json.dumps({
            'func': 'control.sync', 'coord': pointing_model.log_p2dict(coord),
            'altaz': pointing_model.log_p2dict(altaz), 'stepper_altaz': pointing_model.log_p2dict(stepper_altaz)
        }))
    else:
        if hasattr(coord, 'alt'):
            coord = convert_to_icrs(coord, obstime=obstime, atmo_refraction=settings.settings['atmos_refract'])
        park_sync = False
        pt.mark('control.sync 2')
        sync_info = {'time': obstime, 'steps': {'ra': status['rp'], 'dec': status['dp']}, 'coords': coord}
        runtime_settings['sync_info'] = sync_info
        altaz = clean_altaz(altaz)
        pm_real_stepper.clear()
        pm_stepper_real.clear()
        pm_real_stepper.set_model(settings.settings['pointing_model'])
        pm_stepper_real.set_model(settings.settings['pointing_model'])
        pm_real_stepper.add_point(altaz, altaz)
        pm_stepper_real.add_point(altaz, altaz)
        pointing_logger.debug(json.dumps({
            'func': 'control.sync', 'coord': pointing_model.log_p2dict(coord), 'altaz': pointing_model.log_p2dict(altaz)
        }))
    pt.mark('control.sync done')


def ra_deg_d(started_angle, end_angle):
    """
    Finds the degree difference between two angles ang1-ang2, then returns shortest side that will take you
    there - or +.
    :param started_angle: First angle
    :type started_angle: float
    :param end_angle: Second angle
    :type end_angle: float
    :return: The shortest difference between started_angle, end_angle.
    :rtype: float
    :Example:
        >>> import control
        >>> control.ra_deg_d(359.0, 370.0)
        11.0

        >>> import control
        >>> control.ra_deg_d(359.0, -5.0)
        -4.0

        >>> import control
        >>> control.ra_deg_d(90.0, 92.0)
        2.0

        >>> import control
        >>> control.ra_deg_d(-20.0, -5.0)
        15.0
    """
    end_angle = clean_deg(end_angle)
    started_angle = clean_deg(started_angle)

    d_1 = end_angle - started_angle
    d_2 = 360.0 + d_1
    d_3 = d_1 - 360

    return min([d_1, d_2, d_3], key=abs)


def two_sync_calc_error(last_sync, current_sync):
    steps = skycoord_to_steps(last_sync, current_sync['coords'], current_sync['time'],
                              settings.settings['ra_ticks_per_degree'],
                              settings.settings['dec_ticks_per_degree'])
    ra_ther = steps['ra'] - last_sync['steps']['ra']
    ra_exp = current_sync['steps']['ra'] - last_sync['steps']['ra']
    dec_ther = steps['dec'] - last_sync['steps']['dec']
    dec_exp = current_sync['steps']['dec'] - last_sync['steps']['dec']
    if ra_ther == 0:
        ra_error = None
    else:
        ra_error = (ra_exp - ra_ther) / float(ra_ther)
    if dec_ther == 0:
        dec_error = None
    else:
        dec_error = (dec_exp - dec_ther) / float(dec_ther)

    return {
        'ra_error': ra_error,
        'dec_error': dec_error
    }


def skycoord_to_steps(sync_info, wanted_skycoord, wanted_time, ra_steps_per_degree, dec_ticks_per_degree):
    """
    Gives steps needed to be at wanted_skycoord right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord,
    'steps': {'ra': int, 'dec': int}
    :type sync_info: dict
    :param wanted_skycoord: The sky coordinates wanted.
    :type wanted_skycoord: astropy.coordinates.SkyCoord
    :param wanted_time: Time when wanting to be at wanted_skycoord
    :type wanted_time: astropy.time.Time
    :param ra_steps_per_degree: The number of steps per degree for RA.
    :type ra_steps_per_degree: float
    :param dec_ticks_per_degree: The steps per degree for dec.
    :type dec_ticks_per_degree: float
    :return: {'ra': steps_int, 'dec': steps_int}
    :Example:
        >>> import control
        >>> from astropy.coordinates import SkyCoord
        >>> from astropy.time import Time as AstroTime
        >>> import astropy.units as u
        >>> sync_info = {'time': AstroTime("2018-01-01T01:01:01Z", format='isot'),
        ... 'coords': SkyCoord(ra=180.0*u.deg, dec=-20.0 * u.deg, frame='icrs'),
        ... 'steps': {'ra': 2000, 'dec': 2000} }
        >>> wanted_skycoord = SkyCoord(ra=181.0*u.deg, dec=-10.0*u.deg, frame='icrs')
        >>> wanted_time = AstroTime("2018-01-01T01:01:02Z", format='isot')
        >>> dec_ticks_per_degree=177.7777
        >>> ra_steps_per_degree=18.04928*control.SIDEREAL_RATE
        >>> steps = control.skycoord_to_steps(sync_info, wanted_skycoord, wanted_time, ra_steps_per_degree, dec_ticks_per_degree)
        >>> int(steps['dec']), int(steps['ra'])
        (3777, -2301)
    """
    d_ra = ra_deg_d(
        ra_deg_time2(sync_info['coords'].ra.deg, sync_info['time'], wanted_time), wanted_skycoord.ra.deg)
    d_dec = wanted_skycoord.dec.deg - sync_info['coords'].dec.deg

    steps_ra = sync_info['steps']['ra'] - (d_ra * ra_steps_per_degree)
    steps_dec = sync_info['steps']['dec'] + (d_dec * dec_ticks_per_degree)

    # astropy way
    # adj_sync_coord = SkyCoord(ra=ra_deg_time2(sync_info['coords'].ra.deg, sync_info['time'], wanted_time)*u.deg,
    #                           dec=sync_info['coords'].dec.deg * u.deg, frame='icrs')
    # dra, ddec = adj_sync_coord.spherical_offsets_to(wanted_skycoord)

    # steps_ra = sync_info['steps']['ra'] - (dra.deg * (ra_steps_per_degree))
    # steps_dec = sync_info['steps']['dec'] + (ddec.deg * dec_ticks_per_degree)

    return {'ra': steps_ra, 'dec': steps_dec}


def steps_to_skycoord(sync_info, steps, stime, ra_ticks_per_degree, dec_ticks_per_degree):
    """
    Gets sky coordinates if we are at steps right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord,
    'steps': [RA_int, DEC_int]
    :type sync_info: dict
    :param steps: {'ra': steps_int, 'dec': steps_int}
    :type steps: dict
    :param stime: Time that goes with steps
    :type stime: astropy.time.Time
    :param ra_ticks_per_degree: Amount of steps in RA per degree.
    :type: ra_ticks_per_degree: float
    :param dec_ticks_per_degree: Calculate using steps per degree
    :type: float
    :return: the coordinates
    :rtype: astropy.coordinates.SkyCoord
    :Example:
        >>> import control
        >>> from astropy.coordinates import SkyCoord
        >>> from astropy.time import Time as AstroTime
        >>> import astropy.units as u
        >>> sync_info = {'time': AstroTime("2018-01-01T01:01:01Z", format='isot'),
        ... 'coords': SkyCoord(ra=180.0*u.deg, dec=-20.0 * u.deg, frame='icrs'),
        ... 'steps': {'ra': 2000, 'dec': 2000} }
        >>> stime = AstroTime("2018-01-01T01:01:01Z", format='isot')
        >>> dec_ticks_per_degree=177.7777
        >>> ra_steps_per_degree=18.04928*control.SIDEREAL_RATE
        >>> steps = {'dec': 3777.777, 'ra': -2319.99948876672}
        >>> coord = control.steps_to_skycoord(sync_info, steps, stime, ra_steps_per_degree, dec_ticks_per_degree)
        >>> coord.ra.deg, coord.dec.deg
        (181.0, -10.0)
    """

    d_ra = (steps['ra'] - sync_info['steps']['ra']) / ra_ticks_per_degree
    d_dec = (steps['dec'] - sync_info['steps']['dec']) / dec_ticks_per_degree
    ra_deg = ra_deg_time2(sync_info['coords'].ra.deg, sync_info['time'], stime) - d_ra
    ra_deg = clean_deg(ra_deg)

    dec_deg, pole_count = clean_deg(sync_info['coords'].dec.deg + d_dec, True)
    if pole_count % 2 > 0:
        ra_deg = clean_deg(ra_deg + 180.0)

    # print(ra_deg, dec_deg)
    coord = SkyCoord(ra=ra_deg * u.degree,
                     dec=dec_deg * u.degree,
                     frame='icrs')

    # astropy way
    # adj_sync_coord = SkyCoord(ra=ra_deg_time2(sync_info['coords'].ra.deg, sync_info['time'], stime) * u.deg,
    #                          dec=sync_info['coords'].dec.deg * u.deg, frame='icrs')

    # d_ra = (steps['ra'] - sync_info['steps']['ra']) / (ra_track_rate / SIDEREAL_RATE)
    # d_dec = (steps['dec'] - sync_info['steps']['dec']) / dec_ticks_per_degree
    # d_dec = clean_deg(d_dec, True)
    # offset_base = SkyCoord(d_ra * u.deg, d_dec * u.deg, frame='icrs')
    # offset = adj_sync_coord.transform_to(offset_base.skyoffset_frame())
    # offset_lon = offset.lon
    # offset_lon.wrap_angle = Angle(360.0 * u.deg)
    # coord = SkyCoord(ra=offset_lon, dec=offset.lat, frame='icrs')
    return coord


def convert_to_icrs(altaz_coord, earth_location=None, obstime=None, atmo_refraction=False):
    """

    :param altaz_coord:
    :param earth_location:
    :param obstime:
    :param atmo_refraction:
    :return:
    :Example:
        >>> import control
        >>> from astropy.coordinates import EarthLocation, AltAz
        >>> from astropy.time import Time as AstroTime
        >>> import astropy.units as u
        >>> el = EarthLocation(lat=38.9369*u.deg, lon=-95.242*u.deg, height=266.0*u.m)
        >>> t = AstroTime('2018-12-26T22:55:32.281', format='isot', scale='utc')
        >>> b = AltAz(alt=80*u.deg, az=90*u.deg)
        >>> c = control.convert_to_icrs(b, earth_location=el, obstime=t, atmo_refraction=False)
        >>> c.ra.deg, c.dec.deg
        (356.5643249365523, 38.12981040209684)
    """
    if obstime is None:
        obstime = AstroTime.now()
    if earth_location is None:
        earth_location = runtime_settings['earth_location']
    if earth_location is not None:
        pressure = None
        if atmo_refraction and runtime_settings['earth_location_set']:
            pressure = earth_location_to_pressure(earth_location)
        coord = AltAz(alt=altaz_coord.alt.deg * u.deg, az=altaz_coord.az.deg * u.deg,
                      obstime=obstime, location=earth_location, pressure=pressure).transform_to(ICRS)
        return coord


def slew(coord, parking=False):
    if runtime_settings is None or 'sync_info' not in runtime_settings or runtime_settings['sync_info'] is None:
        raise NotSyncedException('Not Synced')
    settings.not_parked()
    coord = clean_altaz(coord)
    stepper_coord = pm_real_stepper.transform_point(coord)
    icrs_stepper = convert_to_icrs(stepper_coord)
    move_to_skycoord(runtime_settings['sync_info'], icrs_stepper, parking)
