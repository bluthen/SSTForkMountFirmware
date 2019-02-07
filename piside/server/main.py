from astropy.utils import iers
import astropy.time
import astropy.coordinates
from astropy.coordinates import solar_system_ephemeris, SkyCoord
import astropy.units as u
from astropy.time import Time as AstroTime
import time

from flask import Flask, redirect, jsonify, request, make_response, url_for, send_from_directory
from flask_socketio import SocketIO, emit
from functools import wraps, update_wrapper
import json
import control
import threading
import re
import sqlite3
import iso8601
import subprocess
import datetime
import traceback
import tempfile
import zipfile
import stellarium_server
import math
import os
import settings
import sstchuck
import network
import sys

from werkzeug.serving import make_ssl_devcert

iers.conf.auto_download = False

paa_process_lock = threading.RLock()
paa_process = None
paa_count = 0

power_thread_quit = False

st_queue = None
app = Flask(__name__, static_folder='../client_refactor/dist/')
socketio = SocketIO(app, async_mode='threading', logger=False, engineio_logger=False)
settings_json_lock = threading.RLock()
db_lock = threading.RLock()
conn = sqlite3.connect('ssteq.sqlite', check_same_thread=False)

runtime_settings = {'time_been_set': False, 'earth_location': None, 'earth_location_set': True, 'sync_info': None,
                    'tracking': True}


# Sets up power switch
# TODO: disable power switch for simulation
def run_power_switch():
    try:
        import RPi.GPIO as GPIO
        RELAY_PIN = 6
        SWITCH_PIN = 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.output(RELAY_PIN, True)

        while not power_thread_quit:
            time.sleep(0.1)
            if GPIO.input(SWITCH_PIN):
                continue
            time.sleep(0.1)
            if not GPIO.input(SWITCH_PIN):
                subprocess.run(['sudo', 'shutdown', '-h', 'now'])

    except ImportError:
        # We are probably in simulation
        print("Warning: Can't use power switch.")


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
    return send_from_directory('../client_refactor/dist', path)


@app.route('/')
@nocache
def root():
    return redirect('/static/index.html')


@app.route('/version')
@nocache
def version():
    return jsonify({"version": "0.0.11"})


@app.route('/settings')
@nocache
def settings_get():
    return jsonify(settings.settings)


@app.route('/shutdown', methods=['PUT'])
@nocache
def shutdown_put():
    control.stepper.set_speed_ra(0.0)
    control.stepper.set_speed_dec(0.0)
    time.sleep(0.25)
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])
    return 'Shutdown', 204


