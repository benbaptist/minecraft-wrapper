# -*- coding: utf-8 -*-

import os
import logging
import importlib

from api.base import API


# Py3-2
import sys
PY3 = sys.version_info > (3,)


class Plugins:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.config = wrapper.config
        self.plugins = {}

    def __getitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        return self.plugins[index]

    def __setitem__(self, index, value):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        self.plugins[index] = value
        return self.plugins[index]

    def __delitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        del self.plugins[index]

    def __iter__(self):
        for i in self.plugins:
            yield i

    def loadplugin(self, i):
        if "disabled_plugins" not in self.wrapper.storage:
            self.wrapper.storage["disabled_plugins"] = []
        self.log.debug("Parsing plugin %s...", i)
        if i[-3:] == ".py":
            plugin = importlib.import_module(i[:-3])
        else:
            return False

        name = getattr(plugin, 'NAME', i[:-3])
        pid = getattr(plugin, 'ID', name)
        if pid in self.plugins:  # Once successfully loaded, further attempts to load the plugin are ignored
            self.log.debug("Plugin '%s' already loaded - not reloading", name)
            return
        disabled = getattr(plugin, 'DISABLED', False)
        if pid in self.wrapper.storage["disabled_plugins"] or disabled:
            self.log.debug("Plugin '%s' disabled - not loading", name)
            return

        dependencies = getattr(plugin, 'DEPENDENCIES', [])

        self.log.debug("Loading plugin %s...", i)
        if dependencies:  # load dependent plugins before continuing...
            # List data type must be used, even if only a single plugin (i.e. =
            # ["supportplugin.py"]
            for dependency in dependencies:
                self.loadplugin(dependency)

        main = plugin.Main(API(self.wrapper, name, pid), logging.getLogger(name))
        self.plugins[pid] = {"main": main, "good": True, "module": plugin}  # "events": {}, "commands": {},
        self.plugins[pid]["name"] = name
        self.plugins[pid]["version"] = getattr(plugin, 'VERSION', (0, 1))
        self.plugins[pid]["summary"] = getattr(plugin, 'SUMMARY', None)
        self.plugins[pid]["description"] = getattr(plugin, 'DESCRIPTION', None)
        self.plugins[pid]["author"] = getattr(plugin, 'AUTHOR', None)
        self.plugins[pid]["website"] = getattr(plugin, 'WEBSITE', None)
        self.plugins[pid]["filename"] = i
        self.wrapper.commands[pid] = {}
        self.wrapper.events[pid] = {}
        self.wrapper.registered_permissions[pid] = {}
        self.wrapper.help[pid] = {}
        main.onEnable()
        self.log.info("Plugin %s loaded...", i)

    def unloadplugin(self, plugin):
        del self.wrapper.commands[plugin]
        del self.wrapper.events[plugin]
        del self.wrapper.help[plugin]
        try:
            self.plugins[plugin]["main"].onDisable()
            self.log.debug("Plugin %s disabled with no errors." % plugin)
        except AttributeError:
            self.log.debug("Plugin %s disabled (has no onDisable() event)." % plugin)
        except Exception as e:
            self.log.exception("Error while disabling plugin '%s': \n%s", (plugin, e))

    def loadplugins(self):
        self.log.info("Loading plugins...")
        if not os.path.exists("wrapper-plugins"):
            os.mkdir("wrapper-plugins")
        sys.path.append("wrapper-plugins")
        for i in os.listdir("wrapper-plugins"):
            try:
                if i[-3:] == ".py":
                    self.loadplugin(i)
                else:
                    continue  # don't attempt to load non-py files
            except Exception as e:
                self.log.exception("Failed to import plugin '%s' (%s)", i, e)
                self.plugins[i] = {"name": i, "good": False}
        self.wrapper.events.callevent("helloworld.event", {"testValue": True})

    def disableplugins(self):
        self.log.info("Disabling plugins...")
        for i in self.plugins:
            self.unloadplugin(i)
        self.log.info("Disabling plugins...Done!")

    def reloadplugins(self):
        for i in self.plugins:
            try:
                self.unloadplugin(i)
            except Exception as e:
                self.log.exception("Failed to unload plugin '%s' (%s)", i, e)
        self.plugins = {}
        self.loadplugins()
        self.log.info("Plugins reloaded")
