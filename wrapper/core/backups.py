# -*- coding: utf-8 -*-

# p2 and py3 compliant (no PyCharm IDE-flagged errors)
#  (still has warnings in both versions)

import datetime
import time

import subprocess
import os
import json
import platform

from api.base import API

# Plans for this: separate backup code into its own method, allow for plugins to control backups more freely.
# I also should probably not use irc=True when broadcasting, and instead should just rely on events and having
# MCserver.py and irc.py print messages themselves for the sake of consistency.

# the comments above mystify me a little... this whole module is really just a wrapper plugin!


class Backups:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        self.log = wrapper.log
        self.api = API(wrapper, "Backups", internal=True)

        self.interval = 0
        self.time = time.time()
        self.backups = []
        self.api.registerEvent("timer.second", self.eachsecond)

    def eachsecond(self, payload):
        self.interval += 1
        if not self.config["Backups"]["enabled"]:
            return
        if time.time() - self.time > self.config["Backups"]["backup-interval"]:
            self.time = time.time()
            if not os.path.exists(self.config["Backups"]["backup-location"]):
                self.log.warning("Backup location %s does not exist -- creating target location...",
                                 self.config["Backups"]["backup-location"])
                os.mkdir(self.config["Backups"]["backup-location"])
            if len(self.backups) == 0 and os.path.exists(self.config["Backups"]["backup-location"] + "/backups.json"):
                with open(self.config["Backups"]["backup-location"] + "/backups.json", "r") as f:
                    try:
                        self.backups = json.loads(f.read())
                    except Exception as e:
                        self.log.error("NOTE - backups.json was unreadable. It might be corrupted. Backups will no "
                                       "longer be automatically pruned.")
                        self.wrapper.events.callevent("wrapper.backupFailure", {
                            "reasonCode": 4, 
                            "reasonText": "backups.json is corrupted. Please contact an administer instantly, as this "
                                          "may be critical."
                        })
                        self.backups = []
            else:
                if len(os.listdir(self.config["Backups"]["backup-location"])) > 0:
                    # import old backups from previous versions of Wrapper.py
                    backuptimestamps = []
                    for backupNames in os.listdir(self.config["Backups"]["backup-location"]):
                        try:
                            backuptimestamps.append(int(backupNames[backupNames.find('-') + 1:backupNames.find('.')]))
                        except Exception as e:
                            pass
                    backuptimestamps.sort()
                    for backupI in backuptimestamps:
                        self.backups.append((int(backupI), "backup-%s.tar" % str(backupI)))
            timestamp = int(time.time())
            # flush argument is required because saving is turned back off immediately in the next step.
            self.api.minecraft.console("save-all flush")
            self.api.minecraft.console("save-off")
            time.sleep(0.5)

            if not os.path.exists(str(self.config["Backups"]["backup-location"])):
                os.mkdir(self.config["Backups"]["backup-location"])

            filename = "backup-%s.tar" % datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d_%H.%M.%S")
            if self.config["Backups"]["backup-compression"]:
                filename += ".gz"
                arguments = ["tar", "czf", "%s/%s" % (self.config["Backups"]["backup-location"].replace(" ", "\\ "),
                                                      filename)]
            else:
                arguments = ["tar", "cfpv", "%s/%s" % (self.config["Backups"]["backup-location"], filename)]

            # Check if tar is installed
            which = "where" if platform.system() == "Windows" else "which"
            if not subprocess.call([which, "tar"]) == 0:
                self.wrapper.events.callevent("wrapper.backupFailure", {"reasonCode": 1,
                                                                 "reasonText": "Tar is not installed. Please install "
                                                                               "tar before trying to make backups."})
                self.log.error("The backup could not begin, because tar does not appear to be installed!")
                self.log.error("If you are on a Linux-based system, please install it through your preferred package "
                               "manager.")
                self.log.error("If you are on Windows, you can find GNU/Tar from this link: http://goo.gl/SpJSVM")
                return

            if not self.wrapper.events.callevent("wrapper.backupBegin", {"file": filename}):
                self.log.warning("A backup was scheduled, but was cancelled by a plugin!")
                return
            if self.config["Backups"]["backup-notification"]:
                self.api.minecraft.broadcast("&cBacking up... lag may occur!", irc=False)

            for backupfile in self.config["Backups"]["backup-folders"]:
                if os.path.exists(backupfile):
                    arguments.append(backupfile)
                else:
                    self.log.warning("Backup file '%s' does not exist - canceling backup", backupfile)
                    self.wrapper.events.callevent("wrapper.backupFailure", {"reasonCode": 3,
                                                                     "reasonText": "Backup file '%s' does not exist."
                                                                                   % backupfile})
                    return
            statuscode = os.system(" ".join(arguments))
            self.api.minecraft.console("save-on")
            if self.config["Backups"]["backup-notification"]:
                self.api.minecraft.broadcast("&aBackup complete!", irc=False)
            self.wrapper.events.callevent("wrapper.backupEnd", {"file": filename, "status": statuscode})
            self.backups.append((timestamp, filename))

            if len(self.backups) > self.config["Backups"]["backups-keep"]:
                self.log.info("Deleting old backups...")
                while len(self.backups) > self.config["Backups"]["backups-keep"]:
                    backup = self.backups[0]
                    if not self.wrapper.events.callevent("wrapper.backupDelete", {"file": filename}):
                        break
                    try:
                        os.remove('%s/%s' % (self.config["Backups"]["backup-location"], backup[1]))
                    except Exception as e:
                        print("Failed to delete backup (%s)" % e)
                    self.log.info("Deleting old backup: %s",
                                  datetime.datetime.fromtimestamp(int(backup[0])).strftime('%Y-%m-%d_%H:%M:%S'))
                    # hink = self.backups[0][1][:]  # not used...
                    del self.backups[0]
            with open(self.config["Backups"]["backup-location"] + "/backups.json", "w") as f:
                f.write(json.dumps(self.backups))

            if not os.path.exists(self.config["Backups"]["backup-location"] + "/" + filename):
                self.wrapper.events.callevent("wrapper.backupFailure", {"reasonCode": 2,
                                                                 "reasonText": "Backup file didn't exist after the tar "
                                                                               "command executed - assuming failure."})
