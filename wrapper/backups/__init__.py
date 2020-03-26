import time
import os
import subprocess
import platform

from wrapper.exceptions import *
from wrapper.commons import *
from wrapper.backups.backup import Backup

# Archival methods
from wrapper.backups.tar import Tar

class Backups:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.server = wrapper.server
        self.config = self.wrapper.config["backups"]
        self.log = wrapper.log_manager.get_logger("backups")

        self.last_backup = time.time()
        self.current_backup = None

    def check_bin_installed(self, bin):
        which = "where" if platform.system() == "Windows" else "which"

        try:
            subprocess.check_output([which, bin])
        except subprocess.CalledProcessError:
            return False

        return True

    def get_best_archive_method(self):
        if self.check_bin_installed("7z"):
            return "7z"
        elif self.check_bin_installed("tar"):
            return "tar"
        elif self.check_bin_installed("zip"):
            return "zip"
        else:
            raise UnsupportedFormat(
                "No archival methods are installed. Please install either 7z, "
                "zip, or tar to use backups."
            )

    def get_archive_method(self):
        if self.config["archive-format"]["format"] == "auto":
            return self.get_best_archive_method()
        else:
            assert self.config["archive-format"]["format"] in ("tar", "7z", "zip")
            return self.config["archive-format"]["format"]

    def get_backup_destination(self):
        # Make this run through realpath later
        return self.config["destination"]

    def get_included_paths(self):
        if self.config["backup-mode"] == "auto":
            # Automatically determine folders and files
            # to backup, based off 'include' settings
            include = []

            if self.config["include"]["world"]:
                include.append(str(self.server.world))

            if self.config["include"]["logs"]:
                include.append("logs")

            if self.config["include"]["server-properties"]:
                include.append("server.properties")

            if self.config["include"]["wrapper-data"]:
                include.append("wrapper-data")

            if self.config["include"]["whitelist-ops-banned"]:
                include.append("banned-ips.json")
                include.append("banned-players.json")
                include.append("ops.json")
                include.append("whitelist.json")

            for include_path in self.config["include-paths"]:
                if include_path not in include:
                    include.append(include_path)

            return include
        elif self.config["backup-mode"] == "manual":
            # Only backup specified files in 'include-paths'
            return self.config["include-paths"]

    def tick(self):
        # If backups are disabled, skip tick
        if not self.config["enable"]:
            return

        # If server isn't fully started, skip tick
        if self.server.state != SERVER_STARTED:
            return

        # If there's a current backup, check on it
        if self.current_backup:
            if self.current_backup.status == BACKUP_STARTED:
                self.server.title({
                    "text": "Backup started. Server may lag.",
                    "color": "red"
                }, title_type="actionbar")
            if self.current_backup.status == BACKUP_COMPLETE:
                details = self.current_backup.details

                self.log.info(
                    "Backup complete. Took %s seconds, and uses %s of storage."
                    % (details["backup-complete"] - details["backup-start"],
                    bytes_to_human(details["filesize"]))
                )

                self.server.title({
                    "text": "Backup complete.",
                    "color": "green"
                }, title_type="actionbar")

                self.last_backup = time.time()

            if self.current_backup.status == BACKUP_FAILED:
                self.log.info("Backup failed.")

            if self.current_backup.status in (BACKUP_COMPLETE, BACKUP_FAILED):
                self.current_backup = None
            return

        # Check when backup is ready
        if time.time() - self.last_backup > self.config["interval-seconds"]:
            # If backup destination path doesn't exist or isn't set, skip backup
            destination = self.get_backup_destination()
            if not destination or not os.path.exists(destination):
                try:
                    os.mkdir(destination)
                except OSError:
                    self.log.error(
                        "Backup path could not be created. Skipping backup"
                    )

                self.last_backup = time.time()
                return

            self.log.info("Starting backup")

            self.current_backup = Backup(self)
            self.current_backup.start()
