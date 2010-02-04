#
# util.py
#

import os

def touch(fname, times = None):
    with file(fname, 'a'):
        os.utime(fname, times)