@app.route('/settings', methods=['PUT'])
@nocache
def settings_put():
    print('settings_put')
    settings_buffer = {}
    args = json.loads(request.form['settings'])
    keys = ["ra_track_rate", "dec_ticks_per_degree", "ra_slew_fastest", "ra_slew_faster", "ra_slew_medium",
            "ra_slew_slower", "ra_slew_slowest",
            "dec_slew_fastest", "dec_slew_faster", "dec_slew_medium", "dec_slew_slower", "dec_slew_slowest",
            "time_autosync", "polar_align_camera_rotation_x", "polar_align_camera_rotation_y"
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

    keys = ["atmos_refract"]
    for key in keys:
        if key in args:
            settings_buffer[key] = bool(args[key])

    keys = ["color_scheme"]
    for key in keys:
        if key in args:
            settings_buffer[key] = str(args[key])

    keys = ["color_scheme", "atmos_refract", "ra_track_rate", "ra_slew_fastest", "ra_slew_faster", "ra_slew_medium",
            "ra_slew_slower", "ra_slew_slowest", "dec_slew_fastest", "dec_slew_faster", "dec_slew_medium",
            "dec_slew_slower", "dec_slew_slowest", "dec_ticks_per_degree", "time_autosync",
            "polar_align_camera_rotation_x", "polar_align_camera_rotation_y"]
    for key in keys:
        if key in args:
            settings.settings[key] = settings_buffer[key]
    keys = ["ra_guide_rate", "ra_direction", "dec_guide_rate", "dec_direction"]
    for key in keys:
        if key in args:
            if 'micro' not in settings_buffer:
                settings_buffer['micro'] = {}
            settings.settings['micro'][key] = float(settings_buffer['micro'][key])
    settings.write_settings(settings.settings)
    control.micro_update_settings()
    print('return')
    return '', 204


@app.route('/settings_horizon_limit', methods=['PUT'])
@nocache
def settings_horizon_limit():
    enabled = request.form.get('horizon_limit_enabled', None)
    points = request.form.get('points', None)
    if not points and enabled is None:
        return 'Missing points/enable', 400
    if enabled:
        enabled = enabled == 'true'
        settings.settings['horizon_limit_enabled'] = enabled
        settings.write_settings(settings.settings)
    if points:
        points = json.loads(points)
        settings.settings['horizon_limit_points'] = points
        settings.write_settings(settings.settings)
    return 'Saved', 204


@app.route('/settings_network_ethernet', methods=['PUT'])
@nocache
def settings_network_ethernet():
    dhcp_server = request.form.get('dhcp_server', None)
    if dhcp_server:
        dhcp_server = dhcp_server.lower() == 'true'
    else:
        dhcp_server = False

    ip = request.form.get('ip', None)
    netmask = request.form.get('netmask', None)

    if None not in (dhcp_server, ip, netmask):
        network.set_ethernet_dhcp_server(dhcp_server)
        network.set_ethernet_static(ip, netmask)
        settings.settings['network']['ip'] = ip
        settings.settings['network']['netmask'] = ip
        settings.settings['network']['dhcp_server'] = ip
    return 'Saved', 204


@app.route('/settings_network_wifi', methods=['PUT'])
@nocache
def settings_network_wifi():
    ssid = request.form.get('ssid', None)
    wpa2key = request.form.get('wpa2key', None)
    channel = request.form.get('channel', None)

    if None in [ssid, channel]:
        return 'Invalid parameters', 400

    if wpa2key and len(wpa2key) < 8 or len(wpa2key) > 63:
        return 'Invalid WPA2Key, must be between eight and 63 characters', 400
    try:
        channel = int(channel)
    except ValueError:
        return 'Invalid channel', 400
    if channel < 1 or channel > 14:
        return 'Invalid channel', 400
    if len(ssid) > 31:
        return 'SSID must be less than 32 characters', 400
    network.hostapd_write(ssid, channel, wpa2key)
    # Stop hostapd and dnsmasq let autohotspot go
    if not settings.is_simulation():
        subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'wlan0', 'disable'])
        subprocess.run(['sudo', '/usr/bin/killall', 'hostapd'])
        subprocess.run(['sudo', '/usr/bin/autohotspotcron'])
    settings.settings['network']['ssid'] = ssid
    settings.settings['network']['wpa2key'] = wpa2key
    settings.settings['network']['channel'] = channel
    settings.write_settings(settings.settings)
    return "Saved", 200


@app.route('/wifi_connect', methods=['DELETE'])
@nocache
def wifi_connect_delete():
    ssid = request.form.get('ssid', None)
    mac = request.form.get('mac', None)
    if None in [ssid, mac]:
        return 'Missing ssid or mac', 400
    stemp = network.root_file_open('/etc/wpa_supplicant/wpa_supplicant.conf')
    wpasup = network.wpa_supplicant_read(stemp[0])
    network.wpa_supplicant_remove(wpasup['networks'], ssid, mac)
    network.wpa_supplicant_write(stemp[0], wpasup['other'], wpasup['networks'])
    network.root_file_close(stemp)
    # If we are currently connected
    wificon = network.current_wifi_connect()
    if wificon['ssid'] == ssid or wificon['mac'] == mac:
        if not settings.is_simulation():
            subprocess.run(['sudo', '/usr/bin/autohotspot'])
    return 'Removed', 200


@app.route('/wifi_known', methods=['GET'])
@nocache
def wifi_known():
    stemp = network.root_file_open('/etc/wpa_supplicant/wpa_supplicant.conf')
    wpasup = network.wpa_supplicant_read(stemp[0])
    network.root_file_close(stemp)
    return jsonify(wpasup['networks'])


