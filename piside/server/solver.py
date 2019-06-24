import shutil
import os
import threading
import subprocess
import astropy.io.fits
import astropy.wcs
import math
import datetime
import traceback


class Solver:
    def __init__(self, work_dir, solver_log_cb, solver_done_cb, final_plot_path):
        """

        :param work_dir: Should be a directory solver can feel free to remove.
        :param solver_log_cb: Calls to log message string
        :param solver_done_cb:  Calls when it is done solving.
        """
        self.__work_dir = work_dir
        self.__thread = None
        self.__solver_log_cb = solver_log_cb
        self.__solver_done_cb = solver_done_cb
        self.__final_plot_path = final_plot_path
        self.low = 33
        self.high = 36
        self.pixel_error = 1
        self.code_tolerance = 0.01
        self.queue = False
        self.__theta = None
        self.__last_solve = None
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

    def running(self):
        # Return true if thread still going
        return self.__thread is not None and self.__thread.is_alive()

    def get_solved_plot_path(self):
        return self.__final_plot_path

    def get_last_solved_info(self):
        return {'polaris_theta': self.__theta, 'last_solve': self.__last_solve, 'solve_time': self.__solve_time}

    def __run(self):
        pre = datetime.datetime.now()
        exitstatus = None
        status = ""
        try:
            # Crop image
            subprocess.check_call(
                ['/usr/bin/convert', os.path.join(self.__work_dir, 'work_image.jpg'), '-gravity', 'center', '-crop',
                 '820x616+0+0', os.path.join(self.__work_dir, 'work_image_crop.jpg')])
            # solve
            process = subprocess.Popen(
                ['/usr/bin/timeout', '120', '/usr/bin/solve-field', '-D', self.__work_dir, '-u', 'degw', '-L', str(self.low), '-H', str(self.high),
                 '-E', str(self.pixel_error), '-c', str(self.code_tolerance),
                 os.path.join(self.__work_dir, 'work_image_crop.jpg')], stdout=subprocess.PIPE)
            for line in process.stdout:
                line = line.rstrip()
                self.__solver_log_cb(line)
            process.wait()
            # if successful
            exitstatus = process.returncode
            if exitstatus == 0:
                wcs_path = os.path.join(self.__work_dir, 'work_image_crop.wcs')
                # Modify wcs
                ncp = None
                polaris = None
                with astropy.io.fits.open(wcs_path, mode='update') as wcsf:
                    wcsf[0].header['CRPIX1'] = wcsf[0].header['CRPIX1'] + 410
                    wcsf[0].header['CRPIX2'] = wcsf[0].header['CRPIX2'] + 308
                    wcsf[0].header['ImageW'] = 1640
                    wcsf[0].header['ImageH'] = 1232
                    # Get info
                    w = astropy.wcs.WCS(wcsf[0].header)
                    ncp = w.wcs_world2pix(0, 90, 0)
                    polaris = w.wcs_world2pix(37.954561, 89.264109, 0)
                    theta = math.atan2(ncp[1] - polaris[1], ncp[0] - polaris[0])
                    self.__theta = theta
                    self.__last_solve = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
                # Make constellations file
                subprocess.check_call(['/usr/bin/plot-constellations', '-w', wcs_path, '-C', '-B', '-b', '15', '-o',
                                       self.__final_plot_path])
                self.__solve_time = (datetime.datetime.now() - pre).total_seconds()
                status = 'Success'
            else:
                status = 'Failed, solver failed.'
        except Exception as e:
            traceback.print_exc()
            status = 'Failed, ' + str(e)
        # Cleanup
        shutil.rmtree(self.__work_dir)
        if not os.path.exists(self.__work_dir):
            os.makedirs(self.__work_dir)
        self.__solver_done_cb(status)

    def solve(self, image):
        self.queue = False
        # Make a copy
        shutil.copyfile(image, os.path.join(self.__work_dir, 'work_image.jpg'))
        # new thread Send to solve field
        if not self.running():
            self.__thread = threading.Thread(target=self.__run)
            self.__thread.start()
