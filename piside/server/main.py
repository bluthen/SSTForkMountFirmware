from flask import Flask, redirect, jsonify
from flask_socketio import SocketIO, emit
import json
import control
from eventlet import monkey_patch
monkey_patch()

st_queue = None
app = Flask(__name__, static_url_path='/static', static_folder='../client/')
socketio = SocketIO(app, async_mode='eventlet', logger=True, engineio_logger=True)
settings = None


@app.route('/')
def root():
    return redirect('/static/index.html')


@app.route('/settings')
def settings_get():
    return jsonify(settings)


@app.route('/settings', methods=['PUT'])
def settings_put():
    global settings
    return jsonify(settings)


@socketio.on('manual_control')
def manual_control(message):
    emit('controls_response', {'data': 33})
    print("Got %s"+json.dumps(message))
    control.manual_control(message['direction'], message['speed'])
    emit('controls_response', {'data': 33})


def main():
    global st_queue, settings
    with open('settings.json') as f:
        settings = json.load(f)
    st_queue = control.init(socketio, settings)
    print('Running...')
    socketio.run(app, host="0.0.0.0", debug=True, log_output=True, use_reloader=False)


if __name__ == '__main__':
    main()
