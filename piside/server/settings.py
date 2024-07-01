import json
import fasteners
import threading
import os
import logging
import copy
import shutil
import subprocess
import pickle

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
def write_settings(arg_settings):
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/ssteq'])
    with _lock:
        with open('settings.json', mode='w') as f_settings:
            json.dump(arg_settings, f_settings)
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/ssteq'])


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def save_pointing_model(model):
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/ssteq'])
    with _lock:
        with open('model.pickle', mode='wb') as f_model:
            pickle.dump(model, f_model)
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/ssteq'])


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def rm_pointing_model():
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/ssteq'])
    with _lock:
        os.remove('model.pickle')
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/ssteq'])


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def load_pointing_model():
    model = None
    with _lock:
        if os.path.isfile('model.pickle'):
            with open('model.pickle', mode='rb') as f_model:
                model = pickle.load(f_model)
    return model


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def copy_settings(tfile):
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/ssteq'])
    with _lock:
        with open('settings.json', mode='wb') as sfile:
            shutil.copyfileobj(tfile, sfile)
    if not is_simulation():
        subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/ssteq'])


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def read_settings():
    # print(default_settings)
    with _lock:
        if not os.path.isfile('settings.json'):
            return copy.deepcopy(default_settings)
        else:
            with open('settings.json') as f_settings:
                s = json.load(f_settings)
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
                with open('last_parked', 'a') as f_last_parked:
                    pass
        except:
            pass


settings = read_settings()


def get_logger(name):
    logger = logging.getLogger(name)
    abspath = os.path.abspath(__file__)
    # dname = os.path.dirname(abspath)
    p = os.path.join(os.path.expanduser('~'), 'logs')
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


runtime_settings = {'time_from_gps': False, 'earth_location_from_gps': False, 'earth_location': None, 'sync_info': None,
                    'tracking': True, 'started_parked': False, 'calibration_logging': False, 'last_locationtz': None}