@app.route('/wifi_connect', methods=['POST'])
@nocache
def wifi_connect():
    ssid = request.form.get('ssid', None)
    mac = request.form.get('mac', None)
    psk = request.form.get('psk', None)
    open_wifi = request.form.get('open', None)
    known = request.form.get('known', None)

    if None in [ssid, mac]:
        return 'Missing ssid or mac', 400
    if not known and not open_wifi and psk is None:
        return 'You must give a passphrase', 400

    stemp = network.root_file_open('/etc/wpa_supplicant/wpa_supplicant.conf')
    wpasup = network.wpa_supplicant_read(stemp[0])

    found = False
    for n in wpasup['networks']:
        if n['ssid'] == ssid and n['bssid'] == mac:
            if psk:
                n['psk'] = psk
            n['priority'] = 5
            found = True
        elif 'priority' in n:
            del n['priority']

    if not found:
        n = {'bssid': mac, 'ssid': "\"%s\"" % ssid}
        if psk:
            n['psk'] = '"' + psk + '"'
        else:
            n['key_mgmt'] = 'None'
        wpasup['networks'].append(n)

    network.wpa_supplicant_write(stemp[0], wpasup['other'], wpasup['networks'])
    network.root_file_close(stemp)
    # TODO: Maybe we do this after responding for user feedback?
    if not settings.is_simulation():
        subprocess.run(['sudo', '/sbin/wpa_cli', '-i', 'wlan0', 'reconfigure'])
        subprocess.run(['sudo', '/usr/bin/autohotspot'])
    return '', 204


@app.route('/set_location', methods=['DELETE'])
@nocache
def unset_location():
    settings.settings['location'] = None
    control.update_location()
    settings.write_settings(settings.settings)
    return 'Unset Location', 200


@app.route('/set_location', methods=['PUT'])
@nocache
def set_location():
    location = request.form.get('location', None)
    location = json.loads(location)
    print(location)
    if 'lat' not in location or 'long' not in location or 'elevation' not in location or (
            'name' not in location and location['name'].strip() != ''):
        return 'Missing arguments', 400
    location = {'lat': float(location['lat']), 'long': float(location['long']),
                'elevation': float(location['elevation']), 'name': str(location['name'])}
    old_location = settings.settings['location']
    settings.settings['location'] = location
    try:
        control.update_location()
    except:
        settings.settings['location'] = old_location
        traceback.print_exc(file=sys.stdout)
        return 'Invalid location', 400
    settings.write_settings(settings.settings)
    return 'Set Location', 200


@app.route('/sync', methods=['DELETE'])
@nocache
def clear_sync():
    control.clear_sync()
    return 'Cleared', 200


@app.route('/sync', methods=['PUT'])
@nocache
def do_sync():
    ra = request.form.get('ra', None)
    dec = request.form.get('dec', None)
    alt = request.form.get('alt', None)
    az = request.form.get('az', None)
    if alt is not None and az is not None:
        if not runtime_settings['earth_location_set']:
            return 'Cant Alt/Az Sync if not location set', 400
        alt = float(alt)
        az = float(az)
        coord = SkyCoord(alt=alt * u.deg, az=az * u.deg, frame='altaz')
    else:
        ra = float(ra)
        dec = float(dec)
        coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    control.sync(coord)
    return jsonify({'text': 'Sync Points: ' + str(control.pm_real_stepper.size())})


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
        if not runtime_settings['earth_location_set']:
            return 'Cant do alt/az slew if no location set.', 400
        alt = float(alt)
        az = float(az)
        altaz = SkyCoord(alt=alt * u.deg, az=az * u.deg, frame='altaz')
        # parking = True
    else:
        ra = float(ra)
        dec = float(dec)
        radec = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
        altaz = control.convert_to_altaz(radec)
    if not control.slewtocheck(altaz):
        return 'Slew position is below horizon or in keep-out area.', 400
    else:
        control.slew(altaz, parking)
        return 'Slewing', 200


