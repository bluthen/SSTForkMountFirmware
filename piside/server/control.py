import threading
import serial
from functools import partial
import time

import datetime
import astropy
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
            status[line_status[0]] = line_status[1]
    # print(status)
    print('status' + str(datetime.datetime.now()))
    return status


def update_location():
    el = astropy.coordinates.EarthLocation(lat=settings['location']['lat'] * u.deg, lon=['location']['long'] * u.deg,
                                           heigh=760.0 * u.m)
    runtime_settings['earth_location'] = el


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
        if runtime_settings['earth_location']:
            altaz = astropy.coordinates.SkyCoord(coord, obstime=astropy.time.Time.now(), location=runtime_settings['earth_location']).altaz
            status['alt'] = altaz.alt.deg
            status['az'] = altaz.az.deg

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
        microserial.write(('ra_set_speed %f\r' % settings['ra_slew_' + speed]).encode())


def dec_set_speed(speed):
    with microseriallock:
        microserial.write(('ra_set_speed %f\r' % settings['ra_slew_' + speed]).encode())


def move_to_skycoord_calc2(move_info, a, set_speed_func):
    t = astropy.time.Time.now() - move_info['lasttime']
    t.format = 'sec'
    t = t.value
    if abs(move_info['v0']) < move_info['max_speed']:
        move_info['steps'] += t * move_info['v0']
        old_v0 = move_info['v0']
        move_info['v0'] = calc_speed(a, move_info['v0'], t)
        if abs(move_info['v0']) > move_info['max_speed']:
            move_info['v0'] = math.copysign(move_info['max_speed'], move_info['v0'])
        if old_v0 != move_info['v0']:
            set_speed_func(move_info['v0'])
        move_info['lasttime'] = astropy.time.Time.now()
    else:
        move_info['steps'] += t * move_info['v0']
        move_info['lasttime'] = astropy.time.Time.now()


def move_to_skycoord_calc(move_info, set_speed_func):
    steps = move_info['wanted_steps'] - move_info['steps']
    dsteps = steps_needed_to_deaccelerate(-move_info['a'], move_info['v0'], move_info['vi'])
    if abs(steps) - abs(dsteps) <= 0:
        # Start slowing down
        move_to_skycoord_calc2(move_info, -move_info['a'], set_speed_func)
    else:
        move_to_skycoord_calc2(move_info, move_info['a'], set_speed_func)


def move_to_skycoord_threadf(sync_info, wanted_skycoord):
    global cancel_slew
    with slew_lock:
        cancel_slew = False
        need_step_position = skycoord_to_steps(sync_info, wanted_skycoord)
        status = get_status()

        ra_info = {'lasttime': astropy.time.Time.now(), 'a': 0, 'vi': 0, 'v0': 0,
                   'wanted_steps': need_step_position['ra'],
                   'max_speed': settings['ra_slew_fast']}

        dec_info = {'lasttime': ra_info['lasttime'], 'a': 0, 'vi': 0, 'v0': 0,
                    'wanted_steps': need_step_position['dec'],
                    'max_speed': settings['ra_slew_fast']}

        ra_info['a'] = math.copysign(settings['ra_max_accel_tpss'], need_step_position['ra'] - status['rp'])
        dec_info['a'] = math.copysign(settings['dec_max_accel_tpss'], need_step_position['dec'] - status['dp'])

        ra_info['vi'] = settings['ra_track_rate']
        dec_info['vi'] = 0.0

        ra_info['v0'] = status['rs']
        dec_info['v0'] = status['ds']

        ra_info['steps'] = status['rp']
        dec_info['steps'] = status['dp']

        loop_count = 0
        while not cancel_slew:
            if abs(ra_info['wanted_steps'] - ra_info['steps']) <= math.ceil(settings['ra_track_rate']) and abs(
                            dec_info['wanted_steps'] - dec_info['steps']) <= math.ceil(
                                15 * settings['dec_ticks_per_degree'] / (60.0 * 60.0)):
                break
            move_to_skycoord_calc(ra_info, ra_set_speed)
            move_to_skycoord_calc(dec_info, dec_set_speed)
            loop_count += 1
            time.sleep(0.2)
            need_step_position = skycoord_to_steps(sync_info, wanted_skycoord)
            status = get_status()
            ra_info['wanted_steps'] = need_step_position['ra']
            dec_info['wanted_steps'] = need_step_position['dec']
            ra_info['v0'] = status['rs']
            dec_info['v0'] = status['ds']
            ra_info['steps'] = status['rp']
            dec_info['steps'] = status['dp']

        # When we are done set back to tracking rate
        ra_set_speed(settings['ra_track_rate'])
        dec_set_speed(0.0)


def slew(ra, dec):
    """

    :param ra: float as deg
    :param dec: float as deg
    :return:
    """
    # TODO: Error conditions
    wanted_skycoord = astropy.coordinates.SkyCoord(ra=ra * u.deg, dec=dec * u.deg, format='icrs')
    move_to_skycoord(runtime_settings['sync_info'], wanted_skycoord)


def move_to_skycoord(sync_info, wanted_skycoord):
    """
    Slew to position
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoords, 'steps': {'ra': int, 'dec': int}
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


def deg_d(wanted, current):
    d_1 = wanted - current
    d_2 = 360.0 + wanted - current
    d_3 = wanted - (360 + current)

    return min([d_1, d_2, d_3], key=abs)


def clean_deg(deg):
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
    coords = astropy.coordinates.SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    sync_info['coords'] = coords
    runtime_settings['sync_info'] = sync_info


def skycoord_to_steps(sync_info, wanted_skycoord):
    """
    Gives steps needs to be at wanted_skycoord right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoords, 'steps': {'ra': int, 'dec': int}
    :param wanted_skycoord: astropy.coordinates.SkyCoord
    :return: {'ra': steps_int, 'dec': steps_int}
    """
    d_ra = deg_d(wanted_skycoord.icrs.ra.deg, ra_deg_now(sync_info['coords'].icrs.ra.deg, sync_info['time']))
    # TODO: For dec take into consideration, altitude, or dec limit
    d_dec = deg_d(wanted_skycoord.icrs.dec.deg, sync_info['coords'].icrs.dec.deg)

    steps_ra = sync_info['steps']['ra'] + d_ra * (settings['ra_track_rate'] / SIDEREAL_RATE)
    steps_dec = sync_info['steps']['ra'] + d_dec * settings['dec_ticks_per_degree']
    return {'ra': steps_ra, 'dec': steps_dec}


def steps_to_skycoord(sync_info, steps):
    """
    Gets sky coordinates if we are at steps right now.
    :param sync_info: has keys 'time': astropy.time.Time, 'coords': astropy.coordinates.SkyCoords, 'steps': [RA_int, DEC_int]
    :param steps: {'ra': steps_int, 'dec': steps_int}
    :return: SkyCoord
    """
    d_ra = (steps['ra'] - sync_info['steps']['ra']) / (settings['ra_track_rate'] / SIDEREAL_RATE)
    d_dec = (steps['dec'] - sync_info['steps']['dec']) / settings['dec_steps_per_degree']
    ra_deg = ra_deg_now(sync_info['coords'].icrs.ra.deg, sync_info['time']) + d_ra
    ra_deg = clean_deg(ra_deg)

    dec_deg = clean_deg(sync_info['coords'].icrs.ra.deg + d_dec)

    coord = astropy.coordinates.SkyCoord(ra=ra_deg * u.degree,
                                         dec=dec_deg * u.degree,
                                         frame='icrs')
    return coord
