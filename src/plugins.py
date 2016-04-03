# -*- coding: utf-8 -*-

import os
import traceback
import sys

from importlib import import_module
from api import API
from log import Log, PluginLog

class Plugins:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.plugins = {}

    def __getitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed to the stuff")
        return self.plugins[index]

    def __setitem__(self, index, value):
        if not type(index) == str:
            raise Exception("A string must be passed to the stuff")
        self.data[index] = value
        return self.plugins[index]

    def __delitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed to the stuff")
        del self.plugins[index]

    def __iter__(self):
        for i in self.plugins:
            yield i

    def loadPlugin(self, i):
        if "disabled_plugins" not in self.wrapper.storage:
            self.wrapper.storage["disabled_plugins"] = []
        self.log.info("Loading plugin %s..." % i)
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
            id = plugin.ID
        except AttributeError:
            id = name
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
        if id in self.wrapper.storage["disabled_plugins"] or disabled:
            self.log.warn("Plugin '%s' disabled - not loading" % name)
            return
        if id in self.plugins:  # Once successfully loaded, further attempts to load the plugin are ignored
            self.log.debug("Plugin '%s' already loaded - not reloading" % name)
            return
        if dependencies:  # load dependent plugins before continuing...
            # List data type must be used, even if only a single plugin (i.e. =
            # ["supportplugin.py"]
            for dependency in dependencies:
                self.loadPlugin(dependency)
        main = plugin.Main(API(self.wrapper, name, id), PluginLog(self.log, name))
        self.plugins[id] = {"main": main, "good": True, "module": plugin}  # "events": {}, "commands": {},
        self.plugins[id]["name"] = name
        self.plugins[id]["version"] = version
        self.plugins[id]["summary"] = summary
        self.plugins[id]["description"] = description
        self.plugins[id]["author"] = author
        self.plugins[id]["website"] = website
        self.plugins[id]["filename"] = i
        self.wrapper.commands[id] = {}
        self.wrapper.events[id] = {}
        self.wrapper.permission[id] = {}
        self.wrapper.help[id] = {}
        main.onEnable()

    def unloadPlugin(self, plugin):
        del self.wrapper.commands[plugin]
        del self.wrapper.events[plugin]
        del self.wrapper.help[plugin]
        try:
            self.plugins[plugin]["main"].onDisable()
        except Exception, e:
            self.log.error("Error while disabling plugin '%s'" % plugin)
            self.log.getTraceback()
        try:
            reload(self.plugins[plugin]["module"])
        except Exception, e:
            self.log.error(
                "Error while reloading plugin '%s' -- it was probably deleted or is a bugged version" % plugin)
            self.log.getTraceback()

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
            except Exception, e:
                for line in traceback.format_exc().split("\n"):
                    self.log.debug(line)
                self.log.error("Failed to import plugin '%s' (%s)" % (i, e))
                self.plugins[i] = {"name": i, "good": False}
        self.wrapper.events.callEvent("helloworld.event", {"testValue": True})

    def disablePlugins(self):
        self.log.info("Disabling plugins...")
        for i in self.plugins:
            self.unloadPlugin(i)
        self.log.info("Plugins disabled")

    def reloadPlugins(self):
        for i in self.plugins:
            try:
                self.unloadPlugin(i)
            except Exception, e:
                for line in traceback.format_exc().split("\n"):
                    self.log.debug(line)
                self.log.error("Failed to unload plugin '%s' (%s)" % (i, e))
                try:
                    reload(self.plugins[plugin]["module"])
                except Exception, ex:
                    pass
        self.plugins = {}
        self.loadPlugins()
        self.log.info("Plugins reloaded")
