# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# from __future__ import unicode_literals

import os
import time
import logging
from api.helpers import mkdir_p, putjsonfile, getjsonfile, pickle_save, pickle_load
from core.config import Config
import threading


class Storage(object):

    def __init__(self, name, root="wrapper-data/json", pickle=True):
        self.Data = {}
        self.name = name
        self.root = root
        self.pickle = pickle
        self.configManager = Config()
        self.configManager.loadconfig()
        self.log = logging.getLogger('Storage.py')
        self.encoding = self.configManager.config["General"]["encoding"]

        if self.pickle:
            self.file_ext = "pkl"
        else:
            self.file_ext = "json"

        self.load()
        self.timer = time.time()
        self.abort = False

        t = threading.Thread(target=self.periodicsave, args=())
        t.daemon = True
        t.start()

    def periodicsave(self):
        # doing it this way (versus just sleeping for 60 seconds),
        # allows faster shutdown response
        while not self.abort:
            if time.time() - self.timer > 60:
                self.save()
                self.timer = time.time()
            time.sleep(1)

    def load(self):
        mkdir_p(self.root)
        if not os.path.exists(
                        "%s/%s.%s" % (self.root, self.name, self.file_ext)):
            # load old json storages if there is no pickled
            # file (and if storage is using pickle)
            if self.pickle:
                self.Data = self.json_load()
            # save to the selected file mode (json or pkl)
            self.save()
        if self.pickle:
            filenameis = "%s.pkl" % self.name
            self.Data = pickle_load(self.root, filenameis)
        else:
            self.Data = self.json_load()

    def save(self):
        if not os.path.exists(self.root):
            mkdir_p(self.root)
        if self.pickle:
            filenameis = "%s.pkl" % self.name
            pickle_save(self.root, filenameis, self.Data, self.encoding)
        else:
            self.json_save()

    def json_save(self):
        putcode = putjsonfile(self.Data, self.name, self.root)
        if not putcode:
            self.log.exception(
                "Error encoutered while saving json data:\n'%s/%s.%s'"
                "\nData Dump:\n%s" % (
                    self.root, self.name, self.file_ext, self.Data))

    def json_load(self):
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
        self.abort = True
        self.save()
