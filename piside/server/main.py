import update_python_paths
import time
import re
import copy
import datetime
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
import zipfile
from functools import wraps, update_wrapper

import astropy.units as u
from astropy.coordinates import ICRS, TETE, AltAz
from skyconv_hadec import HADec
from astropy.utils import iers
from flask import Flask, redirect, jsonify, request, make_response, url_for, send_from_directory
from flask_compress import Compress
from werkzeug.serving import make_ssl_devcert

import control
import db
import handpad_menu
import handpad_server
import lx200proto_server
import network
import settings
import skyconv

iers.conf.auto_download = False
iers.auto_max_age = None

avahi_process = None

power_thread_quit = False

st_queue = None
app = Flask(__name__, static_folder='../client_refactor/dist/')
logging.getLogger('werkzeug').setLevel(logging.ERROR)
# socketio = SocketIO(app, async_mode='threading', logger=False, engineio_logger=False)
settings_json_lock = threading.RLock()

pointing_logger = settings.get_logger('pointing')

RELAY_PIN = 6
SWITCH_PIN = 5

compress = Compress()
update_python_paths.keep_import()


# Sets up power switch
# TODO: disable power switch for simulation
def run_power_switch():
    pass
    # try:
    #     import RPi.GPIO as GPIO
    #     GPIO.setmode(GPIO.BCM)
    #     GPIO.setup(RELAY_PIN, GPIO.OUT)
    #     GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    #     GPIO.output(RELAY_PIN, True)
    #
    #     while not power_thread_quit:
    #         time.sleep(0.1)
    #         if GPIO.input(SWITCH_PIN) == 0:
    #             continue
    #         time.sleep(0.1)
    #         if GPIO.input(SWITCH_PIN) == 1:
    #             subprocess.run(['sudo', 'shutdown', '-h', 'now'])
    #
    # except ImportError:
    #     # We are probably in simulation
    #     print("Warning: Can't use power switch.")


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
    s = copy.deepcopy(settings.settings)
    s['encoder_logging'] = control.encoder_logging_enabled
    s['calibration_logging'] = settings.runtime_settings['calibration_logging']
    if not s['location']:
        s['location'] = {
            'lat': control.DEFAULT_LAT_DEG,
            'long': control.DEFAULT_LON_DEG,
            'name': 'Unset Location'
        }
    # print(s)
    return jsonify(s)


@app.route('/api/settings_dl')
@nocache
def settings_dl_get():
    return send_from_directory(directory='./', filename='settings.json', as_attachment=True,
                               attachment_filename='ssteq25_settings.json')


@app.route('/api/settings_dl', methods=['POST'])
@nocache
def settings_dl_post():
    file = request.files['file']
    with tempfile.TemporaryFile(suffix='.json') as tfile:
        file.save(tfile)
        tfile.seek(0)
        json.load(tfile)  # just to check it is at least a json
        tfile.seek(0)
        settings.copy_settings(tfile)
    if not settings.is_simulation():
        t = threading.Timer(5, reboot)
        t.start()
    return 'Updated Settings'


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
        return send_from_directory(os.path.join(os.path.expanduser('~'), 'logs'), 'pointing.log', as_attachment=True,
                                   attachment_filename='pointing_log.txt')
    elif logger_name == 'calibration':
        ret = []
        for row in control.calibration_log:
            # TODO: just support ra/dec right now add others
            if 'sync' in row and 'slewto' in row and 'slewfrom' in row:
                ret.append({
                    'slewfrom': {'ra': row['slewfrom'].ra.deg, 'dec': row['slewfrom'].dec.deg},
                    'slewto': {'ra': row['slewto'].ra.deg, 'dec': row['slewto'].dec.deg},
                    'sync': {'ra': row['sync'].ra.deg, 'dec': row['sync'].dec.deg}
                })
        return jsonify(ret)
    elif logger_name == 'encoder':
        if control.encoder_logging_enabled:
            control.encoder_logging_file.flush()
        return send_from_directory(os.path.join(os.path.expanduser('~'), 'logs'), 'stepper_encoder.csv',
                                   as_attachment=True,
                                   attachment_filename='stepper_encoder.csv')


