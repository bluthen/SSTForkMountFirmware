import gc
import sys
import time

import adafruit_debouncer
from adafruit_debouncer import Debouncer

import adafruit_character_lcd.character_lcd as characterlcd
import adafruit_dotstar
import board
import busio
import supervisor
from digitalio import DigitalInOut, Direction, Pull
from pulseio import PWMOut

gc.collect()

dot = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=1)
dot[0] = (0, 0, 0)
uart = None
gc.collect()

version = 1

# FOR PWM Levels see https://jared.geek.nz/2013/feb/linear-led-pwm
PWM_LEVELS_LCD = [5000, 12071, 65535]
PWM_LEVELS_BUTTONS = [100, 300, 738]
brightness_pwm = 2
button_pwm = PWMOut(board.D10)
lcd_pwm = PWMOut(board.D11)

buttons = {}
lcd = None
inf = None
outf = None
availf = None


# Built in red LED
# led = DigitalInOut(board.D13)
# led.direction = Direction.OUTPUT


def setup():
    global lcd, inf, outf, availf, uart
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
    inf = lambda x: sys.stdin.read(x)
    outf = lambda x: sys.stdout.write(x)
    availf = lambda: supervisor.runtime.serial_bytes_available
    uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=2)


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


def display_awake():
    lcd_pwm.duty_cycle = PWM_LEVELS_LCD[brightness_pwm]
    button_pwm.duty_cycle = PWM_LEVELS_BUTTONS[brightness_pwm]


def display_sleep():
    lcd_pwm.duty_cycle = 0
    button_pwm.duty_cycle = 0


def get_gps_lines():
    t = time.monotonic()
    uart.reset_input_buffer()
    uart.readline()
    lines = []
    while True:
        if time.monotonic() - t >= 2.5:
            return ['ERROR', 'ERROR']
        line = uart.readline()
        if line:
            line = line.decode()
            if line.find('$GPRMC') == 0:
                lines = [line.rstrip()]
            if len(lines) == 1 and line.find('$GPGGA') == 0:
                lines.append(line.rstrip())
                return lines


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
    global brightness_pwm
    button_sequence = []
    buttons_released = []
    buttons_pressed = []
    display_awake()
    is_display_sleep = False
    wake_timer = time.monotonic()
    no_cmd_timer = time.monotonic()
    no_cmd_display = False

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
            if len(cmd) >= 3:
                no_cmd_timer = time.monotonic()
                if no_cmd_display and cmd[0] == '@' and cmd[-1] == '!':
                    no_cmd_display = False
                    lcd.cursor_position(0, 0)
                    lcd.message = '\n'.join(lcd_state)
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
                    brightness_pwm = int(cmd[2])
                    display_awake()
                    outf('@K!')
                elif cmd == '@GPS!':
                    gpslines = '\n'.join(get_gps_lines())
                    outf('@' + gpslines + '!')
                else:
                    outf('@N!')

        buttons_released.clear()
        buttons_pressed.clear()
        for button in buttons.items():
            if button[1].fell:
                # print(button[0])
                wake_timer = time.monotonic()
                if is_display_sleep:
                    display_awake()
                    is_display_sleep = False
                else:
                    button_sequence.append(button[0])
            if button[1].value:  # not pressed
                buttons_released.append(button[0])
            else:
                buttons_pressed.append(button[0])

        if time.monotonic() - wake_timer > 120 and not is_display_sleep:
            display_sleep()
            is_display_sleep = True

        if not no_cmd_display and time.monotonic() - no_cmd_timer > 30:
            no_cmd_display = True
            lcd.cursor_position(0, 0)
            lcd.message = '\n'.join(['Communication with  ',
                                     'mount lost.         ',
                                     '                    ',
                                     '                    '])
        for b in buttons.values():
            b.update()


setup()
gc.collect()
while True:
    try:
        main_loop()
    except:
        pass
