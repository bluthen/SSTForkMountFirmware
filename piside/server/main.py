from flask import Flask, redirect, jsonify, request
from flask_socketio import SocketIO, emit
import json
import control
import threading
from eventlet import monkey_patch
import re
import sqlite3
import iso8601
import subprocess
import datetime

monkey_patch()

st_queue = None
app = Flask(__name__, static_url_path='/static', static_folder='../client/')
socketio = SocketIO(app, async_mode='eventlet', logger=True, engineio_logger=True)
settings = None
settings_json_lock = threading.RLock()
db_lock = threading.RLock()
conn = sqlite3.connect('ssteq.sqlite', check_same_thread=False)

runtime_settings = {'time_been_set': False, 'earth_location': None, 'sync_info': None}


@app.route('/')
def root():
    return redirect('/static/index.html')


@app.route('/settings')
def settings_get():
    return jsonify(settings)


@app.route('/settings', methods=['PUT'])
def settings_put():
    global settings
    print('settings_put')
    settings_buffer = {}
    args = json.loads(request.form['settings'])
    keys = ["ra_track_rate", "ra_slew_fast", "ra_slew_slow", "dec_slew_fast", "dec_slew_slow", "dec_ticks_per_degree",
            "ra_max_accel_tpss", "dec_max_accel_tpss"]
    for key in keys:
        if key in args:
            settings_buffer[key] = float(args[key])
    keys = ["ra_max_tps", "ra_guide_rate", "ra_direction", "dec_max_tps", "dec_guide_rate", "dec_direction"]
    for key in keys:
        if key in args:
            if 'micro' not in settings_buffer:
                settings_buffer['micro'] = {}
            settings_buffer['micro'][key] = float(args[key])

    keys = ["ra_track_rate", "ra_slew_fast", "ra_slew_slow", "dec_slew_fast", "dec_slew_slow", "dec_ticks_per_degree",
            "ra_max_accel_tpss", "dec_max_accel_tpss"]
    for key in keys:
        if key in args:
            settings[key] = float(settings_buffer[key])
    keys = ["ra_max_tps", "ra_guide_rate", "ra_direction", "dec_max_tps", "dec_guide_rate", "dec_direction"]
    for key in keys:
        if key in args:
            if 'micro' not in settings_buffer:
                settings_buffer['micro'] = {}
            settings['micro'][key] = float(settings_buffer['micro'][key])
    with settings_json_lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)
    control.micro_update_settings()
    print('return')
    return '', 204


@app.route('/set_location', methods=['PUT'])
def set_location():
    location = request.form.get('location', None)
    location = json.loads(location)
    if 'lat' not in location or 'long' not in location or 'name' not in location:
        return 'Missing arguments', 400
    location = {'lat': str(location['lat']), 'long': str(location['long']), 'name': str(location['name'])}
    control.update_location(location)
    settings['location'] = location
    with settings_json_lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)
    return 'Set Location', 200


@app.route('/sync', methods=['PUT'])
def do_sync():
    ra = float(request.form.get('ra', None))
    dec = float(request.form.get('dec', None))
    control.sync(ra, dec)
    return 'Synced', 200


@app.route('/slewto', methods=['PUT'])
def do_slewto():
    ra = float(request.form.get('ra', None))
    dec = float(request.form.get('dec', None))
    control.slew(ra, dec)
    return 'Slewing', 200


@app.route('/slewto', methods=['DELETE'])
def stop_slewto():
    control.cancel_slews()
    return 'Stopping Slew', 200


@app.route('/set_time', methods=['PUT'])
def set_time():
    s = datetime.datetime.now()
    time = request.form.get('time', None)
    overwrite = request.form.get('overwrite', None)
    if runtime_settings['time_been_set'] and not overwrite:
        return 'Already Set', 200
    d = iso8601.parse_date(time)
    ntpstat = subprocess.run(['/usr/bin/ntpstat'])
    if ntpstat.returncode != 0:
        d = d + (datetime.datetime.now() - s)
        time = d.isoformat()
        daterun = subprocess.run(['/usr/bin/sudo', '/bin/date', '-s', time])
        if daterun.returncode == 0:
            runtime_settings['time_been_set'] = True
            return 'Date Set', 200
        else:
            return 'Failed to set date', 500
    runtime_settings['time_been_set'] = True
    return 'NTP Set', 200


@app.route('/search_object', methods=['GET'])
def search_object():
    search = request.args.get('search', None)
    if not search:
        return
    dso_search = search
    star_search = search
    if re.match(r'.*\d+$', search):
        dso_search = '%' + dso_search + '|%'
        star_search = '%' + star_search
    else:
        dso_search = '%' + dso_search + '%'
        star_search = '%' + star_search + '%'
    # catalogs = {'IC': ['IC'], 'NGC': ['NGC'], 'M': ['M', 'Messier'], 'Pal': ['Pal'], 'C': ['C', 'Caldwell'], 'ESO': ['ESO'], 'UGC': ['UGC'], 'PGC': ['PGC'], 'Cnc': ['Cnc'], 'Tr': ['Tr'], 'Col': ['Col'], 'Mel': ['Mel'], 'Harvard': ['Harvard'], 'PK': ['PK']}
    with db_lock:
        cur = conn.cursor()
        cur.execute('SELECT * from dso where search like ? limit 10', (dso_search,))
        dso = cur.fetchall()
        cur.execute('SELECT * from stars where bf like ? or proper like ? limit 10', (star_search, star_search))
        stars = cur.fetchall()
        cur.close()
    return jsonify({'dso': dso, 'stars': stars})


@app.route('/search_location', methods=['GET'])
def search_location():
    search = request.args.get('search', None)
    if not search:
        return
    search = search.strip()
    # If zipcode search
    if re.match(r'\d+$', search):
        search = search + '%'
        with db_lock:
            cur = conn.cursor()
            cur.execute('SELECT * from uscities where postalcode like ? limit 20', (search,))
            cities = cur.fetchall()
            cur.close()
            return jsonify({'cities': cities})
    else:
        cstate = search.split(',')
        if len(cstate) == 1:
            # Just search city
            city = cstate[0]
            city = city.strip()
            search = city + '%'
            cur = conn.cursor()
            cur.execute('SELECT * from uscities where city like ? limit 20', (search,))
            cities = cur.fetchall()
            cur.close()
            return jsonify({'cities': cities})
        else:
            city = cstate[0]
            state = cstate[1]

            city = city.strip()
            state = state.strip()
            # If using state abbreviation
            if len(state) == 2:
                abbr = state.upper()
                cur = conn.cursor()
                city = city + '%'
                cur.execute('SELECT * from uscities where city like ? and state_abbr = ? limit 20', (city, abbr))
                cities = cur.fetchall()
                cur.close()
                return jsonify({'cities': cities})
            else:
                # State must be full name
                cur = conn.cursor()
                city = city + '%'
                state = state + '%'
                cur.execute('SELECT * from uscities where city like ? and state like ? limit 20', (city, state))
                cities = cur.fetchall()
                cur.close()
                return jsonify({'cities': cities})


@socketio.on('manual_control')
def manual_control(message):
    emit('controls_response', {'data': 33})
    print("Got %s" + json.dumps(message))
    control.manual_control(message['direction'], message['speed'])
    emit('controls_response', {'data': 33})


def main():
    global st_queue, settings
    with settings_json_lock:
        with open('settings.json') as f:
            settings = json.load(f)
    st_queue = control.init(socketio, settings, runtime_settings)
    print('Running...')
    socketio.run(app, host="0.0.0.0", debug=True, log_output=True, use_reloader=False)


if __name__ == '__main__':
    main()
