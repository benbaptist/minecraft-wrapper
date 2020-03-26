import time
import os

from subprocess import PIPE, Popen

from wrapper.commons import *
from wrapper.exceptions import *

class Backup(object):
    def __init__(self, backups):
        self.backups = backups
        self.wrapper = backups.wrapper
        self.log = backups.log
        self.config = self.wrapper.config["backups"]

        self.name = None
        self.proc = None

        self.backup_complete = None

    @property
    def status(self):
        if not self.proc:
            return -1

        status_code = self.proc.poll()

        if status_code == 0:
            if not self.backup_complete:
                self.backup_complete = time.time()

            return BACKUP_COMPLETE
        elif status_code == None:
            return BACKUP_STARTED
        else:
            return BACKUP_FAILED

        return BACKUP_STARTED

    @property
    def details(self):
        if not self.status == BACKUP_COMPLETE:
            raise EOFError("Backup is not complete")

        return {
            "backup-start": self.backup_start,
            "backup-complete": self.backup_complete,
            "name": self.name,
            "path": self.path,
            "archive-method": self.archive_method,
            "filesize": os.path.getsize(self.path),
            "compression": self.config["archive-format"]["compression"]["enable"],
            "include-paths": self.backups.get_included_paths()
        }

    def build_command(self):
        include_paths = self.backups.get_included_paths()
        destination = self.backups.get_backup_destination()
        compression = self.config["archive-format"]["compression"]["enable"]

        self.archive_method = self.backups.get_archive_method()

        self.log.debug("Using archive method '%s'" % self.archive_method)

        path = os.path.join(destination, self.name)

        if self.archive_method == "tar":
            path = "%s.%s" % (path, "tar.gz" if compression else "tar")

            command = [
                "tar", "-cvzf" if compression else "-cvf", path
            ] + include_paths
        elif self.archive_method == "7z":
            path = "%s.7z" % path

            command = [
                "7z", "a", "-mx=9" if compression else "-mx=0",
                path
            ] + include_paths
        elif self.archive_method == "zip":
            path = "%s.7z" % path
            command = ["zip"]
        else:
            raise UnsupportedFormat(self.archive_method)

        return (command, path)

    def execute_command(self, command):
        self.log.debug("Command: %s" % " ".join(command))
        self.proc = Popen(command, stdout=PIPE, stderr=PIPE)

    def start(self):
        self.backup_start = time.time()
        self.name = "backup_%s" % time.strftime("%Y-%m-%d_%H-%M-%S")

        command, self.path = self.build_command()
        self.execute_command(command)

    def cancel(self):
        return
