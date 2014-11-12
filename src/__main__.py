# -*- coding: utf-8 -*-
import socket, datetime, time, sys, threading, random, subprocess, os, json, signal, traceback, ConfigParser, ast, proxy, web, globals, storage, hashlib
from log import *
from config import Config
from irc import IRC
from server import Server
from importlib import import_module
from scripts import Scripts
import importlib
from api import API
try:
	import requests
	IMPORT_REQUESTS = True
except:
	IMPORT_REQUESTS = False

class Wrapper:
	def __init__(self):
		self.log = Log()
		self.configManager = Config(self.log)
		self.plugins = {}
		self.server = False
		self.proxy = False
		self.halt = False
		self.listeners = []
		self.storage = storage.Storage("main", self.log)
		self.permissions = storage.Storage("permissions", self.log)
		
		self.commands = {}
		self.events = {}
		self.permission = {}
	def loadPlugin(self, i):
		self.log.info("Loading plugin %s..." % i)
		if os.path.isdir("wrapper-plugins/%s" % i):
			plugin = import_module(i)
			name = i
		elif i[-3:] == ".py":
			plugin = import_module(i[:-3])
			name = i[:-3]
		else:
			return False
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
		main = plugin.Main(API(self, name, id), PluginLog(self.log, name))
		self.plugins[id] = {"main": main, "good": True, "module": plugin} #  "events": {}, "commands": {},
		self.plugins[id]["name"] = name
		self.plugins[id]["version"] = version
		self.plugins[id]["summary"] = summary
		self.plugins[id]["description"] = description 
		self.plugins[id]["filename"] = i
		self.commands[id] = {}
		self.events[id] = {}
		self.permission[id] = {}
		main.onEnable()
	def unloadPlugin(self, plugin):
		del self.commands[plugin]
		del self.events[plugin]
		try:
			self.plugins[plugin]["main"].onDisable()
		except:
			self.log.error("Error while disabling plugin '%s'" % plugin)
			self.log.getTraceback()
		reload(self.plugins[plugin]["module"])
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
		self.callEvent("helloworld.event", {"testValue": True})
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
	def callEvent(self, event, payload):
		if event == "player.runCommand":
			if not self.playerCommand(payload): return False
		for sock in self.listeners:
			sock.append({"event": event, "payload": payload})
		try:
			for pluginID in self.events:
				if event in self.events[pluginID]:
					try:
						result = self.events[pluginID][event](payload)
						if result == False:
							return False
					except:
						self.log.error("Plugin '%s' errored out when executing callback event '%s':" % (pluginID, event))
						for line in traceback.format_exc().split("\n"):
							self.log.error(line)
		except:
			self.log.error("A serious runtime error occurred - if you notice any strange behaviour, please restart immediately")
		return True
	def playerCommand(self, payload):
		self.log.info("%s executed: /%s %s" % (str(payload["player"]), payload["command"], " ".join(payload["args"])))
		if payload["command"] == "wrapper":
			player = payload["player"]
			buildString = self.getBuildString()
			player.message({"text": "Wrapper.py Version %s" % (buildString), "color": "gray", "italic": True})
			return False
		if payload["command"] in ("plugins", "pl"):
			player = payload["player"]
			if player.isOp():
				player.message({"text": "List of plugins installed:", "color": "red", "italic": True})
				for id in self.plugins:
					plugin = self.plugins[id]
					if plugin["good"]:
						name = plugin["name"]
						version = plugin["version"]
						summary = plugin["summary"]
						description = plugin["description"]
					else:
						name = id
						version = None
						summary = None
						description = ""
					if summary == None:
						summary = {"text": "No description is available for this plugin", "color": "gray", "italic": True, 
							"hoverEvent": {"action": "show_text", "value": description}}
					else:
						summary = {"text": summary, "color": "white", "hoverEvent": {"action": "show_text", "value": description}}
					
					if version == None: version = "v?.?"
					else: version = ".".join([str(_) for _ in version])
					if plugin["good"]:
						player.message({"text": name, "color": "dark_green", "hoverEvent": {"action": "show_text", "value": "Filename: %s | ID: %s" % (plugin["filename"], id)}, "extra":[{"text": " v%s" % version, "color": "dark_gray"}, {"text": " - ", "color": "white"}, summary]})
					else:
						player.message({"text": name, "color": "dark_red", "extra":[{"text": " - ", "color": "white"}, {"text": "Failed to import this plugin!", "color": "red", "italic": "true"}]})
				return False
		if payload["command"] == "reload":
			player = payload["player"]
			if player.isOp():
				try:
					self.reloadPlugins()
					player.message({"text": "Plugins reloaded.", "color": "green"})
				except:
					self.log.error("Failure to reload plugins:")
					self.log.error(traceback.format_exc())
					player.message({"text": "An error occurred while reloading plugins. Please check the console immediately for a traceback.", "color": "red"})
				return False
		if payload["command"] in ("permissions", "perm", "perms", "super"):
			player = payload["player"]
			if not "groups" in self.permissions: self.permissions["groups"] = {}
			if not "users" in self.permissions: self.permissions["users"] = {}
			if not "Default" in self.permissions["groups"]: self.permissions["groups"]["Default"] = {"permissions": {}}
			if player.isOp():
				def args(i):
					try: return payload["args"][i]
					except: return ""
				def argsAfter(i):
					try: return " ".join(payload["args"][i:])
					except: return ""
				def usage(l):
					player.message("&cUsage: /%s %s" % (payload["command"], l))
				command = args(0)
				if command == "groups":
					group = args(1)
					subcommand = args(2)
					if subcommand == "new":
						self.permissions["groups"][group] = {"permissions": {}}
						player.message("&aCreated a new permissions group '%s'!" % group)
					elif subcommand == "delete":
						if not group in self.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						del self.permissions["groups"][group]
						player.message("&aDeleted permissions group '%s'." % group)
					elif subcommand == "set":
						if not group in self.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						node = args(3)
						value = argsAfter(4)
						if len(value) == 0: value = True
						if value in ("True", "False"): value = ast.literal_eval(value) 
						if len(node) > 0:
							self.permissions["groups"][group]["permissions"][node] = value
							player.message("&aAdded permission node '%s' to group '%s'!" % (node, group))
						else:
							usage("groups %s set <permissionNode> [value]" % group)
					elif subcommand == "remove":
						if not group in self.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						node = args(3)
						if node in self.permissions["groups"][group]["permissions"]:
							del self.permissions["groups"][group]["permissions"][node]
							player.message("&aRemoved permission node '%s' from group '%s'." % (node, group))
					elif subcommand == "info":
						if not group in self.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						player.message("&aUsers in the group '%s':" % group)
						for uuid in self.permissions["users"]:
							if group in self.permissions["users"][uuid]["groups"]:
								player.message(uuid)
						player.message("&aPermissions for the group '%s':" % group)
						for node in self.permissions["groups"][group]["permissions"]:
							value = self.permissions["groups"][group]["permissions"][node]
							if value == True:
								player.message("- %s: &2%s" % (node, value))
							elif value == False:
								player.message("- %s: &4%s" % (node, value))
							else:
								player.message("- %s: &7%s" % (node, value))
					else:
						player.message("&cList of groups: %s" % ", ".join(self.permissions["groups"]))
						usage("groups <groupName> [new/delete/set/remove/info]")
				elif command == "users":
					username = args(1)
					subcommand = args(2)
					try:
						if len(username) > 0: uuid = self.proxy.lookupUsername(username)
					except:
						player.message("&cUsername '%s' does not exist." % username)
						return False
					if len(username) > 0:
						if uuid not in self.permissions["users"]:
							self.permissions["users"][uuid] = {"groups": [], "permissions": {}}
					if subcommand == "group":
						group = args(3)
						if len(group) > 0:
							if not group in self.permissions["groups"]:
								player.message("&cGroup '%s' does not exist!" % group)
								return
							if group not in self.permissions["users"][uuid]["groups"]:
								self.permissions["users"][uuid]["groups"].append(group)
								player.message("&aAdded user '%s' to group '%s'!" % (username, group))
							else:
								player.message("&aAlready added user '%s' to group '%s'!" % (username, group))
						else:
							usage("users <username> groups <groupName>")
					elif subcommand == "set":
						node = args(3)
						value = argsAfter(4)
						if len(value) == 0: value = True
						if value in ("True", "False"): value = ast.literal_eval(value) 
						if len(node) > 0:
							self.permissions["users"][uuid]["permissions"][node] = value
							player.message("&aAdded permission node '%s' to user '%s'!" % (node, username))
						else:
							usage("users %s set <permissionNode> [value]" % username)
					elif subcommand == "info":
						player.message("&aUser '%s' is in these groups: " % username)
						for group in self.permissions["users"][uuid]["groups"]:
							player.message("- %s" % group)
						player.message("&aUser '%s' is granted these individual permissions (not including permissions inherited from groups): " % username)
						for node in self.permissions["users"][uuid]["permissions"]:
							value = self.permissions["users"][uuid]["permissions"][node]
							if value == True:
								player.message("- %s: &2%s" % (node, value))
							elif value == False:
								player.message("- %s: &4%s" % (node, value))
							else:
								player.message("- %s: &7%s" % (node, value))
					else:
						usage("users <username> [group/set/info]")
				else:
					usage("[groups/users/RESET] (Note: RESET is case-sensitive!)")
				return False
		for pluginID in self.commands:
			if pluginID == "Wrapper.py":
				try: 
					self.commands[pluginID][command](payload["player"], payload["args"])
				except: pass
				continue
			if pluginID not in self.plugins: continue
			plugin = self.plugins[pluginID]
			if not plugin["good"]: continue
			commandName = payload["command"]
			if commandName in self.commands[pluginID]:
				try:
					command = self.commands[pluginID][commandName]
					player = payload["player"]
					if player.hasPermission(command["permission"]):
						command["callback"](payload["player"], payload["args"])
					else:
						player.message({"translate": "commands.generic.permission", "color": "red"})
					return False
				except:
					self.log.error("Plugin '%s' errored out when executing command: '<%s> /%s':" % (pluginID, payload["player"], command))
					for line in traceback.format_exc().split("\n"):
						self.log.error(line)
					payload["player"].message({"text": "An internal error occurred on the server side while trying to execute this command. Apologies.", "color": "red"})
					return False
		return True
	def getUUID(self, name):
		f = open("usercache.json", "r")
		data = json.loads(f.read())
		f.close()
		for u in data:
			if u["name"] == name:
				return u["uuid"]
		return False
	def start(self):
		self.configManager.loadConfig()
		self.config = self.configManager.config
		signal.signal(signal.SIGINT, self.SIGINT)
		
		self.api = API(self, "Wrapper.py")
		
		self.server = Server(sys.argv, self.log, self.configManager.config, self)
		self.server.init()
		
		self.loadPlugins()
		
		if self.config["IRC"]["enabled"]:
			self.irc = IRC(self.server, self.config, self.log, self, self.config["IRC"]["server"], self.config["IRC"]["port"], self.config["IRC"]["nick"], self.config["IRC"]["channels"])
			t = threading.Thread(target=self.irc.init, args=())
			t.daemon = True
			t.start()
		# Old, deactivated web interface code. Will work on this more soon after the release of 0.7.0.
		#if self.config["Web"]["web-enabled"]:
