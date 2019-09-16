from astropy.utils import iers
import astropy.time
import astropy.coordinates
from astropy.coordinates import solar_system_ephemeris, SkyCoord
import astropy.units as u
from astropy.time import Time as AstroTime
import time

from flask import Flask, redirect, jsonify, request, make_response, url_for, send_from_directory
from functools import wraps, update_wrapper
import json
import control
import threading
import re
import sqlite3
import subprocess
import datetime
import tempfile
import zipfile
import os
import settings
import sstchuck
import network
import sys
import socket
import lx200proto_server
import skyconv

from werkzeug.serving import make_ssl_devcert

iers.conf.auto_download = False
iers.auto_max_age = None


def correct_dir():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)


correct_dir()

avahi_process = None

power_thread_quit = False

st_queue = None
app = Flask(__name__, static_folder='../client_refactor/dist/')
# socketio = SocketIO(app, async_mode='threading', logger=False, engineio_logger=False)
settings_json_lock = threading.RLock()
db_lock = threading.RLock()
conn = sqlite3.connect('ssteq.sqlite', check_same_thread=False)

pointing_logger = settings.get_logger('pointing')

RELAY_PIN = 6
SWITCH_PIN = 5


# Sets up power switch
# TODO: disable power switch for simulation
def run_power_switch():
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.output(RELAY_PIN, True)

        while not power_thread_quit:
            time.sleep(0.1)
            if GPIO.input(SWITCH_PIN) == 0:
                continue
            time.sleep(0.1)
            if GPIO.input(SWITCH_PIN) == 1:
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


@app.route('/api/version')
@nocache
def version():
    return jsonify({"version": control.version, "version_date": control.version_date_str})


@app.route('/api/settings')
@nocache
def settings_get():
    return jsonify(settings.settings)


@app.route('/api/hostname')
@nocache
def hostname_get():
    return jsonify({'hostname': socket.gethostname()})


@app.route('/api/shutdown', methods=['PUT'])
@nocache
def shutdown_put():
    control.set_shutdown()
    return 'Shutdown', 200


@app.route('/api/logger', methods=['GET'])
@nocache
def logger_get():
    logger_name = request.args.get('name')
    if logger_name == 'pointing':
        pointing_logger.handlers[0].flush()
        return send_from_directory('./logs', 'pointing.log', as_attachment=True, attachment_filename='pointing_log.txt')


