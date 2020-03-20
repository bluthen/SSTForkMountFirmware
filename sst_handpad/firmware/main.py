# Itsy Bitsy M0 Express IO demo
# Welcome to CircuitPython 2.2 :)

import board
import gc
import time
from digitalio import DigitalInOut, Direction, Pull
import pulseio
import adafruit_character_lcd.character_lcd as characterlcd

gc.collect()

# Built in red LED
# led = DigitalInOut(board.D13)
# led.direction = Direction.OUTPUT

# Digital input with pullup on D7, D9, and D10
buttons = []
for p in [board.A4, board.A3, board.A5, board.A1, board.A2, board.D2]:
    button = DigitalInOut(p)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    buttons.append(button)

# FOR PWM Levels see https://jared.geek.nz/2013/feb/linear-led-pwm
PWM_LEVELS = [0, 738, 1959, 4087, 7373, 12071, 18431, 26705, 37146, 50005, 65535]

button_pwm = pulseio.PWMOut(board.D10)
lcd_pwm = pulseio.PWMOut(board.D11)
lcd_pwm.duty_cycle = PWM_LEVELS[9]

lcd_rs = DigitalInOut(board.D3)
lcd_en = DigitalInOut(board.D4)
lcd_d7 = DigitalInOut(board.D7)
lcd_d6 = DigitalInOut(board.D9)
lcd_d5 = DigitalInOut(board.D12)
lcd_d4 = DigitalInOut(board.D13)

lcd_columns = 20
lcd_rows = 4

lcd = characterlcd.Character_LCD(rs=lcd_rs, en=lcd_en, d4=lcd_d4, d5=lcd_d5, d6=lcd_d6, d7=lcd_d7, columns=lcd_columns,
                                 lines=lcd_rows)
lcd.message = 'Hello Greta.\nYou\'re the best\n2\n3'
lcd.cursor = True
lcd.blink = True


######################### HELPERS ##############################



######################### MAIN LOOP ##############################

i = 0
j = 0
# k=0
while True:
    # spin internal LED around! autoshow is on
    #if k == 0:
    #    lcd_rs.value = not lcd_rs.value
    if i == 0:
        j = (j + 1) % 10
        # lcd_pwm.duty_cycle = PWM_LEVELS[j]
        button_pwm.duty_cycle = PWM_LEVELS[j]

    if not buttons[0].value:
        print("Button UP pressed!", end="\t")
    if not buttons[1].value:
        print("Button ENTER pressed!", end="\t")
    if not buttons[2].value:
        print("Button DOWN pressed!", end="\t")
    if not buttons[3].value:
        print("Button LEFT pressed!", end="\t")
    if not buttons[4].value:
        print("Button RIGHT pressed!", end="\t")
    if not buttons[5].value:
        print("Button ESC pressed!", end="\t")

    i = (i + 1) % 256  # run from 0 to 255
    #k = (k+1) % 1000
    time.sleep(0.01)  # make bigger to slow down

    # print("1")
