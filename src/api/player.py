# coding=utf-8
import storage, api, time, fnmatch, json, threading

from mcpkt import ClientBound18 as defPacketsCB
from mcpkt import ClientBound19 as PacketsCB19

class Player:
	"""
	Player objects contains methods and data of a currently logged-in player. This object is destroyed
	upon logging off. """
	def __init__(self, username, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.permissions = wrapper.permissions
		self.log = wrapper.log

		self.username = username
		self.name = self.username  # just an alias - same variable
		self.loggedIn = time.time()
		self.abort = False

		self.uuid = self.wrapper.getUUID(username)
		self.client = None
		self.clientPackets = defPacketsCB

		if not self.wrapper.proxy == False:
			for client in self.wrapper.proxy.clients:
				if client.username == username:
					self.client = client
					self.uuid = client.uuid
					if self.getClient().version > 49:
						self.clientPackets = PacketsCB19
					break
		# hopefully these will never happen again:
		if self.uuid is None:
			self.log.error("UUID for %s was 'None'. Proxy mode is %s Please report this issue (and this line) to "
						   "http://github.com/benbaptist/minecraft-wrapper/issues" % (self.username, str(self.wrapper.proxy)))
		if self.uuid is False:
			self.log.error("UUID for %s was False. Proxy mode is %s. Please report this issue (and this line) to"
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
		"""
		:param string: command to execute (no preceding slash) in the console
		Run a command in the Minecraft server's console.
		"""
		try:
			self.wrapper.server.console(string)
		except:
			pass
	def execute(self, string):
		"""
		:param string: command to execute (no preceding slash)
		 Run a command as this player. If proxy mode is not enabled,
		it simply falls back to using the 1.8 'execute' command.
		To be clear, this does NOT work with any Wrapper.py or commands.
		The command is sent straight to the server without going through the wrapper.
		"""
		try:
			self.client.message("/%s" % string)
		except:
			self.console("execute %s ~ ~ ~ %s" % (self.name, string))
	def say(self, string):
		""" :param string: message sent to the server as the player.
		Send a message as a player.

		Beware: the message string is sent directly to the server
		without wrapper filtering,so it could be used to execute commands as the player if
		the string is prefixed with a slah, for instance.
		* Only works in proxy mode. """
		self.client.message(string)
	def getClient(self):
		"""
		:returns: player client object
		"""
		if self.client == None:
			for client in self.wrapper.proxy.clients:
				try:
					if client.username == self.username:
						self.client = client
						return self.client
				except:
					pass
		else:
			return self.client
	def processColorCodesOld(self, message):
		"""
		:param message: message text containing '&' to represent the chat formatting codes
		:return: mofified text containing the section sign (§) and the formatting code.
		"""
		for i in api.API.colorCodes:
			message = message.replace("&" + i, "\xc2\xa7" + i)
		return message
	def getPosition(self):
		""":returns: a tuple of the player's current position, if they're on ground, and yaw/pitch of head. """
		return self.getClient().position + self.getClient().head
	def getGamemode(self):
		""":returns:  the player's current gamemode. """
		return self.getClient().gamemode
	def getDimension(self):
		""":returns: the player's current dimension.
		-1 for Nether,
		 0 for Overworld
		 1 for End.
		 """
		return self.getClient().dimension
	def setGamemode(self, gm=0):
		"""
		:param gm: desired gamemode, as a value 0-3
		Sets the user's gamemode.
		"""
		if gm in (0, 1, 2, 3):
			self.client.gamemode = gm
			self.console("gamemode %d %s" % (gm, self.username))
	def setResourcePack(self, url, hashrp=""):
		"""
		:param url: URL of resource pack
		:param hashrp: resource pack hash
		Sets the player's resource pack to a different URL. If the user hasn't already allowed
		resource packs, the user will be prompted to change to the specified resource pack.
		Probably broken right now.
		"""
		if self.getClient().version < 7:
			self.client.send(0x3f, "string|bytearray", ("MC|RPack", url))
		else:
			self.client.send(self.clientPackets.resourcepacksend, "string|string", (url, hashrp))
	def isOp(self):
		"""
		:returns: whether or not the player is currently a server operator.
		"""
		operators = json.loads(open("ops.json", "r").read())
		for i in operators:
			if i["uuid"] == str(self.uuid) or i["name"] == self.username:
				return True
		return False

	# region Visual notifications
	def message(self, message=""):
		if isinstance(message, dict):
			self.wrapper.server.console("tellraw %s %s" % (self.username, json.dumps(message)))
		else:
			self.wrapper.server.console("tellraw %s %s" % (self.username, self.wrapper.server.processColorCodes(message)))
	def actionMessage(self, message=""):
		if self.getClient().version > 10:
			self.getClient().send(self.clientPackets.chatmessage, "string|byte", (json.dumps({"text": self.processColorCodesOld(message)}), 2))
	def setVisualXP(self, progress, level, total):
		""" Change the XP bar on the client's side only. Does not affect actual XP levels. """
		if self.getClient().version > 10:
			self.getClient().send(self.clientPackets.setexperience, "float|varint|varint", (progress, level, total))
		else:
			self.getClient().send(self.clientPackets.setexperience, "float|short|short", (progress, level, total))
	def openWindow(self, type, title, slots):
		self.getClient().windowCounter += 1
		if self.getClient().windowCounter > 200: self.getClient().windowCounter = 2
		if self.getClient().version > 10:
			self.getClient().send(self.clientPackets.openwindow, "ubyte|string|json|ubyte", (self.getClient().windowCounter, "0", {"text": title}, slots))
		return None # return a Window object soon
	# endregion Visual notifications

	# region Abilities & Client-Side Stuff
	def getClientpacketlist(self):
		"""allow plugins to get the players client plugin list per their
		client version (list in mcpky.py).. eg:
			packets = player.getClientpacketlist()
			player.client.send(packets.playerabilities, "byte|float|float", (0x0F, 1, 1))"""
		return self.clientPackets
	def setPlayerFlying(self, fly): # UNFINISHED FUNCTION - setting byte bits 0x2 and 0x4 (set flying, allow flying)
		if fly:
			self.getClient().send(self.clientPackets.playerabilities , "byte|float|float", (0x06, 1, 1))  # player abilities
		else:
			self.getClient().send(self.clientPackets.playerabilities , "byte|float|float", (0x00, 1, 1))
	def setBlock(self, position): # Unfinished function, will be used to make phantom blocks visible ONLY to the client
		pass
	# endregion

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
		if "users" not in self.permissions:
			self.permissions["users"] = {}
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				self.permissions["users"][uuid]["permissions"][node] = value
	def removePermission(self, node):
		""" Completely removes a permission node from the player. They will inherit this permission from their groups or from plugin defaults. 
		
		If the player does not have the specific permission, an IndexError is raised. Note that this method has no effect on nodes inherited from groups or plugin defaults. """
		if "users" not in self.permissions:
			self.permissions["users"] = {}
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				if node in self.permissions["users"][uuid]["permissions"]:
					del self.permissions["users"][uuid]["permissions"][node]
				else:
					raise IndexError("%s does not have permission node '%s'" % (self.username, node))
	def hasGroup(self, group):
		""" Returns a boolean of whether or not the player is in the specified permission group. """
		self.uuid = self.wrapper.lookupUUIDbyUsername(self.username)  #init the perms for new player
		if "users" not in self.permissions:
			self.permissions["users"] = {}
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				return group in self.permissions["users"][uuid]["groups"]
		return False
	def getGroups(self):
		""" Returns a list of permission groups that the player is in. """
		if "users" not in self.permissions:
			self.permissions["users"] = {}
		self.uuid = self.wrapper.lookupUUIDbyUsername(self.username)  # init the perms for new player
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				return self.permissions["users"][uuid]["groups"]
		return [] # If the user is not in the permission database, return this
	def setGroup(self, group):
		""" Adds the player to a specified group. If the group does not exist, an IndexError is raised. """
		if not group in self.permissions["groups"]:
			raise IndexError("No group with the name '%s' exists" % group)
		self.uuid = self.wrapper.lookupUUIDbyUsername(self.username)  # init the perms for new player
		if "users" not in self.permissions:
			self.permissions["users"] = {}
		for uuid in self.permissions["users"]:
			if uuid == str(self.uuid):
				self.permissions["users"][uuid]["groups"].append(group)
	def removeGroup(self, group):
		""" Removes the player to a specified group. If they are not part of the specified group, an IndexError is raised. """
		if "users" not in self.permissions:
			self.permissions["users"] = {}
		self.uuid = self.wrapper.lookupUUIDbyUsername(self.username)  # init the perms for new player
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
