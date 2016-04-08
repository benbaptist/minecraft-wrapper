# -*- coding: utf-8 -*-

import os
import traceback
import sys

from api.base import API

from importlib import import_module
from utils.log import Log

class Plugins:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.plugins = {}

    def __getitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        return self.plugins[index]

    def __setitem__(self, index, value):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        self.data[index] = value
        return self.plugins[index]

    def __delitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        del self.plugins[index]

    def __iter__(self):
        for i in self.plugins:
            yield i

    def loadPlugin(self, i):
        if "disabled_plugins" not in self.wrapper.storage:
            self.wrapper.storage["disabled_plugins"] = []
        self.log.info("Loading plugin %s...", i)
        if os.path.isdir("wrapper-plugins/%s" % i):
            plugin = import_module(i)
            name = i
        elif i[-3:] == ".py":
            plugin = import_module(i[:-3])
            name = i[:-3]
        else:
            return False

        # Leaving these for now due to EAFP
        try:
            disabled = plugin.DISABLED
        except AttributeError:
            disabled = False
        try:
            # if used, plugin.DEPENDENCIES must be a 'list' type (even if only
            # one item); e.g. = ["some.py", "another.py", etc]
            dependencies = plugin.DEPENDENCIES
        except AttributeError:
            dependencies = False
        try:
            name = plugin.NAME
        except AttributeError:
            pass
        try:
            pid = plugin.ID
        except AttributeError:
            pid = name
        try:
            version = plugin.VERSION
        except AttributeError:
            version = (0, 1)
        try:
            description = plugin.DESCRIPTION
        except AttributeError:
            description = None
        try:
            summary = plugin.SUMMARY
        except AttributeError:
            summary = None
        try:
            author = plugin.AUTHOR
        except AttributeError:
            author = None
        try:
            website = plugin.WEBSITE
        except AttributeError:
            website = None
        if pid in self.wrapper.storage["disabled_plugins"] or disabled:
            self.log.warn("Plugin '%s' disabled - not loading", name)
            return
        if pid in self.plugins:  # Once successfully loaded, further attempts to load the plugin are ignored
            self.log.debug("Plugin '%s' already loaded - not reloading", name)
            return
        if dependencies:  # load dependent plugins before continuing...
            # List data type must be used, even if only a single plugin (i.e. =
            # ["supportplugin.py"]
            for dependency in dependencies:
                self.loadPlugin(dependency)

        main = plugin.Main(API(self.wrapper, name, pid), Log(name))
        self.plugins[pid] = {"main": main, "good": True, "module": plugin}  # "events": {}, "commands": {},
        self.plugins[pid]["name"] = name
        self.plugins[pid]["version"] = version
        self.plugins[pid]["summary"] = summary
        self.plugins[pid]["description"] = description
        self.plugins[pid]["author"] = author
        self.plugins[pid]["website"] = website
        self.plugins[pid]["filename"] = i
        self.wrapper.commands[pid] = {}
        self.wrapper.events[pid] = {}
        self.wrapper.permission[pid] = {}
        self.wrapper.help[pid] = {}
        main.onEnable()

    def unloadPlugin(self, plugin):
        del self.wrapper.commands[plugin]
        del self.wrapper.events[plugin]
        del self.wrapper.help[plugin]
        try:
            self.plugins[plugin]["main"].onDisable()
        except Exception as  e:
            self.log.exception("Error while disabling plugin '%s'", plugin)
        try:
            reload(self.plugins[plugin]["module"])
        except Exception as  e:
            self.log.exception("Error while reloading plugin '%s' -- it was probably deleted or is a bugged version", plugin)

    def loadPlugins(self):
        self.log.info("Loading plugins...")
        if not os.path.exists("wrapper-plugins"):
            os.mkdir("wrapper-plugins")
        sys.path.append("wrapper-plugins")
        for i in os.listdir("wrapper-plugins"):
            try:
                if i[0] == ".":
                    continue
                if os.path.isdir("wrapper-plugins/%s" % i):
                    self.loadPlugin(i)
                elif i[-3:] == ".py":
                    self.loadPlugin(i)
            except Exception as  e:
                self.log.exception("Failed to import plugin '%s' (%s)", (i, e))
                self.plugins[i] = {"name": i, "good": False}
        self.wrapper.events.callEvent("helloworld.event", {"testValue": True})

    def disablePlugins(self):
        self.log.info("Disabling plugins...")
        for i in self.plugins:
            self.unloadPlugin(i)
        self.log.info("Disabling plugins...Done!")

    def reloadPlugins(self):
        for i in self.plugins:
            try:
                self.unloadPlugin(i)
            except Exception as  e:
                self.log.exception("Failed to unload plugin '%s' (%s)", (i, e))
                try:
                    reload(self.plugins[plugin]["module"])
                except Exception as  ex:
                    pass
        self.plugins = {}
        self.loadPlugins()
        self.log.info("Plugins reloaded")