@app.route('/api/logger', methods=['DELETE'])
@nocache
def logger_clear():
    args = request.json
    logger_name = args.get('name')
    if logger_name == 'encoder':
        control.encoder_logging_clear = True
        return 'Clearing encoder log', 200
    elif logger_name == 'calibration':
        control.calibration_log = []
        return 'Calibration log cleared', 200
    return 'Invalid logger', 400


@app.route('/api/logger', methods=['PUT'])
@nocache
def logger_put():
    args = request.json
    logger_name = args.get('name')
    enabled = args.get('enabled')
    if logger_name == 'encoder':
        control.start_stop_encoder_logger(enabled)
        if enabled:
            return 'Starting logger', 200
        else:
            return 'Stopping logging', 200
    elif logger_name == 'calibration':
        settings.runtime_settings['calibration_logging'] = enabled
        return 'Calibration setting set', 200
    else:
        return 'Invalid logger', 400


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
    if 'micro' in args:
        keys = ["ra_guide_rate", "ra_direction", "dec_guide_rate", "dec_direction", "dec_disable", "ra_disable",
                "ra_accel_tpss", "dec_accel_tpss"]
        for key in keys:
            if key in args['micro']:
                if 'micro' not in settings_buffer:
                    settings_buffer['micro'] = {}
                print('=== settingsb micro ' + key, args['micro'][key])
                settings_buffer['micro'][key] = float(args['micro'][key])

    keys = ["atmos_refract", "ra_use_encoder", "dec_use_encoder", "limit_encoder_step_fillin"]
    for key in keys:
        if key in args:
            settings_buffer[key] = bool(args[key])

    keys = ["color_scheme"]
    for key in keys:
        if key in args:
            settings_buffer[key] = str(args[key])

    keys = ["color_scheme", "atmos_refract", "ra_track_rate", "ra_slew_fastest", "ra_slew_faster", "ra_slew_medium",
            "ra_encoder_pulse_per_degree", "dec_encoder_pulse_per_degree",
            "ra_use_encoder", "dec_use_encoder", "limit_encoder_step_fillin",
            "ra_slew_slower", "ra_slew_slowest", "dec_slew_fastest", "dec_slew_faster", "dec_slew_medium",
            "dec_slew_slower", "dec_slew_slowest", "ra_ticks_per_degree", "dec_ticks_per_degree", "time_autosync",
            "polar_align_camera_rotation_x", "polar_align_camera_rotation_y"]
    for key in keys:
        if key in args:
            settings.settings[key] = settings_buffer[key]
    if 'micro' in settings_buffer:
        keys = ["ra_guide_rate", "ra_direction", "dec_guide_rate", "dec_direction", "dec_disable", "ra_disable",
                "ra_accel_tpss", "dec_accel_tpss"]
        for key in keys:
            if key in settings_buffer['micro']:
                print('=== settings micro ' + key, float(settings_buffer['micro'][key]))
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
    settings.settings['network']['ssid'] = ssid
    settings.settings['network']['wpa2key'] = wpa2key
    settings.settings['network']['channel'] = channel
    settings.write_settings(settings.settings)
    if not settings.is_simulation():
        def reconnect():
            # Stop hostapd and dnsmasq let autohotspot go
            subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'wlan0', 'disable'])
            subprocess.run(['sudo', '/usr/bin/killall', 'hostapd'])
            subprocess.run(['sudo', '/usr/bin/autohotspot'])

        t1 = threading.Thread(target=reconnect)
        t1.start()
    return "Updated Wifi Settings", 200


@app.route('/api/wifi_connect', methods=['DELETE'])
@nocache
def wifi_connect_delete():
    reqj = request.json
    ssid = reqj.get('ssid', None)
    mac = reqj.get('mac', None)
    if None in [ssid, mac]:
        return 'Missing ssid or mac', 400
    stemp = network.root_file_open('/ssteq/etc/wpa_supplicant.conf')
    wpasup = network.wpa_supplicant_read(stemp[0])
    network.wpa_supplicant_remove(wpasup['networks'], ssid, mac)
    network.wpa_supplicant_write(stemp[0], wpasup['other'], wpasup['networks'])
    network.root_file_close(stemp)
    # If we are currently connected
    wificon = network.current_wifi_connect()
    if wificon['ssid'] == ssid or wificon['mac'] == mac:
        def reconnect():
            if not settings.is_simulation():
                subprocess.run(['sudo', '/usr/bin/autohotspot'])

        t1 = threading.Thread(target=reconnect)
        t1.start()
    return 'Removed', 200


