from fractions import Fraction
import shutil
import time
import types


def iw_scan_decode():
    with open('./simulation_files/iw_output', 'r') as f:
        return f.read()


def iw_scan():
    return types.SimpleNamespace(**{'stdout': types.SimpleNamespace(**{'decode': iw_scan_decode})})
