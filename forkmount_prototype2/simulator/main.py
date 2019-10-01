import serial
import time
import sys

serialcom = None
cmds = {'ra_max_tps': None, 'ra_guide_rate': None, 'ra_direction': None, 'dec_max_tps': None, 'dec_guide_rate': None,
        'dec_direction': None}
sd = {'RASpeed': 0.0, 'RAClock': 0, 'RAPosition': 0, 'DECSpeed': 0.0,
      'DECClock': 0, 'DECPosition': 0, 'RA_v0': 0., 'RA_vi': 0., 'DEC_v0': 0., 'DEC_vi': 0.}
configvars = {
    'ra_max_tps': 12000,
    'ra_guide_rate': 20,
    'dec_max_tps': 12000,
    'dec_guide_rate': 6,
    'debug_enabled': 0,
    'autoguide_enabled': 1,
    'ra_direction': 1,
    'dec_direction': 1,
    'ra_accel_tpss': 1000,
    'dec_accel_tpss': 1000,
}


def swrite(str):
    serialcom.write(str.encode())


def millis():
    return int(round(time.time() * 1000))


def print_prompt():
    swrite("$ ")


def command_set_var(args):
    if len(args) < 1:
        swrite("ERROR: Missing [variable_name] argument.\r")
        return

    if len(args) < 2:
        swrite("ERROR: Missing [value] argument.\r")
        return
    arg_name = args[0]
    arg_val = args[1]

    value = float(arg_val)
    print('set_var', arg_name, arg_val)
    if arg_name == "ra_max_tps":
        configvars['ra_max_tps'] = value
    elif arg_name == "ra_guide_rate":
        configvars['ra_guide_rate'] = value
    elif arg_name == "ra_direction":
        configvars['ra_direction'] = int(value)
    elif arg_name == "dec_max_tps":
        configvars['dec_max_tps'] = value
    elif arg_name == "dec_guide_rate":
        configvars['dec_guide_rate'] = value
    elif arg_name == "dec_direction":
        configvars['dec_direction'] = int(value)
    elif arg_name == 'ra_accel_tpss':
        configvars['ra_accel_tpss'] = value
    elif arg_name == 'dec_accel_tpss':
        configvars['dec_accel_tpss'] = value
    else:
        serialcom.write("ERROR: Invalid variable name '".encode())
        serialcom.write(arg_name.encode())
        serialcom.write.println("'\r".encode())

    print_prompt()


def command_qs(args):
    swrite("rs:")
    swrite("%.7f\r" % getRASpeed())
    swrite("ds:")
    swrite("%.7f\r" % getDECSpeed())
    rap = round(getRAPosition())
    decp = round(getDECPosition())
    swrite("rp:")
    swrite("%d\r" % rap)
    swrite("dp:")
    swrite("%d\r" % decp)
    # TODO: Simulate encoder better
    swrite("re:")
    swrite("%d\r" % 0)
    swrite("de:")
    swrite("%d\r" % 0)
    swrite("ri:")
    swrite("%d\r" % rap)
    swrite("di:")
    swrite("%d\r" % decp)
    print_prompt()


def command_status(args):
    swrite("ra_max_tps=")
    swrite("%.7f\r" % configvars['ra_max_tps'])
    swrite("ra_guide_rate=")
    swrite("%.7f\r" % configvars['ra_guide_rate'])
    swrite("ra_direction=")
    swrite("%d\r" % configvars['ra_direction'])
    swrite("ra_accel_tpss=")
    swrite("%.7f\r" % configvars['ra_accel_tpss'])
    swrite("dec_max_tps=")
    swrite("%.7f\r" % configvars['dec_max_tps'])
    swrite("dec_guide_rate=")
    swrite("%.7f\r" % configvars['dec_guide_rate'])
    swrite("dec_direction=")
    swrite("%.7f\r" % configvars['dec_direction'])
    swrite("dec_accel_tpss=")
    swrite("%.7f\r" % configvars['dec_accel_tpss'])
    swrite("debug:")
    swrite("%d\r" % configvars['debug_enabled'])
    swrite("autoguide:")
    swrite("%d\r" % configvars['autoguide_enabled'])
    swrite("ra_speed:")
    swrite("%.7f\r" % getRASpeed())
    swrite("dec_speed:")
    swrite("%.7f\r" % getDECSpeed())
    rap = round(getRAPosition())
    decp = round(getDECPosition())
    swrite("ra_pos:")
    swrite("%d\r" % rap)
    swrite("dec_pos:")
    swrite("%d\r" % decp)
    # TODO: Simulate encoder better
    swrite("ra_enc:")
    swrite("%d\r" % 0)
    swrite("dec_enc:")
    swrite("%d\r" % 0)
    swrite("ra_tip:")
    swrite("%d\r" % rap)
    swrite("dec_tip:")
    swrite("%d\r" % decp)
    print_prompt()


