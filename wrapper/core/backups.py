# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import datetime
import time

import subprocess
import os
import platform

from api.base import API
from api.helpers import putjsonfile, getjsonfile, mkdir_p

# I should probably not use irc=True when broadcasting, and instead should just rely on events and having
# MCserver.py and irc.py print messages themselves for the sake of consistency.


class Backups(object):

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        self.encoding = self.config["General"]["encoding"]
        self.log = wrapper.log
        self.api = API(wrapper, "Backups", internal=True)

        self.interval = 0
        self.backup_interval = self.config["Backups"]["backup-interval"]
        self.time = time.time()
        self.backups = []
        self.enabled = self.config["Backups"]["enabled"]  # allow plugins to shutdown backups via api
        self.timerstarted = False
        if self.enabled and self.dotarchecks():  # only register event if used and tar installed!
            self.api.registerEvent("timer.second", self.eachsecond)
            self.timerstarted = True
            self.log.debug("Backups Enabled..")

    # noinspection PyUnusedLocal
    def eachsecond(self, payload):
        self.interval += 1
        if time.time() - self.time > self.backup_interval and self.enabled:
            self.dobackup()

    def pruneoldbackups(self, filename="IndependentPurge"):
        if len(self.backups) > self.config["Backups"]["backups-keep"]:
            self.log.info("Deleting old backups...")
            while len(self.backups) > self.config["Backups"]["backups-keep"]:
                backup = self.backups[0]
                if not self.wrapper.events.callevent("wrapper.backupDelete", {"file": filename}):
                    break
                try:
                    os.remove('%s/%s' % (self.config["Backups"]["backup-location"], backup[1]))
                except Exception as e:
                    self.log.error("Failed to delete backup (%s)", e)
                self.log.info("Deleting old backup: %s",
                              datetime.datetime.fromtimestamp(int(backup[0])).strftime('%Y-%m-%d_%H:%M:%S'))
                # hink = self.backups[0][1][:]  # not used...
                del self.backups[0]
        putjsonfile(self.backups, "backups", self.config["Backups"]["backup-location"])

    def dotarchecks(self):
        # Check if tar is installed
        which = "where" if platform.system() == "Windows" else "which"
        if not subprocess.call([which, "tar"]) == 0:
            self.wrapper.events.callevent("wrapper.backupFailure",
                                          {"reasonCode": 1, "reasonText": "Tar is not installed. Please install "
                                                                          "tar before trying to make backups."})
            self.log.error("Backups will not work, because tar does not appear to be installed!")
            self.log.error("If you are on a Linux-based system, please install it through your preferred package "
                           "manager.")
            self.log.error("If you are on Windows, you can find GNU/Tar from this link: http://goo.gl/SpJSVM")
            return False
        else:
            return True

    def dobackup(self):
        self.log.debug("Backup starting.")
        self._settime()
        self._checkforbackupfolder()
        self._getbackups()  # populate self.backups
        self._performbackup()
        self.log.debug("Backup cycle complete.")

    def _checkforbackupfolder(self):
        if not os.path.exists(self.config["Backups"]["backup-location"]):
            self.log.warning("Backup location %s does not exist -- creating target location...",
                             self.config["Backups"]["backup-location"])
            mkdir_p(self.config["Backups"]["backup-location"])

    def _doserversaving(self, desiredstate=True):
        """
        :param desiredstate: True = turn serversaving on
                             False = turn serversaving off
        :return:

        Future expansion to allow config of server saving state glabally in config.  Plan to include a glabal
        config option for periodic or continuous server disk saving of the minecraft server.
        """
        if desiredstate:
            self.api.minecraft.console("save-all flush")  # flush argument is required
            self.api.minecraft.console("save-on")
        else:
            self.api.minecraft.console("save-all flush")  # flush argument is required
            self.api.minecraft.console("save-off")
            time.sleep(0.5)

    def _performbackup(self):
        timestamp = int(time.time())

        # Turn off server saves...
        self._doserversaving(False)

        # Create tar arguments
        filename = "backup-%s.tar" % datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d_%H.%M.%S")
        if self.config["Backups"]["backup-compression"]:
            filename += ".gz"
            arguments = ["tar", "czf", "%s/%s" % (self.config["Backups"]["backup-location"].replace(" ", "\\ "),
                                                  filename)]
        else:
            arguments = ["tar", "cfpv", "%s/%s" % (self.config["Backups"]["backup-location"], filename)]

        # Process begin Events
        if not self.wrapper.events.callevent("wrapper.backupBegin", {"file": filename}):
            self.log.warning("A backup was scheduled, but was cancelled by a plugin!")
            return
        if self.config["Backups"]["backup-notification"]:
            self.api.minecraft.broadcast("&cBacking up... lag may occur!", irc=False)

        # Do backups
        serverpath = self.config["General"]["server-directory"]
        for backupfile in self.config["Backups"]["backup-folders"]:
            backup_file_and_path = "%s/%s" % (serverpath, backupfile)
            if os.path.exists(backup_file_and_path):
                arguments.append(backup_file_and_path)
            else:
                self.log.warning("Backup file '%s' does not exist - canceling backup", backup_file_and_path)
                self.wrapper.events.callevent("wrapper.backupFailure", {"reasonCode": 3,
                                                                        "reasonText": "Backup file '%s' does not exist."
                                                                        % backup_file_and_path})
                return
        statuscode = os.system(" ".join(arguments))

        # TODO add a wrapper properties config item to set save mode of server
        # restart saves, call finish Events
        self._doserversaving()
        if self.config["Backups"]["backup-notification"]:
            self.api.minecraft.broadcast("&aBackup complete!", irc=False)
        self.wrapper.events.callevent("wrapper.backupEnd", {"file": filename, "status": statuscode})
        self.backups.append((timestamp, filename))

        # Prune backups
        self.pruneoldbackups(filename)

        # Check for success
        if not os.path.exists(self.config["Backups"]["backup-location"] + "/" + filename):
            self.wrapper.events.callevent("wrapper.backupFailure",
                                          {"reasonCode": 2, "reasonText": "Backup file didn't exist after the tar "
                                                                          "command executed - assuming failure."})

    def _getbackups(self):
        if len(self.backups) == 0 and os.path.exists(self.config["Backups"]["backup-location"] + "/backups.json"):
            loadcode = getjsonfile("backups", self.config["Backups"]["backup-location"],
                                   encodedas=self.encoding)
            if not loadcode:
                self.log.error("NOTE - backups.json was unreadable. It might be corrupted. Backups will no "
                               "longer be automatically pruned.")
                self.wrapper.events.callevent("wrapper.backupFailure", {
                    "reasonCode": 4,
                    "reasonText": "backups.json is corrupted. Please contact an administer instantly, as this "
                                  "may be critical."
                })
                self.backups = []
            else:
                self.backups = loadcode
        else:
            if len(os.listdir(self.config["Backups"]["backup-location"])) > 0:
                # import old backups from previous versions of Wrapper.py
                backuptimestamps = []
                for backupNames in os.listdir(self.config["Backups"]["backup-location"]):
                    # noinspection PyBroadException,PyUnusedLocal
                    try:
                        backuptimestamps.append(int(backupNames[backupNames.find('-') + 1:backupNames.find('.')]))
                    except Exception as e:
                        pass
                backuptimestamps.sort()
                for backupI in backuptimestamps:
                    self.backups.append((int(backupI), "backup-%s.tar" % str(backupI)))

    def _settime(self):
        self.time = time.time()
