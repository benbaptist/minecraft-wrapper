# -*- coding: utf-8 -*-

# from __future__ import unicode_literals

import json
import os
import time
import logging
# import threading
# import copy

try:
    # noinspection PyUnresolvedReferences
    str2 = unicode
except NameError:
    str2 = str


class Storage:

    def __init__(self, name, root="wrapper-data/json", encoding="UTF-8"):
        self.name = name
        self.root = root
        self.encoding = encoding
        self.log = logging.getLogger('Wrapper.py')

        self.data = {}
        self.load()
        self.time = time.time()
        # self.dataOld = {}
        # self.abort = False

        # t = threading.Thread(target=self.periodicsave, args=())
        # t.daemon = True
        # t.start()

    # def __del__(self):
        # self.abort = True
        # self.save()
        # pass

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

    def __iter__(self):
        for i in self.data:
            yield i

    # def periodicsave(self):
    #     while not self.abort:
    #         if time.time() - self.time > 60:
    #             if not self.data == self.dataOld:
    #                 try:
    #                     self.save()
    #                 except Exception as e:
    #                     self.log.warning("Could not periodicsave data \n(%s)", e)
    #                 self.time = time.time()
    #         time.sleep(1)

    def mkdir(self, dirpath):
        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath, exist_ok=True)
            except Exception as e:
                self.log.warning("Could not create directory '%s' \n(%s)", dirpath, e)

    def load(self):
        self.mkdir(self.root)
        if not os.path.exists("%s/%s.json" % (self.root, self.name)):
            self.save()
        with open("%s/%s.json" % (self.root, self.name), "r") as f:
            try:
                self.data = json.loads(f.read(), encoding=self.encoding)
            except Exception as e:
                self.log.exception("Failed to load '%s/%s.json' (%s)", self.root, self.name, e)
                return
        # self.dataOld = copy.deepcopy(self.data)

    def save(self):
        if not os.path.exists(self.root):
            self.mkdir(self.root)
        try:
            with open("%s/%s.json" % (self.root, self.name), "w") as f:
                f.write(json.dumps(self.data, ensure_ascii=False, encoding=self.encoding, indent=2))
                # self.flush = False  # where is this self variable used?  Why is it not defined in __init__?
        except Exception as e:
            self.log.exception(e)

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
        # self.flush = True