# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# from __future__ import unicode_literals

import os
import time
import logging
from api.helpers import mkdir_p, putjsonfile, getjsonfile
from api.helpers import pickle_save, pickle_load
from core.config import Config
import threading


class Storage(object):
    """
    The Storage class underpins the API.base.getStorage().  The
    object is available once you call storage = api.getStorage().

    :init() arguments:
        :name: Storage name on disk.
        :root="wrapper-data/json": File path of the storage.
        :pickle=True: True to use Binary storage, False to use json.

    :Methods:
        :load():
        :save():
        :close():

    :Properties/variables:
        :periodic_save_timer:  Default is 60 seconds
        :paused_saving:  Set to True to pause the periodic save.

    """

    def __init__(self, name, root="wrapper-data/json", pickle=True):
        # type: (str, str, bool) -> None
        """
        :param name: Name of Storage
        :param root: Path on disk to storage data
        :param pickle: Boolean; Pickle (True) or not (False, use Json)

        """
        self.Data = {}
        self.name = name
        self.root = root
        self.pickle = pickle
        self.configManager = Config()
        self.configManager.loadconfig()
        self.log = logging.getLogger('Storage.py')
        self.encoding = self.configManager.config["General"]["encoding"]
        self.paused_saving = False
        self.periodic_save_timer = 60

        if self.pickle:
            self.file_ext = "pkl"
        else:
            self.file_ext = "json"

        self.load()
        self.timer = time.time()
        self.abort = False

        t = threading.Thread(target=self._periodicsave, args=())
        t.daemon = True
        t.start()

    def _periodicsave(self):
        # doing it this way (versus just sleep() for certain number of seconds),
        # allows faster shutdown response
        while not self.abort:
            if self.paused_saving:
                time.sleep(1)
                continue
            if time.time() - self.timer > self.periodic_save_timer:
                self.save()
                self.timer = time.time()
            time.sleep(1)

    def load(self):
        """
        Loads the Storage data from disk.

        In conjunction with setting the storages paused_saving to true,
         this allows you to make changes to a wrapper storage on disk
         while wrapper is running.

        :return: Nothing

        """

        mkdir_p(self.root)
        if not os.path.exists(
                        "%s/%s.%s" % (self.root, self.name, self.file_ext)):
            # load old json storages if there is no pickled
            # file (and if storage is using pickle)
            if self.pickle:
                self.Data = self._json_load()
            # save to the selected file mode (json or pkl)
            self.save()
        if self.pickle:
            filenameis = "%s.pkl" % self.name
            self.Data = pickle_load(self.root, filenameis)
        else:
            self.Data = self._json_load()

    def save(self):
        """
        Force a save of the Storage to disk.  Saves are also done
         periodically and when the storage is closed.

        :return: Nothing
        """
        if not os.path.exists(self.root):
            mkdir_p(self.root)
        if self.pickle:
            filenameis = "%s.pkl" % self.name
            pickle_save(self.root, filenameis, self.Data, self.encoding)
        else:
            self._json_save()

    def _json_save(self):
        putcode = putjsonfile(self.Data, self.name, self.root)
        if not putcode:
            self.log.exception(
                "Error encoutered while saving json data:\n'%s/%s.%s'"
                "\nData Dump:\n%s" % (
                    self.root, self.name, self.file_ext, self.Data))

    def _json_load(self):
        try_load = getjsonfile(self.name, self.root, encodedas=self.encoding)
        if try_load is None:
            self.log.exception("bad file or data '%s/%s.json'" %
                               (self.root, self.name))
            return {}
        if try_load is False:
            # file just does not exist (yet); return without comments/errors.
            return {}
        else:
            return try_load

    def close(self):
        """
        Close the Storage and save it's Data to disk.

        :return: Nothing
        """
        self.abort = True
        self.save()