@app.route('/api/settings', methods=['PUT'])
@nocache
def settings_put():
    print('settings_put')
    settings_buffer = {}
    args = request.json
    keys = ["ra_track_rate", "ra_ticks_per_degree", "dec_ticks_per_degree",
            "ra_encoder_pulse_per_degree", "dec_encoder_pulse_per_degree",
            "ra_slew_fastest", "ra_slew_faster", "ra_slew_medium",
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

    keys = ["atmos_refract", "use_encoders", "limit_encoder_step_fillin"]
    for key in keys:
        if key in args:
            settings_buffer[key] = bool(args[key])

    keys = ["color_scheme"]
    for key in keys:
        if key in args:
            settings_buffer[key] = str(args[key])

    keys = ["color_scheme", "atmos_refract", "ra_track_rate", "ra_slew_fastest", "ra_slew_faster", "ra_slew_medium",
            "ra_slew_slower", "ra_slew_slowest", "dec_slew_fastest", "dec_slew_faster", "dec_slew_medium",
            "dec_slew_slower", "dec_slew_slowest", "ra_ticks_per_degree", "dec_ticks_per_degree", "time_autosync",
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
    return 'Settings Saved', 200


@app.route('/api/settings_horizon_limit', methods=['PUT'])
@nocache
def settings_horizon_limit():
    reqj = request.json
    enabled = reqj.get('horizon_limit_enabled', None)
    points = reqj.get('points', None)
    dec_greater_than = reqj.get('dec_greater_than', None)
    dec_less_than = reqj.get('dec_less_than', None)
    if points is None and enabled is None and dec_greater_than is None:
        return 'Missing points/enable', 400
    if enabled is not None:
        settings.settings['horizon_limit_enabled'] = enabled
        settings.write_settings(settings.settings)
    if dec_greater_than is not None and dec_less_than is not None:
        settings.settings['horizon_limit_dec']['greater_than'] = dec_greater_than
        settings.settings['horizon_limit_dec']['less_than'] = dec_less_than
        settings.write_settings(settings.settings)
    if points is not None:
        settings.settings['horizon_limit_points'] = points
        settings.write_settings(settings.settings)
    return 'Saved Slew Setting', 200


@app.route('/api/settings_network_ethernet', methods=['PUT'])
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
        settings.settings['network']['netmask'] = netmask
        settings.settings['network']['dhcp_server'] = dhcp_server
    return 'Saved Network', 200


@app.route('/api/settings_network_wifi', methods=['PUT'])
@nocache
def settings_network_wifi():
    reqj = request.json
    ssid = reqj.get('ssid', None)
    wpa2key = reqj.get('wpa2key', None)
    channel = reqj.get('channel', None)

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
    return "Updated Wifi Settings", 200


@app.route('/api/wifi_connect', methods=['DELETE'])
@nocache
def wifi_connect_delete():
    reqj = request.json
    ssid = reqj.get('ssid', None)
    mac = reqj.get('mac', None)
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


@app.route('/api/wifi_known', methods=['GET'])
@nocache
def wifi_known():
    stemp = network.root_file_open('/etc/wpa_supplicant/wpa_supplicant.conf')
    wpasup = network.wpa_supplicant_read(stemp[0])
    network.root_file_close(stemp)
    return jsonify(wpasup['networks'])


@app.route('/api/wifi_connect', methods=['POST'])
@nocache
def wifi_connect():
    reqj = request.json
    ssid = reqj.get('ssid', None)
    mac = reqj.get('mac', None)
    psk = reqj.get('psk', None)
    open_wifi = reqj.get('open', None)
    known = reqj.get('known', None)

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
    return 'Connecting...', 200


@app.route('/api/set_location', methods=['DELETE'])
@nocache
def unset_location():
    settings.settings['location'] = None
    control.update_location()
    settings.write_settings(settings.settings)
    return 'Unset Location', 200


@app.route('/api/set_location', methods=['PUT'])
@nocache
def set_location():
    location = request.json
    print(location)
    if 'lat' not in location or 'long' not in location or 'elevation' not in location or (
            'name' not in location and location['name'].strip() != ''):
        return 'Missing arguments', 400
    location = {'lat': float(location['lat']), 'long': float(location['long']),
                'elevation': float(location['elevation']), 'name': str(location['name'])}
    try:
        control.set_location(location['lat'], location['long'], location['elevation'], location['name'])
    except Exception as e:
        print(e)
        return 'Invalid location', 400
    return 'Set Location', 200


@app.route('/api/sync', methods=['GET'])
@nocache
def get_sync_points():
    points = []
    frame = skyconv.model_real_stepper.frame()
    for point in skyconv.model_real_stepper.get_from_points():
        if frame == 'altaz':
            points.append({'alt': point.alt.deg, 'az': point.az.deg})
        else:
            points.append({'ha': point.ha.deg, 'dec': point.dec.deg})
    return jsonify({'frame': frame, 'points': points})


@app.route('/api/sync', methods=['DELETE'])
@nocache
def clear_sync():
    control.clear_sync()
    return 'Cleared Sync Points', 200


@app.route('/api/sync', methods=['PUT'])
@nocache
def do_sync():
    reqj = request.json
    ra = reqj.get('ra')
    dec = reqj.get('dec', None)
    alt = reqj.get('alt', None)
    az = reqj.get('az', None)
    if alt is not None and az is not None:
        alt = float(alt)
        az = float(az)
    else:
        ra = float(ra)
        dec = float(dec)
    try:
        size = control.set_sync(ra, dec, alt, az)
    except Exception as e:
        return str(e), 400
    return jsonify({'text': 'Sync Points: ' + str(size)})


@app.route('/api/sync', methods=['POST'])
@nocache
def post_sync():
    reqj = request.json
    model = reqj.get('model')
    if model not in ['single', 'buie', 'affine_all']:
        return 'Invalid model', 400
    # Set models
    control.clear_sync()
    settings.settings['pointing_model'] = model
    settings.write_settings(settings.settings)
    return 'Pointing Model Set', 200


@app.route('/api/slewto', methods=['PUT'])
@nocache
def do_slewto():
    reqj = request.json
    ra = reqj.get('ra')
    dec = reqj.get('dec')
    alt = reqj.get('alt')
    az = reqj.get('az')
    ra_steps = reqj.get('ra_steps')
    dec_steps = reqj.get('dec_steps')
    try:
        if ra_steps is not None and dec_steps is not None:
            control.set_slew(ra_steps=int(ra_steps), dec_steps=int(dec_steps))
        elif alt is not None and az is not None:
            alt = float(alt)
            az = float(az)
            control.set_slew(alt=alt, az=az)
        else:
            ra = float(ra)
            dec = float(dec)
            control.set_slew(ra=ra, dec=dec)
    except Exception as e:
        return str(e), 400
    return 'Slewing', 200


@app.route('/api/slewto_check', methods=['PUT'])
@nocache
def do_slewtocheck():
    reqj = request.json
    ra = float(reqj.get('ra'))
    dec = float(reqj.get('dec', None))
    radec = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    return jsonify({'slewcheck': control.slewtocheck(radec)})


@app.route('/api/slewto', methods=['DELETE'])
@nocache
def stop_slewto():
    control.cancel_slews()
    return 'Stopping Slew', 200


@app.route('/api/set_time', methods=['PUT'])
@nocache
def set_time():
    reqj = request.json
    time_str = reqj.get('time')
    # overwrite = request.form.get('overwrite', None)
    status = control.set_time(time_str)
    if status[1] == 'NTP Set':
        return status[1], 200
    return status[1], 200 if status[0] else 500


@app.route('/api/set_park_position', methods=['PUT'])
@nocache
def set_park_position():
    control.set_park_position_here()
    return 'Park Position Set', 200


@app.route('/api/set_park_position', methods=['DELETE'])
@nocache
def unset_park_position():
    # Will just be default if none
    settings.settings['park_position'] = None
    settings.write_settings(settings.settings)
    return 'Park Position Unset', 200


@app.route('/api/park', methods=['PUT'])
@nocache
def do_park():
    control.stop_tracking()
    if not settings.settings['park_position']:
        coord = SkyCoord(alt=control.DEFAULT_PARK['alt'] * u.deg,
                         az=control.DEFAULT_PARK['az'] * u.deg, frame='altaz')
    else:
        coord = SkyCoord(alt=settings.settings['park_position']['alt'] * u.deg,
                         az=settings.settings['park_position']['az'] * u.deg, frame='altaz')
    control.slew(coord, parking=True)
    return 'Parking.', 200


@app.route('/api/start_tracking', methods=['PUT'])
@nocache
def start_tracking():
    control.start_tracking()
    return 'Tracking', 200


@app.route('/api/stop_tracking', methods=['PUT'])
@nocache
def stop_tracking():
    control.stop_tracking()
    return 'Stopped Tracking', 200


def to_list_of_lists(tuple_of_tuples):
    b = [list(x) for x in tuple_of_tuples]
    return b


def to_list_of_dicts(tuple_of_tuples, keys):
    b = []
    for r in tuple_of_tuples:
        d = {}
        for i in range(len(r)):
            d[keys[i]] = r[i]
        b.append(d)
    return b


@app.route('/api/altitude_data', methods=['POST'])
@nocache
def altitude_data():
    reqj = request.json
    if reqj.get('ra'):
        ra = reqj['ra']
        dec = reqj['dec']
        coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    else:
        alt = reqj['alt']
        az = reqj['az']
        coord = skyconv.altaz_to_icrs(SkyCoord(alt=alt * u.deg, az=az * u.deg, frame='altaz'))
    altazes = skyconv.icrs_to_altaz(coord, atmo_refraction=True, obstime=reqj['times'])
    return jsonify(altazes.alt.deg.tolist())


@app.route('/api/convert_coord', methods=['POST'])
@nocache
def conver_coord():
    reqj = request.json
    if reqj.get('ra'):
        ra = reqj['ra']
        dec = reqj['dec']
        coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
        altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
        return jsonify({'alt': altaz.alt.deg, 'az': altaz.az.deg})
    else:
        alt = reqj['alt']
        az = reqj['az']
        coord = skyconv.altaz_to_icrs(SkyCoord(alt=alt * u.deg, az=az * u.deg, frame='altaz'))
        return jsonify({'ra': coord.ra.deg, 'dec': coord.dec.deg})


@app.route('/api/search_object', methods=['GET'])
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
            if settings.runtime_settings['earth_location_set']:
                location = settings.runtime_settings['earth_location']
            coord = astropy.coordinates.get_body(body, AstroTime.now(),
                                                 location=location)
            ra = coord.ra.deg
            dec = coord.dec.deg
            coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
            if do_altaz:
                altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
                altaz = {'alt': altaz.alt.deg, 'az': altaz.az.deg}
            else:
                altaz = {'alt': None, 'az': None}
            planets.append(
                {
                    'type': 'planet', 'name': body.title(), 'ra': coord.icrs.ra.deg, 'dec': coord.icrs.dec.deg,
                    'alt': altaz['alt'],
                    'az': altaz['az']
                }
            )
    dso_search = search
    star_search = search
    if re.match(r'.*\d+$', search):
        dso_search = '%' + dso_search + '|%'
        star_search = '%' + star_search
    else:
        dso_search = '%' + dso_search + '%'
        star_search = '%' + star_search + '%'
    # catalogs = {'IC': ['IC'], 'NGC': ['NGC'], 'M': ['M', 'Messier'], 'Pal': ['Pal'], 'C': ['C', 'Caldwell'],
    # 'ESO': ['ESO'], 'UGC': ['UGC'], 'PGC': ['PGC'], 'Cnc': ['Cnc'], 'Tr': ['Tr'], 'Col': ['Col'], 'Mel': ['Mel'],
    # 'Harvard': ['Harvard'], 'PK': ['PK']}
    dso_columns = ["ra", "dec", "type", "const", "mag", "name", "r1", "r2", "search"]
    stars_columns = ["ra", "dec", "bf", "proper", "mag", "con"]

    with db_lock:
        cur = conn.cursor()
        cur.execute(('SELECT %s from dso where search like ? limit 10' % ','.join(dso_columns)), (dso_search,))
        dso = cur.fetchall()
        cur.execute('SELECT \'star\',%s from stars where bf like ? or proper like ? limit 10' % ','.join(stars_columns),
                    (star_search, star_search))
        stars = cur.fetchall()
        cur.close()
    dso = to_list_of_dicts(dso, dso_columns)
    stars = to_list_of_dicts(stars, ['type'] + stars_columns)
    # Alt az
    for ob in dso:
        print(ob['ra'], ob['dec'], ob['r1'], ob['r2'])
        ob['ra'] = float(ob['ra']) * (360. / 24.)
        ob['dec'] = float(ob['dec'])
        if not ob['mag']:
            ob['mag'] = None
        else:
            ob['mag'] = float(ob['mag'])
        if not ob['r1']:
            ob['r1'] = None
        else:
            ob['r1'] = float(ob['r1'])
        if not ob['r2']:
            ob['r2'] = None
        else:
            ob['r2'] = float(ob['r2'])
        if do_altaz:
            coord = SkyCoord(ra=ob['ra'] * u.deg, dec=ob['dec'] * u.deg, frame='icrs')
            altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
            ob['alt'] = altaz.alt.deg
            ob['az'] = altaz.az.deg
        else:
            ob['alt'] = None
            ob['az'] = None
    for ob in stars:
        ob['ra'] = float(ob['ra']) * (360. / 24.)
        ob['dec'] = float(ob['dec'])
        if not ob['mag']:
            ob['mag'] = None
        else:
            ob['mag'] = float(ob['mag'])
        if do_altaz:
            coord = SkyCoord(ra=ob['ra'] * u.deg, dec=ob['dec'] * u.deg, frame='icrs')
            altaz = skyconv.icrs_to_altaz(coord, atmo_refraction=True)
            ob['alt'] = altaz.alt.deg
            ob['az'] = altaz.az.deg
        else:
            ob['alt'] = None
            ob['az'] = None

    return jsonify({'dso': dso, 'stars': stars, 'planets': planets})


def reboot():
    if not settings.is_simulation():
        return subprocess.run(['/usr/bin/sudo', '/sbin/reboot'])


@app.route('/api/firmware_update', methods=['POST'])
@nocache
def firmware_update():
    file = request.files['file']
    with tempfile.TemporaryFile(suffix='.zip') as tfile:
        file.save(tfile)
        tfile.seek(0)
        zip_ref = zipfile.ZipFile(tfile)
        if settings.is_simulation():
            zip_ref.extractall('/home/russ/projects/starsynctrackers/SSTForkMountFirmware/piside/upload_test')
        else:
            zip_ref.extractall('/home/pi/SSTForkMountFirmware/piside')
    try:
        subprocess.run(['/usr/bin/python3', 'post_update.py'])
    except Exception as e:
        print(e)
    if not settings.is_simulation():
        t = threading.Timer(5, reboot)
        t.start()
    return 'Updated Firmware'


@app.route('/api/wifi_scan', methods=['GET'])
@nocache
def wifi_scan():
    aps = network.wifi_client_scan_iw()
    connected = network.current_wifi_connect()
    return jsonify({'aps': aps, 'connected': connected})


@app.route('/api/location_preset', methods=['POST'])
@nocache
def location_preset_add():
    location = request.json
    name = location['name']
    lat = location['lat']
    long = location['long']
    elevation = location['elevation']
    settings.settings['location_presets'].append({'name': name, 'lat': lat, 'long': long, 'elevation': elevation})
    settings.write_settings(settings.settings)
    return "Saved Location Preset", 200


@app.route('/api/location_preset', methods=['DELETE'])
@nocache
def location_preset_del():
    location = request.json
    idx = location['index']
    del settings.settings['location_presets'][idx]
    settings.write_settings(settings.settings)
    return "Deleted Location Preset", 200


@app.route('/api/search_location', methods=['GET'])
@nocache
def search_location():
    search = request.args.get('search', None)
    if not search:
        return
    search = search.strip()
    columns = ["postalcode", "city", "state", "state_abbr", "latitude", "longitude", "elevation"]
    # If zipcode search
    if re.match(r'\d+$', search):
        search = search + '%'
        with db_lock:
            cur = conn.cursor()
            cur.execute(('SELECT %s from uscities where postalcode like ? limit 20' % ','.join(columns)), (search,))
            cities = cur.fetchall()
            cur.close()
    else:
        cstate = search.split(',')
        if len(cstate) == 1:
            # Just search city
            city = cstate[0]
            city = city.strip()
            search = city + '%'
            with db_lock:
                cur = conn.cursor()
                cur.execute(('SELECT %s from uscities where city like ? limit 20' % ','.join(columns)), (search,))
                cities = cur.fetchall()
                cur.close()
        else:
            city = cstate[0]
            state = cstate[1]

            city = city.strip()
            state = state.strip()
            # If using state abbreviation
            if len(state) == 2:
                abbr = state.upper()
                city = city + '%'
                with db_lock:
                    cur = conn.cursor()
                    cur.execute(
                        ('SELECT %s from uscities where city like ? and state_abbr = ? limit 20' % ','.join(columns)),
                        (city, abbr))
                    cities = cur.fetchall()
                    cur.close()
            else:
                # State must be full name
                city = city + '%'
                state = state + '%'
                with db_lock:
                    cur = conn.cursor()
                    cur.execute(
                        ('SELECT %s from uscities where city like ? and state like ? limit 20' % ','.join(columns)),
                        (city, state))
                    cities = cur.fetchall()
                    cur.close()
    cities = to_list_of_dicts(cities, columns)
    for city in cities:
        city['latitude'] = float(city['latitude'])
        city['longitude'] = float(city['longitude'])
        city['elevation'] = float(city['elevation'])
    return jsonify(cities)


@app.route('/api/manual_control', methods=['POST'])
@nocache
def manual_control():
    message = request.json
    # print("Got %s" + json.dumps(message))
    control.manual_control(message['direction'], message['speed'])
    return 'Moving', 200


@app.route('/api/status', methods=['GET'])
@nocache
def status_get():
    return jsonify(control.last_status)


@app.route('/')
@nocache
def root():
    return redirect('/index.html')


@app.route('/advanced_slew_limits/<path:path>')
@nocache
def send_static_advanced_slew(path):
    return send_from_directory('../client_refactor/dist', path)


@app.route('/<path:path>')
@nocache
def send_static(path):
    return send_from_directory('../client2/dist', path)


def main():
    global st_queue, power_thread_quit, avahi_process
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
    st_queue = control.init()

    lx200proto_thread = threading.Thread(target=lx200proto_server.main)
    lx200proto_thread.start()

    sstchuck_thread = threading.Thread(target=sstchuck.run)
    sstchuck_thread.start()

    hostname = socket.gethostname()
    # TODO: What about when they change hostname? Or can move this to systemd?
    avahi_process = subprocess.Popen(
        ['/usr/bin/avahi-publish-service', hostname, '_sstmount._tcp', '5000', '/'])
    print('Running...')
    try:
        ssl_context = None
        if len(sys.argv) == 2 and sys.argv[1] == '--https':
            make_ssl_devcert('../key')
            ssl_context = ('../key.crt', '../key.key')
        app.run(host="0.0.0.0", debug=False, use_reloader=False, ssl_context=ssl_context)
        power_thread_quit = True
        sstchuck.terminate()
        lx200proto_server.terminate()
        lx200proto_thread.join()
        sstchuck_thread.join()
        power_thread.join()
        avahi_process.kill()
    finally:
        pass


if __name__ == '__main__':
    main()
