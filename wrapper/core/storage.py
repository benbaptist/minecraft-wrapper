# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

# from __future__ import unicode_literals

import os
import time
import logging
from api.helpers import mkdir_p, putjsonfile, getjsonfile
from core.config import Config
import threading

try:
    # noinspection PyUnresolvedReferences
    str2 = unicode
except NameError:
    str2 = str


class Storage:

    def __init__(self, name, root="wrapper-data/json", encoding="default"):
        self.name = name
        self.root = root
        self.configManager = Config()
        self.configManager.loadconfig()

        if encoding == "default":
            self.encoding = self.configManager.config["General"]["encoding"]
        else:
            self.encoding = encoding

        self.log = logging.getLogger('Wrapper.py')

        self.data = {}
        self.load()
        self.time = time.time()
        self.abort = False

        t = threading.Thread(target=self.periodicsave, args=())
        t.daemon = True
        t.start()

    def __getitem__(self, index):
        if not type(index) in (str, str2):
            raise Exception("A string must be passed - got %s" % type(index))
        try:
            return self.data[index]
        except KeyError:
            self.log.debug("failed to get key: <%s> out of data:\n%s", index, self.data)

    def __setitem__(self, index, value):
        if not type(index) in (str, str2):
            raise Exception("A string must be passed - got %s" % type(index))
        self.data[index] = value
        return self.data[index]

    def __delattr__(self, index):
        if not type(index) in (str, str2):
            raise Exception("A string must be passed - got %s" % type(index))
        del self.data[index]

    def __delitem__(self, index):
        if not type(index) in (str, str2):
            raise Exception("A string must be passed - got %s" % type(index))
        del self.data[index]

    def __iter__(self):
        if self.data is None:
            self.data = {}
        # noinspection PyTypeChecker
        for i in self.data:
            yield i

    def periodicsave(self):  # EAFTP
        while not self.abort:
            if time.time() - self.time > 60:
                self.save()
                self.time = time.time()
            time.sleep(1)

    def load(self):
        mkdir_p(self.root)
        if not os.path.exists("%s/%s.json" % (self.root, self.name)):
            self.save()
        self.data = getjsonfile(self.name, self.root, encodedas=self.encoding)
        if self.data is False:
            self.log.exception("bad directory or filename '%s/%s.json'", self.root, self.name,)

    def save(self):
        if not os.path.exists(self.root):
            mkdir_p(self.root)
        putcode = putjsonfile(self.data, self.name, self.root)
        if not putcode:
            self.log.exception("TypeError or non-existent path: '%s/%s.json'\nData Dump:\n%s",
                               self.root, self.name, self.data)

    def close(self):
        self.save()
        self.abort = True

    def key(self, key, value=None):
        if value is None:
            return self.getkey(key)
        else:
            self.setkey(key, value)

    def getkey(self, key):
        if key in self.data:
            return self.data[key]
        else:
            return None

    def setkey(self, key, value=None):
        if value is None:
            if key in self.data:
                del self.data[key]
        else:
            self.data[key] = value
