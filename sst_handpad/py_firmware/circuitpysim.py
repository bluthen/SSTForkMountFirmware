import curses
import os
import time

win = None
_all_buttons = []


def curses_wrapper(window, func):
    global win
    print('curses_wrapper')
    win = window
    win.nodelay(True)
    func()


def setup_curses(func):
    print('setup_curses')
    os.environ.setdefault('ESCDELAY', '25')
    curses.wrapper(curses_wrapper, func)


class Character_LCD:
    def __init__(self, rs=None, en=None, d4=None, d5=None, d6=None, d7=None, columns=20, lines=4):
        self.columns = columns
        self.lines = lines
        self._pos = [0, 0]
        self._buffer = [
            "                    ",
            "                    ",
            "                    ",
            "                    "
        ]

    def _println(self, s, line):
        win.addnstr(line, 0, s, self.columns)
        win.refresh()

    def _fill_str(self, s):
        s_len = len(s)
        if s_len < self.columns:
            s += ' ' * (self.columns - s_len)
        s = s[0:self.columns]
        return s

    def _clearln(self, line):
        win.addnstr(line, 0, ' ' * self.columns, self.columns)
        win.refresh()

    @property
    def message(self):
        # TODO: This will have spaces to fill in columns I think real doesn't.
        return '\n'.join(self._buffer)

    @message.setter
    def message(self, value):
        vsplit = value.split('\n')
        lrows = len(vsplit)
        lines_refresh = list(range(self._pos[1], self._pos[1] + lrows))
        vsplit[0] = self._buffer[self._pos[1]][:self._pos[0]] + vsplit[0]
        c = 0
        for i in lines_refresh:
            self._buffer[i] = self._fill_str(vsplit[c])
            c += 1
            self._println(self._buffer[i], i)
        self._pos = [0, 0]

    @property
    def blink(self):
        return False

    @blink.setter
    def blink(self, value):
        pass

    @property
    def cursor(self):
        return False

    @cursor.setter
    def cursor(self, value):
        pass

    def clear(self):
        for i in range(self.lines):
            self._clearln(i)

    def cursor_position(self, column, row):
        self._pos = [column, row]
        pass


class Direction:
    INPUT = 1
    OUTPUT = 2


class Pull:
    UP = 1


class board:
    D1 = 1
    D2 = 2
    D3 = 3
    D4 = 4
    D5 = 5
    D6 = 6
    D7 = 7
    D8 = 8
    D9 = 9
    D10 = 10
    D11 = 11
    D12 = 12
    D13 = 13
    D14 = 14
    A1 = 15
    A2 = 16
    A3 = 17
    A4 = 18
    A5 = 19


class curses_input:
    ESC = 27
    ENTER = 10
    BACKSPACE = 263
    DOWN = 258
    UP = 259
    LEFT = 260
    RIGHT = 261


_pin_key_map = {
    board.A4: curses_input.UP,
    board.A3: curses_input.ENTER,
    board.A5: curses_input.DOWN,
    board.A1: curses_input.LEFT,
    board.A2: curses_input.RIGHT,
    board.D2: curses_input.ESC
}


class DigitalInOut:
    def __init__(self, pin):
        self._pin = pin
        self.direction = 2
        self.pull = 1
        self.value = (self.pull == Pull.UP)
        if pin in _pin_key_map:
            self.cinput = _pin_key_map[pin]
        else:
            self.cinput = None
        self.ctime = 0
        _all_buttons.append(self)


class PWMOut:
    def __init__(self, pin):
        self.duty_cycle = 0


hold_mode = False
hold_time = 0.1
hold_ctime = 0


def set_input_buttons():
    global hold_mode, hold_time
    i = win.getch()
    # if i != -1:
    #     print(i)
    now = time.time()
    if i == 104 and (now - hold_ctime) > 0.1:  # h - hold mode
        hold_mode = not hold_mode
        if hold_mode:
            # print('hold mode')
            hold_time = 10
        else:
            # print('hold mode off')
            hold_time = 0.1
    for button in _all_buttons:
        if i == button.cinput:
            # since pull up
            button.value = (not button.pull == Pull.UP)
            button.ctime = now
        elif button.value == (not button.pull == Pull.UP) and (now - button.ctime) > hold_time:
            button.value = (button.pull == Pull.UP)


def update():
    set_input_buttons()
