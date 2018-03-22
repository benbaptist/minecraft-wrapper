# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# This looks interesting, but not quite sure the intention

import os
import stat

from api.base import API
from api.helpers import mkdir_p

scripts = {
    "server-start.sh":  """ # This script is called just before the server starts. 
                            # It's safe to make changes to the world file, server.properties, etc. since the server
                            # has not started yet.
                            # Arguments passed to this script: None """,
    "server-stop.sh":   """ # This script is called right after the server has stopped. 
                            # It's safe to make changes to the world file, server.properties, etc. since the server
                            # is completely shutdown.
                            # Arguments passed to this script: None """,
    "backup-begin.sh":  """ # This script is called when a backup starts.
                            # Note that the backup hasn't started yet at the time of calling this script, and thus
                            # the file is non-existent.
                            # Arguments passed to this script: None """,
    "backup-finish.sh": """ # This script is called when a backup has finished.
                            # Arguments passed to this script: backup-filename """
}


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class Scripts(object):

    def __init__(self, wrapper):
        self.api = API(wrapper, "Scripts", internal=True)
        self.wrapper = wrapper
        self.config = wrapper.config

        # Register the events
        self.api.registerEvent("server.start", self._startserver)
        self.api.registerEvent("server.stopped", self._stopserver)
        self.api.registerEvent("wrapper.backupBegin", self._backupbegin)
        self.api.registerEvent("wrapper.backupEnd", self._backupend)

        self.createdefaultscripts()

    def createdefaultscripts(self):
        if not os.path.exists("wrapper-data"):
            mkdir_p("wrapper-data")
        if not os.path.exists("wrapper-data/scripts"):
            mkdir_p("wrapper-data/scripts")
        for script in scripts:
            path = "wrapper-data/scripts/%s" % script
            if not os.path.exists(path):
                with open(path, "w") as f:
                    f.write(scripts[script])
                os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    # Events

    def _startserver(self, payload):
        os.system("wrapper-data/scripts/server-start.sh")

    def _stopserver(self, payload):
        os.system("wrapper-data/scripts/server-stop.sh")

    def _backupbegin(self, payload):
        os.system("wrapper-data/scripts/backup-begin.sh %s" % payload["file"])

    def _backupend(self, payload):
        os.system("wrapper-data/scripts/backup-finish.sh %s" % payload["file"])
