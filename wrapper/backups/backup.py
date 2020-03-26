import time
import os

from subprocess import PIPE, Popen

from wrapper.commons import *
from wrapper.exceptions import *

class Backup(object):
    def __init__(self, backups):
        self.backups = backups
        self.wrapper = backups.wrapper
        self.config = self.wrapper.config["backups"]

        self.name = None
        self.proc = None

    @property
    def status(self):
        if not self.proc:
            return -1

        status_code = self.proc.poll()

        if status_code == 0:
            return BACKUP_COMPLETE

        return BACKUP_STARTED

    def build_command(self):
        include_paths = self.backups.get_included_paths()
        destination = self.backups.get_backup_destination()
        compression = self.config["archive-format"]["compression"]["enable"]

        archive_method = self.backups.get_archive_method()

        path = os.path.join(destination, self.name)

        if archive_method == "tar":
            path = "%s.%s" % (path, "tar.gz" if compression else "tar")

            command = [
                "tar", "-cvzf" if compression else "-cvf", path
            ] + include_paths
        elif archive_method == "7z":
            path = "%s.7z" % path

            command = [
                "7z", "a", "-mx=9" if compression else "-mx=0",
                path
            ] + include_paths
        elif archive_method == "zip":
            path = "%s.7z" % path
            command = ["zip"]
        else:
            raise UnsupportedFormat(archive_method)

        return command

    def execute_command(self, command):
        print("command", command)
        self.proc = Popen(command, stdout=PIPE, stderr=PIPE)

    def start(self):
        self.backup_start = time.time()
        self.name = "backup_%s" % time.strftime("%Y-%m-%d_%H-%M-%S")

        command = self.build_command()
        self.execute_command(command)

    def cancel(self):
        return