#			if web.IMPORT_SUCCESS:
#				self.web = web.Web(self)
#				t = threading.Thread(target=self.web.wrap, args=())
#				t.daemon = True
#				t.start()
#			else:
#				self.log.error("Web remote could not be started because you do not have the required modules installed: pkg_resources")
#				self.log.error("Hint: http://stackoverflow.com/questions/7446187")
		if len(sys.argv) < 2:
			wrapper.server.args = wrapper.configManager.config["General"]["command"].split(" ")
		else:
			wrapper.server.args = sys.argv[1:]
		
		consoleDaemon = threading.Thread(target=self.console, args=())
		consoleDaemon.daemon = True
		consoleDaemon.start()
		
		t = threading.Thread(target=self.timer, args=())
		t.daemon = True
		t.start()
		
		if self.config["General"]["shell-scripts"]:
			if os.name in ("posix", "mac"):
				self.scripts = Scripts(self)
			else:
				self.log.error("Sorry, but shell scripts only work on *NIX-based systems! If you are using a *NIX-based system, please file a bug report.")
		
		if self.config["Proxy"]["proxy-enabled"]:
			t = threading.Thread(target=self.startProxy, args=())
			t.daemon = True
			t.start()
		if self.config["General"]["auto-update-wrapper"]:
			t = threading.Thread(target=self.checkForUpdates, args=())
			t.daemon = True
			t.start()
		self.server.__handle_server__()
		
		self.disablePlugins()
	def startProxy(self):
		if proxy.IMPORT_SUCCESS:
			self.proxy = proxy.Proxy(self)
			proxyThread = threading.Thread(target=self.proxy.host, args=())
			proxyThread.daemon = True
			proxyThread.start()
		else:
			self.log.error("Proxy mode could not be started because you do not have one or more of the following modules installed: pycrypt and requests")
	def SIGINT(self, s, f):
		self.shutdown()
	def shutdown(self):
		self.halt = True
		sys.exit(0)
	def rebootWrapper(self):
		self.halt = True
		os.system(" ".join(sys.argv) + "&")
	def getBuildString(self):
		if globals.type == "dev":
			return "%s (development build #%d)" % (Config.version, globals.build)
		else:
			return "%s (stable)" % Config.version
	def checkForUpdates(self):
		if not IMPORT_REQUESTS:
			self.log.error("Can't automatically check for new Wrapper.py versions because you do not have the requests module installed!")
			return
		while not self.halt:
			time.sleep(3600)
			self.checkForUpdate(True)
	def checkForUpdate(self, auto):
		self.log.info("Checking for new builds...")
		if globals.type == "dev":
			try:
				r = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/docs/version.json")
				data = r.json()
				if data["build"] > globals.build and data["type"] == "dev":
					if auto:
						self.log.info("New Wrapper.py development build #%d available for download! (currently on #%d)" % (data["build"], globals.build))
						self.log.info("Because you are running a development build, you must manually update Wrapper.py To update Wrapper.py manually, please type /update-wrapper.")
					else:
						self.log.info("New Wrapper.py development build #%d available! Updating... (currently on #%d)" % (data["build"], globals.build))
						try:
							self.performUpdate("dev", data["version"], data["build"])
						except:
							self.log.error("Error while performing update:")
							self.log.getTraceback()
				else:
					self.log.info("No new versions available.")
			except:
				self.log.warn("Failed to check for updates - are you connected to the internet?")
		else:
			try:
				r = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/docs/version.json")
				data = r.json()
				if data["build"] > globals.build and data["type"] == "stable":
					self.log.info("New Wrapper.py %s available! Updating... (currently on %s)" % (data["version"], Config.version))
					try:
						self.performUpdate("stable", data["version"], data["build"])
					except:
						self.log.error("Error while performing update:")
						self.log.getTraceback()
				else:
					self.log.info("No new versions available.")
			except:
				self.log.warn("Failed to check for updates - are you connected to the internet?")
	def performUpdate(self, type, version, build):
		if type == "dev": repo = "development"
		else: repo = "master"
		wrapperHash = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/%s/docs/Wrapper.py.md5" % repo).text
		wrapperFile = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/%s/Wrapper.py" % repo).content
		self.log.info("Verifying Wrapper.py...")
		if hashlib.md5(wrapperFile).hexdigest() == wrapperHash:
			self.log.info("Wrapper.py successfully verified.")
			with open(sys.argv[0], "w") as f:
				f.write(wrapperFile)
			self.log.info("Wrapper.py %s (#%d) installed. Please reboot the Wrapper.py." % (".".join(version), build))
	def timer(self):
		while not self.halt:
			self.callEvent("timer.second", None)
			time.sleep(1)
	def console(self):
		while not self.halt:
			input = raw_input("")
			if len(input) < 1: continue
			if input[0] is not "/": 
				try:
					self.server.console(input)
				except:
					break
				continue
			def args(i): 
				try: return input[1:].split(" ")[i];
				except:pass;
			command = args(0)
			if command == "halt":
				self.server.stop("Halting server...")
				self.halt = True
				sys.exit()
			elif command == "stop":
				self.server.stop("Stopping server...")
			elif command == "start":
				self.server.start()
			elif command == "restart":
				self.server.stop("Server restarting, be right back!")
			elif command == "reload":
				self.reloadPlugins()
			elif command == "update-wrapper":
				self.checkForUpdate(False)
			elif command == "plugins":
				self.log.info("List of Wrapper.py plugins installed:")
				for id in self.plugins:
					plugin = self.plugins[id]
					if plugin["good"]:
						name = plugin["name"]
						summary = plugin["summary"]
						if summary == None: summary = "No description available for this plugin"
						
						version = plugin["version"]
							
						self.log.info("%s v%s - %s" % (name, ".".join([str(_) for _ in version]), summary))
					else:
						self.log.info("%s failed to load!" % (plug))
			elif command == "help":
				self.log.info("/reload - reload plugins")	
				self.log.info("/plugins - lists plugins")	
				self.log.info("/update-wrapper - Checks for new updates, and will install them automatically if one is available")
				self.log.info("/start & /stop - start and stop the server without auto-restarting respectively without shutting down Wrapper.py")
				self.log.info("/restart - restarts the server, obviously")				
				self.log.info("/halt - shutdown Wrapper.py completely")
				self.log.info("Wrapper.py Version %s" % self.getBuildString())
			else:
				self.log.error("Invalid command %s" % command)
if __name__ == "__main__":
	wrapper = Wrapper()
	log = wrapper.log
	log.info("Wrapper.py started - Version %s" % wrapper.getBuildString())
	
	try:
		t = threading.Thread(target=wrapper.start(), args=())
		t.daemon = True
		t.start()
	except SystemExit:
		#log.error("Wrapper.py received SystemExit")
		wrapper.disablePlugins()
		wrapper.halt = True
		try:
			for player in wrapper.server.players:
				wrapper.server.run("kick %s Wrapper.py received shutdown signal - bye" % player)
			time.sleep(0.2)
			wrapper.server.run("save-all")
			wrapper.server.run("stop")
		except:
			pass
	except:
		log.error("Wrapper.py crashed - stopping sever to be safe")
		for line in traceback.format_exc().split("\n"):
			log.error(line)
		wrapper.halt = True
		wrapper.disablePlugins()
		try:
			wrapper.server.stop("Wrapper.py crashed - please contact a server admin instantly")
		except:
			print "Failure to shutdown server cleanly!"
