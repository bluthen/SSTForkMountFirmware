"""
Handpad protocol:

SST          ABOUT                             HANDPAD RESPONSE
--------     --------------------              -------------------
@SSTHP!      Asks handpad what version of      @SSTHP_\d{3}!
             handpad version is running
             also used for a handshake.

@B!          Get button press queue info       @{SEQUENCE}!
             since last check.                 SEQUENCE is any combo of:
                                               U D L R E S
                                                  U is up
                                                  D is down
                                                  L is left
                                                  R is right
                                                  E is enter
                                                  S is escape
@J!          Get buttons that are currently    @{BUTTONS}!
             not pressed                       U D L R E S

@K!          Get buttons that are currently    @{BUTTONS}!
             pressed                           U D L R E S



@D#{string}! Write string on line #            @K!

@R!          Clear screen                      @K!

@L##!        Set light level                   @K!


@GPS!        Get GPS Info                      @{GPS_INFO}!
                                               TODO of what GPS_INFO is
                                               maybe NMEA GGS string

             Unknown command                   @N!

"""

import serial
import serial.tools
import serial.tools.list_ports
import threading
import time
import re
import traceback
from handpad_menu import Menu, menu_structure
import db

MAX_BUFFER = 255
kill = False

handpad_server = None


class HandpadServer:
    def __init__(self):
        self.serial_lock = threading.RLock()
        self.serial = None
        self.last_devices = []
        self.buffer = ""

    def write_line(self, line_num, line_str):
        with self.serial_lock:
            self.serial.write(('@D{line_num:d}{line_str:s}!' % line_num, line_str).encode())
            s=self.__read_serial_cmd()
            # print('write_line', s)

    def get_buttons(self):
        with self.serial_lock:
            self.serial.write('@B!'.encode())
            s = self.__read_serial_cmd()
            # print('get_buttons', s)
            ret = []
            for i in range(1, len(s), 2):
                d = s[i]
                c = int(s[i + 1])
                ret.extend([d] * c)
            return ret

    def discover(self):
        all_devices = []
        diff_devices = []
        for s in serial.tools.list_ports.grep('/dev/ttyACM\d+'):
            if s.device not in self.last_devices:
                diff_devices.append(s.device)
            all_devices.append(s.device)
        # # TODO Remove when testing
        # all_devices=['/dev/pts/6']
        # diff_devices=['/dev/pts/6']
        self.last_devices = all_devices
        return diff_devices

    def __read_serial_cmd(self, timeout=2):
        s = self.buffer
        found_at = False
        with self.serial_lock:
            start = time.time()
            while time.time() - start < timeout:
                if self.serial.in_waiting > 0:
                    s += self.serial.read(self.serial.in_waiting).decode()
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
                        # print(s)
                        return s
                time.sleep(0.01)
        # print(s)
        # print('timed out')
        return ''

    def reset(self):
        with self.serial_lock:
            self.serial = None
            self.last_devices = []
            self.buffer = ""

    def test(self, device):
        try:
            ser = serial.Serial(device, 115200, timeout=2)
            self.serial = ser
            if self.serial.in_waiting > 0:
                self.serial.read(serial.in_waiting)
            self.serial.write('@SSTHP!'.encode())
            s = self.__read_serial_cmd()
            # print('test', s)
            if re.match('@SSTHP_\d{3}!', s):
                return True
            else:
                self.serial.close()
                self.serial = None
        except:
            if self.serial:
                self.serial.close()
                self.serial = None
            return False

    def close(self):
        with self.serial_lock:
            if self.serial:
                self.serial.close()
                self.serial = None

    def println(self, text, line):
        with self.serial_lock:
            i = 20 - len(text[0:20])
            text += ' '*i
            self.serial.write('@D{line:d}{text:s}!'.format(text=text, line=line).encode())
            s = self.__read_serial_cmd()
            # print('println', s)

    def clearall(self):
        for i in range(4):
            self.clearln(i)

    def clearln(self, line):
        with self.serial_lock:
            self.serial.write('@D{line:d}{text:s}!'.format(text=' ' * 20, line=line).encode())
            s = self.__read_serial_cmd()
            # print('clearln', s)

    def set_brightness(self, level):
        with self.serial_lock:
            self.serial.write('@L{level:d}!'.format(level=level).encode())
            s = self.__read_serial_cmd()
            # print('brightness', s)

    def input(self):
        with self.serial_lock:
            self.serial.write('@B!'.encode())
            s = self.__read_serial_cmd()
            # print('input', s)
            if len(s) > 2:
                return s[1:len(s) - 1]
            return []

    def released(self):
        with self.serial_lock:
            self.serial.write('@J!'.encode())
            s = self.__read_serial_cmd()
            # print('released', s)
            if len(s) > 2:
                return s[len(s) - 2]
            return ''

    def pressed(self):
        with self.serial_lock:
            self.serial.write('@K!'.encode())
            s = self.__read_serial_cmd()
            # print('pressed', s)
            if len(s) > 2:
                return s[len(s) - 2]
            return ''

    def gps(self):
        with self.serial_lock:
            self.serial.write('@GPS!'.encode())
            s = self.__read_serial_cmd(10)
            s = s[1:]
            s = s[:len(s)-1]
            return s.split('\n')

    def run(self):
        try_devices = self.discover()
        good = False
        for device in try_devices:
            # print(device)
            if self.test(device):
                good = True
                break
        if good:
            # print('Found handpad')
            main_menu = Menu(menu_structure, self)
            main_menu.run_loop()


def terminate():
    global kill
    kill = True


def run():
    main()


def main():
    global kill, handpad_server
    handpad_server = HandpadServer()
    while not kill:
        try:
            while not kill:
                handpad_server.reset()
                handpad_server.run()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print('Keyboard quitting')
            kill = True
            traceback.print_exc()
        except:
            traceback.print_exc()
    handpad_server.close()


if __name__ == '__main__':
    main()
