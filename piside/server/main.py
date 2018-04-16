from flask import Flask, redirect, jsonify, request, make_response, url_for, send_from_directory
from flask_socketio import SocketIO, emit
from functools import wraps, update_wrapper
import json
import control
import threading
from eventlet import monkey_patch
import re
import sqlite3
import iso8601
import subprocess
import datetime
import sys
import traceback
import tempfile
import zipfile
from astropy.utils import iers
import astropy.time
import astropy.coordinates
from astropy.coordinates import solar_system_ephemeris
import astropy.units as u
import stellarium_server
import math
import os
iers.conf.auto_download = False

monkey_patch()

st_queue = None
app = Flask(__name__, static_folder='../client/')
socketio = SocketIO(app, async_mode='eventlet', logger=False, engineio_logger=False)
settings = None
settings_json_lock = threading.RLock()
db_lock = threading.RLock()
conn = sqlite3.connect('ssteq.sqlite', check_same_thread=False)

runtime_settings = {'time_been_set': False, 'earth_location': None, 'sync_info': None, 'tracking': True}


@app.context_processor
def override_url_for():
    """
    Generate a new token on every request to prevent the browser from
    caching static files.
    """
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)

@app.route('/static/<path:path>')
@nocache
def send_static(path):
    return send_from_directory('../client', path)

@app.route('/')
@nocache
def root():
    return redirect('/static/index.html')


@app.route('/version')
@nocache
def version():
    return jsonify({"version": "0.0.6"})


@app.route('/settings')
@nocache
def settings_get():
    return jsonify(settings)


@app.route('/settings', methods=['PUT'])
@nocache
def settings_put():
    global settings
    print('settings_put')
    settings_buffer = {}
    args = json.loads(request.form['settings'])
    keys = ["ra_track_rate", "dec_ticks_per_degree", "ra_slew_fastest", "ra_slew_faster", "ra_slew_medium", "ra_slew_slower", "ra_slew_slowest",
            "dec_slew_fastest", "dec_slew_faster", "dec_slew_medium", "dec_slew_slower", "dec_slew_slowest",
            ]
    for key in keys:
        if key in args:
            settings_buffer[key] = float(args[key])
    keys = ["ra_max_tps", "ra_guide_rate", "ra_direction", "dec_guide_rate", "dec_direction"]
    for key in keys:
        if key in args:
            if 'micro' not in settings_buffer:
                settings_buffer['micro'] = {}
            settings_buffer['micro'][key] = float(args[key])

    keys = ["ra_track_rate", "ra_slew_fastest", "ra_slew_faster", "ra_slew_medium", "ra_slew_slower", "ra_slew_slowest",
            "dec_slew_fastest", "dec_slew_faster", "dec_slew_medium", "dec_slew_slower", "dec_slew_slowest",
            "dec_ticks_per_degree"]
    for key in keys:
        if key in args:
            settings[key] = settings_buffer[key]
    keys = ["ra_guide_rate", "ra_direction", "dec_guide_rate", "dec_direction"]
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


@app.route('/set_location', methods=['DELETE'])
@nocache
def unset_location():
    settings['location'] = None
    runtime_settings['earth_location'] = None
    with settings_json_lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)
    return 'Unset Location', 200


@app.route('/set_location', methods=['PUT'])
@nocache
def set_location():
    location = request.form.get('location', None)
    location = json.loads(location)
    print(location)
    if 'lat' not in location or 'long' not in location or 'name' not in location and location['name'].strip() != '':
        return 'Missing arguments', 400
    location = {'lat': float(location['lat']), 'long': float(location['long']), 'name': str(location['name'])}
    old_location = settings['location']
    settings['location'] = location
    try:
        control.update_location()
    except:
        settings['location'] = old_location
        traceback.print_exc(file=sys.stdout)
        return 'Invalid location', 400
    with settings_json_lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)
    return 'Set Location', 200


