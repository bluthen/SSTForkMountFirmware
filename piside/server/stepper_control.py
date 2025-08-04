import traceback

import serial
import threading
import time


class StepperControl:
    def __init__(self, port, baud):
        self.serial = serial.Serial(port, baud, timeout=2)
        self.serial_lock = threading.RLock()
        self.__setting_keys = ['ra_max_tps', 'ra_guide_rate', 'ra_direction', 'dec_max_tps', 'dec_guide_rate',
                               'dec_direction', 'dec_disable', 'ra_disable', 'ra_accel_tpss',
                               'dec_accel_tpss', 'ra_run_current', 'dec_run_current', 'ra_med_current',
                               'dec_med_current', 'ra_med_current_threshold', 'dec_med_current_threshold',
                               'ra_hold_current', 'dec_hold_current', 'ra_backlash', 'dec_backlash',
                               'ra_backlash_speed', 'dec_backlash_speed']

    def __read_serial_until_prompt(self):
        s = ""
        t = time.time()
        with self.serial_lock:
            while True:
                if self.serial.in_waiting > 0:
                    s += self.serial.read(self.serial.in_waiting).decode()
                    if '$' in s:
                        break
                elif time.time() - t > 0.02:
                    self.serial.write(b'\r')
                elif time.time() - t > 0.25:
                    break
                else:
                    time.sleep(0.01)
        return s

    def get_status(self):
        with self.serial_lock:
            self.serial.reset_input_buffer()
            self.serial.write(b'qs\r')
            s = self.__read_serial_until_prompt()
        # TODO: Might need to make a shorter status if transfer time longer than tracking tick interval
        # print(len(s))
        s = s.split()
        # print(s)
        status = {}
        for line in s:
            # print('@@@', line)
            line_status = line.split(':')
            if len(line_status) == 2 and line_status[0].strip() and line_status[1].strip():
                # TODO: Maybe and issue with vmc_simulator that shows here sometimes.
                try:
                    status[line_status[0]] = float(line_status[1])
                except ValueError:
                    print('StepperControl.get_status() - error: line, line_status = ', line, line_status)
                    raise
        # print(status)
        # print('status' + str(datetime.datetime.now()))
        return status

    def update_setting(self, key, value):
        if key not in self.__setting_keys:
            raise KeyError('Invalid setting key')
        with self.serial_lock:
            self.serial.write(('set_var %s %f\r' % (key, value)).encode())

    def update_settings(self, settings):
        for setting in settings:
            if setting not in self.__setting_keys:
                raise KeyError('Invalid setting key: ' + setting)
        with self.serial_lock:
            for setting in settings:
                self.serial.write(('set_var %s %f\r' % (setting, settings[setting])).encode())
                self.__read_serial_until_prompt()

    def autoguide_disable(self):
        with self.serial_lock:
            self.serial.reset_input_buffer()
            self.serial.write('autoguide_disable\r'.encode())
            self.__read_serial_until_prompt()

    def autoguide_enable(self):
        with self.serial_lock:
            self.serial.reset_input_buffer()
            self.serial.write('autoguide_enable\r'.encode())
            self.__read_serial_until_prompt()

    def set_speed_ra(self, speed):
        with self.serial_lock:
            self.serial.reset_input_buffer()
            self.serial.write(('ra_set_speed %f\r' % speed).encode())
            self.__read_serial_until_prompt()

    def set_speed_dec(self, speed):
        with self.serial_lock:
            self.serial.reset_input_buffer()
            self.serial.write(('dec_set_speed %f\r' % speed).encode())
            self.__read_serial_until_prompt()
