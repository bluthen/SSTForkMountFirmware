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
import serial
from functools import partial
import time

import datetime
import astropy
from astropy.coordinates import EarthLocation, SkyCoord, Angle
from astropy.time import Time as AstroTime
import astropy.units as u
import astropy.units.si as usi
import math

import settings

SIDEREAL_RATE = 0.004178074568511751  # 15.041"/s
AXIS_RA = 1
AXIS_DEC = 2

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
microserial = None
microseriallock = threading.RLock()
slew_lock = threading.RLock()
manual_lock = threading.RLock()
status_interval = None
socketio = None
inited = False
runtime_settings = None
slewing = False

cancel_slew = False
last_status = None


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


def read_serial_until_prompt():
    s = ""
    with microseriallock:
        while True:
            if microserial.in_waiting > 0:
                s += microserial.read(microserial.in_waiting).decode()
            else:
                s += microserial.read(1).decode()
            if '$' in s:
                # print('BREAK', s, 'BREAK')
                break
    return s


def get_status():
    with microseriallock:
        microserial.reset_input_buffer()
        microserial.write(b'qs\r')
        s = read_serial_until_prompt()
    # TODO: Might need to make a shorter status if transfer time longer than tracking tick interval
    # print(len(s))
    s = s.split()
    # print(s)
    status = {}
    for line in s:
        # print('@@@', line)
        line_status = line.split(':')
        if len(line_status) == 2:
            status[line_status[0]] = float(line_status[1])
    # print(status)
    # print('status' + str(datetime.datetime.now()))
    return status


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
    altaz = convert_to_altaz(skycoord)
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
        >>> altaz = control.to_altaz(radec, earth_location, t)
        >>> altaz.alt.deg, altaz.az.deg
        (55.55803292036938, 64.41850910955343)
    """
    if obstime is None:
        obstime = AstroTime.now()
    if earth_location is None:
        earth_location = runtime_settings['earth_location']
    if earth_location is not None:
        pressure = None
        if atmo_refraction and runtime_settings['earth_location_set']:
            pressure = earth_location_to_pressure(earth_location)
        altaz = coord.transform_to(
            astropy.coordinates.AltAz(obstime=obstime, location=earth_location,
                                      pressure=pressure))
        return altaz
    else:
        return None


def send_status():
    global slewing, last_status
    status = get_status()
    status['ra'] = None
    status['dec'] = None
    status['alt'] = None
    status['az'] = None
    status['time'] = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    status['time_been_set'] = runtime_settings['time_been_set']
    status['synced'] = runtime_settings['sync_info'] is not None
    inhorizon = False
    if status['synced']:
        coord = steps_to_skycoord(runtime_settings['sync_info'], {'ra': status['rp'], 'dec': status['dp']},
                                  AstroTime.now(), settings.settings['ra_track_rate'],
                                  settings.settings['dec_ticks_per_degree'])
        status['ra'] = coord.icrs.ra.deg
        status['dec'] = coord.icrs.dec.deg
        # print('earth_location', runtime_settings['earth_location'])
        status['alt'] = None
        status['az'] = None
        if runtime_settings['earth_location_set']:
            altaz = convert_to_altaz(coord)
            below_horizon = below_horizon_limit(altaz)
            if below_horizon and runtime_settings['tracking']:
                runtime_settings['tracking'] = False
                ra_set_speed(0)
                status['alert'] = 'In horizon limit, tracking stopped'
            # print(altaz)
            status['alt'] = altaz.alt.deg
            status['az'] = altaz.az.deg
    status['slewing'] = slewing
    status['tracking'] = runtime_settings['tracking']
    last_status = status
    socketio.emit('status', status)


def micro_update_settings():
    with microseriallock:
        microserial.reset_input_buffer()
        microserial.write(('set_var ra_max_tps %f\r' % settings.settings['ra_slew_fastest']).encode())
        read_serial_until_prompt()
        microserial.write(('set_var ra_guide_rate %f\r' % settings.settings['micro']['ra_guide_rate']).encode())
        read_serial_until_prompt()
        microserial.write(('set_var ra_direction %f\r' % settings.settings['micro']['ra_direction']).encode())
        read_serial_until_prompt()
        microserial.write(('set_var dec_max_tps %f\r' % settings.settings['dec_slew_fastest']).encode())
        read_serial_until_prompt()
        microserial.write(('set_var dec_guide_rate %f\r' % settings.settings['micro']['dec_guide_rate']).encode())
        read_serial_until_prompt()
        microserial.write(('set_var dec_direction %f\r' % settings.settings['micro']['dec_direction']).encode())
        read_serial_until_prompt()
        if runtime_settings['tracking']:
            ra_set_speed(settings.settings['ra_track_rate'])
        else:
            ra_set_speed(0)
        dec_set_speed(0)


def init(osocketio, fruntime_settings):
    global microserial, microseriallock, status_interval, socketio, inited, runtime_settings
    if inited:
        return
    inited = True
    # print('Inited')
    runtime_settings = fruntime_settings
    socketio = osocketio
    # Load settings file
    # Open serial port
    microserial = serial.Serial(settings.settings['microserial']['port'], settings.settings['microserial']['baud'],
                                timeout=2)
    update_location()
    if settings.settings['park_position'] and runtime_settings['earth_location_set']:
        coord = astropy.coordinates.SkyCoord(alt=settings.settings['park_position']['alt'] * u.deg,
                                             az=settings.settings['park_position']['az'] * u.deg, frame='altaz',
                                             obstime=AstroTime.now(),
                                             location=runtime_settings['earth_location']).icrs
        sync(coord)
    micro_update_settings()
    status_interval = SimpleInterval(send_status, 1)


def manual_control(direction, speed):
    # TODO: Acceleration
    # TODO: Disabling autoguiding
    global microserial, microseriallock, slew_lock, manual_lock
    # print('manual_control', direction, speed)
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
                    # TODO: if currently tracking (when would we not, parked then manual move?)
                    done = False
                    with microseriallock:
                        status = get_status()
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
                            ra_set_speed(sspeed)
                        else:
                            done = True
                    if not done:
                        # print('timer')
                        timers[direction] = threading.Timer(0.1, partial(manual_control, direction, None))
                        timers[direction].start()
                else:
                    done = False
                    with microseriallock:
                        status = get_status()
                        if status['ds'] != 0:
                            # print(status)
                            sspeed = status['ds'] - math.copysign(settings.settings['dec_slew_fastest'] / 10.0,
                                                                  status['ds'])
                            if status['ds'] == 0 or sspeed / status['ds'] < 0:
                                sspeed = 0
                                done = True
                            # print(sspeed)
                            dec_set_speed(sspeed)
                        else:
                            done = True
                    if not done:
                        timers[direction] = threading.Timer(0.1, partial(manual_control, direction, None))
                        timers[direction].start()
            else:
                # If not current manually going other direction
                with microseriallock:
                    status = get_status()
                    # print(status)
                    if OPPOSITE_MANUAL[direction] in timers:
                        return
                    if direction == 'left':
                        sspeed = status['rs'] - settings.settings['ra_slew_' + speed] / 10.0
                        # print('ra_slew_'+speed, settings.settings['ra_slew_'+speed]/10.0)
                        if abs(sspeed) > settings.settings['ra_slew_' + speed]:
                            sspeed = -settings.settings['ra_slew_' + speed]
                        # print(sspeed)
                        ra_set_speed(sspeed)
                    elif direction == 'right':
                        sspeed = status['rs'] + settings.settings['ra_slew_' + speed] / 10.0
                        if abs(sspeed) > settings.settings['ra_slew_' + speed]:
                            sspeed = settings.settings['ra_slew_' + speed]
                        # print(sspeed)
                        ra_set_speed(sspeed)
                    elif direction == 'up':
                        # print('--------------- dec up %.1f' % settings.settings['dec_slew_' + speed])
                        sspeed = status['ds'] + settings.settings['dec_slew_' + speed] / 10.0
                        if abs(sspeed) > settings.settings['dec_slew_' + speed]:
                            sspeed = settings.settings['dec_slew_' + speed]
                        # print(sspeed)
                        dec_set_speed(sspeed)
                    elif direction == 'down':
                        sspeed = status['ds'] - settings.settings['dec_slew_' + speed] / 10.0
                        if abs(sspeed) > settings.settings['dec_slew_' + speed]:
                            sspeed = -settings.settings['dec_slew_' + speed]
                        # print('--------------- dec down -%.1f' % settings.settings['dec_slew_' + speed])
                        # print(sspeed)
                        dec_set_speed(sspeed)
                    timers[direction] = threading.Timer(0.5, partial(manual_control, direction, None))
                    timers[direction].start()
        finally:
            slew_lock.release()


def autoguide_disable():
    with microseriallock:
        microserial.reset_input_buffer()
        microserial.write('autoguide_disable\r'.encode())
        read_serial_until_prompt()


def autoguide_enable():
    with microseriallock:
        microserial.reset_input_buffer()
        microserial.write('autoguide_enable\r'.encode())
        read_serial_until_prompt()


def ra_set_speed(speed):
    with microseriallock:
        microserial.reset_input_buffer()
        microserial.write(('ra_set_speed %f\r' % speed).encode())
        read_serial_until_prompt()


def dec_set_speed(speed):
    with microseriallock:
        microserial.reset_input_buffer()
        microserial.write(('dec_set_speed %f\r' % speed).encode())
        read_serial_until_prompt()


def move_to_skycoord_threadf(sync_info, wanted_skycoord, parking=False):
    global cancel_slew, slewing
    # sleep_time must be < 1
    sleep_time = 0.1
    loops_to_full_speed = 10.0

    ra_close_enough = 3.0
    dec_close_enough = 3.0

    # TODO: Backlash

    data = {'time': [], 'rpv': [], 'dpv': [], 'rsp': [], 'dsp': [], 'rv': [], 'dv': [], 'era': [], 'edec': []}

    try:
        slew_lock.acquire()
        autoguide_disable()
        slewing = True
        cancel_slew = False
        if type(wanted_skycoord) is dict and 'ra_steps' in wanted_skycoord:
            need_step_position = {'ra': wanted_skycoord['ra_steps'], 'dec': wanted_skycoord['dec_steps']}
            ra_close_enough = 0
            dec_close_enough = 0
        else:
            need_step_position = skycoord_to_steps(sync_info, wanted_skycoord, AstroTime.now(),
                                                   settings.settings['ra_track_rate'],
                                                   settings.settings['dec_ticks_per_degree'])
        last_datetime = datetime.datetime.now()
        started_slewing = last_datetime
        total_time = 0.0
        first = True
        while not cancel_slew:
            if not parking:
                need_step_position = skycoord_to_steps(sync_info, wanted_skycoord, AstroTime.now(),
                                                       settings.settings['ra_track_rate'],
                                                       settings.settings['dec_ticks_per_degree'])
            now = datetime.datetime.now()
            status = get_status()
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
                ra_set_speed(ra_speed)
            if not math.isclose(status['ds'], dec_speed, rel_tol=0.02):
                dec_set_speed(dec_speed)

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
            ra_set_speed(settings.settings['ra_track_rate'])
        else:
            ra_set_speed(0)
        dec_set_speed(0.0)
    finally:
        autoguide_enable()
        slewing = False
        slew_lock.release()


class NotSyncedException(Exception):
    pass


def slew(radec, parking=False):
    """
    Slew to coordinates.
    :param radec: sky coordinate to slew to
    :type radec: astropy.coordinates.SkyCoord
    :param parking: If a parking slew
    :type parking: bool
    :return:
    """
    # TODO: Error conditions
    if runtime_settings is None or 'sync_info' not in runtime_settings or runtime_settings['sync_info'] is None:
        raise NotSyncedException('Not Synced')
    move_to_skycoord(runtime_settings['sync_info'], radec, parking)


def adjust_ra_dec_for_atmospheric_refraction(ra, dec, earth_location=None):
    """
    Gives you displacment ra, dec when adjusting with atmospheric_refraction
    :param ra: float as deg
    :param dec: float as deg
    :param earth_location: EarthLocation defaults to runtime_settings['earth_location']
    :return: {ra: deg_float, dec: deg_float}
    """
    if earth_location is None:
        earth_location = runtime_settings['earth_location']
    radec_skycoord = astropy.coordinates.SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    altaz = convert_to_altaz(radec_skycoord, earth_location, obstime=True)
    adj_skycoord = astropy.coordinates.AltAz(alt=altaz.alt, az=altaz.az,
                                             location=earth_location,
                                             obstime=AstroTime.now()).transform_to(astropy.coordinates.ICRS)
    return {'ra': adj_skycoord.icrs.ra.deg, 'dec': adj_skycoord.icrs.dec.deg}


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


def slew_to_steps(ra_steps, dec_steps):
    """

    :param ra_steps: steps
    :param dec_steps: steps
    :return:
    """
    # TODO: Error conditions
    wanted_skycoord = {'ra_steps': ra_steps, 'dec_steps': dec_steps}
    move_to_skycoord(runtime_settings['sync_info'], wanted_skycoord, True)


def move_to_skycoord(sync_info, wanted_skycoord, parking=False):
    """
    Slew to position
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord, 'steps': {'ra': int, 'dec': int}
    :param wanted_skycoord: astropy.coordinates.SkyCoord
    :param parking: boolean if shouldn't recalculate because of earth location, parking or altaz
    :return:
    """
    global cancel_slew
    cancel_slew = True
    thread = threading.Thread(target=move_to_skycoord_threadf, args=(sync_info, wanted_skycoord, parking))
    thread.start()


def cancel_slews():
    global cancel_slew
    cancel_slew = True


def calc_speed(a, v0, t):
    return 2 * a * t + v0


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
        >>> elevation_to_pressure(10000)
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
    :return: Cleaned up value.
    :rtype: float
    :Example:

        >>> import control
        >>> control.clean_deg(91.0, True)
        89.0

        >>> import control
        >>> control.clean_deg(-91.0, True)
        -89.0

        >>> import control
        >>> control.clean_deg(-190.0, True)
        10.0

        >>> import control
        >>> control.clean_deg(190.0, True)
        -10.0

        >>> import control
        >>> control.clean_deg(390.0, True)
        30.0

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


def sync(coord):
    """
    Sync telescope position
    :param coord: Telescope position
    :type coord: astropy.coordinates.SkyCord
    :return:
    """
    sync_info = {}
    status = get_status()

    sync_info['time'] = AstroTime.now()
    sync_info['steps'] = {'ra': status['rp'], 'dec': status['dp']}
    sync_info['coords'] = coord
    runtime_settings['sync_info'] = sync_info


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
                              settings.settings['ra_track_rate'],
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


def skycoord_to_steps(sync_info, wanted_skycoord, wanted_time, ra_track_rate, dec_ticks_per_degree):
    """
    Gives steps needed to be at wanted_skycoord right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord,
    'steps': {'ra': int, 'dec': int}
    :type sync_info: dict
    :param wanted_skycoord: The sky coordinates wanted.
    :type wanted_skycoord: astropy.coordinates.SkyCoord
    :param wanted_time: Time when wanting to be at wanted_skycoord
    :type wanted_time: astropy.time.Time
    :param ra_track_rate: The track rate in steps per second.
    :type ra_track_rate: float
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
        >>> wanted_time = AstroTime("2018-01-01T01:01:01Z", format='isot')
        >>> dec_ticks_per_degree=177.7777
        >>> ra_track_rate=18.04928
        >>> control.skycoord_to_steps(sync_info, wanted_skycoord, wanted_time, ra_track_rate, dec_ticks_per_degree)
        {'dec': 3777.2464047949525, 'ra': -2319.959811492603}

    """
    d_ra = ra_deg_d(ra_deg_time2(sync_info['coords'].icrs.ra.deg, sync_info['time'], wanted_time),
                    wanted_skycoord.icrs.ra.deg)
    d_dec = wanted_skycoord.icrs.dec.deg - sync_info['coords'].icrs.dec.deg

    steps_ra = sync_info['steps']['ra'] - (d_ra * (ra_track_rate / SIDEREAL_RATE))
    steps_dec = sync_info['steps']['dec'] + (d_dec * dec_ticks_per_degree)

    # astropy way
    # adj_sync_coord = SkyCoord(ra=ra_deg_time2(sync_info['coords'].icrs.ra.deg, sync_info['time'], wanted_time) * u.deg,
    #                           dec=sync_info['coords'].icrs.dec.deg * u.deg, frame='icrs')
    # dra, ddec = adj_sync_coord.spherical_offsets_to(wanted_skycoord)

    # steps_ra = sync_info['steps']['ra'] - (dra.deg * (ra_track_rate / SIDEREAL_RATE))
    # steps_dec = sync_info['steps']['dec'] + (ddec.deg * dec_ticks_per_degree)

    return {'ra': steps_ra, 'dec': steps_dec}


def steps_to_skycoord(sync_info, steps, stime, ra_track_rate, dec_ticks_per_degree):
    """
    Gets sky coordinates if we are at steps right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord,
    'steps': [RA_int, DEC_int]
    :type sync_info: dict
    :param steps: {'ra': steps_int, 'dec': steps_int}
    :type steps: dict
    :param stime: Time that goes with steps
    :type stime: astropy.time.Time
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
        >>> ra_track_rate=18.04928
        >>> steps = {'dec': 3777.777, 'ra': -2319.99948876672}
        >>> coord = control.steps_to_skycoord(sync_info, steps, stime, ra_track_rate, dec_ticks_per_degree)
        >>> coord.ra.deg, coord.dec.deg
        (181.0, -10.0)


    """

    d_ra = (steps['ra'] - sync_info['steps']['ra']) / (ra_track_rate / SIDEREAL_RATE)
    d_dec = (steps['dec'] - sync_info['steps']['dec']) / dec_ticks_per_degree
    ra_deg = ra_deg_time2(sync_info['coords'].icrs.ra.deg, sync_info['time'], stime) - d_ra
    ra_deg = clean_deg(ra_deg)

    dec_deg, pole_count = clean_deg(sync_info['coords'].icrs.dec.deg + d_dec, True)
    # TODO: Fix RA if dec went across pole
    if pole_count % 2 > 0:
        ra_deg = clean_deg(ra_deg + 180.0)

    # print(ra_deg, dec_deg)
    coord = SkyCoord(ra=ra_deg * u.degree,
                     dec=dec_deg * u.degree,
                     frame='icrs')

    # astropy way
    # adj_sync_coord = SkyCoord(ra=ra_deg_time2(sync_info['coords'].icrs.ra.deg, sync_info['time'], stime) * u.deg,
    #                          dec=sync_info['coords'].icrs.dec.deg * u.deg, frame='icrs')

    # d_ra = (steps['ra'] - sync_info['steps']['ra']) / (ra_track_rate / SIDEREAL_RATE)
    # d_dec = (steps['dec'] - sync_info['steps']['dec']) / dec_ticks_per_degree
    # d_dec = clean_deg(d_dec, True)
    # offset_base = SkyCoord(d_ra * u.deg, d_dec * u.deg, frame='icrs')
    # offset = adj_sync_coord.transform_to(offset_base.skyoffset_frame())
    # offset_lon = offset.lon
    # offset_lon.wrap_angle = Angle(360.0 * u.deg)
    # coord = SkyCoord(ra=offset_lon, dec=offset.lat, frame='icrs')
    return coord


def new_slew(coord):
    if hasattr(coord, 'ra'):
        altaz = convert_to_altaz(coord, atmo_refraction=settings.settings['atmos_refract'])
    elif hasattr(coord, 'alt'):
        altaz = coord


#Finding point in triangle
# xaedes answer
# https://stackoverflow.com/questions/2049582/how-to-determine-if-a-point-is-in-a-2d-triangle
# https://www.gamedev.net/forums/topic/295943-is-this-a-better-point-in-triangle-test-2d/
def tr_sign(p1, p2, p3):
    return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])


def tr_point_in_triangle(pt, t1, t2, t3):
    """
    :param pt: Point checking
    :type pt: array [float, float]
    :param t1: first point of triangle
    :type t1: array [float, float]
    :param t2: second point of triangle
    :type t2: array [float, float]
    :param t3: third point of triangle
    :type t3: array [float, float]
    :return: true if point in triangle
    :rtype: bool
    """
    d1 = tr_sign(pt, t1, t2)
    d2 = tr_sign(pt, t2, t3)
    d3 = tr_sign(pt, t3, t1)

    h_neg = d1 < 0 or d2 < 0 or d3 < 0
    h_pos = d1 > 0 or d2 > 0 or d3 > 0

    return not (h_neg and h_pos)


sync_points = []
distance_matrix = []
triangles = []

def add_sync_point(coord):
    """

    :param coord:
    :return:
    """
    if not hasattr(coord, 'alt'):
        raise AssertionError('coord should be an alt-az coordinate')
    # TODO: Check if coord already in sync_points first and don't add if so.
    row = []
    for i in range(len(sync_points)):
        distance_matrix[i].append(coord.separation(sync_points[i]).deg)
        row.append(coord.separation(sync_points[i]).deg)
    row.append(0.0)
    sync_points.append(coord)
    distance_matrix.append(row)

    for i in range(len(sync_points)):
        min_v1 = 999999999.0
        min_idx1 = -1
        min_v2 = 999999999.0
        min_idx2 = -1
        for j in range(len(sync_points)):
            if i == j:
                continue
            if distance_matrix[i][j] < min_v1:
                min_v2 = min_v1
                min_idx2 = min_idx1
                min_v1 = distance_matrix[i][j]
                min_idx1 = j
        #TODO: Finish


def find_triangle(coord):
    #TODO finish
    pass


