import json
import fasteners
import threading
import os
import logging
import copy
import subprocess

_lock = threading.RLock()
_plock = threading.RLock()

with open('default_settings.json') as f:
    default_settings = json.load(f)


def deepupdate(to_update, odict):
    for k in to_update:
        if isinstance(to_update[k], dict) and k in odict and isinstance(odict[k], dict):
            deepupdate(to_update[k], odict[k])
        else:
            if k in odict:
                to_update[k] = odict[k]


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def write_settings(settings):
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/ssteq'])
    with _lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/ssteq'])



@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def read_settings():
    # print(default_settings)
    with _lock:
        if not os.path.isfile('settings.json'):
            return copy.deepcopy(default_settings)
        else:
            with open('settings.json') as f:
                s = json.load(f)
                s1 = copy.deepcopy(default_settings)
                deepupdate(s1, s)
                # print(json.dumps(s1))
                return s1


def is_simulation():
    return 'simulation' in settings and settings['simulation']


def last_parked():
    return os.path.isfile('last_parked')


def not_parked():
    if os.path.isfile('last_parked'):
        try:
            with _plock:
                os.unlink('last_parked')
        except:
            pass


def parked():
    if not os.path.isfile('last_parked'):
        try:
            with _plock:
                with open('last_parked', 'a') as f:
                    pass
        except:
            pass


settings = read_settings()


def get_logger(name):
    logger = logging.getLogger(name)
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    p = os.path.join('/home/pi/', 'logs')
    if not os.path.exists(p):
        os.makedirs(p)
    p = os.path.join(p, name + '.log')
    if len(logger.handlers) == 0:
        try:
            if os.stat(p).st_size > 10000000:
                os.remove(p)
        except:
            pass
        handler = logging.FileHandler(p)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


runtime_settings = {'time_been_set': False, 'earth_location': None, 'earth_location_set': True, 'sync_info': None,
                    'tracking': True, 'started_parked': False, 'calibration_logging': False}
