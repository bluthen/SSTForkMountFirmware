from flask import Flask, redirect
from flask_socketio import SocketIO, emit
import json
import control

st_queue = None
app = Flask(__name__, static_url_path='/static', static_folder='../client/')
socketio = SocketIO(app)


@app.route('/')
def root():
    return redirect('/static/index.html')

@app.route('/settings')
def settings_get():
    pass

@app.route('/settings', methods=['PUT'])
def settings_put():
    pass


@socketio.on('manual_control')
def manual_control(message):
    control.manual_control(message['direction'], message['speed'])
    print("Got %s"+json.dumps(message))
    #emit('controls_response', {'data': 33})


def main():
    socketio.run(app)


if __name__ == '__main__':
    st_queue = control.init()
    main()
