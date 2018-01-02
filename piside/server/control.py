import threading
import time
from flask_socketio import SocketIO, emit
import queue
import json
import filelock
import serial
from functools import partial
import datetime
import re

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
settings = None
microserial=None
microseriallock = threading.RLock()
status_interval = None
socketio = None
inited = False


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


def send_status():
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
    #TODO: Might need to make a shorter status if transfer time longer than tracking tick interval
    #print(len(s))
    s = s.split()
    #print(s)
    status = {}
    for line in s:
        line_status = line.split(':')
        if len(line_status) == 2:
           status[line_status[0]] = line_status[1]
    #print(status)
    print('status'+str(datetime.datetime.now()))
    socketio.emit('status', status)


def init(osocketio, fsettings):
    global settings, microserial, microseriallock, status_interval, socketio, inited
    if inited:
        return
    inited = True
    print('Inited')
    settings = fsettings
    socketio = osocketio
    #Load settings file
    #Open serial port
    microserial = serial.Serial(settings['microserial']['port'], settings['microserial']['baud'], timeout=2)
    microserial.write(('set_var ra_max_tps %f\r' % settings['micro']['ra_max_tps']).encode())
    microserial.write(('set_var ra_guide_rate %f\r' % settings['micro']['ra_guide_rate']).encode())
    microserial.write(('set_var ra_direction %f\r' % settings['micro']['ra_direction']).encode())
    microserial.write(('set_var dec_max_tps %f\r' % settings['micro']['dec_max_tps']).encode())
    microserial.write(('set_var dec_guide_rate %f\r' % settings['micro']['dec_guide_rate']).encode())
    microserial.write(('set_var dec_direction %f\r' % settings['micro']['dec_direction']).encode())
    microserial.write(('ra_set_speed %f\r' % settings['ra_track_rate']).encode())
    status_interval = SimpleInterval(send_status, 1)


def manual_control(direction, speed):
    global microserial, microseriallock
    if direction not in ['left', 'right', 'up', 'down']:
        return
    # If not currently slewing somewhere else
    if direction in timers:
        timers[direction].cancel()
        del timers[direction]
    if not speed:
        if direction in ['left', 'right']:
            #TODO: if currently tracking (when would we not?)
            with microseriallock:
                microserial.write(('ra_set_speed %f\r' % settings['ra_track_rate']).encode())
            #else:
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
                    microserial.write(('ra_set_speed %f\r' % settings['ra_slew_'+speed]).encode())
            elif direction == 'right':
                microserial.write(('ra_set_speed -%f\r' % settings['ra_slew_' + speed]).encode())
            elif direction == 'up':
                print('Trying to do dec_set_speed')
                microserial.write(('dec_set_speed %f\r' % settings['dec_slew_' + speed]).encode())
            elif direction == 'down':
                microserial.write(('dec_set_speed -%f\r' % settings['dec_slew_' + speed]).encode())
            timers[direction] = threading.Timer(0.75, partial(manual_control, direction, None))
            timers[direction].start()
