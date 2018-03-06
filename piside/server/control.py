import threading
import serial
from functools import partial
import time

import datetime
import astropy
from astropy.coordinates import EarthLocation, SkyCoord, Angle
from astropy.time import Time as AstroTime
import astropy.units as u
import math

import main

SIDEREAL_RATE = 0.004178074568511751  # 15.041"/s
AXIS_RA = 1
AXIS_DEC = 2

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
settings = None
microserial = None
microseriallock = threading.RLock()
slew_lock = threading.RLock()
status_interval = None
socketio = None
inited = False
runtime_settings = None
slewing = False

cancel_slew = False
last_status = None


class SimpleInterval:
    def __init__(self, func, sec):
        print('Simple Interval')
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


def get_status():
    with microseriallock:
        microserial.reset_input_buffer()
        microserial.write(b'qs\r')
        s = ""
        s += microserial.read(1).decode()
        while True:
            if microserial.in_waiting > 0:
                s += microserial.read(microserial.in_waiting).decode()
            else:
                s += microserial.read(1).decode()
            if '$' in s:
                break
    # TODO: Might need to make a shorter status if transfer time longer than tracking tick interval
    # print(len(s))
    s = s.split()
    # print(s)
    status = {}
    for line in s:
        line_status = line.split(':')
        if len(line_status) == 2:
            status[line_status[0]] = float(line_status[1])
    # print(status)
    #print('status' + str(datetime.datetime.now()))
    return status


def slewtocheck(ra, dec):
    if not ra or not dec:
        return False
    wanted_skycoord = astropy.coordinates.SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    altaz = to_altaz_asdeg(wanted_skycoord)
    # TODO: Check if in keepout zone
    # Check if above horizon
    if altaz['alt'] < 0:
        return False
    else:
        return True


def update_location():
    print(settings['location'])
    if not settings['location']['lat']:
        return
    el = EarthLocation(lat=settings['location']['lat'] * u.deg,
                       lon=settings['location']['long'] * u.deg,
                       height=405.0 * u.m)
    runtime_settings['earth_location'] = el


def to_altaz_asdeg(coord):
    if runtime_settings['earth_location']:
        # altaz = SkyCoord(coord, obstime=astropy.time.Time.now(),
        #                 location=runtime_settings['earth_location']).altaz
        altaz = coord.transform_to(
            astropy.coordinates.AltAz(obstime=AstroTime.now(), location=runtime_settings['earth_location']))
        # print(altaz)
        return {'alt': altaz.alt.deg, 'az': altaz.az.deg}
    else:
        return {'alt': None, 'az': None}


def send_status():
    global slewing, last_status
    status = get_status()
    status['ra'] = None
    status['dec'] = None
    status['alt'] = None
    status['az'] = None
    status['time_been_set'] = runtime_settings['time_been_set']
    status['synced'] = runtime_settings['sync_info'] is not None
    if status['synced']:
        coord = steps_to_skycoord(runtime_settings['sync_info'], {'ra': status['rp'], 'dec': status['dp']},
                                  AstroTime.now(), settings['ra_track_rate'], settings['dec_ticks_per_degree'])
        status['ra'] = coord.icrs.ra.deg
        status['dec'] = coord.icrs.dec.deg
        # print('earth_location', runtime_settings['earth_location'])
        altaz = to_altaz_asdeg(coord)
        # print(altaz)
        status['alt'] = altaz['alt']
        status['az'] = altaz['az']
    status['slewing'] = slewing
    status['tracking'] = runtime_settings['tracking']
    last_status = status
    socketio.emit('status', status)


def micro_update_settings():
    with microseriallock:
        microserial.write(('set_var ra_max_tps %f\r' % settings['micro']['ra_max_tps']).encode())
        microserial.write(('set_var ra_guide_rate %f\r' % settings['micro']['ra_guide_rate']).encode())
        microserial.write(('set_var ra_direction %f\r' % settings['micro']['ra_direction']).encode())
        microserial.write(('set_var dec_max_tps %f\r' % settings['micro']['dec_max_tps']).encode())
        microserial.write(('set_var dec_guide_rate %f\r' % settings['micro']['dec_guide_rate']).encode())
        microserial.write(('set_var dec_direction %f\r' % settings['micro']['dec_direction']).encode())
        if runtime_settings['tracking']:
            ra_set_speed(settings['ra_track_rate'])
        else:
            ra_set_speed(0)
        microserial.write(('dec_set_speed %f\r' % (0,)).encode())


