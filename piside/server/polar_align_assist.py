from picamera import PiCamera
from time import sleep
from fractions import Fraction
import os
import sys
import select
import datetime

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


def ramtmp_generator(camera, single):
    global ramtmp_count

    stop_capture = False
    while not stop_capture:
        last = datetime.datetime.now()
        yield '/ramtmp/%d.jpg' % (ramtmp_count)
        ramtmp_count += 1
        old_file = "/ramtmp/%d.jpg" % (ramtmp_count-2,)
        if os.path.exists(old_file):
            os.remove(old_file)
        print('ramtmp_generator', file=sys.stderr, flush=True)
        print('CAPTURED '+str(ramtmp_count-1), flush=True)
        dt = 0.25 - (datetime.datetime.now() - last).total_seconds()
        print(dt, file=sys.stderr, flush=True)
        if dt > 0:
            sleep(dt)
        # queue.put('/ramtmp/%d.jpg' % (paa_count-1,))
        # socketio.emit('paa_capture_response', {'message': 'captured'})
        qitem = None
        if select.select([sys.stdin], [], [], 0.0)[0]:
            qitem = sys.stdin.readline().strip()
        if single or qitem == 'stop':
            stop_capture = True
        if qitem:
            sline = qitem.split(' ')
            if len(sline) == 3:
                exposure_time = int(sline[0])
                camera.shutter_speed = exposure_time
                camera.framerate = Fraction(1000000.0 / exposure_time)
                camera.iso = int(sline[2])
                single = sline[1].lower() == 'true'
    print('ramtmp_generator done', file=sys.stderr, flush=True)


def capture(exposure_time, single=False, camera=None, camerainfo=detect_camera_hardware(), iso=800):
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
        camera.capture_sequence(ramtmp_generator(camera, single), use_video_port=True)
        print('capture sequence done')
        #camera.stop_preview()
    finally:
        if created_camera and camera:
            camera.close()


def main():
    line = sys.stdin.readline().strip()
    with get_camera() as camera:
        while line:
            sline = line.split(' ')
            if len(sline) == 3:
                exposure_time = int(sline[0])
                single = sline[1].lower() == 'true'
                iso = int(sline[2])
                capture(exposure_time, single, camera, iso=iso)
            if line.strip() == 'QUIT':
                return
            line = sys.stdin.readline().strip()


if __name__ == '__main__':
    main()
