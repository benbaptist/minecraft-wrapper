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
# noinspection PyProtectedMember
from api.helpers import _secondstohuman, format_bytes

# I should probably not use irc=True when broadcasting, and instead should
# just rely on events and having MCserver.py and irc.py print messages
# themselves for the sake of consistency.


class Backups(object):

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        self.encoding = self.config["General"]["encoding"]
        self.log = wrapper.log
        self.api = API(wrapper, "Backups", internal=True)

        # self.wrapper.backups.idle
        self.idle = True
        self.inprogress = False
        self.backup_interval = self.config["Backups"]["backup-interval"]
        self.time = time.time()
        self.backups = []

        # allow plugins to shutdown backups via api
        self.enabled = self.config["Backups"]["enabled"]

        # only register event if used and tar installed.
        if self.enabled and self.dotarchecks():
            self.api.registerEvent("timer.second", self.eachsecond)
            self.log.debug("Backups Enabled..")

    # noinspection PyUnusedLocal
    def eachsecond(self, payload):
        # only run backups in server running/starting states
        if self.wrapper.javaserver.vitals.state in (1, 2) and not self.idle:
            if time.time() - self.time > self.backup_interval and self.enabled:
                self.dobackup()

    def pruneoldbackups(self, filename="IndependentPurge"):
        if len(self.backups) > self.config["Backups"]["backups-keep"]:
            self.log.info("Deleting old backups...")
            while len(self.backups) > self.config["Backups"]["backups-keep"]:
                backup = self.backups[0]
                if not self.wrapper.events.callevent("wrapper.backupDelete", {"file": filename}):  # noqa
                    """ eventdoc
                                    <group> Backups <group>

                                    <description> Called upon deletion of a backup file.
                                    <description>

                                    <abortable> Yes, return False to abort. <abortable>

                                    <comments>
                                    
                                    <comments>
                                    <payload>
                                    "file": filename
                                    <payload>

                                """  # noqa
                    break
                try:
                    os.remove(
                        '%s/%s' % (self.config["Backups"]["backup-location"],
                                   backup[1])
                    )
                except Exception as e:
                    self.log.error("Failed to delete backup (%s)", e)
                self.log.info("Deleting old backup: %s",
                              datetime.datetime.fromtimestamp(int(backup[0])).strftime('%Y-%m-%d_%H:%M:%S'))  # noqa
                # hink = self.backups[0][1][:]  # not used...
                del self.backups[0]
        putjsonfile(
            self.backups, "backups", self.config["Backups"]["backup-location"])

    def dotarchecks(self):
        # Check if tar is installed
        which = "where" if platform.system() == "Windows" else "which"
        if not subprocess.call([which, "tar"]) == 0:
            self.wrapper.events.callevent(
                "wrapper.backupFailure",
                {"reasonCode": 1,
                 "reasonText": "Tar is not installed. Please install "
                               "tar before trying to make backups."},
                abortable=False
            )
            """ eventdoc
                <group> Backups <group>

                <description> Indicates failure of backup.
                <description>

                <abortable> No - informatinal only <abortable>

                <comments>
                Reasoncode and text provide more detail about specific problem.
                1 - Tar not installed.
                2 - Backup file does not exist after the tar operation.
                3 - Specified file does not exist.
                4 - backups.json is corrupted
                5 - unable to create backup directory
                <comments>
                <payload>
                "reasonCode": an integer 1-4
                "reasonText": a string description of the failure.
                <payload>

            """
            self.log.error(
                "Backups will not work, because tar does not appear "
                "to be installed!"
            )
            self.log.error(
                "If you are on a Linux-based system, please install it through"
                " your preferred package manager."
            )
            self.log.error(
                "If you are on Windows, you can find GNU/Tar from this link:"
                " http://goo.gl/SpJSVM"
            )
            return False
        else:
            return True

    def dobackup(self):
        self.inprogress = True
        self.log.debug("Backup starting.")
        self._settime()
        if not self._checkforbackupfolder():
            self.inprogress = False
            self.wrapper.events.callevent(
                "wrapper.backupFailure",
                {
                 "reasonCode": 5,
                 "reasonText": "Backup location could not be found/created!"
                },
                abortable=False
            )
            self.log.warning("")
        self._getbackups()  # populate self.backups
        self._performbackup()
        self.log.debug("dobackup() cycle complete.")
        self.inprogress = False

    def _checkforbackupfolder(self):
        if not os.path.exists(self.config["Backups"]["backup-location"]):
            self.log.warning(
                "Backup location %s does not exist -- creating target "
                "location...", self.config["Backups"]["backup-location"]
            )
            mkdir_p(self.config["Backups"]["backup-location"])
        if not os.path.exists(self.config["Backups"]["backup-location"]):
            self.log.error(
                "Backup location %s could not be created!",
                self.config["Backups"]["backup-location"]
            )
            return False
        return True

    def _performbackup(self):
        timestamp = int(time.time())

        # Turn off server saves...
        self.wrapper.javaserver.doserversaving(False)
        # give server time to save
        time.sleep(1)

        # Create tar arguments
        filename = "backup-%s.tar" % datetime.datetime.fromtimestamp(
            int(timestamp)).strftime("%Y-%m-%d_%H.%M.%S")
        if self.config["Backups"]["backup-compression"]:
            filename += ".gz"
            arguments = ["tar", "czf", "%s/%s" % (
                self.config["Backups"]["backup-location"].replace(" ", "\\ "),
                filename)]
        else:
            arguments = ["tar", "cfpv", "%s/%s" % (
                self.config["Backups"]["backup-location"], filename)]

        # Process begin Events
        if not self.wrapper.events.callevent("wrapper.backupBegin", {"file": filename}):  # noqa
            self.log.warning(
                "A backup was scheduled, but was cancelled by a plugin!"
            )
            """ eventdoc
                <group> Backups <group>

                <description> Indicates a backup is being initiated.
                <description>

                <abortable> Yes, return False to abort. <abortable>

                <comments>
                A console warning will be issued if a plugin cancels the backup.
                <comments>
                <payload>
                "file": Name of backup file.
                <payload>

            """
            self.wrapper.javaserver.doserversaving(True)
            # give server time to save
            time.sleep(1)
            return

        if self.config["Backups"]["backup-notification"]:
            self.api.minecraft.broadcast(
                "&cBacking up... lag may occur!", irc=False)

        # Do backups
        serverpath = self.config["General"]["server-directory"]
        for backupfile in self.config["Backups"]["backup-folders"]:
            backup_file_and_path = "%s/%s" % (serverpath, backupfile)
            if os.path.exists(backup_file_and_path):
                arguments.append(backup_file_and_path)
            else:
                self.log.warning(
                    "Backup file '%s' does not exist - canceling backup",
                    backup_file_and_path
                )
                self.wrapper.events.callevent(
                    "wrapper.backupFailure",
                    {"reasonCode": 3,
                     "reasonText": "Backup file '%s' does not "
                                   "exist." % backup_file_and_path},
                    abortable=False
                )
                """ eventdoc
                                <description> internalfunction <description>

                            """
                return
        # perform TAR backup
        statuscode = os.system(" ".join(arguments))

        # TODO add a wrapper properties config item to set save mode of server
        # restart saves, call finish Events
        self.wrapper.javaserver.doserversaving(True)
        self.backups.append((timestamp, filename))

        # Prune backups
        self.pruneoldbackups(filename)

        # Check for success
        finalbackup = "%s/%s" % (self.config["Backups"]["backup-location"],
                                 filename)

        if not os.path.exists(finalbackup):
            self.wrapper.events.callevent(
                "wrapper.backupFailure",
                {"reasonCode": 2,
                 "reasonText": "Backup file didn't exist after the tar "
                               "command executed - assuming failure."},
                abortable=False
            )
            """ eventdoc
                <description> internalfunction <description>

            """
            summary = "backup failed"
        else:
            # find size of completed backup file
            backupsize = os.path.getsize(finalbackup)
            size_of, units = format_bytes(backupsize)
            timetook = _secondstohuman(int(time.time()) - timestamp)
            desc = "were backed up.  The operation took"
            summary = "%s %s %s %s" % (size_of, units, desc, timetook)

        self.wrapper.events.callevent(
            "wrapper.backupEnd",
            {"file": filename, "status": statuscode, "summary": summary},
            abortable=False
        )
        """ eventdoc
            <group> Backups <group>

            <description> Indicates a backup is complete.
            <description>

            <abortable> No - informational only <abortable>

            <comments>
            <comments>
            <payload>
            "file": Name of backup file.
            "status": Status code from TAR
            "summary": string summary of operation 
            <payload>

        """
        if self.config["Backups"]["backup-notification"]:
            self.api.minecraft.broadcast("&aBackup cycle complete!", irc=False)
            self.api.minecraft.broadcast("&a%s" % summary, irc=False)

    def _getbackups(self):
        if len(self.backups) == 0 and os.path.exists(self.config["Backups"]["backup-location"] + "/backups.json"):  # noqa - long if statement
            loadcode = getjsonfile(
                "backups", self.config["Backups"]["backup-location"],
                encodedas=self.encoding
            )
            if not loadcode:
                self.log.error(
                    "NOTE - backups.json was unreadable. It might be corrupted."
                    " Backups will no longer be automatically pruned."
                )
                self.wrapper.events.callevent(
                    "wrapper.backupFailure",
                    {"reasonCode": 4,
                     "reasonText": "backups.json is corrupted. Please contact"
                                   " an administer instantly, as this may be "
                                   "critical."
                     },
                    abortable=False
                )
                """ eventdoc
                    <description> internalfunction <description>

                """
                self.backups = []
            else:
                self.backups = loadcode
        else:
            if len(os.listdir(self.config["Backups"]["backup-location"])) > 0:
                # import old backups from previous versions of Wrapper.py
                backuptimestamps = []
                for backupNames in os.listdir(
                        self.config["Backups"]["backup-location"]
                ):
                    # noinspection PyBroadException,PyUnusedLocal
                    try:
                        backuptimestamps.append(int(backupNames[backupNames.find('-') + 1:backupNames.find('.')]))  # noqa - large one-liner
                    except Exception as e:
                        pass
                backuptimestamps.sort()
                for backupI in backuptimestamps:
                    self.backups.append(
                        (int(backupI), "backup-%s.tar" % str(backupI))
                    )

    def _settime(self):
        self.time = time.time()
