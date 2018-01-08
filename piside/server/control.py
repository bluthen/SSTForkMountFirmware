import threading
import serial
from functools import partial
import time

import datetime
import astropy
from astropy.coordinates import EarthLocation, SkyCoord
import astropy.units as u
import math

import main

SIDEREAL_RATE = 0.004178074551055444  # 15.041"/s
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

cancel_slew = False


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
    print('status' + str(datetime.datetime.now()))
    return status


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
        altaz = SkyCoord(coord, obstime=astropy.time.Time.now(),
                     location=runtime_settings['earth_location']).altaz
        # print(altaz)
        return {'alt': altaz.alt.deg, 'az': altaz.az.deg}
    else:
        return {'alt': None, 'az': None}


def send_status():
    status = get_status()
    status['ra'] = None
    status['dec'] = None
    status['alt'] = None
    status['az'] = None
    status['time_been_set'] = runtime_settings['time_been_set']
    status['synced'] = runtime_settings['sync_info'] is not None
    if status['synced']:
        coord = steps_to_skycoord(runtime_settings['sync_info'], {'ra': status['rp'], 'dec': status['dp']})
        status['ra'] = coord.icrs.ra.deg
        status['dec'] = coord.icrs.dec.deg
        # print('earth_location', runtime_settings['earth_location'])
        altaz = to_altaz_asdeg(coord)
        # print(altaz)
        status['alt'] = altaz['alt']
        status['az'] = altaz['az']

    socketio.emit('status', status)


def micro_update_settings():
    with microseriallock:
        microserial.write(('set_var ra_max_tps %f\r' % settings['micro']['ra_max_tps']).encode())
        microserial.write(('set_var ra_guide_rate %f\r' % settings['micro']['ra_guide_rate']).encode())
        microserial.write(('set_var ra_direction %f\r' % settings['micro']['ra_direction']).encode())
        microserial.write(('set_var dec_max_tps %f\r' % settings['micro']['dec_max_tps']).encode())
        microserial.write(('set_var dec_guide_rate %f\r' % settings['micro']['dec_guide_rate']).encode())
        microserial.write(('set_var dec_direction %f\r' % settings['micro']['dec_direction']).encode())
        microserial.write(('ra_set_speed %f\r' % settings['ra_track_rate']).encode())
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
    micro_update_settings()
    update_location()
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
                    microserial.write(('ra_set_speed %f\r' % settings['ra_track_rate']).encode())
                # else:
                # ra_set_speed 0
                pass
            else:
                with microseriallock:
                    microserial.write(b'dec_set_speed 0\r')
        else:
            # If not current manually going other direction
            with microseriallock:
                if OPPOSITE_MANUAL[direction] in timers:
                    return
                if direction == 'left':
                    microserial.write(('ra_set_speed %f\r' % settings['ra_slew_' + speed]).encode())
                elif direction == 'right':
                    microserial.write(('ra_set_speed -%f\r' % settings['ra_slew_' + speed]).encode())
                elif direction == 'up':
                    print('Trying to do dec_set_speed')
                    microserial.write(('dec_set_speed %f\r' % settings['dec_slew_' + speed]).encode())
                elif direction == 'down':
                    microserial.write(('dec_set_speed -%f\r' % settings['dec_slew_' + speed]).encode())
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

def move_to_skycoord_threadf(sync_info, wanted_skycoord):
    global cancel_slew
    with slew_lock:
        cancel_slew = False
        need_step_position = skycoord_to_steps(sync_info, wanted_skycoord)
        status = get_status()
        first = True
        while not cancel_slew:
            if abs(need_step_position['ra'] - status['rp']) <= math.ceil(settings['ra_track_rate']) and abs(
                            need_step_position['dec'] - status['dp']) <= math.ceil(
                                15 * settings['dec_ticks_per_degree'] / (60.0 * 60.0)):
                break
            # TODO Acceleration
            ra_delta =need_step_position['ra'] - status['rp']
            if abs(ra_delta) < math.ceil(settings['ra_track_rate']) and not math.isclose(status['rs'], settings['ra_track_rate'], abs_tol=0.1):
                ra_set_speed(settings['ra_track_rate'])
            elif abs(ra_delta) < settings['ra_slew_fast']/3.0:
                # Need to go at least 2 * ra_track_rate
                speed = 3.0*ra_delta
                if abs(speed) < settings['ra_track_rate']:
                    speed = math.copysign(2*settings['ra_track_rate'], speed)
                ra_set_speed(speed)
            elif first:
                ra_set_speed(math.copysign(settings['ra_slew_slow'], ra_delta))
            elif abs(ra_delta) > settings['ra_slew_slow']:
                ra_set_speed(math.copysign(settings['ra_slew_fast'], ra_delta))

            dec_delta = need_step_position['dec'] - status['dp']
            if abs(dec_delta) < 15 * settings['dec_ticks_per_degree'] / (60.0 * 60.0):
                dec_set_speed(0.0)
            elif abs(dec_delta) < settings['dec_slew_fast']/3.0:
                dec_set_speed(3.0*dec_delta)
            elif first:
                dec_set_speed(math.copysign(settings['dec_slew_slow'], dec_delta))
            else:
                dec_set_speed(math.copysign(settings['dec_slew_fast'], dec_delta))
            first = False
            time.sleep(0.2)
            need_step_position = skycoord_to_steps(sync_info, wanted_skycoord)
            status = get_status()
        ra_set_speed(settings['ra_track_rate'])
        dec_set_speed(0.0)