@app.route('/slewto_check', methods=['PUT'])
@nocache
def do_slewtocheck():
    ra = float(request.form.get('ra', None))
    dec = float(request.form.get('dec', None))
    radec = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='ircs')
    return jsonify({'slewcheck': control.slewtocheck(radec)})


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
    # if runtime_settings['time_been_set'] and not overwrite:
    #    return 'Already Set', 200
    d = iso8601.parse_date(time)
    ntpstat = subprocess.run(['/usr/bin/ntpstat'])
    if ntpstat.returncode != 0:
        d = d + (datetime.datetime.now() - s)
        time = d.isoformat()
        if not settings.is_simulation():
            daterun = subprocess.run(['/usr/bin/sudo', '/bin/date', '-s', time])
        else:
            daterun = {'returncode': 0}
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
    if not runtime_settings['earth_location_set']:
        return 'You must set location before setting park position.', 400
    status = control.stepper.get_status()
    coord = control.steps_to_skycoord(runtime_settings['sync_info'], {'ra': status['rp'], 'dec': status['dp']},
                                      AstroTime.now(), settings.settings['ra_track_rate'],
                                      settings.settings['dec_ticks_per_degree'])
    altaz = control.convert_to_altaz(coord, atmo_refraction=settings.settings['atmos_refract'])
    settings.settings['park_position'] = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
    settings.write_settings(settings.settings)
    return 'Park Position Set', 200


@app.route('/set_park_position', methods=['DELETE'])
@nocache
def unset_park_position():
    settings.settings['park_position'] = None
    settings.write_settings(settings.settings)
    return 'Park Position Unset', 200


@app.route('/park', methods=['PUT'])
@nocache
def do_park():
    # TODO: If started parked we can use 0,0
    if not runtime_settings['earth_location_set']:
        return 'Location not set', 400
    if not settings.settings['park_position']:
        return 'No park position has been set.', 400
    if not runtime_settings['sync_info']:
        return 'No sync info has been set.', 400
    runtime_settings['tracking'] = False
    control.stepper.set_speed_ra(0)
    coord = SkyCoord(alt=settings.settings['park_position']['alt'] * u.deg,
                     az=settings.settings['park_position']['az'] * u.deg, frame='altaz')
    control.slew(coord, parking=True)
    return 'Parking.', 200


@app.route('/start_tracking', methods=['PUT'])
@nocache
def start_tracking():
    settings.not_parked()
    runtime_settings['tracking'] = True
    control.stepper.set_speed_ra(settings.settings['ra_track_rate'])
    return 'Tracking', 200


@app.route('/stop_tracking', methods=['PUT'])
@nocache
def stop_tracking():
    runtime_settings['tracking'] = False
    control.stepper.set_speed_ra(0)
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
            location = None
            if runtime_settings['earth_location_set']:
                location = runtime_settings['earth_location']
            coord = astropy.coordinates.get_body(body, AstroTime.now(),
                                                 location=location)
            ra = coord.ra.deg
            dec = coord.dec.deg
            coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
            if do_altaz:
                altaz = control.convert_to_altaz(coord, atmo_refraction=settings.settings['atmos_refract'])
                altaz = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
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
            coord = SkyCoord(ra=(360.0 / 24.0) * float(ob[0]) * u.deg, dec=float(ob[1]) * u.deg, frame='icrs')
            altaz = control.convert_to_altaz(coord, atmo_refraction=settings.settings['atmos_refract'])
            altaz = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
        else:
            altaz = {'alt': None, 'az': None}
        ob.append(altaz['alt'])
        ob.append(altaz['az'])
    for ob in stars:
        if do_altaz:
            coord = SkyCoord(ra=(360.0 / 24.0) * float(ob[7]) * u.deg, dec=float(ob[8]) * u.deg, frame='icrs')
            altaz = control.convert_to_altaz(coord, atmo_refraction=settings.settings['atmos_refract'])
            altaz = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
        else:
            altaz = {'alt': None, 'az': None}
        ob.append(altaz['alt'])
        ob.append(altaz['az'])

    return jsonify({'dso': dso, 'stars': stars, 'planets': planets})


def reboot():
    if not settings.is_simulation():
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
    try:
        subprocess.run(['/usr/bin/python3', 'post_update.py'])
    except:
        pass
    t = threading.Timer(5, reboot)
    t.start()
    return 'Updated'


@app.route('/wifi_scan', methods=['GET'])
@nocache
def wifi_scan():
    aps = network.wifi_client_scan_iw()
    connected = network.current_wifi_connect()
    return jsonify({'aps': aps, 'connected': connected})


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
    # print("Got %s" + json.dumps(message))
    control.manual_control(message['direction'], message['speed'])
    emit('controls_response', {'data': 33})


