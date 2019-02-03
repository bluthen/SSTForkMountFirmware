import json
import fasteners
import threading
import os
_lock = threading.RLock()
_plock = threading.RLock()

with open('default_settings.json') as f:
    default_settings = json.load(f)


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def write_settings(settings):
    with _lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def read_settings():
    with _lock:
        if not os.path.isfile('settings.json'):
            return default_settings.copy()
        else:
            with open('settings.json') as f:
                s = json.load(f)
                s1 = default_settings.copy()
                s1.update(s)
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