def slew(ra, dec):
    """

    :param ra: float as deg
    :param dec: float as deg
    :return:
    """
    # TODO: Error conditions
    wanted_skycoord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    move_to_skycoord(runtime_settings['sync_info'], wanted_skycoord)


def move_to_skycoord(sync_info, wanted_skycoord):
    """
    Slew to position
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord, 'steps': {'ra': int, 'dec': int}
    :param wanted_skycoord: astropy.coordinates.SkyCoord
    :return:
    """
    global cancel_slew
    cancel_slew = True
    thread = threading.Thread(target=move_to_skycoord_threadf, args=(sync_info, wanted_skycoord))
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
    if dec:
        while deg > 90 or deg < -90:
            if deg > 90:
                deg = 90 - (deg-90)
            if deg < -90:
                deg = -90 - (deg + 90)
        return deg
    else:
        if deg < 0:
            while deg < 0:
                deg += 360.0
        elif deg > 360.0:
            deg = deg % 360
        return deg


def ra_deg_now(ra_deg, time_st):
    """
    Gives RA in degrees now if we didn't track since time.
    :param ra_deg: In degrees
    :param time_st: Time astropy.time.Time from when it stopped tracking
    :return:
    """
    now = astropy.time.Time.now()
    td = now - time_st
    td.format = 'sec'
    ra_deg = ra_deg - (td.value * SIDEREAL_RATE)
    ra_deg = clean_deg(ra_deg)
    return ra_deg


def sync(ra, dec):
    sync_info = {}
    status = get_status()

    sync_info['time'] = astropy.time.Time.now()
    sync_info['steps'] = {'ra': status['rp'], 'dec': status['dp']}
    coords = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    sync_info['coords'] = coords
    runtime_settings['sync_info'] = sync_info


def ra_deg_d(wanted, current):
    d_1 = wanted - current
    d_2 = 360.0 + wanted - current
    d_3 = wanted - (360 + current)

    return min([d_1, d_2, d_3], key=abs)


def skycoord_to_steps(sync_info, wanted_skycoord):
    """
    Gives steps needs to be at wanted_skycoord right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord, 'steps': {'ra': int, 'dec': int}
    :param wanted_skycoord: astropy.coordinates.SkyCoord
    :return: {'ra': steps_int, 'dec': steps_int}
    """
    d_ra = ra_deg_d(wanted_skycoord.icrs.ra.deg, ra_deg_now(sync_info['coords'].icrs.ra.deg, sync_info['time']))
    # TODO: For dec take into consideration, altitude, or dec limit
    d_dec = wanted_skycoord.icrs.dec.deg - sync_info['coords'].icrs.dec.deg

    steps_ra = sync_info['steps']['ra'] + d_ra * (settings['ra_track_rate'] / SIDEREAL_RATE)
    steps_dec = sync_info['steps']['dec'] + d_dec * settings['dec_ticks_per_degree']
    return {'ra': steps_ra, 'dec': steps_dec}


def steps_to_skycoord(sync_info, steps):
    """
    Gets sky coordinates if we are at steps right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoord, 'steps': [RA_int, DEC_int]
    :param steps: {'ra': steps_int, 'dec': steps_int}
    :return: SkyCoord
    """
    d_ra = (steps['ra'] - sync_info['steps']['ra']) / (settings['ra_track_rate'] / SIDEREAL_RATE)
    d_dec = (steps['dec'] - sync_info['steps']['dec']) / settings['dec_ticks_per_degree']
    ra_deg = ra_deg_now(sync_info['coords'].icrs.ra.deg, sync_info['time']) + d_ra
    ra_deg = clean_deg(ra_deg)

    dec_deg = clean_deg(sync_info['coords'].icrs.dec.deg + d_dec, dec=True)
    # print(ra_deg, dec_deg)
    coord = SkyCoord(ra=ra_deg * u.degree,
                     dec=dec_deg * u.degree,
                     frame='icrs')
    return coord
