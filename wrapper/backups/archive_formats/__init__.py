import os
import threading
import platform

from subprocess import PIPE, Popen
from wrapper.commons import *

class ArchiveFormat(object):
    def __init__(self, name, destination, include, compression):
        self.name = name
        self.destination = destination
        self.include = include
        self.compression = compression

    def check_bin_installed(self, bin):
        which = "where" if platform.system() == "Windows" else "which"
        status_code = subprocess.call(which, "tar")

        return status_code == 0
