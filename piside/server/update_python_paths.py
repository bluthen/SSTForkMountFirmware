import os
import sys


def correct_dir():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    sys.path.append(os.path.join(dname, 'site-packages.zip'))


correct_dir()
