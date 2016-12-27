# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

# noinspection PyPep8Naming

"""
* just an odd note in an odd place *

 backups is one of the newer api modules and some thought was given to making these methods snake_case when it
 was first being written.

Wrapper's orginal convention throughtout the codebase was mixed camelCase.  The internal code is being
converted (going forward) to snake_case per PEP-8.
However, PEP-8 acknowledges that:

'mixedCase [... is allowed ...] in contexts where that's already the prevailing style (e.g. threading.py), to retain
backwards compatibility.'

This is certainly the case with the wrapper plugin API.  Converting the entire plugin API to snake_case will
break all existing plugins.  Implementing this API with snake_case will create an inconsitent `look 'n feel` within
wrapper's plugin API.  The only other alternative would be to clutter the code with wrappers between oldFunctions and
new_functions.

"""


# noinspection PyPep8Naming
class Backups:
    """
    These methods are accessed using 'self.api.backups'

     This class wraps the wrapper.backups functions.  Wrapper starts starts core.backups.py
     class Backups (as .backups).  This API class manipulates the backups instance within
     core.wrapper
    """

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log

    def verifyTarInstalled(self):
        """
        checks for tar on users system.
        :return: True if installed, False if not (along with error logs and console messages).
        """
        return self.wrapper.backups.dotarchecks()

    def performBackup(self):
        """
        Perform an immediate backup
        :return: check console for messages (or wrapper backup Events)
        """
        self.wrapper.backups.dobackup()

    def pruneBackups(self):
        """
        prune backups according to wrapper properties settings.
        :return: Output to console and logs
        """
        self.wrapper.backups.pruneoldbackups()

    def disableBackups(self):
        """
        Allow plugin to temporarily shut off backups (only during this wrapper session).
        :return: None
        """
        self.wrapper.backups.enabled = False

    def enableBackups(self):
        """
        Allow plugin to re-enable disabled backups or enable backups during this wrapper session.
        :return: True.  returns False if tar is not installed
        """
        self.wrapper.backups.enabled = True
        if not self.wrapper.backups.timerstarted:
            if not self.wrapper.backups.dotarchecks():
                return False
            self.wrapper.backups.timerstarted = True
            self.wrapper.backups.api.registerEvent("timer.second", self.wrapper.backups.eachsecond)

    def adjustBackupInterval(self, desired_interval):
        """
        Adjust the backup interval for automatic backups.
        :param desired_interval: interval in seconds for regular backups
        :return:
        """
        interval = int(desired_interval)
        self.wrapper.backups.config["Backups"]["backup-interval"] = interval
        self.wrapper.configManager.save()
        self.wrapper.backups.backup_interval = interval

    def adjustBackupsKept(self, desired_number):
        """
        Adjust the number of backups kept.
        :param desired_number: number of desired backups
        :return:
        """
        num_kept = int(desired_number)
        self.wrapper.backups.config["Backups"]["backups-keep"] = num_kept
        self.wrapper.configManager.save()
