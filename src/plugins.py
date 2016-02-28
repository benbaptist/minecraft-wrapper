import os, traceback, sys
from importlib import import_module
from api import API
from log import *
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
		if "disabled_plugins" not in self.wrapper.storage: self.wrapper.storage["disabled_plugins"] = []
		self.log.info("Loading plugin %s..." % i)
		if os.path.isdir("wrapper-plugins/%s" % i):
			plugin = import_module(i)
			name = i
		elif i[-3:] == ".py":
			plugin = import_module(i[:-3])
			name = i[:-3]
		else:
			return False
		try: disabled = plugin.DISABLED
		except: disabled = False
		try: dependencies = plugin.DEPENDENCIES  # if used, plugin.DEPENDENCIES must be a 'list' type (even if only one item); e.g. = ["some.py", "another.py", etc]
		except: dependencies = False
		try: name = plugin.NAME
		except: pass
		try: id = plugin.ID
		except: id = name
		try: version = plugin.VERSION
		except: version = (0, 1)
		try: description = plugin.DESCRIPTION
		except: description = None
		try: summary = plugin.SUMMARY
		except: summary = None
		try: author = plugin.AUTHOR
		except: author = None
		try: website = plugin.WEBSITE
		except: website = None
		if id in self.wrapper.storage["disabled_plugins"] or disabled:
			self.log.warn("Plugin '%s' disabled - not loading" % name)
			return
		if id in self.plugins:  # Once successfully loaded, further attempts to load the plugin are ignored
			self.log.debug("Plugin '%s' already loaded - not reloading" % name)
			return
		if dependencies:  # load dependent plugins before continuing...
			for dependency in dependencies:  # List data type must be used, even if only a single plugin (i.e. = ["supportplugin.py"]
				self.loadPlugin(dependency)
		main = plugin.Main(API(self.wrapper, name, id), PluginLog(self.log, name))
		self.plugins[id] = {"main": main, "good": True, "module": plugin} #  "events": {}, "commands": {},
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
		except:
			self.log.error("Error while disabling plugin '%s'" % plugin)
			self.log.getTraceback()
		try:
			reload(self.plugins[plugin]["module"])
		except:
			self.log.error("Error while reloading plugin '%s' -- it was probably deleted or is a bugged version" % plugin)
			self.log.getTraceback()
	def loadPlugins(self):
		self.log.info("Loading plugins...")
		if not os.path.exists("wrapper-plugins"):
			os.mkdir("wrapper-plugins")
		sys.path.append("wrapper-plugins")
		for i in os.listdir("wrapper-plugins"):
			try:
				if i[0] == ".": continue
				if os.path.isdir("wrapper-plugins/%s" % i): self.loadPlugin(i)
				elif i[-3:] == ".py": self.loadPlugin(i)
			except:
				for line in traceback.format_exc().split("\n"):
					self.log.debug(line)
				self.log.error("Failed to import plugin '%s'" % i)
				self.plugins[i] = {"name": i, "good": False}
		self.wrapper.events.callEvent("helloworld.event", {"testValue": True})
	def disablePlugins(self):
		self.log.error("Disabling plugins...")
		for i in self.plugins:
			self.unloadPlugin(i)
	def reloadPlugins(self):
		for i in self.plugins:
			try:
				self.unloadPlugin(i)
			except:
				for line in traceback.format_exc().split("\n"):
					self.log.debug(line)
				self.log.error("Failed to unload plugin '%s'" % i)
				try:
					reload(self.plugins[plugin]["module"])
				except:
					pass
		self.plugins = {}
		self.loadPlugins()
		self.log.info("Plugins reloaded")

