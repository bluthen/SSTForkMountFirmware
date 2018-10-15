import settings

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
import shutil
import img_average

# Version 2 Camera resolution 3280x2464 max 10s exposure
# Version 1 Camera resolution 2592x1944 max 6s exposure
CAMERAV1 = {'version': 1, 'resolution': (2592, 1944), 'max_exposure': 6000000, 'smallest_framerate': Fraction(1,6)}
CAMERAV2 = {'version': 2, 'resolution': (3280, 2464), 'max_exposure': 10000000, 'smallest_framerate': Fraction(1,10)}
CAMERAUNKNOWN = {'version': -1, 'resolution': (0, 0), 'max_exposure': 100}

ramtmp_count = 0

def detect_camera_hardware():
    with PiCamera() as camera:
        width = camera.MAX_RESOLUTION[0]
        if width == 2592: # v1 max resolution
            return CAMERAV1
        elif width == 3280: # v2 max resolution
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
    camera.resolution = (int(camerainfo['resolution'][0]/binning), int(camerainfo['resolution'][1]/binning))
    return camera


def delete_files(path):
    for fn in os.listdir(path):
        fp = os.path.join(path, fn)
        try:
            if os.path.isfile(fp):
                os.unlink(fp)
        except:
            pass


def ramtmp_generator(camera, count, delay, calibrate_mode):
    global ramtmp_count

    if calibrate_mode:
        delete_files('/caltmp')

    stop_capture = False
    i = 0
    while not stop_capture:
        last = datetime.datetime.now()
        if i == 0:
            print('STATUS First Exposure...', flush=True)
        else:
            print('STATUS Capturing image %d' % (i+1,), flush=True)
        yield '/ramtmp/%d.jpg' % (ramtmp_count)
        ramtmp_count += 1
        old_file = "/ramtmp/%d.jpg" % (ramtmp_count-2,)
        if os.path.exists(old_file):
            os.remove(old_file)
        if calibrate_mode:
            shutil.copyfile("/ramtmp/%d.jpg" % (ramtmp_count-1), "/caltmp/%d.jpg" % (ramtmp_count-1))
        print('ramtmp_generator', file=sys.stderr, flush=True)
        print('CAPTURED '+str(ramtmp_count-1), flush=True)
        dt = delay - (datetime.datetime.now() - last).total_seconds()
        print(dt, file=sys.stderr, flush=True)
        if dt > 0:
            sleep(dt)
        # queue.put('/ramtmp/%d.jpg' % (paa_count-1,))
        # socketio.emit('paa_capture_response', {'message': 'captured'})
        line = None
        if select.select([sys.stdin], [], [], 0.0)[0]:
            line = sys.stdin.readline().strip()
        if line:
            cmd = parse_cmd(line)
            if cmd:
                exposure_time = int(cmd['exposure_time'])
                camera.shutter_speed = exposure_time
                camera.framerate = Fraction(1000000.0 / exposure_time)
                camera.iso = cmd['iso']
                i = 0
                count = cmd['count']
                delay = cmd['delay']
                calibrate_mode = cmd['calibrate_mode']
        i += 1
        if (count != -1 and i >= count) or line == 'stop':
            stop_capture = True
    print("CAPTUREDONE", flush=True)
    if calibrate_mode:
        print('ramtmp_generator calibrating', ramtmp_count, file=sys.stderr, flush=True)
        print("STATUS Averaging images", flush=True)
        img_average.average('/caltmp')
        shutil.copyfile('/caltmp/average.jpg', '/ramtmp/%d.jpg' % (ramtmp_count,))
        delete_files('/caltmp')
        ramtmp_count += 1
        old_file = "/ramtmp/%d.jpg" % (ramtmp_count-2,)
        if os.path.exists(old_file):
            os.remove(old_file)
        print('CAPTURED ' + str(ramtmp_count - 1), flush=True)
    print('STATUS Done capturing', flush=True)
    print('ramtmp_generator done', file=sys.stderr, flush=True)


def capture(exposure_time=100000, iso=800, count=1, delay=0.25, calibrate_mode=False, camera=None, camerainfo=detect_camera_hardware()):
    print('STATUS Setting up camera', flush=True)
    created_camera = False
    if exposure_time > camerainfo['max_exposure']:
        exposure_time = camerainfo['max_exposure']
    framerate = Fraction(1000000.0/exposure_time)
    try:
        if not camera:
            created_camera = True
            print('Getting Camera')
            camera = get_camera()
            print('Got Camera')
        #camera.start_preview()
        #camera.exposure_mode = 'night'
        #camera.awb_mode = 'fluorescent'
        camera.iso = iso
        #sleep(10)
        camera.shutter_speed = exposure_time
        camera.framerate = framerate
        print('Starting capture_sequence')
        camera.capture_sequence(ramtmp_generator(camera, count, delay, calibrate_mode), use_video_port=True)
        print('capture sequence done')
        #camera.stop_preview()
    finally:
        if created_camera and camera:
            camera.close()


def parse_cmd(line):
    sline = line.strip().split(' ')
    # Arg 1: exposure_time microseconds
    # Arg 2: ISO
    # Arg 3: num of exposures (-1 for inf)
    # Arg 4: Delay between exposures (s)
    # Arg 5: If calibrate mode
    ret = {}
    if len(sline) == 5:
        ret['exposure_time'] = int(sline[0])
        ret['iso'] = int(sline[1])
        ret['count'] = int(sline[2])
        ret['delay'] = float(sline[3])
        ret['calibrate_mode'] = sline[4].lower() == 'true'
        return ret
    return None


def main():
    line = sys.stdin.readline()
    with get_camera() as camera:
        while line != '':
            cmd = parse_cmd(line)
            if cmd:
                print('cmd:', cmd, file=sys.stderr, flush=True)
                capture(cmd['exposure_time'], cmd['iso'], cmd['count'], cmd['delay'], cmd['calibrate_mode'], camera)
            if line.strip() == 'QUIT':
                return
            line = sys.stdin.readline()


if __name__ == '__main__':
    main()
