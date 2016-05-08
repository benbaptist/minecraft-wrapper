# -*- coding: utf-8 -*-

import os
import sys
import logging

from api.base import API

try:
    from importlib import reload
except ImportError:
    from importlib import import_module as reload  # name shadows in 2.x (un avoidable)


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
        self.plugins[index] = value
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
        self.log.debug("Parsing plugin %s...", i)
        if i[-3:] == ".py":
            plugin = reload(i[:-3])
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
                self.loadPlugin(dependency)

        main = plugin.Main(API(self.wrapper, name, pid), logging.getLogger(name))
        self.plugins[pid] = {"main": main, "good": True, "module": plugin}  # "events": {}, "commands": {},
        self.plugins[pid]["name"] = name
        self.plugins[pid]["version"] = getattr(plugin, 'VERSION', (0,1))
        self.plugins[pid]["summary"] = getattr(plugin, 'SUMMARY', None)
        self.plugins[pid]["description"] = getattr(plugin, 'DESCRIPTION', None)
        self.plugins[pid]["author"] = getattr(plugin, 'AUTHOR', None)
        self.plugins[pid]["website"] = getattr(plugin, 'WEBSITE', None)
        self.plugins[pid]["filename"] = i
        self.wrapper.commands[pid] = {}
        self.wrapper.events[pid] = {}
        self.wrapper.permission[pid] = {}
        self.wrapper.help[pid] = {}
        main.onEnable()
        self.log.info("Plugin %s loaded...", i)

    def unloadPlugin(self, plugin):
        del self.wrapper.commands[plugin]
        del self.wrapper.events[plugin]
        del self.wrapper.help[plugin]
        try:
            self.plugins[plugin]["main"].onDisable()
            self.log.debug("Plugin %s disabled with no errors." % plugin)
        except AttributeError:
            self.log.debug("Plugin %s disabled (has no onDisable() event)." % plugin)
        except Exception as  e:
            self.log.exception("Error while disabling plugin '%s': \n%s", (plugin, e))
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
                if i[-3:] == ".py":
                    self.loadPlugin(i)
                else:
                    continue  # don't attempt to load non-py files
            except Exception as  e:
                self.log.exception("Failed to import plugin '%s' (%s)", i, e)
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
                self.log.exception("Failed to unload plugin '%s' (%s)", i, e)
                try:
                    reload(self.plugins[i]["module"])
                except Exception as  ex:
                    pass
        self.plugins = {}
        self.loadPlugins()
        self.log.info("Plugins reloaded")
