
**< class Backups >**

    These methods are accessed using 'self.api.backups'

     This class wraps the wrapper.backups functions.  Wrapper starts
     starts core.backups.py class Backups (as .backups).  This API
     class manipulates the backups instance within core.wrapper

    

** verifyTarInstalled(self)**

        checks for tar on users system.

        :returns: True if installed, False if not (along with error logs
         and console messages).

        

** performBackup(self)**

        Perform an immediate backup

        :returns: check console for messages (or wrapper backup Events)

        

** pruneBackups(self)**

        prune backups according to wrapper properties settings.

        :returns: Output to console and logs

        

** disableBackups(self)**

        Allow plugin to temporarily shut off backups (only during
        this wrapper session).

        :returns: None

        

** enableBackups(self)**

        Allow plugin to re-enable disabled backups or enable backups
        during this wrapper session.

        :returns:
            :True: tar is installed
            :False: tar is not installed

        

** adjustBackupInterval(self, desired_interval)**

        Adjust the backup interval for automatic backups.

        :arg desired_interval: interval in seconds for regular backups

        :returns:

        

** adjustBackupsKept(self, desired_number)**

        Adjust the number of backups kept.

        :arg desired_number: number of desired backups

        :returns:

        
