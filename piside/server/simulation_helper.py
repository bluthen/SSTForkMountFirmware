from fractions import Fraction
import shutil
import time
import types


class PiCamera:
    def __init__(self, camera_num=0, stereo_mode='none', stereo_decimate=False, resolution=None, framerate=None,
                 sensor_mode=0, led_pin=None, clock_mode='reset', framerate_range=None):
        self.MAX_RESOLUTION = [3280, 2464]
        if resolution != None:
            self.resolution = tuple(resolution)
        else:
            self.resolution = tuple(self.MAX_RESOLUTION)
        self.shutter_speed = 100000
        self.framerate = Fraction(1000000.0 / self.shutter_speed)
        self.iso = 100

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def start_preview(self):
        pass

    def capture(self, output, format=None, use_video_port=False, resize=None, splitter_port=0, bayer=False, **options):
        time.sleep(2000000.0 / self.shutter_speed)
        shutil.copyfile('./sim_cam.jpg', output)

    def close(self):
        pass

    def capture_sequence(self, outputs, format='jpeg', use_video_port=False, resize=None, splitter_port=0, burst=False,
                         bayer=False, **options):
        time.sleep(4 * self.shutter_speed/1000000.0)
        for output in outputs:
            shutil.copyfile('./sim_cam.jpg', output)
            time.sleep(self.shutter_speed/1000000.0)


def iw_scan_decode():
    with open('./simulation_files/iw_output', 'r') as f:
        return f.read()


def iw_scan():
    return types.SimpleNamespace(**{'stdout': types.SimpleNamespace(**{'decode': iw_scan_decode})})