@app.route('/sync', methods=['PUT'])
@nocache
def do_sync():
    ra = request.form.get('ra', None)
    dec = request.form.get('dec', None)
    alt = request.form.get('alt', None)
    az = request.form.get('az', None)
    if alt is not None and az is not None:
        alt = float(alt)
        az = float(az)
        coord = astropy.coordinates.SkyCoord(alt=alt * u.deg,
                                             az=az * u.deg, frame='altaz',
                                             obstime=astropy.time.Time.now(),
                                             location=runtime_settings['earth_location'])
        ra = coord.icrs.ra.deg
        dec = coord.icrs.dec.deg
    ra = float(ra)
    dec = float(dec)
    last_sync = None
    if 'sync_info' in runtime_settings:
        last_sync = runtime_settings['sync_info']
    control.sync(ra, dec)
    err = {'ra_error': None, 'dec_error': None}
    if last_sync:
        err = control.two_sync_calc_error(last_sync, runtime_settings['sync_info'])
    if err['ra_error'] is not None and math.isnan(err['ra_error']):
        err['ra_error'] = None
    if err['dec_error'] is not None and math.isnan(err['dec_error']):
        err['dec_error'] = None
    return jsonify(err)


@app.route('/slewto', methods=['PUT'])
@nocache
def do_slewto():
    ra = request.form.get('ra', None)
    dec = request.form.get('dec', None)
    alt = request.form.get('alt', None)
    az = request.form.get('az', None)
    ra_steps = request.form.get('ra_steps', None)
    dec_steps = request.form.get('dec_steps', None)
    parking = False
    if ra_steps is not None and dec_steps is not None:
        control.slew_to_steps(int(ra_steps), int(dec_steps))
        return 'Slewing', 200
    elif alt is not None and az is not None:
        alt = float(alt)
        az = float(az)
        coord = astropy.coordinates.SkyCoord(alt=alt * u.deg,
                                             az=az * u.deg, frame='altaz',
                                             obstime=astropy.time.Time.now(),
                                             location=runtime_settings['earth_location'])
        ra = coord.icrs.ra.deg
        dec = coord.icrs.dec.deg
        parking = True
    ra = float(ra)
    dec = float(dec)
    if not control.slewtocheck(ra, dec):
        return 'Slew position is below horizon or in keep-out area.', 400
    else:
        control.slew(ra, dec, parking)
        return 'Slewing', 200


@app.route('/slewto_check', methods=['PUT'])
@nocache
def do_slewtocheck():
    ra = float(request.form.get('ra', None))
    dec = float(request.form.get('dec', None))
    return jsonify({'slewcheck': control.slewtocheck(ra, dec)})


@app.route('/slewto', methods=['DELETE'])
@nocache
def stop_slewto():
    control.cancel_slews()
    return 'Stopping Slew', 200


@app.route('/set_time', methods=['PUT'])
@nocache
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


@app.route('/set_park_position', methods=['PUT'])
@nocache
def set_park_position():
    if runtime_settings['sync_info'] is None:
        return 'You must have synced once before setting park position.', 400
    if not runtime_settings['earth_location']:
        return 'You must set location before setting park position.', 400
    status = control.get_status()
    coord = control.steps_to_skycoord(runtime_settings['sync_info'], {'ra': status['rp'], 'dec': status['dp']},
                                      astropy.time.Time.now(), settings['ra_track_rate'],
                                      settings['dec_ticks_per_degree'])
    altaz = control.to_altaz_asdeg(coord)
    settings['park_position'] = altaz
    with settings_json_lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)
    return 'Park Position Set', 200


@app.route('/set_park_position', methods=['DELETE'])
@nocache
def unset_park_position():
    settings['park_position'] = None
    with settings_json_lock:
        with open('settings.json', mode='w') as f:
            json.dump(settings, f)
    return 'Park Position Unset', 200


