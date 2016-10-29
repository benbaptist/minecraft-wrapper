# -*- coding: utf-8 -*-


class Backups:
    """ This class wraps the wrapper.javaserver backups functions.  Wrapper starts javaserver(McServer class)
     and javaserver starts core.backups.py class Backups (as .backups).  This API class manipulates backups within
     wrapper.javaserver"""

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log

    def verify_tar_installed(self):
        """
        checks for tar on users system.
        :return: True if installed, False if not (along with error logs and console messages).
        """
        return self.wrapper.javaserver.backups.dotarchecks()

    def perform_backup(self):
        """
        Perform an immediate backup
        :return: check console for messages (or wrapper backup Events)
        """
        self.wrapper.javaserver.backups.dobackup()

    def prune_backups(self):
        """
        prune backups according to wrapper properties settings.
        :return: Output to console and logs
        """
        self.wrapper.javaserver.backups.pruneoldbackups()

    def disable_backups(self):
        """
        Allow plugin to temporarily shut off backups (only during this wrapper session).
        :return: None
        """
        self.wrapper.javaserver.backups.enabled = False

    def enable_backups(self):
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

    def adjust_backup_interval(self, desired_interval):
        """
        Adjust the backup interval for automatic backups.
        :param desired_interval: interval in seconds for regular backups
        :return:
        """
        interval = int(desired_interval)
        self.wrapper.javaserver.backups.config["Backups"]["backup-interval"] = interval
        self.wrapper.configManager.save()

    def adjust_backups_kept(self, desired_number):
        """
        Adjust the number of backups kept.
        :param desired_number: number of desired backups
        :return:
        """
        num_kept = int(desired_number)
        self.wrapper.javaserver.backups.config["Backups"]["backups-keep"] = num_kept
        self.wrapper.configManager.save()
