import settings
import subprocess

if settings.is_simulation():
    from simulation_helper import PiCamera
else:
    from picamera import PiCamera
from time import sleep
from fractions import Fraction
import os
import sys
import select
import datetime

# Version 2 Camera resolution 3280x2464 max 10s exposure
# Version 1 Camera resolution 2592x1944 max 6s exposure
CAMERAV1 = {'version': 1, 'resolution': (2592, 1944), 'max_exposure': 6000000, 'smallest_framerate': Fraction(1, 6)}
CAMERAV2 = {'version': 2, 'resolution': (3280, 2464), 'max_exposure': 10000000, 'smallest_framerate': Fraction(1, 10)}
CAMERAUNKNOWN = {'version': -1, 'resolution': (0, 0), 'max_exposure': 100}

ramtmp_count = 0

RAMTMP = '/ramtmp'

if settings.is_simulation():
    RAMTMP = './simulation_files' + RAMTMP


def detect_camera_hardware():
    with PiCamera() as camera:
        width = camera.MAX_RESOLUTION[0]
        if width == 2592:  # v1 max resolution
            return CAMERAV1
        elif width == 3280:  # v2 max resolution
            return CAMERAV2
        return CAMERAUNKNOWN


def exposure_auto(camerainfo, file_name):
    with PiCamera(resolution=camerainfo['resolution']) as camera:
        camera.start_preview()
        sleep(2)
        camera.capture(file_name)
        return file_name


def get_camera(camerainfo=detect_camera_hardware(), binning=2):
    camera = PiCamera()
    camera.resolution = (int(camerainfo['resolution'][0] / binning), int(camerainfo['resolution'][1] / binning))
    return camera


def delete_files(path):
    for fn in os.listdir(path):
        fp = os.path.join(path, fn)
        try:
            if os.path.isfile(fp):
                os.unlink(fp)
        except:
            pass


def ramtmp_generator(camera, count, delay):
    global ramtmp_count

    stop_capture = False
    i = 0
    while not stop_capture:
        last = datetime.datetime.now()
        if i == 0:
            print('STATUS First Exposure...', flush=True)
        else:
            pass
            # print('STATUS Capturing image %d' % (i + 1,), flush=True)
        yield RAMTMP + '/%d.jpg' % (ramtmp_count)
        ramtmp_count += 1
        old_file = RAMTMP + "/%d.jpg" % (ramtmp_count - 2,)
        if os.path.exists(old_file):
            os.remove(old_file)
        print('LOG ramtmp_generator', flush=True)
        print('CAPTURED ' + str(ramtmp_count - 1), flush=True)
        dt = delay - (datetime.datetime.now() - last).total_seconds()
        print('LOG ', dt, flush=True)
        if dt > 0:
            sleep(dt)
        # queue.put(RAMTMP+'/%d.jpg' % (paa_count-1,))
        # socketio.emit('paa_capture_response', {'message': 'captured'})
        line = None
        while select.select([sys.stdin], [], [], 0.0)[0]:
            line = sys.stdin.readline().strip()
        if line:
            try:
                cmd = parse_cmd(line)
                if cmd:
                    exposure_time = int(cmd['exposure_time'])
                    camera.shutter_speed = exposure_time
                    framerate = Fraction(1000000.0 / exposure_time)
                    if framerate > 40:
                        framerate = Fraction(40)
                    camera.framerate = framerate
                    camera.iso = cmd['iso']
                    i = 0
                    count = cmd['count']
                    delay = cmd['delay']
            except:
                print('LOG exception while running camera cmd', sys.exc_info()[0])
        i += 1
        if (count != -1 and i >= count) or line == 'stop':
            stop_capture = True
    print("CAPTUREDONE", flush=True)
    print('STATUS Done capturing', flush=True)
    print('LOG ramtmp_generator done', flush=True)


def capture(exposure_time=100000, iso=800, count=1, delay=0.25, camera=None,
            camerainfo=detect_camera_hardware()):
    print('STATUS Setting up camera', flush=True)
    created_camera = False
    if exposure_time > camerainfo['max_exposure']:
        exposure_time = camerainfo['max_exposure']
    framerate = Fraction(1000000.0 / exposure_time)
    try:
        if not camera:
            created_camera = True
            print('Getting Camera')
            camera = get_camera()
            print('Got Camera')
        # camera.start_preview()
        # camera.exposure_mode = 'night'
        # camera.awb_mode = 'fluorescent'
        camera.iso = iso
        # sleep(10)
        camera.shutter_speed = exposure_time
        camera.framerate = framerate
        print('Starting capture_sequence')
        camera.capture_sequence(ramtmp_generator(camera, count, delay), use_video_port=True)
        print('capture sequence done')
        # camera.stop_preview()
    finally:
        if created_camera and camera:
            camera.close()


def parse_cmd(line):
    sline = line.strip().split(' ')
    # Arg 1: exposure_time microseconds
    # Arg 2: ISO
    # Arg 3: num of exposures (-1 for inf)
    # Arg 4: Delay between exposures (s)
    ret = {}
    if len(sline) == 4:
        ret['exposure_time'] = int(sline[0])
        ret['iso'] = int(sline[1])
        ret['count'] = int(sline[2])
        ret['delay'] = float(sline[3])
        return ret
    return None


def rm_in_dir(dir):
    for the_file in os.listdir(dir):
        file_path = os.path.join(dir, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)


def main():
    rm_in_dir(RAMTMP)
    line = sys.stdin.readline()
    with get_camera() as camera:
        while line != '':
            cmd = parse_cmd(line)
            if cmd:
                print('LOG cmd:', cmd, flush=True)
                capture(cmd['exposure_time'], cmd['iso'], cmd['count'], cmd['delay'], camera)
            if line.strip() == 'QUIT':
                return
            line = sys.stdin.readline()


if __name__ == '__main__':
    main()