@app.route('/api/wifi_known', methods=['GET'])
@nocache
def wifi_known():
    stemp = network.root_file_open('/ssteq/etc/wpa_supplicant.conf')
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

    stemp = network.root_file_open('/ssteq/etc/wpa_supplicant.conf')
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

    def reconnect():
        if not settings.is_simulation():
            subprocess.run(['sudo', '/sbin/wpa_cli', '-i', 'wlan0', 'reconfigure'])
            subprocess.run(['sudo', '/usr/bin/autohotspot'])

    t1 = threading.Thread(target=reconnect)
    t1.start()
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
    return 'Cleared Model', 200


@app.route('/api/sync', methods=['PUT'])
@nocache
def do_sync():
    reqj = request.json
    try:
        size = control.set_sync(**reqj)
    except Exception as e:
        traceback.print_tb(e)
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
    try:
        control.set_slew(**reqj)
    except Exception as e:
        traceback.print_exc()
        return str(e), 400
    return 'Slewing', 200


@app.route('/api/slewto_check', methods=['PUT'])
@nocache
def do_slewtocheck():
    reqj = request.json
    frame = reqj.get('frame')
    ra = float(reqj.get('ra'))
    dec = float(reqj.get('dec', None))
    if frame == 'tete':
        frame_args = skyconv.get_frame_init_args('tete')
        coord = TETE(ra=ra * u.deg, dec=dec * u.deg, **frame_args)
    else:
        coord = ICRS(ra=ra * u.deg, dec=dec * u.deg)
    return jsonify({'slewcheck': control.slewtocheck(coord)})


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
    settings.settings['park_position'] = control.DEFAULT_PARK
    settings.write_settings(settings.settings)
    return 'Park Position Unset', 200


@app.route('/api/park', methods=['PUT'])
@nocache
def do_park():
    control.park_scope()
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


@app.route('/api/altitude_data', methods=['POST'])
@nocache
def altitude_data():
    reqj = request.json
    frame = reqj.get('frame')
    obstime = reqj['times']
    if frame in ['tete', 'icrs']:
        ra = reqj['ra']
        dec = reqj['dec']
        if frame == 'tete':
            frame_args = skyconv.get_frame_init_args('tete', obstime=obstime[0])
            coord = TETE(ra=ra * u.deg, dec=dec * u.deg, **frame_args)
            coord = skyconv.to_icrs(coord)
        else:  # ICRS
            coord = ICRS(ra=ra * u.deg, dec=dec * u.deg)
    elif frame == 'hadec':
        frame_args = skyconv.get_frame_init_args('hadec', obstime=obstime[0])
        coord = HADec(ha=reqj['ha'] * u.deg, dec=reqj['dec']*u.deg, **frame_args)
        coord = skyconv.to_icrs(coord)
    else:  # AltAz
        frame_args = skyconv.get_frame_init_args('altaz', obstime=obstime[0])
        coord = AltAz(alt=reqj['alt'] * u.deg, az=reqj['az'] * u.deg, **frame_args)
        coord = skyconv.to_icrs(coord)
    altazes = skyconv.to_altaz(coord, obstime=obstime)
    return jsonify(altazes.alt.deg.tolist())


@app.route('/api/convert_coord', methods=['POST'])
@nocache
def conver_coord():
    reqj = request.json
    frame = reqj.get('frame')
    if frame in ['icrs', 'tete']:
        ra = reqj['ra']
        dec = reqj['dec']
        if frame == 'tete':
            frame_args = skyconv.get_frame_init_args('tete')
            coord = TETE(ra=ra * u.deg, dec=dec * u.deg, **frame_args)
        else:
            coord = ICRS(ra=ra * u.deg, dec=dec * u.deg)
    elif frame == 'hadec':
        frame_args = skyconv.get_frame_init_args('hadec')
        coord = HADec(ha=reqj['ha'] * u.deg, dec=reqj['dec'] * u.deg, **frame_args)
    else:
        frame_args = skyconv.get_frame_init_args('altaz')
        if reqj['alt'] < 5:
            frame_args['pressure'] = 0
        coord = AltAz(alt=reqj['alt'] * u.deg, az=reqj['az'] * u.deg, **frame_args)
    icrs = skyconv.to_icrs(coord)
    hadec = skyconv.to_hadec(icrs)
    altaz = skyconv.to_altaz(icrs)
    tete = skyconv.to_tete(icrs)
    return jsonify({'icrs': {'ra': icrs.ra.deg, 'dec': icrs.dec.deg},
                    'altaz': {'alt': altaz.alt.deg, 'az': altaz.az.deg},
                    'tete': {'ra': tete.ra.deg, 'dec': tete.dec.deg},
                    'hadec': {'ha': hadec.ha.deg, 'dec': hadec.dec.deg}})


