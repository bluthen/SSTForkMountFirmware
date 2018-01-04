from flask import Flask, redirect, jsonify, request
from flask_socketio import SocketIO, emit
import json
import control
import filelock
import threading
from eventlet import monkey_patch
monkey_patch()

st_queue = None
app = Flask(__name__, static_url_path='/static', static_folder='../client/')
socketio = SocketIO(app, async_mode='eventlet', logger=True, engineio_logger=True)
settings = None
settings_json_lock = threading.RLock()



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
    keys = ["ra_track_rate", "ra_slew_fast", "ra_slew_slow", "dec_slew_fast", "dec_slew_slow", "dec_ticks_per_degree"]
    for key in keys:
        if key in args:
            settings_buffer[key] = float(args[key])
    keys = ["ra_max_tps", "ra_guide_rate", "ra_direction", "dec_max_tps", "dec_guide_rate", "dec_direction"]
    for key in keys:
        if key in args:
            if 'micro' not in settings_buffer:
                settings_buffer['micro'] = {}
            settings_buffer['micro'][key] = float(args[key])

    keys = ["ra_track_rate", "ra_slew_fast", "ra_slew_slow", "dec_slew_fast", "dec_slew_slow", "dec_ticks_per_degree"]
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


@socketio.on('manual_control')
def manual_control(message):
    emit('controls_response', {'data': 33})
    print("Got %s"+json.dumps(message))
    control.manual_control(message['direction'], message['speed'])
    emit('controls_response', {'data': 33})


def main():
    global st_queue, settings
    with settings_json_lock:
        with open('settings.json') as f:
            settings = json.load(f)
    st_queue = control.init(socketio, settings)
    print('Running...')
    socketio.run(app, host="0.0.0.0", debug=True, log_output=True, use_reloader=False)


if __name__ == '__main__':
    main()
