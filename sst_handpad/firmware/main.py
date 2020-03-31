import gc
import time
import sys
import adafruit_debouncer
from adafruit_debouncer import Debouncer

# Uncomment if simulation
from circuitpysim import board
from circuitpysim import DigitalInOut, Direction, Pull
from circuitpysim import PWMOut
import circuitpysim as characterlcd

SIMULATION = True

# Uncomment if real
# import board
# from digitalio import DigitalInOut, Direction, Pull
# from pulseio import PWMOut
# import adafruit_character_lcd.character_lcd as characterlcd
# SIMULATION = False


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
    for p in {'U': board.A4, 'E': board.A3, 'D': board.A5, 'L': board.A1, 'R': board.A2, 'S': board.D2}.items():
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
    start = time.time()
    while time.time() - start < .1:
        avail = availf()
        if avail > 0:
            s += inf(avail)
            start = time.time()
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


# ######################## MAIN LOOP ##############################
def main_loop():
    button_sequence = []
    buttons_released = []
    buttons_pressed = []
    i = 0
    j = 0

    lcd.message = 'StarSync Trackers\nInitializing...\n\n'

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
                lcd.cursor_position(0, line)
                lcd.message = cmd[3:len(cmd) - 1]
                outf('@K!')
            elif cmd == '@SSTHP!':
                s = '@SSTHP_{version:03d}!'.format(version=version)
                outf(s)
            elif cmd[1] == 'C':
                line = int(cmd[2])
                column = int(cmd[3])
                lcd.cursor_position(column, line)
                outf('@K!')
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
        time.sleep(0.005)  # make bigger to slow down


setup()
if SIMULATION:
    characterlcd.setup_curses(main_loop)
else:
    main_loop()