def init(osocketio, fsettings, fruntime_settings):
    global settings, microserial, microseriallock, status_interval, socketio, inited, runtime_settings
    if inited:
        return
    inited = True
    print('Inited')
    runtime_settings = fruntime_settings
    settings = fsettings
    socketio = osocketio
    # Load settings file
    # Open serial port
    microserial = serial.Serial(settings['microserial']['port'], settings['microserial']['baud'], timeout=2)
    update_location()
    if settings['park_position'] and runtime_settings['earth_location']:
        coord = astropy.coordinates.SkyCoord(alt=settings['park_position']['alt'] * u.deg,
                                             az=settings['park_position']['az'] * u.deg, frame='altaz',
                                             obstime=AstroTime.now(),
                                             location=runtime_settings['earth_location']).icrs
        sync(coord.ra.deg, coord.dec.deg)
    micro_update_settings()
    status_interval = SimpleInterval(send_status, 1)


def manual_control(direction, speed):
    # TODO: Acceleration limit
    global microserial, microseriallock, slew_lock
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
                # TODO: if currently tracking (when would we not?)
                with microseriallock:
                    if runtime_settings['tracking']:
                        microserial.write(('ra_set_speed %f\r' % settings['ra_track_rate']).encode())
                    else:
                        microserial.write('ra_set_speed 0\r'.encode())
            else:
                with microseriallock:
                    microserial.write(b'dec_set_speed 0\r')
        else:
            # If not current manually going other direction
            with microseriallock:
                if OPPOSITE_MANUAL[direction] in timers:
                    return
                if direction == 'left':
                    microserial.write(('ra_set_speed -%.1f\r' % settings['ra_slew_' + speed]).encode())
                elif direction == 'right':
                    microserial.write(('ra_set_speed %.1f\r' % settings['ra_slew_' + speed]).encode())
                elif direction == 'up':
                    #print('--------------- dec up %.1f' % settings['dec_slew_' + speed])
                    microserial.write(('dec_set_speed %.1f\r' % settings['dec_slew_' + speed]).encode())
                elif direction == 'down':
                    #print('--------------- dec down -%.1f' % settings['dec_slew_' + speed])
                    microserial.write(('dec_set_speed -%.1f\r' % settings['dec_slew_' + speed]).encode())
                timers[direction] = threading.Timer(0.75, partial(manual_control, direction, None))
                timers[direction].start()
    finally:
        slew_lock.release()


def ra_set_speed(speed):
    with microseriallock:
        microserial.write(('ra_set_speed %f\r' % speed).encode())


def dec_set_speed(speed):
    with microseriallock:
        microserial.write(('dec_set_speed %f\r' % speed).encode())


