import traceback, ast, random
class Commands:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.log = wrapper.log
		
		self.commands = {}
	def __getitem__(self, index):
		if not type(index) == str:
			raise Exception("A string must be passed to the stuff")
		return self.commands[index]
	def __setitem__(self, index, value):
		if not type(index) == str:
			raise Exception("A string must be passed to the stuff")
		self.commands[index] = value
		return self.commands[index]
	def __delitem__(self, index):
		if not type(index) == str:
			raise Exception("A string must be passed to the stuff")
		del self.commands[index]
	def __iter__(self):
		for i in self.commands:
			yield i
	def playerCommand(self, payload):
		player = payload["player"]
		self.log.info("%s executed: /%s %s" % (str(payload["player"]), payload["command"], " ".join(payload["args"])))
		def args(i):
			try: return payload["args"][i]
			except: return ""
		def argsAfter(i):
			try: return " ".join(payload["args"][i:])
			except: return ""
		for pluginID in self.commands:
			if pluginID == "Wrapper.py":
				try:
					print(self.commands[pluginID])
					self.commands[pluginID][command](payload["player"], payload["args"])
				except: pass
				continue
			if pluginID not in self.wrapper.plugins: continue
			plugin = self.wrapper.plugins[pluginID]
			if not plugin["good"]: continue
			commandName = payload["command"]
			if commandName in self.commands[pluginID]:
				try:
					command = self.commands[pluginID][commandName]
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
		if payload["command"] == "wrapper":
			if not player.isOp(): return 
			buildString = self.wrapper.getBuildString()
			if len(args(0)) > 0:
				subcommand = args(0)
				if subcommand == "update":
					player.message({"text": "Checking for new Wrapper.py updates...","color":"yellow"})
					update = self.checkForNewUpdate()
					if update:
						version, build, type = update
						player.message("&bNew Wrapper.py Version %s (Build #%d) available!)" % (".".join([str(_) for _ in version]), build))
						player.message("&bYou are currently on %s." % self.wrapper.getBuildString())
						player.message("&aPerforming update...")
						if self.performUpdate(version, build, type):
							player.message("&aUpdate completed! Version %s #%d (%s) is now installed. Please reboot Wrapper.py to apply changes." % (version, build, type))
						else:
							player.message("&cAn error occured while performing update. Please check the Wrapper.py console as soon as possible for an explanation and traceback. If you are unsure of the cause, please file a bug report on http://github.com/benbaptist/minecraft-wrapper with the traceback.")
					else:
						player.message("&cNo new Wrapper.py versions available.")
				elif subcommand == "halt":
					player.message("&cHalting Wrapper.py... goodbye!")
					self.wrapper.shutdown()
				elif subcommand in ("mem", "memory"):
					if self.wrapper.server.getMemoryUsage():
						player.message("&cServer Memory: %d bytes" % self.wrapper.server.getMemoryUsage())
					else:
						player.message("&cError: Couldn't retrieve memory usage for an unknown reason")
				elif subcommand == "random":
					player.message("&cRandom number: &a%d" % random.randrange(0, 99999999))
			else:
				player.message({"text": "Wrapper.py Version %s" % (buildString), "color": "gray", "italic": True})
			return
		if payload["command"] in ("plugins", "pl"):
			if player.isOp():
				player.message({"text": "List of plugins installed:", "color": "red", "italic": True})
				for id in self.wrapper.plugins:
					plugin = self.wrapper.plugins[id]
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
			if player.isOp():
				if args(0) == "server":
					return
				try:
					self.wrapper.plugins.reloadPlugins()
					player.message({"text": "Plugins reloaded.", "color": "green"})
					if self.wrapper.server.getServerType() != "vanilla":
						player.message({"text": "Note: If you meant to reload the server's plugins and not Wrapper.py's plugins, run `/reload server`.", "color": "gold"})
				except:
					self.log.error("Failure to reload plugins:")
					self.log.error(traceback.format_exc())
					player.message({"text": "An error occurred while reloading plugins. Please check the console immediately for a traceback.", "color": "red"})
				return False

		if payload["command"] in ("ban-ip", "pardon-ip"):
			if player.isOp():
				if self.wrapper.config["Proxy"]["proxy-enabled"]:
					player.message({"text": "Proxy mode!", "color": "dark_purple"})
					player.message({"text": "Note: This will not work in proxy mode", "color": "red"})
					player.message({"text": "In proxy mode, use /proxy-ban-ip or /proxy-pardon-ip.", "color": "green"})
					return False
		if payload["command"] == "proxy-ban-ip":
			if player.isOp():
				if self.wrapper.config["Proxy"]["proxy-enabled"]:
					if len(args(0)) > 0:
						ipnumbers = str(args(0)).split(".")
						if len(ipnumbers) != 4:
							player.message("&cinvalid ip address format: %s" % args(0))
							return False
						for ipnumber in range(0,4):
							if int(ipnumbers[ipnumber]) > 255 or int(ipnumbers[ipnumber]) < 0:
								player.message("&cinvalid ip component: %s  &5%s" % (args(0), str(ipnumbers[ipnumber])))
								return False
						self.wrapper.proxy.banIP(args(0))
						player.message({"text": "IP address banned!", "color": "yellow"})
						return False
				else:
					player.message({"text": "This will only work in proxy mode", "color": "red"})
					player.message({"text": "The server is not in proxy mode (use /ban-ip).", "color": "red"})
					return False
		if payload["command"] == "proxy-pardon-ip":
			if player.isOp():
				if self.wrapper.config["Proxy"]["proxy-enabled"]:
					if len(args(0)) > 0:
						ipnumbers = str(args(0)).split(".")
						if len(ipnumbers) != 4:
							player.message("&cinvalid ip address format: %s" % args(0))
							return False
						for ipnumber in range(0,4):
							if int(ipnumbers[ipnumber]) > 255 or int(ipnumbers[ipnumber]) < 0:
								player.message("&cinvalid ip component: %s  &5%s" % (args(0), str(ipnumbers[ipnumber])))
								return False
						ipuse = ""
						if self.wrapper.proxy.pardonIP(args(0)) is True:
							player.message({"text": "IP address unbanned!", "color": "gold"} % str((args(0))))
						else:
							player.message({"text": "IP unban failed!", "color": "red"})
						return False
				else:
					player.message({"text": "This will only work in proxy mode", "color": "red"})
					player.message({"text": "The server is not in proxy mode (use /ban-ip).", "color": "red"})
					return False

		if payload["command"] in ("help", "?"):
			helpGroups = [{"name": "Minecraft", "description": "List regular server commands"}]
			for id in self.wrapper.help:
				plugin = self.wrapper.help[id]
				for help in plugin:
					helpGroups.append({"name": help, "description": plugin[help][0]})
			if len(args(1)) > 0:
				group = args(0).lower()
				page = args(1)
			else:
				group = ""
				page = args(0)
			try: page = int(page) - 1
			except:
				if len(page) > 0:
					group = page.lower()
				page = 0
			def showPage(page, items, command, perPage):
				pageCount = len(items) / perPage
				if (int(len(items) / perPage)) != (float(len(items)) / perPage): pageCount += 1
				if page >= pageCount or page < 0:
					player.message("&cNo such page '%s'!" % str(page + 1))
					return
				player.message(" ") # Padding, for the sake of making it look a bit nicer
				player.message({"text": "--- Showing ", "color": "dark_green", "extra":[
					{"text": "help", "clickEvent": {"action": "run_command", "value": "/help"}},
					{"text": " page %d of %d ---" % (page + 1, pageCount)}
				]})
				for i,v in enumerate(items):
					if not i / perPage == page: continue 
					player.message(v)
				if pageCount > 1:
					if page > 0:
						prevButton = {"text": "Prev", "underlined": True, "clickEvent": {"action": "run_command", "value": "%s %d" % (command, page)}}
					else:
						prevButton = {"text": "Prev", "italic": True, "color": "gray"}
					if page <= pageCount:
						nextButton = {"text": "Next", "underlined": True, "clickEvent": {"action": "run_command", "value": "%s %d" % (command, page + 2)}}
					else:
						nextButton = {"text": "Next", "italic": True, "color": "gray"}
					player.message({"text": "--- ", "color": "dark_green", "extra":[
						prevButton,
						{"text": " | "},
						nextButton,
						{"text": " ---"}
					]})
			if len(group) > 0:
				if group == "minecraft":
					player.execute("help %d" % (page + 1))
				else:
					player.message(" ") # Padding, for the sake of making it look a bit nicer
					for id in self.wrapper.help:
						for groupName in self.wrapper.help[id]:
							if groupName.lower() == group:
								group = self.wrapper.help[id][groupName][1]
								items = []
								for i in group:
									command, args, permission = i[0].split(" ")[0], "", None
									if i[0].split(" ") > 1:
										args = " ".join(i[0].split(" ")[1:])
									if not player.hasPermission(i[2]):
										continue
									if len(i) > 1 and player.isOp():
										permission = {"text": "Requires permission '%s'." % i[2], "color": "gray", "italic": True}
									items.append({"text": "", "extra":[
										{"text": command, "color": "gold", "clickEvent": {"action": "suggest_command", "value": command}, "hoverEvent": {"action": "show_text", "value": permission}},
										{"text": " "+args, "color": "red", "italic": True},
										{"text": " - %s " % i[1]}
									]})
								showPage(page, items, "/help %s" % groupName, 4)
								return
					player.message("&cThe help group '%s' does not exist." % group)
			else:
				items = []
				for v in helpGroups:
					items.append({"text": "", "extra":[
						{"text": v["name"], "color": "gold", "clickEvent": {"action": "run_command", "value": "/help " + v["name"]}},
						{"text": " - " + v["description"]}
					]})
				showPage(page, items, "/help", 8)
			return False
		if payload["command"] == "playerstats":
			subcommand = args(0)
			if player.isOp():
				totalPlaytime = {}
				players = self.wrapper.api.minecraft.getAllPlayers()
				for uu in players:
					if not "logins" in players[uu]: 
						continue
					playerName = self.wrapper.getUsername(uu)
					totalPlaytime[playerName] = [0, 0]
					for i in players[uu]["logins"]:
						totalPlaytime[playerName][0] += players[uu]["logins"][i] - int(i)
						totalPlaytime[playerName][1] += 1
				def secondsToHuman(seconds):
					result = "None at all!"; plural = "s"
					if seconds > 0:
						result = "%d seconds" % seconds
					if seconds > 59:
						if (seconds/60) == 1: plural = ""
						result = "%d minute%s" % (seconds/60, plural)
					if seconds > 3599:
						if (seconds/3600) == 1: plural = ""
						result = "%d hour%s" % (seconds/3600, plural)
					if seconds > 86400:
						if (seconds/86400) == 1: plural = ""
						result = "%s day%s" % (str(seconds/86400.0), plural)
					return result
				if subcommand == "all":
					player.message("&6----- All Players' Playtime -----")
					for name in totalPlaytime:
						seconds = totalPlaytime[name][0]
						result = secondsToHuman(seconds)
						player.message("&e%s: &6%s (%d logins)" % (name, result, totalPlaytime[name][1])) # 86400.0
				else:
					topPlayers = []
					for username in totalPlaytime:
						topPlayers.append((totalPlaytime[username][0], username))
					topPlayers.sort(); topPlayers.reverse()
					player.message("&6----- Top 10 Players' Playtime -----")
					for i,p in enumerate(topPlayers):
						result = secondsToHuman(p[0])
						player.message("&7%d. &e%s: &6%s" % (i+1, p[1], result))
						if i == 9: break
				return 
		if payload["command"] in ("permissions", "perm", "perms", "super"):
			if not "groups" in self.wrapper.permissions: self.wrapper.permissions["groups"] = {}
			if not "users" in self.wrapper.permissions: self.wrapper.permissions["users"] = {}
			if not "Default" in self.wrapper.permissions["groups"]: self.wrapper.permissions["groups"]["Default"] = {"permissions": {}}
			if player.isOp():
				def usage(l):
					player.message("&cUsage: /%s %s" % (payload["command"], l))
				command = args(0)
				if command == "groups":
					group = args(1)
					subcommand = args(2)
					if subcommand == "new":
						self.wrapper.permissions["groups"][group] = {"permissions": {}}
						player.message("&aCreated a new permissions group '%s'!" % group)
					elif subcommand == "delete":
						if not group in self.wrapper.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						del self.wrapper.permissions["groups"][group]
						player.message("&aDeleted permissions group '%s'." % group)
					elif subcommand == "set":
						if not group in self.wrapper.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						node = args(3)
						value = argsAfter(4)
						if len(value) == 0: value = True
						if value in ("True", "False"): value = ast.literal_eval(value) 
						if len(node) > 0:
							self.wrapper.permissions["groups"][group]["permissions"][node] = value
							player.message("&aAdded permission node '%s' to group '%s'!" % (node, group))
						else:
							usage("groups %s set <permissionNode> [value]" % group)
					elif subcommand == "remove":
						if not group in self.wrapper.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						node = args(3)
						if node in self.wrapper.permissions["groups"][group]["permissions"]:
							del self.wrapper.permissions["groups"][group]["permissions"][node]
							player.message("&aRemoved permission node '%s' from group '%s'." % (node, group))
					elif subcommand == "info":
						if not group in self.wrapper.permissions["groups"]:
							player.message("&cGroup '%s' does not exist!" % group)
							return
						player.message("&aUsers in the group '%s':" % group)
						for uuid in self.wrapper.permissions["users"]:
							if group in self.wrapper.permissions["users"][uuid]["groups"]:
								player.message("%s: &2%s" % (self.wrapper.lookupUsernamebyUUID(str(uuid)), str(uuid)))
						player.message("&aPermissions for the group '%s':" % group)
						for node in self.wrapper.permissions["groups"][group]["permissions"]:
							value = self.wrapper.permissions["groups"][group]["permissions"][node]
							if value == True:
								player.message("- %s: &2%s" % (node, value))
							elif value == False:
								player.message("- %s: &4%s" % (node, value))
							else:
								player.message("- %s: &7%s" % (node, value))
					else:
						player.message("&cList of groups: %s" % ", ".join(self.wrapper.permissions["groups"]))
						usage("groups <groupName> [new/delete/set/remove/info]")
				elif command == "users":
					username = args(1)
					subcommand = args(2)
					#try:
					if len(username) > 0: uuid = str(self.wrapper.lookupUUIDbyUsername(username))
					#except:
					#player.message("&cUsername '%s' does not exist." % username)
					#return False
					if len(username) > 0:
						if uuid not in self.wrapper.permissions["users"]:
							self.wrapper.permissions["users"][uuid] = {"groups": [], "permissions": {}}
					if subcommand == "group":
						group = args(3)
						if len(group) > 0:
							if not group in self.wrapper.permissions["groups"]:
								player.message("&cGroup '%s' does not exist!" % group)
								return
							if group not in self.wrapper.permissions["users"][uuid]["groups"]:
								self.wrapper.permissions["users"][uuid]["groups"].append(group)
								player.message("&aAdded user '%s' to group '%s'!" % (username, group))
							else:
								self.wrapper.permissions["users"][uuid]["groups"].remove(group)
								player.message("&aRemoved user '%s' from group '%s'!" % (username, group))
						else:
							usage("users <username> group <groupName>")
					elif subcommand == "set":
						node = args(3)
						value = argsAfter(4)
						if len(value) == 0: value = True
						if value in ("True", "False"): value = ast.literal_eval(value) 
						if len(node) > 0:
							self.wrapper.permissions["users"][uuid]["permissions"][node] = value
							player.message("&aAdded permission node '%s' to player '%s'!" % (node, username))
						else:
							usage("users %s set <permissionNode> [value]" % username)
					elif subcommand == "remove":
						node = args(3)
						if not node in self.wrapper.permissions["users"][uuid]["permissions"]:
							player.message("&cPlayer '%s' never had permission '%s'!" % (username, node))
							return
						if node in self.wrapper.permissions["users"][uuid]["permissions"]:
							del self.wrapper.permissions["users"][uuid]["permissions"][node]
							player.message("&aRemoved permission node '%s' from player '%s'." % (node, username))
							return
					elif subcommand == "info":
						player.message("&aUser '%s' is in these groups: " % username)
						for group in self.wrapper.permissions["users"][uuid]["groups"]:
							player.message("- %s" % group)
						player.message("&aUser '%s' is granted these individual permissions (not including permissions inherited from groups): " % username)
						for node in self.wrapper.permissions["users"][uuid]["permissions"]:
							value = self.wrapper.permissions["users"][uuid]["permissions"][node]
							if value == True:
								player.message("- %s: &2%s" % (node, value))
							elif value == False:
								player.message("- %s: &4%s" % (node, value))
							else:
								player.message("- %s: &7%s" % (node, value))
					else:
						usage("users <username> <group/set/remove/info>")
				else:
					usage("<groups/users/RESET> (Note: RESET is case-sensitive!)")
					player.message("&cAlias commands: /perms, /perm, /super")
				return False
		return True
