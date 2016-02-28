import storage, api, time, fnmatch, json, threading
class Player:
	""" Player objects contains methods and data of a currently logged-in player. This object is destroyed upon logging off. """
	def __init__(self, username, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.permissions = wrapper.permissions
		self.name = username
		self.username = self.name # just an alias - same variable
		self.loggedIn = time.time()
		self.abort = False
		self.log = wrapper.log
		
		self.uuid = self.wrapper.getUUID(username)
		self.client = None
		if not self.wrapper.proxy == False:
			for client in self.wrapper.proxy.clients:
				if client.username == username:
					self.client = client
					self.uuid = client.uuid
					break
		if self.uuid == None: # Potential hack for UUID==None sometimes
			if not self.wrapper.proxy == False:
				self.uuid = self.wrapper.proxy.lookupUsername(self.username)
				self.log.error("UUID for %s was 'None' but has been reset using proxy.lookupUsername (%s). Proxy mode is "
								"on. Please report this issue (and this line) to http://github.com/benbaptist/minecraft-wrapper/issues" % (self.username, self.uuid))
			else:
				self.log.error("UUID for %s is set as None in Player object. Cannot be fixed. Proxy mode is off. Please "
								"report this issue (and this line) to http://github.com/benbaptist/minecraft-wrapper/issues " % self.username)
		if self.uuid == False:
			self.log.error("UUID for %s is set to False. Proxy mode is %s. Please report this issue (and this line) to"
							" http://github.com/benbaptist/minecraft-wrapper/issues" % (self.username, str(self.wrapper.proxy)))
		
		self.data = storage.Storage(self.uuid, root="wrapper-data/players")
		if not "firstLoggedIn" in self.data: self.data["firstLoggedIn"] = (time.time(), time.tzname)
		if not "logins" in self.data:
			self.data["logins"] = {}
		t = threading.Thread(target=self.__track__, args=())
		t.daemon = True
		t.start()
	def __str__(self):
		return self.username
	def __track__(self):
		self.data["logins"][int(self.loggedIn)] = time.time()
		while not self.abort:
			self.data["logins"][int(self.loggedIn)] = int(time.time())
			time.sleep(1)
	def console(self, string):
		""" Run a command in the Minecraft server's console. """
		try:
			self.wrapper.server.console(string)
		except:
			pass
	def execute(self, string):
		""" Run a vanilla command as this player. Works best in proxy mode. If proxy mode is not enabled, it simply falls back to using the 1.8 'execute' command. 
		
		To be clear, this does NOT work with any Wrapper.py commands. The command is sent straight to the vanilla server."""
		try:
			self.client.message("/%s" % string)
		except:
			self.console("execute %s ~ ~ ~ %s" % (self.name, string))
	def say(self, string):
		""" Send a message as a player. Beware, as this does not filter commands, so it could be used to execute commands as the player. Only works in proxy mode. """
		self.client.message(string)
	def getClient(self):
		if self.client == None:
			for client in self.wrapper.proxy.clients:
				try:
					if client.username == username:
						self.client = client
						return self.client
				except:
					pass
		else:
			return self.client
	def processColorCodesOld(self, message): # Not sure if this is used anymore. Might delete.
		for i in api.API.colorCodes:
			message = message.replace("&" + i, "\xc2\xa7" + i)
		return message
	def getPosition(self):
		""" Returns a tuple of the player's current position, if they're on ground, and yaw/pitch of head. """
		return self.getClient().position + self.getClient().head
#	def getHead(self): Commenting out for just one build, then I'll remove the code itself in the next push (hopefully, if I remember)
#		""" Returns a tuple of the player's head position. Same as last two values from player.getPosition() """
#		return self.getClient().head
	def getGamemode(self):
		""" Returns the player's current gamemode. """
		return self.getClient().gamemode
	def getDimension(self):
		""" Returns the player's current dimension. -1 for Nether, 0 for Overworld, and 1 for End. """
		return self.getClient().dimension
	def setGamemode(self, gm=0):
		""" Sets the user's gamemode. """
		if gm in (0, 1, 2, 3):
			self.client.gamemode = gm
			self.console("gamemode %d %s" % (gm, self.username))
	def setResourcePack(self, url):
		""" Sets the player's resource pack to a different URL. If the user hasn't already allowed resource packs, the user will be prompted to change to the specified resource pack. Probably broken right now. """
		if self.client.version < 7:
			self.client.send(0x3f, "string|bytearray", ("MC|RPack", url))
		else:
			self.client.send(0x48, "string|string", (url, ""))
	def isOp(self):
		""" Returns whether or not the player is currently a server operator.  """
		operators = json.loads(open("ops.json", "r").read())
		for i in operators:
			if i["uuid"] == str(self.uuid) or i["name"] == self.username:
				return True
		return False
	# Visual notifications
	def message(self, message=""):
		if isinstance(message, dict):
			self.wrapper.server.console("tellraw %s %s" % (self.username, json.dumps(message)))
		else:
			self.wrapper.server.console("tellraw %s %s" % (self.username, self.wrapper.server.processColorCodes(message)))
	def actionMessage(self, message=""):
		if self.getClient().version > 10:
			self.getClient().send(0x02, "string|byte", (json.dumps({"text": self.processColorCodesOld(message)}), 2))
	def setVisualXP(self, progress, level, total):
		""" Change the XP bar on the client's side only. Does not affect actual XP levels. """
		if self.getClient().version > 10:
			self.getClient().send(0x1f, "float|varint|varint", (progress, level, total))
		else:
			self.getClient().send(0x1f, "float|short|short", (progress, level, total))
	def openWindow(self, type, title, slots):
		self.getClient().windowCounter += 1
		if self.getClient().windowCounter > 200: self.getClient().windowCounter = 2
		if self.getClient().version > 10:
			self.getClient().send(0x2d, "ubyte|string|json|ubyte", (self.getClient().windowCounter, "0", {"text": title}, slots))
		return None # return a Window object soon
	# Abilities & Client-Side Stuff
	def setPlayerFlying(self, fly): # UNFINISHED FUNCTION
		if fly:
			self.getClient().send(0x13, "byte|float|float", (255, 1, 1))
		else:
			self.getClient().send(0x13, "byte|float|float", (0, 1, 1))
	def setBlock(self, position): # Unfinished function, will be used to make phantom blocks visible ONLY to the client
		pass
	# Inventory-related actions. These will probably be split into a specific Inventory class.
	def getItemInSlot(self, slot):
		return self.getClient().inventory[slot]
	def getHeldItem(self):
		""" Returns the item object of an item currently being held. """
		return self.getClient().inventory[36 + self.getClient().slot]
	# Permissions-related
	def hasPermission(self, node):
		""" If the player has the specified permission node (either directly, or inherited from a group that the player is in), it will return the value (usually True) of the node. Otherwise, it returns False. """
		if node == None: return True
		if "users" not in self.permissions:
			self.permissions["users"] = {}
		uuid = str(self.uuid)
		if uuid in self.permissions["users"]:
			for perm in self.permissions["users"][uuid]["permissions"]:	
				if node in fnmatch.filter([node], perm):
					return self.permissions["users"][uuid]["permissions"][perm]
		if uuid not in self.permissions["users"]: return False
		allgroups = []  # summary of groups included children groups
		for group in self.permissions["users"][uuid]["groups"]:  # get the parent groups
			if group not in allgroups:
				allgroups.append(group)
		itemsToProcess = allgroups[:]  # process and find child groups
		while len(itemsToProcess) > 0:
			parseparent = itemsToProcess.pop(0)
			for groupPerm in self.permissions["groups"][parseparent]["permissions"]:
				if (groupPerm in self.permissions["groups"]) and self.permissions["groups"][parseparent]["permissions"][groupPerm] and (groupPerm not in allgroups):
					allgroups.append(groupPerm)
					itemsToProcess.append(groupPerm)
		for group in allgroups:
			for perm in self.permissions["groups"][group]["permissions"]:
				if node in fnmatch.filter([node], perm):
					return self.permissions["groups"][group]["permissions"][perm]
		for perm in self.permissions["groups"]["Default"]["permissions"]:
			if node in fnmatch.filter([node], perm):
				return self.permissions["groups"]["Default"]["permissions"][perm]
		for id in self.wrapper.permission:
			if node in self.wrapper.permission[id]:
				return self.wrapper.permission[id][node]
		return False
	def setPermission(self, node, value=True):
		""" Adds the specified permission node and optionally a value to the player. 
		
		Value defaults to True, but can be set to False to explicitly revoke a particular permission from the player, or to any arbitrary value. """
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				self.permissions["users"][uuid]["permissions"][node] = value
	def removePermission(self, node):
		""" Completely removes a permission node from the player. They will inherit this permission from their groups or from plugin defaults. 
		
		If the player does not have the specific permission, an IndexError is raised. Note that this method has no effect on nodes inherited from groups or plugin defaults. """
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				if node in self.permissions["users"][uuid]["permissions"]:
					del self.permissions["users"][uuid]["permissions"][node]
				else:
					raise IndexError("%s does not have permission node '%s'" % (self.username, node))
	def hasGroup(self, group):
		""" Returns a boolean of whether or not the player is in the specified permission group. """
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				return group in self.permissions["users"][uuid]["groups"]
		return False
	def getGroups(self):
		""" Returns a list of permission groups that the player is in. """
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				return self.permissions["users"][uuid]["groups"]
		return [] # If the user is not in the permission database, return this
	def setGroup(self, group):
		""" Adds the player to a specified group. If the group does not exist, an IndexError is raised. """
		if not group in self.permissions["groups"]:
			raise IndexError("No group with the name '%s' exists" % group)
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				self.permissions["users"][uuid]["groups"].append(group)
	def removeGroup(self, group):
		""" Removes the player to a specified group. If they are not part of the specified group, an IndexError is raised. """
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				if group in self.permissions["users"][uuid]["groups"]:
					self.permissions["users"][uuid]["groups"].remove(group)
				else:
					raise IndexError("%s is not part of the group '%s'" % (self.username, group))
	# Player Information 
	def getFirstLogin(self):
		""" Returns a tuple containing the timestamp of when the user first logged in for the first time, and the timezone (same as time.tzname). """
		return self.data["firstLoggedIn"]
	# Cross-server commands
	def connect(self, address, port):
		""" Upon calling, the player object will become defunct and the client will be transferred to another server (provided it has online-mode turned off). """
		self.client.connect(address, port)
