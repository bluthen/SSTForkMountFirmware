import gc
import time
import sys
import adafruit_debouncer
from adafruit_debouncer import Debouncer

# Uncomment if simulation
# from circuitpysim import board
# from circuitpysim import DigitalInOut, Direction, Pull
# from circuitpysim import PWMOut
# import circuitpysim as characterlcd
# SIMULATION = True

# Uncomment if real
import board
from digitalio import DigitalInOut, Direction, Pull
from pulseio import PWMOut
import adafruit_character_lcd.character_lcd as characterlcd

SIMULATION = False

version = 1

gc.collect()

# FOR PWM Levels see https://jared.geek.nz/2013/feb/linear-led-pwm
PWM_LEVELS = [0, 738, 1959, 4087, 7373, 12071, 18431, 26705, 37146, 50005, 65535]
button_pwm = PWMOut(board.D10)
lcd_pwm = PWMOut(board.D11)
lcd_pwm.duty_cycle = PWM_LEVELS[9]

buttons = {}
lcd = None
inf = None
outf = None
availf = None


# Built in red LED
# led = DigitalInOut(board.D13)
# led.direction = Direction.OUTPUT


def setup():
    global lcd, inf, outf, availf
    # Digital input with pullup on D7, D9, and D10
    for p in {'U': board.A4, 'E': board.A3, 'D': board.A2, 'L': board.A5, 'R': board.A1, 'S': board.D2}.items():
        but = DigitalInOut(p[1])
        but.direction = Direction.INPUT
        but.pull = Pull.UP
        buttons[p[0]] = Debouncer(but)

    lcd_rs = DigitalInOut(board.D3)
    lcd_en = DigitalInOut(board.D4)
    lcd_d7 = DigitalInOut(board.D7)
    lcd_d6 = DigitalInOut(board.D9)
    lcd_d5 = DigitalInOut(board.D12)
    lcd_d4 = DigitalInOut(board.D13)

    lcd_columns = 20
    lcd_rows = 4

    lcd = characterlcd.Character_LCD(rs=lcd_rs, en=lcd_en, d4=lcd_d4, d5=lcd_d5, d6=lcd_d6, d7=lcd_d7,
                                     columns=lcd_columns,
                                     lines=lcd_rows)
    lcd.cursor = False
    lcd.blink = False
    if SIMULATION:
        import serial
        ser = serial.Serial('/dev/pts/5', 115200, timeout=2)
        inf = lambda x: ser.read(x).decode()
        outf = lambda x: ser.write(x.encode())
        availf = lambda: ser.in_waiting
    else:
        import supervisor
        inf = lambda x: sys.stdin.read(x)
        outf = lambda x: sys.stdout.write(x)
        availf = lambda: supervisor.runtime.serial_bytes_available


def read_cmd():
    s = ""
    found_at = False
    start = time.monotonic()
    while time.monotonic() - start < .1:
        avail = availf()
        if avail > 0:
            s += inf(avail)
            start = time.monotonic()
        if not found_at:
            idx = s.find('@')
            if idx >= 0:
                s = s[idx:]
                found_at = True
        if found_at:
            idx = s.find('!')
            if idx >= 0:
                s = s[:idx + 1]
                return s
        time.sleep(0.01)
    return ''


def line_diff(from_line, to_line):
    to_line = to_line + ' ' * (20 - len(to_line))
    steps = []
    for i in range(20):
        if to_line[i] != from_line[i]:
            steps.append([i, to_line[i]])
    last_idx = -1
    ret = []
    for s in steps:
        if len(ret) > 0 and s[0] - 1 == last_idx:
            ret[-1][1] += s[1]
        elif len(ret) == 0:
            ret.append(s)
        else:
            ret.append(s)
        last_idx = s[0]
    if len(ret) > 5:
        ret = [[0, to_line]]
    return ret


# ######################## MAIN LOOP ##############################
def main_loop():
    button_sequence = []
    buttons_released = []
    buttons_pressed = []
    i = 0
    j = 0

    lcd_state = [
        'StarSync Trackers   ',
        'Initializing...     ',
        '                    ',
        '                    '
    ]

    lcd.message = '\n'.join(lcd_state)

    while True:
        if availf() > 0:
            cmd = read_cmd()
            if cmd == '@B!':
                outf('@{sequence:s}!'.format(sequence=''.join(button_sequence)))
                button_sequence.clear()
            elif cmd == '@J!':
                outf('@{sequence:s}!'.format(sequence=''.join(buttons_released)))
            elif cmd == '@K!':
                outf('@{sequence:s}!'.format(sequence=''.join(buttons_pressed)))
            elif cmd[1] == 'D':
                line = int(cmd[2])
                msg = cmd[3:len(cmd) - 1][0:20]
                msg = msg + ' ' * (20 - len(msg))
                diff = line_diff(lcd_state[line], msg)
                for d in diff:
                    lcd.cursor_position(d[0], line)
                    lcd.message = d[1]
                lcd_state[line] = msg
                outf('@K!')
            elif cmd == '@SSTHP!':
                s = '@SSTHP_{version:03d}!'.format(version=version)
                outf(s)
            elif cmd[1] == 'R':
                lcd.clear()
                outf('@K!')
            elif cmd[1] == 'L':
                level = int(cmd[2:4])
                # TODO: Set brightness level
                outf('@K!')
            elif cmd == '@GPS!':
                # TODO GPS
                outf('@GPSTODO!')
                pass
            else:
                outf('@N!')

        buttons_released.clear()
        buttons_pressed.clear()
        for button in buttons.items():
            if button[1].fell:
                # print(button[0])
                button_sequence.append(button[0])
            if button[1].value:  # not pressed
                buttons_released.append(button[0])
            else:
                buttons_pressed.append(button[0])

        i = (i + 1) % 256  # run from 0 to 255
        if SIMULATION:
            characterlcd.update()
        for b in buttons.values():
            b.update()


setup()
if SIMULATION:
    characterlcd.setup_curses(main_loop)
else:
    try:
        main_loop()
    except:
        last_error = e
