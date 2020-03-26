import os
import threading
import time

from subprocess import PIPE, Popen
from wrapper.commons import *

class Tar:
    def __init__(self, name, destination, include, compression):
        self.name = name
        self.destination = destination
        self.include = include
        self.compression = compression

        self.command = ["tar"]

        if self.compression:
            self.command += ["-cvzf"]
            filename = "%s.tar.gz" % name
        else:
            self.command += ["-cvf"]
            filename = "%s.tar" % name

        path = os.path.join(destination, filename)
        self.command += [path] + include

        print(self.command)

        self.proc = Popen(self.command, stdout=PIPE, stderr=PIPE)
        self.thread = threading.Thread(target=self._thread, args=())
        self.thread.daemon = True
        self.thread.start()

        self.status = BACKUP_STARTED

    def _thread(self):
        print("_thread")
        while self.proc.poll() is None:
            line = self.proc.stdout.readline()
            if len(line) < 1: continue

            print(line)

        status_code = self.proc.poll()
        print("Ended with status code %s" % status_code)

        if status_code == 0:
            self.status = BACKUP_COMPLETE
        else:
            self.status = BACKUP_FAILURE

# BACKUP_STARTED = 0x05
# BACKUP_COMPLETE = 0x06
# BACKUP_FAILURE = 0x07

if __name__ == "__main__":
    tar = Tar("wowzers", "/tmp/", ["README.md"], True)

    while True:
        print(tar.status)
        time.sleep(.1)
