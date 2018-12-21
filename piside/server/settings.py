import json
import fasteners


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def write_settings(settings):
    with open('settings.json', mode='w') as f:
        json.dump(settings, f)


@fasteners.interprocess_locked('/tmp/ssteq_settings_lock')
def read_settings():
    with open('settings.json') as f:
        s = json.load(f)
        # TODO: Use a full hard coded defaults for keys for upgrades
        if 'horizon_limit_enabled' not in s:
            s['horizon_limit_enabled'] = False
        return s


def is_simulation():
    return 'simulation' in settings and settings['simulation']


settings = read_settings()
