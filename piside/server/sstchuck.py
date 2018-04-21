import serial.tools.list_ports
import control
import time
import traceback

terminateself = False


# remember needs ssteq25 needs teensy udev rules

def readline(serialcon):
    s = ""
    while True:
        if serialcon.in_waiting > 0:
            s += serialcon.read(serialcon.in_waiting).decode()
        else:
            s += serialcon.read(1).decode()
            if s == '':
                break
        if '\n' in s or '\r' in s:
            break
    return s


def runchuck(port):
    with serial.Serial(port.device, 115200, timeout=0.5) as chuckserial:
        chuckserial.dtr = True
        chuckserial.reset_output_buffer()
        readline(chuckserial)
        readline(chuckserial)
        line = readline(chuckserial).strip()
        moving = False
        if line.startswith('SSTC0:'):
            while not terminateself and line != '':
                # print('SSTChuck: line: ' + line)
                v = line.strip().split(':')[1].split(',')
                controls = {'x': int(v[0]), 'y': int(v[1]), 'bz': v[2] == '1', 'bc': v[3] == '1'}
                # print(controls)
                if abs(controls['x']) > 60 and abs(controls['y']) > 60:
                    moving = True
                    if controls['x'] < 0:
                        control.manual_control('left', 'fastest')
                    else:
                        control.manual_control('right', 'fastest')
                    if controls['y'] < 0:
                        control.manual_control('down', 'fastest')
                    else:
                        control.manual_control('up', 'fastest')
                elif abs(controls['x']) > 80:
                    moving = True
                    if controls['x'] < 0:
                        control.manual_control('left', 'fastest')
                        control.manual_control('up', None)
                        control.manual_control('down', None)
                    else:
                        control.manual_control('right', 'fastest')
                        control.manual_control('up', None)
                        control.manual_control('down', None)
                elif abs(controls['y']) > 80:
                    moving = True
                    if controls['y'] < 0:
                        control.manual_control('down', 'fastest')
                        control.manual_control('left', None)
                        control.manual_control('right', None)
                    else:
                        control.manual_control('up', 'fastest')
                        control.manual_control('left', None)
                        control.manual_control('right', None)
                elif abs(controls['x']) > 30 and abs(controls['y']) > 30:
                    moving = True
                    if controls['x'] < 0:
                        control.manual_control('left', 'medium')
                    else:
                        control.manual_control('right', 'medium')
                    if controls['y'] < 0:
                        control.manual_control('down', 'medium')
                    else:
                        control.manual_control('up', 'medium')
                elif abs(controls['x']) > 40:
                    if controls['x'] < 0:
                        control.manual_control('left', 'medium')
                        control.manual_control('up', None)
                        control.manual_control('down', None)
                    else:
                        control.manual_control('right', 'medium')
                        control.manual_control('up', None)
                        control.manual_control('down', None)
                elif abs(controls['y']) > 40:
                    moving = True
                    if controls['y'] < 0:
                        control.manual_control('down', 'medium')
                        control.manual_control('left', None)
                        control.manual_control('right', None)
                    else:
                        control.manual_control('up', 'medium')
                        control.manual_control('left', None)
                        control.manual_control('right', None)
                elif abs(controls['x']) > 5 and abs(controls['y']) > 5:
                    moving = True
                    if controls['x'] < 0:
                        control.manual_control('left', 'slowest')
                    else:
                        control.manual_control('right', 'slowest')
                    if controls['y'] < 0:
                        control.manual_control('down', 'slowest')
                    else:
                        control.manual_control('up', 'slowest')
                elif abs(controls['x']) > 5:
                    moving = True
                    if controls['x'] < 0:
                        control.manual_control('left', 'slowest')
                        control.manual_control('up', None)
                        control.manual_control('down', None)
                    else:
                        control.manual_control('right', 'slowest')
                        control.manual_control('up', None)
                        control.manual_control('down', None)
                elif abs(controls['y']) > 5:
                    moving = True
                    if controls['y'] < 0:
                        control.manual_control('down', 'slowest')
                        control.manual_control('left', None)
                        control.manual_control('right', None)
                    else:
                        control.manual_control('up', 'slowest')
                        control.manual_control('left', None)
                        control.manual_control('right', None)
                elif moving:
                    moving = False
                    control.manual_control('up', None)
                    control.manual_control('down', None)
                    control.manual_control('left', None)
                    control.manual_control('right', None)
                line = readline(chuckserial).strip()


def terminate():
    global terminateself
    terminateself = True


def run(settings):
    # Try to detect comport
    # print('Started SSTChuck')
    ignore_devices = []
    while not terminateself:
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                # print(port.device)
                if port.manufacturer == 'Teensyduino' and port.device != settings['microserial']['port'] and \
                                port.device not in ignore_devices:
                    # print('SSTChuck: Trying device: ' + port.device)
                    runchuck(port)
        except:
            print(traceback.format_exc())
        time.sleep(5)
