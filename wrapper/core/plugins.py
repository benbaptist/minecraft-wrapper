# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import os
import logging
import importlib
import sys

from api.base import API
from api.helpers import mkdir_p


class Plugins(object):

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.config = wrapper.config
        self.plugins = {}
        self.plugins_loaded = []
        if "disabled_plugins" not in self.wrapper.storage:
            self.wrapper.storage["disabled_plugins"] = []
        if not os.path.exists("wrapper-plugins"):
            mkdir_p("wrapper-plugins")
        sys.path.append("wrapper-plugins")

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

    def loadplugin(self, name, available_files):
        if name in self.plugins_loaded:
            # Don't try to load a previously errored ( attempted to load..) plugin
            return False
        self.log.debug("Reading plugin file %s.py ...", name)
        # hack to remove previously loaded modules during reloads
        if name in sys.modules:
            del sys.modules[name]

        plugin = importlib.import_module(name)
        pid = getattr(plugin, 'ID', name)  # from the plugin head.. e.g., 'ID = "com.benbaptist.plugins.essentials"'
        disabled = getattr(plugin, 'DISABLED', False)
        dependencies = getattr(plugin, 'DEPENDENCIES', [])

        if pid in self.wrapper.storage["disabled_plugins"] or disabled:
            self.log.debug("Plugin '%s' disabled - not loading", name)
            return True

        if pid in self.plugins:  # Once successfully loaded, further attempts to load the plugin are ignored
            self.log.debug("Plugin '%s' is already loaded (probably as a dependency) - not reloading", name)
            return True

        # check for unloaded dependencies and develop a list of required dependencies.
        good_deps = True
        dep_loads = []
        if dependencies:
            for dep in dependencies:
                # allow a user to specify name or full filename for dependencies
                dep_name = dep
                if dep[-3:] == '.py':
                    dep_name = dep[:-3]
                if dep_name in available_files:
                    # if the plugin was already loaded, the dependency is satisfied...
                    if dep_name not in self.plugins_loaded:
                        dep_loads.append(dep_name)
                else:
                    good_deps = False
                    self.log.warn("Plugin '%s'.py is missing a dependency: '%s.py'", name, dep_name)
        if not good_deps:
            self.log.warn("Plugin '%s'.py failed to load because of missing dependencies.", name)
            return False

        # load the required dependencies first.
        for dependency in dep_loads:
            if self.loadplugin(dependency, available_files):
                self.log.debug("Dependency '%s' loaded.", dependency)
                self.plugins_loaded.append(name)
            else:
                self.log.warn("Dependency '%s' could not be loaded.", dependency)
                self.log.warn("Plugin '%s'.py failed to load because of missing dependency '%s'.", name, dependency)
                self.plugins_loaded.append(name)
                return False

        # Finally, initialize this plugin
        self.log.debug("Loading plugin %s...", name)
        if not getattr(plugin, 'Main', False):
            self.log.warn("Plugin '%s' is malformed and missing a class 'Main'", name)
            self.plugins_loaded.append(name)
            return False
        has_onenable = getattr(getattr(plugin, 'Main', False), 'onEnable', False)
        if not has_onenable:
            self.log.warn("Plugin '%s' is missing an 'onEnable' method.", name)
            self.plugins_loaded.append(name)
            return False

        main = plugin.Main(API(self.wrapper, name, pid), logging.getLogger(name))
        self.plugins[pid] = {"main": main, "good": True, "module": plugin}  # "events": {}, "commands": {}}
        self.plugins[pid]["name"] = getattr(plugin, "NAME", name)
        self.plugins[pid]["version"] = getattr(plugin, 'VERSION', (0, 1))
        self.plugins[pid]["summary"] = getattr(plugin, 'SUMMARY', None)
        self.plugins[pid]["description"] = getattr(plugin, 'DESCRIPTION', None)
        self.plugins[pid]["author"] = getattr(plugin, 'AUTHOR', None)
        self.plugins[pid]["website"] = getattr(plugin, 'WEBSITE', None)
        self.plugins[pid]["filename"] = "%s.py" % name
        self.wrapper.commands[pid] = {}
        self.wrapper.events[pid] = {}
        self.wrapper.registered_permissions[pid] = {}
        self.wrapper.help[pid] = {}
        main.onEnable()
        self.log.info("Plugin %s loaded...", name)
        self.plugins_loaded.append(name)
        return True

    def unloadplugin(self, plugin):
        try:
            self.plugins[plugin]["main"].onDisable()
            self.log.debug("Plugin %s disabled with no errors.", plugin)
        except AttributeError:
            self.log.debug("Plugin %s disabled (has no onDisable() event).", plugin)
        except Exception as e:
            self.log.exception("Error while disabling plugin '%s': \n%s", plugin, e)
        finally:
            del self.wrapper.commands[plugin]
            del self.wrapper.events[plugin]
            del self.wrapper.help[plugin]
            self.plugins_loaded = []

    def loadplugins(self):
        self.log.info("Loading plugins...")
        files = os.listdir("wrapper-plugins")
        py_files = []
        for i in files:
            name = i[:-3]
            ext = i[-3:]
            if ext == ".py":
                if name not in py_files:
                    py_files.append(name)

        for names in py_files:
            self.loadplugin(names, py_files)

    def disableplugins(self):
        self.log.info("Disabling plugins...")
        for i in self.plugins:
            self.unloadplugin(i)
        self.plugins = {}
        self.log.info("Disabling plugins...Done!")

    def reloadplugins(self):
        self.plugins_loaded = []
        self.disableplugins()
        self.loadplugins()
        self.log.info("Plugins reloaded")