def move_to_skycoord_threadf(sync_info, wanted_skycoord, parking=False):
    global cancel_slew, slewing
    try:
        slew_lock.acquire()
        slewing = True
        cancel_slew = False
        need_step_position = skycoord_to_steps(sync_info, wanted_skycoord, AstroTime.now(), settings['ra_track_rate'],
                                               settings['dec_ticks_per_degree'])
        status = get_status()
        first = True
        while not cancel_slew:
            if abs(need_step_position['ra'] - status['rp']) <= math.ceil(settings['ra_track_rate']) and abs(
                            need_step_position['dec'] - status['dp']) <= math.ceil(
                                15 * settings['dec_ticks_per_degree'] / (60.0 * 60.0)):
                break
            # TODO Acceleration
            ra_delta = need_step_position['ra'] - status['rp']
            if abs(ra_delta) < math.ceil(settings['ra_track_rate']) and not math.isclose(status['rs'],
                                                                                         settings['ra_track_rate'],
                                                                                         abs_tol=0.1):
                if runtime_settings['tracking']:
                    ra_set_speed(settings['ra_track_rate'])
                else:
                    ra_set_speed(0)

            elif abs(ra_delta) < settings['ra_slew_fast'] / 3.0:
                # Need to go at least 2 * ra_track_rate
                speed = 3.0 * ra_delta
                if abs(speed) < settings['ra_track_rate']:
                    speed = math.copysign(2 * settings['ra_track_rate'], speed)
                ra_set_speed(speed)
            elif first:
                ra_set_speed(math.copysign(settings['ra_slew_slow'], ra_delta))
            elif abs(ra_delta) > settings['ra_slew_slow']:
                ra_set_speed(math.copysign(settings['ra_slew_fast'], ra_delta))

            dec_delta = need_step_position['dec'] - status['dp']
            if abs(dec_delta) < 15 * settings['dec_ticks_per_degree'] / (60.0 * 60.0):
                dec_set_speed(0.0)
            elif abs(dec_delta) < settings['dec_slew_fast'] / 3.0:
                dec_set_speed(3.0 * dec_delta)
            elif first:
                dec_set_speed(math.copysign(settings['dec_slew_slow'], dec_delta))
            else:
                dec_set_speed(math.copysign(settings['dec_slew_fast'], dec_delta))
            first = False
            time.sleep(0.2)
            if not parking:
                need_step_position = skycoord_to_steps(sync_info, wanted_skycoord, AstroTime.now(),
                                                       settings['ra_track_rate'],
                                                       settings['dec_ticks_per_degree'])
            status = get_status()
        if runtime_settings['tracking']:
            ra_set_speed(settings['ra_track_rate'])
        else:
            ra_set_speed(0)
        dec_set_speed(0.0)
    finally:
        slewing = False
        slew_lock.release()


def slew(ra, dec, parking=False):
    """

    :param ra: float as deg
    :param dec: float as deg
    :return:
    """
    # TODO: Error conditions
    wanted_skycoord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    move_to_skycoord(runtime_settings['sync_info'], wanted_skycoord, parking)


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
        >>> ra1 = control.ra_deg_time2(1.0, time1, Time("2018-01-01T01:01:02Z", format='isot'))
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


def sync(ra, dec):
    sync_info = {}
    status = get_status()

    sync_info['time'] = AstroTime.now()
    sync_info['steps'] = {'ra': status['rp'], 'dec': status['dp']}
    coords = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    sync_info['coords'] = coords
    runtime_settings['sync_info'] = sync_info


def ra_deg_d(started_angle, end_angle):
    """
    Finds the degree difference between two angles ang1-ang2, then returns shortest side that will take you there - or +.
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


def skycoord_to_steps(sync_info, wanted_skycoord, wanted_time, ra_track_rate, dec_ticks_per_degree):
    """
    Gives steps needed to be at wanted_skycoord right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord, 'steps': {'ra': int, 'dec': int}
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
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord, 'steps': [RA_int, DEC_int]
    :type sync_info: dict
    :param steps: {'ra': steps_int, 'dec': steps_int}
    :type steps: dict
    :param time: Time that goes with steps
    :type time: astropy.time.Time
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
    #TODO: Fix RA if dec went across pole
    if pole_count % 2 > 0:
        ra_deg = clean_deg(ra_deg+180.0)

    # print(ra_deg, dec_deg)
    coord = SkyCoord(ra=ra_deg * u.degree,
                    dec=dec_deg * u.degree,
                    frame='icrs')

    # astropy way
    #adj_sync_coord = SkyCoord(ra=ra_deg_time2(sync_info['coords'].icrs.ra.deg, sync_info['time'], stime) * u.deg,
    #                          dec=sync_info['coords'].icrs.dec.deg * u.deg, frame='icrs')

    #d_ra = (steps['ra'] - sync_info['steps']['ra']) / (ra_track_rate / SIDEREAL_RATE)
    #d_dec = (steps['dec'] - sync_info['steps']['dec']) / dec_ticks_per_degree
    #d_dec = clean_deg(d_dec, True)
    #offset_base = SkyCoord(d_ra * u.deg, d_dec * u.deg, frame='icrs')
    #offset = adj_sync_coord.transform_to(offset_base.skyoffset_frame())
    #offset_lon = offset.lon
    #offset_lon.wrap_angle = Angle(360.0 * u.deg)
    #coord = SkyCoord(ra=offset_lon, dec=offset.lat, frame='icrs')
    return coord
