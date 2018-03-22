# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.


# noinspection PyPep8Naming
class Backups(object):
    """
    .. code:: python

        def __init__(self, wrapper)

    ..

    These methods are accessed using 'self.api.backups'

    .. code:: python

        <yourobject> = self.api.backups
        <yourobject>.<backups_method>

    ..

    This class wraps the wrapper.backups functions.  Wrapper starts
    core.backups.py class Backups (as .backups).  This API
    class manipulates the backups instance within core.wrapper

    """

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log

    def verifyTarInstalled(self):
        """
        checks for tar on users system.

        :returns: True if installed, False if not (along with error logs
         and console messages).

        """
        return self.wrapper.backups.dotarchecks()

    def performBackup(self):
        """
        Perform an immediate backup

        :returns: check console for messages (or wrapper backup Events)

        """
        self.wrapper.backups.dobackup()

    def pruneBackups(self):
        """
        prune backups according to wrapper properties settings.

        :returns: Output to console and logs

        """
        self.wrapper.backups.pruneoldbackups()

    def disableBackups(self):
        """
        Allow plugin to temporarily shut off backups (only during
        this wrapper session).

        :returns: None

        """
        self.wrapper.backups.enabled = False

    def enableBackups(self):
        """
        Allow plugin to re-enable disabled backups or enable backups
        during this wrapper session.

        :returns:
            :True: tar is installed
            :False: tar is not installed

        """
        self.wrapper.backups.enabled = True
        if not self.wrapper.backups.timerstarted:
            if not self.wrapper.backups.dotarchecks():
                return False
            self.wrapper.backups.timerstarted = True
            self.wrapper.backups.api.registerEvent(
                "timer.second", self.wrapper.backups.eachsecond)

    def adjustBackupInterval(self, desired_interval):
        """
        Adjust the backup interval for automatic backups.

        :arg desired_interval: interval in seconds for regular backups

        :returns:

        """
        interval = int(desired_interval)
        self.wrapper.backups.config["Backups"]["backup-interval"] = interval
        self.wrapper.configManager.save()
        self.wrapper.backups.backup_interval = interval

    def adjustBackupsKept(self, desired_number):
        """
        Adjust the number of backups kept.

        :arg desired_number: number of desired backups

        :returns:

        """
        num_kept = int(desired_number)
        self.wrapper.backups.config["Backups"]["backups-keep"] = num_kept
        self.wrapper.configManager.save()
