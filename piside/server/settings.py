import json
import fasteners

with open('default_settings.json') as f:
    default_settings = json.load(f)


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def write_settings(settings):
    with open('settings.json', mode='w') as f:
        json.dump(settings, f)


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def read_settings():
    with open('settings.json') as f:
        s = json.load(f)
        s1 = default_settings.copy()
        s1.update(s)
        return s1


def is_simulation():
    return 'simulation' in settings and settings['simulation']


settings = read_settings()