@app.route('/park', methods=['PUT'])
@nocache
def do_park():
    # TODO: If started parked we can use 0,0
    if not runtime_settings['earth_location']:
        return 'Location not set', 400
    if not settings['park_position']:
        return 'No park position has been set.', 400
    if not runtime_settings['sync_info']:
        return 'No sync info has been set.', 400
    runtime_settings['tracking'] = False
    control.ra_set_speed(0)
    coord = astropy.coordinates.SkyCoord(alt=settings['park_position']['alt'] * u.deg,
                                         az=settings['park_position']['az'] * u.deg, frame='altaz',
                                         obstime=astropy.time.Time.now(), location=runtime_settings['earth_location'])
    coord = astropy.coordinates.SkyCoord(ra=coord.icrs.ra, dec=coord.icrs.dec, frame='icrs')
    control.move_to_skycoord(runtime_settings['sync_info'], coord.icrs, True)
    return 'Parking.', 200


@app.route('/start_tracking', methods=['PUT'])
@nocache
def start_tracking():
    runtime_settings['tracking'] = True
    control.ra_set_speed(settings['ra_track_rate'])
    return 'Tracking', 200


@app.route('/stop_tracking', methods=['PUT'])
@nocache
def stop_tracking():
    runtime_settings['tracking'] = False
    control.ra_set_speed(0)
    return 'Stopped Tracking', 200


def to_list_of_lists(tuple_of_tuples):
    b = [list(x) for x in tuple_of_tuples]
    return b


@app.route('/search_object', methods=['GET'])
@nocache
def search_object():
    do_altaz = True
    search = request.args.get('search', None)
    if not search:
        return
    planet_search = search.lower()
    bodies = solar_system_ephemeris.bodies
    planets = []
    for body in bodies:
        if body.find('earth') != -1:
            continue
        if body.find(planet_search) != -1:
            coord = astropy.coordinates.get_body(body, astropy.time.Time.now(),
                                                 location=runtime_settings['earth_location'])
            ra = coord.ra.deg
            dec = coord.dec.deg
            coord = astropy.coordinates.SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
            if do_altaz:
                altaz = control.to_altaz_asdeg(coord)
            else:
                altaz = {'alt': None, 'az': None}
            planets.append(
                [body.title(), coord.icrs.ra.deg * 24.0 / 360.0, coord.icrs.dec.deg, altaz['alt'], altaz['az']])
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
    dso = to_list_of_lists(dso)
    stars = to_list_of_lists(stars)
    # Alt az
    for ob in dso:
        if do_altaz:
            coord = astropy.coordinates.SkyCoord(ra=(360.0 / 24.0) * float(ob[0]) * u.deg, dec=float(ob[1]) * u.deg,
                                                 frame='icrs')
            altaz = control.to_altaz_asdeg(coord)
        else:
            altaz = {'alt': None, 'az': None}
        ob.append(altaz['alt'])
        ob.append(altaz['az'])
    for ob in stars:
        if do_altaz:
            coord = astropy.coordinates.SkyCoord(ra=(360.0 / 24.0) * float(ob[7]) * u.deg, dec=float(ob[8]) * u.deg,
                                                 frame='icrs')
            altaz = control.to_altaz_asdeg(coord)
        else:
            altaz = {'alt': None, 'az': None}
        ob.append(altaz['alt'])
        ob.append(altaz['az'])

    return jsonify({'dso': dso, 'stars': stars, 'planets': planets})


def reboot():
    return subprocess.run(['/usr/bin/sudo', '/sbin/reboot'])


@app.route('/firmware_update', methods=['POST'])
@nocache
def firmware_update():
    file = request.files['file']
    with tempfile.TemporaryFile(suffix='.zip') as tfile:
        file.save(tfile)
        tfile.seek(0)
        zip_ref = zipfile.ZipFile(tfile)
        zip_ref.extractall('/home/pi/SSTForkMountFirmware/piside')
    t = threading.Timer(5, reboot)
    t.start()
    return 'Updated'


@app.route('/search_location', methods=['GET'])
@nocache
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

    # TODO: Config if start stellarium server.
    stellarium_thread = threading.Thread(target=stellarium_server.run)
    stellarium_thread.start()


    print('Running...')
    socketio.run(app, host="0.0.0.0", debug=False, log_output=False, use_reloader=False)
    stellarium_server.terminate()
    stellarium_thread.join()


if __name__ == '__main__':
    main()