@app.route('/api/search_object', methods=['GET'])
@nocache
def search_object():
    search = request.args.get('search', None)
    m = re.match(r'^([a-zA-Z]+)(\d+)$', search)
    if m:
        search = m.group(1) + ' ' + m.group(2)
    if not search:
        return
    planets = db.search_planets(search)
    stars = db.search_stars(search)
    dso = db.search_dso(search)
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
            subprocess.run(['sudo', 'mount', '-o', 'remount,rw', '/ssteq'])
            zip_ref.extractall('/ssteq/piside')
            subprocess.run(['sudo', 'mount', '-o', 'remount,ro', '/ssteq'])
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


@app.route('/api/location_gps', methods=['POST'])
@nocache
def location_use_gps():
    if handpad_server.serial:
        lines = handpad_server.handpad_server.gps()
        if lines[0] == 'ERROR':
            return 'Error reading GPS', 500
        info = handpad_menu.parse_gps(lines)
        if info is None:
            return 'No satellites yet, try again later', 500
        control.set_location(info['location']['lat'], info['location']['long'], info['location']['elevation'],
                             'GPS')
        return 'Location set with GPS', 200
    else:
        return 'Handpad not connected', 500


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
    cities = db.search_cities(search)
    return jsonify(cities)


@app.route('/api/manual_control', methods=['POST'])
@nocache
def manual_control():
    message = request.json
    # print("Got %s" + json.dumps(message))
    control.set_alive(message['client_id'])
    control.manual_control(message['direction'], message['speed'], message['client_id'])
    return 'Moving', 200


@app.route('/api/status', methods=['GET'])
@nocache
def status_get():
    client_id = request.args.get('client_id')
    control.set_alive(client_id)
    return jsonify(control.last_status)


@app.route('/api/extra_logging', methods=['GET'])
@nocache
def extra_logging_get():
    lx200proto_server.extra_logging = True
    return 'Okay', 200


@app.route('/')
@nocache
def root():
    return redirect('/index.html')


@app.route('/advanced_slew_limits/<path:path>')
@nocache
def send_static_advanced_slew(path):
    return send_from_directory('../client_advanced_slew_limits/dist', path)


@app.route('/<path:path>')
@nocache
def send_static(path):
    return send_from_directory('../client_main/dist', path)


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

    handpad_thread = threading.Thread(target=handpad_server.run)
    handpad_thread.start()

    hostname = socket.gethostname()
    # TODO: What about when they change hostname? Or can move this to systemd?
    avahi_process = subprocess.Popen(
        ['/usr/bin/avahi-publish-service', hostname, '_sstmount._tcp', '5000', '/'])

    def reconnect():
        time.sleep(30)
        # Stop hostapd and dnsmasq let autohotspot go
        subprocess.run(['sudo', '/root/ctrl_dnsmasq.py', 'wlan0', 'disable'])
        subprocess.run(['sudo', '/usr/bin/killall', 'hostapd'])
        subprocess.run(['sudo', '/usr/bin/autohotspot'])

    if not settings.is_simulation():
        t1 = threading.Thread(target=reconnect)
        t1.start()

    print('Running...')
    try:
        ssl_context = None
        if len(sys.argv) == 2 and sys.argv[1] == '--https':
            make_ssl_devcert('../key')
            ssl_context = ('../key.crt', '../key.key')
        compress.init_app(app)
        app.run(host="0.0.0.0", debug=False, use_reloader=False, ssl_context=ssl_context)
        power_thread_quit = True
        handpad_server.terminate()
        lx200proto_server.terminate()
        lx200proto_thread.join()
        handpad_thread.join()
        power_thread.join()
        avahi_process.kill()
    finally:
        pass


if __name__ == '__main__':
    main()
