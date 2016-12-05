# -*- coding: utf-8 -*-


# noinspection PyPep8Naming

"""
Wrapper's orginal convention throughtout the codebase has been camelCase from the begining.  The internal code
should be converted (going forward) to snake_case per PEP-8.
However, PEP-8 also acknowledges that:

'mixedCase is allowed only in contexts where that's already the prevailing style (e.g. threading.py), to retain
backwards compatibility.'

This is certainly the case with the wrapper plugin API.  Converting the entire plugin API to snake_case will
break all existing plugins.  Creating this API with snake_case will create an inconsitent `look 'n feel` within
the API.  The only other alternative would be to create excessive wrappers between oldFunctions and new_functions
(and does not serve to remove the oldFunctions anyway!)
"""


# noinspection PyPep8Naming
class Backups:
    """ This class wraps the wrapper.javaserver backups functions.  Wrapper starts javaserver(McServer class)
     and javaserver starts core.backups.py class Backups (as .backups).  This API class manipulates backups within
     wrapper.javaserver"""

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log

    def verifyTarInstalled(self):
        """
        checks for tar on users system.
        :return: True if installed, False if not (along with error logs and console messages).
        """
        return self.wrapper.javaserver.backups.dotarchecks()

    def performBackup(self):
        """
        Perform an immediate backup
        :return: check console for messages (or wrapper backup Events)
        """
        self.wrapper.javaserver.backups.dobackup()

    def pruneBackups(self):
        """
        prune backups according to wrapper properties settings.
        :return: Output to console and logs
        """
        self.wrapper.javaserver.backups.pruneoldbackups()

    def disableBackups(self):
        """
        Allow plugin to temporarily shut off backups (only during this wrapper session).
        :return: None
        """
        self.wrapper.javaserver.backups.enabled = False

    def enableBackups(self):
        """
        Allow plugin to re-enable disabled backups or enable backups during this wrapper session.
        :return: True.  returns False if tar is not installed
        """
        self.wrapper.javaserver.backups.enabled = True
        if not self.wrapper.javaserver.backups.timerstarted:
            if not self.wrapper.javaserver.backups.dotarchecks():
                return False
            self.wrapper.javaserver.backups.timerstarted = True
            self.wrapper.javaserver.backups.api.registerEvent("timer.second", self.wrapper.javaserver.backups.eachsecond)

    def adjustBackupInterval(self, desired_interval):
        """
        Adjust the backup interval for automatic backups.
        :param desired_interval: interval in seconds for regular backups
        :return:
        """
        interval = int(desired_interval)
        self.wrapper.javaserver.backups.config["Backups"]["backup-interval"] = interval
        self.wrapper.configManager.save()

    def adjustBackupsKept(self, desired_number):
        """
        Adjust the number of backups kept.
        :param desired_number: number of desired backups
        :return:
        """
        num_kept = int(desired_number)
        self.wrapper.javaserver.backups.config["Backups"]["backups-keep"] = num_kept
        self.wrapper.configManager.save()
