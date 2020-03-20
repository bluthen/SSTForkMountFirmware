import serial
import serial.tools
import serial.tools.list_ports
import threading
import time
import re
import traceback

MAX_BUFFER = 255

"""
Handpad protocol:

SST          ABOUT                             HANDPAD RESPONSE
--------     --------------------              -------------------
@SSTHP!      Asks handpad what version of      @SSTHP_\d{3}!
             handpad version is running  
             also used for a handshake.
          
@B!          Get button press info since       @{SEQUENCE}! 
             last check.                       SEQUENCE is any combo of:
                                               U# D# L# R# E# S#
                                               Where # is 1-9
                                                  U is up
                                                  D is down
                                                  L is left
                                                  R is right
                                                  E is enter
                                                  S is escape
                                            
@D#{string}! Write string on line #            @K!

@C#,#!       Put cursor on line,column         @K!

@NC!         No cursor                         @K!

@CL!         Clear screen                      @K!


@GPS!        Get GPS Info                      @{GPS_INFO}!
                                               TODO of what GPS_INFO is 
                                               maybe NMEA GGS string

"""


class HandpadServer:
    def __init__(self):
        self.serial_lock = threading.RLock()
        self.serial = None
        self.buffer = ""

    def write_line(self, line_num, line_str):
        self.serial.write(('@D{line_num:d}{line_str:s}!' % line_num, line_str).encode())
        self.__read_serial_cmd()

    def get_buttons(self):
        self.serial.write('@B!'.encode())
        s = self.__read_serial_cmd()
        ret = []
        for i in range(1, len(s), 2):
            d = s[i]
            c = int(s[i + 1])
            ret.extend([d] * c)
        return ret

    def discover(self):
        devices = []
        for s in serial.tools.list_ports.grep('/dev/ttyACM\d+'):
            devices.append(s.device)
        return devices

    def __read_serial_cmd(self):
        s = self.buffer
        found_at = False
        with self.serial_lock:
            while True:
                if self.serial.in_waiting > 0:
                    s += self.serial.read(self.serial.in_waiting).decode()
                else:
                    s += self.serial.read(1).decode()
                if not found_at:
                    idx = s.find('@')
                    if idx >= 0:
                        s = s[idx:]
                        found_at = True
                if found_at:
                    idx = s.find('!')
                    if idx >= 0:
                        s = s[:idx + 1]
                        break
        return s

    def test(self, device):
        try:
            ser = serial.Serial(device, 115200, timeout=2)
            self.serial = ser
            self.serial.write('@SSTHP!'.encode())
            s = self.__read_serial_cmd(2)
            if re.match('@SSTHP_\d{3}!', s):
                return True
            else:
                self.serial.close()
                self.serial = None
        except:
            self.serial.close()
            self.serial = None
            return False

    def close(self):
        if self.serial:
            self.serial.close()
            self.serial = None


def terminate():
    global kill
    kill = True


def main():
    global kill
    handpad_server = HandpadServer()
    try:
        while not kill:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('Keyboard quitting')
        kill = True
    else:
        traceback.print_exc()
    handpad_server.close()
