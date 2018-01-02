import threading
import time
from flask_socketio import SocketIO, emit
import queue
import json
import filelock
import serial
from functools import partial

timers = {}
OPPOSITE_MANUAL = {'left': 'right', 'right': 'left', 'up': 'down', 'down': 'up'}
settings=None
microserial=None
microseriallock = threading.RLock()


def init():
    global settings
    #Load settings file
    with filelock.FileLock('settings.json.lock'):
        with open('settings.json') as f:
            settings = json.load(f)
    #Open serial port
    # microserial = serial.Serial(settings['microserial']['port'], settings['microserial']['baud'])
    # microserial.write(('set_var ra_max_tps=%f\r' % settings['micro']['ra_max_tps']).encode())
    # microserial.write(('set_var ra_guide_rate=%f\r' % settings['micro']['ra_guide_rate']).encode())
    # microserial.write(('set_var ra_direction=%f\r' % settings['micro']['ra_direction']).encode())
    # microserial.write(('set_var dec_max_tps=%f\r' % settings['micro']['dec_max_tps']).encode())
    # microserial.write(('set_var dec_guide_rate=%f\r' % settings['micro']['dec_guide_rate']).encode())
    # microserial.write(('set_var dec_direction=%f\r' % settings['micro']['dec_direction']).encode())


def manual_control(direction, speed):
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
                microserial.write(('ra_set_speed %f' % settings['ra_track_rate']).encode())
            #else:
            # ra_set_speed 0
            pass
        else:
            with microseriallock:
                microserial.write(b'dec_set-speed 0')
    else:
        # If not current manually going other direction
        if timers[OPPOSITE_MANUAL[direction]]:
            return
        if direction == 'left':
            with microseriallock:
                microserial.write(('ra_set_speed %f' % settings['ra_slew_'+speed]).encode())
        elif direction == 'right':
            microserial.write(('ra_set_speed -%f' % settings['ra_slew_' + speed]).encode())
        elif direction == 'up':
            microserial.write(('dec_set_speed %f' % settings['dec_slew_' + speed]).encode())
        elif direction == 'down':
            microserial.write(('dec_set_speed -%f' % settings['dec_slew_' + speed]).encode())
        threading.Timer(0.75, partial(manual_control, direction, None))