def command_ra_set_speed(args):
    if len(args) < 1:
        swrite("ERROR: Missing [value] argument.\r")
        return

    arg_val = args[0]
    value = float(arg_val)
    print('ra_set_speed', value)
    setRASpeed(value)
    swrite("ra_speed:")
    swrite("%.7f\r" % getRASpeed())
    print_prompt()


def command_dec_set_speed(args):
    if len(args) < 1:
        swrite("ERROR: Missing [value] argument.\r")
        return

    value = float(args[0])
    print('dec_set_speed', value)
    setDECSpeed(value)
    swrite("dec_speed:")
    swrite("%.7f\r" % getDECSpeed())
    print_prompt()


def setRASpeed(speed):
    if abs(speed) > configvars['ra_max_tps']:
        sd['RASpeed'] = (abs(speed) / speed) * configvars['ra_max_tps']
    else:
        sd['RASpeed'] = speed
    sd['RAClock'] = millis()


def getRASpeed():
    return sd['RA_v0']


def getRAPosition():
    return sd['RAPosition']


def setDECSpeed(speed):
    if abs(speed) > configvars['dec_max_tps']:
        sd['DECSpeed'] = (abs(speed) / speed) * configvars['dec_max_tps']
    else:
        sd['DECSpeed'] = speed
    sd['DECClock'] = millis()


def getDECSpeed():
    return sd['DEC_v0']


def getDECPosition():
    return sd['DECPosition']


def command_help(args):
    swrite("Commands:\r")
    swrite("  set_var [variable_name] [value] Sets variable\r")
    swrite("  ra_set_speed [tps]           Moves RA to tick position\r")
    swrite("  dec_set_speed [tps]          Moves DEC to tick position\r")
    swrite("  autoguide_disable            Disables Autoguiding port input\r")
    swrite("  autoguide_enable             Enables Autoguiding prot input\r")
    swrite("  status                       Shows status/variable info\r")
    swrite("  qs                           Shows speed/position info\r")
    swrite("  help                         This help info\r")
    print_prompt()


def command_autoguide_disable(args):
    configvars['autoguide_enabled'] = 0
    print_prompt()


def command_autoguide_enable(args):
    configvars['autoguide_enabled'] = 1
    print_prompt()


def run_steppers():
    now = millis()
    rat = (float(now - sd['RAClock'])) / 1000.0
    x, v = motion_func(configvars['ra_accel_tpss'], sd['RA_v0'], sd['RAPosition'], rat, sd['RASpeed'])
    sd['RAPosition'] = x
    sd['RAClock'] = now
    sd['RA_v0'] = v

    rat = (float(now - sd['DECClock'])) / 1000.0
    x, v = motion_func(configvars['dec_accel_tpss'], sd['DEC_v0'], sd['DECPosition'], rat, sd['DECSpeed'])
    sd['DECPosition'] = x
    sd['DECClock'] = now
    sd['DEC_v0'] = v


def motion_func(a, v_0, x_0, t, speed_wanted):
    # When do we hit v_max
    if speed_wanted < v_0:
        a = -abs(a)
    t_v_max = (speed_wanted - v_0) / a
    dt_v_max = t - t_v_max
    if dt_v_max > 0:
        p = 0.5 * a * t_v_max * t_v_max + v_0 * float(t_v_max) + x_0
        p += speed_wanted * dt_v_max
        v = speed_wanted
    else:
        v = a * t + v_0
        p = 0.5 * a * t * t + v_0 * float(t) + x_0
    return p, v


def main():
    global serialcom, sio
    cmd_funcs = {'set_var': command_set_var, 'ra_set_speed': command_ra_set_speed,
                 'dec_set_speed': command_dec_set_speed,
                 'autoguide_disable': command_autoguide_disable, 'autoguide_enable': command_autoguide_enable,
                 'status': command_status, 'qs': command_qs, 'help': command_help}
    serialcom = serial.Serial(port=sys.argv[1], baudrate=115200)
    line = b''
    while True:
        # while serialcom.in_waiting > 0:
        c = serialcom.read(1)
        if c == b'\r' or c == b'\n':
            run_steppers()
            line = line.decode()
            line_split = line.split(' ')
            if line_split[0] in cmd_funcs:
                if len(line_split[0]) > 1:
                    cmd_funcs[line_split[0]](line_split[1:])
                else:
                    cmd_funcs[line_split[0]]([])
            else:
                command_help([])
            line = b''
        else:
            line += c
            if len(line) > 50:
                line = b''
        # time.sleep(0.00007)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: %s virtual_serial_port" % sys.argv[0])
        print("To setup virtual serial port:")
        print("    socat -d -d pty,raw,echo=0 pty,raw,echo=0")
        sys.exit(1)
    main()