@app.route('/paa_capture', methods=['POST'])
@nocache
def paa_capture_post():
    exposure = int(request.form.get('exposure'))
    iso = int(request.form.get('iso'))
    paa_capture(exposure, iso)
    return "Capturing", 200


def paa_capture(exposure, iso):
    global paa_process
    with paa_process_lock:
        print('Staring paa process')
        if not paa_process or paa_process.poll() is not None:
            paa_process = subprocess.Popen(
                ['/usr/bin/python3', '-u', 'polar_align_assist.py'],
                bufsize=0,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            #    stderr=subprocess.PIPE)
            # set_nonblock(paa_process.stdout.fileno())
            # set_nonblock(paa_process.stderr.fileno())
            t = threading.Thread(target=listen_paa_stdout, args=(paa_process,))
            t.start()
            # t = threading.Thread(target=listen_paa_stderr, args=(paa_process,))
            # t.start()
        time.sleep(2)
        print('Writing to paa process')
        paa_process.stdin.write(('%d %d %d %f\n' % (exposure, iso, -1, 0.25)).encode())


@app.route('/paa_capture', methods=['DELETE'])
@nocache
def paa_capture_stop():
    with paa_process_lock:
        if paa_process and paa_process.poll() is None:
            paa_process.stdin.write('stop\n'.encode())
    return 'Stopping', 200


@app.route('/paa_image', methods=['GET'])
@nocache
def paa_image():
    global paa_count
    img = '%d.jpg' % (paa_count,)
    print('paa_image', img, flush=True)
    if settings.is_simulation():
        return send_from_directory('./simulation_files/ramtmp', img)
    else:
        return send_from_directory('/ramtmp', img)


def listen_paa_stdout(process):
    global paa_count
    while process.poll() is None:
        line = process.stdout.readline().decode().strip()
        sline = line.split(' ', 1)
        if len(sline) == 2 and sline[0] == 'CAPTURED':
            paa_count = int(sline[1])
            socketio.emit('paa_capture_response', {'paa_count': paa_count, 'done': False})
        elif sline[0] == 'CAPTUREDONE':
            socketio.emit('paa_capture_response', {'paa_count': paa_count, 'done': True})
        elif sline[0] == 'STATUS':
            socketio.emit('paa_capture_response', {'status': sline[1]})
        else:
            print('polar_align_assist.py:', line)


def main():
    global st_queue, power_thread_quit
    power_thread_quit = False
    if not settings.settings['power_switch']:
        power_thread_quit = True
    power_thread = threading.Thread(target=run_power_switch)
    power_thread.start()
    wifiinfo = network.hostapd_read()
    for key in wifiinfo.keys():
        settings.settings['network'][key] = wifiinfo[key]
    ethernetinfo = network.read_ethernet_settings()
    for key in ethernetinfo.keys():
        settings.settings['network'][key] = ethernetinfo[key]
    st_queue = control.init(socketio, runtime_settings)

    # TODO: Config if start stellarium server.
    stellarium_thread = threading.Thread(target=stellarium_server.run)
    stellarium_thread.start()

    sstchuck_thread = threading.Thread(target=sstchuck.run)
    sstchuck_thread.start()
    paa_capture(1000000 * 10, 800)

    print('Running...')
    try:
        ssl_context = None
        if len(sys.argv) == 2 and sys.argv[1] == '--https':
            make_ssl_devcert('../key')
            ssl_context = ('../key.crt', '../key.key')
        socketio.run(app, host="0.0.0.0", debug=False, log_output=False, use_reloader=False,
                     ssl_context=ssl_context)
        power_thread_quit = True
        stellarium_server.terminate()
        sstchuck.terminate()
        stellarium_thread.join()
        sstchuck_thread.join()
        power_thread.join()
    finally:
        if paa_process and paa_process.poll() is None:
            paa_process.stdin.write('STOP\nQUIT\n'.encode())
            try:
                paa_process.wait(10)
            except subprocess.TimeoutExpired:
                paa_process.kill()


if __name__ == '__main__':
    main()
