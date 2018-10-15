import json
import fasteners


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def write_settings(settings):
    with open('settings.json', mode='w') as f:
        json.dump(settings, f)


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def read_settings():
    with open('settings.json') as f:
        return json.load(f)


def is_simulation():
    return 'simulation' in settings and settings['simulation']


settings = read_settings()
