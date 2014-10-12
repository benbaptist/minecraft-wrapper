import json, time, StringIO, nbt, items, storage, fnmatch
class API:
	statusEffects = {
		"speed": 1,
		"slowness": 2,
		"haste": 3,
		"mining_fatigue": 4,
		"strength": 5,
		"instant_health": 6,
		"instant_damage": 7,
		"jump_boost": 8,
		"nausea": 9,
		"regeneration": 10,
		"resistance": 11,
		"fire_resistance": 12,
		"water_breathing": 13,
		"invisibility": 14,
		"blindness": 15,
		"night_vision": 16,
		"hunger": 17,
		"weakness": 18,
		"poison": 19,
		"wither": 20,
		"health_boost": 21,
		"absorption": 22,
		"saturation": 23
	}
	colorCodes = {
		"0": "black",
		"1": "dark_blue",
		"2": "dark_green",
		"3": "dark_aqua",
		"4": "dark_red",
		"5": "dark_purple",
		"6": "gold",
		"7": "gray",
		"8": "dark_gray",
		"9": "blue",
		"a": "green",
		"b": "aqua",
		"c": "red",
		"d": "light_purple",
		"e": "yellow",
		"f": "white",
		"r": "\xc2\xa7r",
		"k": "\xc2\xa7k", # obfuscated
		"l": "\xc2\xa7l", # bold
		"m": "\xc2\xa7m", # strikethrough
		"n": "\xc2\xa7n", # underline
		"o": "\xc2\xa7o", # italic,
	}
	def __init__(self, wrapper, name="", id=None):
		self.wrapper = wrapper
		self.name = name
		self.minecraft = Minecraft(wrapper)
		self.server = wrapper.server
		if id == None:
			self.id = name
		else:
			self.id = id
	def registerCommand(self, name, callback, permission=None):
		""" This registers a command that, when executed in Minecraft, will execute callback(player, args). 
		permission is an optional attribute if you want your command to only be executable if the player has a specified permission node.
		"""
		self.wrapper.log.debug("[%s] Registered command '%s'" % (self.name, name))
		if self.id not in self.wrapper.commands: self.wrapper.commands[self.id] = {}
		self.wrapper.commands[self.id][name] = {"callback": callback, "permission": permission}
	def registerEvent(self, eventType, callback):
		""" Register an event and a callback. See [doc link needed here] for a list of events. callback(payload) when an event occurs, and the contents of payload varies between events."""
		self.wrapper.log.debug("[%s] Registered event '%s'" % (self.name, eventType))
		if self.id not in self.wrapper.events: self.wrapper.events[self.id] = {}
		self.wrapper.events[self.id][eventType] = callback
	def registerPermission(self, permission=None, value=False):
		""" Used to set a default for a specific permission node. 
		
		Note: You do not need to run this function unless you want certain permission nodes to be granted by default. 
		i.e. `essentials.list` should be on by default, so players can run /list without having any permissions."""
		self.wrapper.log.debug("[%s] Registered permission '%s' with default value: %s" % (self.name, permission, value))
		if self.id not in self.wrapper.permission: self.wrapper.permission[self.id] = {}
		self.wrapper.permission[self.id][permission] = value 
	def blockForEvent(self, eventType):
		""" Blocks until the specified event is called. """
		sock = []
		self.wrapper.listeners.append(sock)
		while True:
			for event in sock:
				if event["event"] == eventType:
					payload = event["payload"][:]
					self.wrapper.listeners.remove(sock)
					return payload
				else:
					sock.remove(event)
			time.sleep(0.05)
	def callEvent(self, event, payload):
		""" Invokes the specific event. Payload is extra information relating to the event. Errors may occur if you don't specify the right payload information. """
		self.wrapper.callEvent(event, payload)
	def getPluginContext(self, id):
		""" Returns the content of another plugin with the specified ID. 
		
		i.e. api.getPluginContext(\"com.benbaptist.plugins.essentials\")"""
		if id in self.wrapper.plugins:
			return self.wrapper.plugins[id]["main"]
		else:
			raise Exception("Plugin %s does not exist!" % id)
	def getStorage(self, name, world=False):
		""" Return a storage object for storing configurations, player data, and anything else your plugin will need to remember. 
		
		Setting world=True will store the data inside the current world folder.  
		"""
		if world == False:
			return storage.Storage(name, False, root=".wrapper-data/plugins/%s" % self.id)
		else:
			return storage.Storage(name, True, root="%s/plugins/%s" % (self.minecraft.getWorldName(), self.id))
class Minecraft:
	""" This class contains functions related to in-game features directly. These methods are located at self.api.minecraft."""
	def __init__(self, wrapper):
		self.wrapper = wrapper
		
		self.blocks = items.Blocks
	def getWorldName(self):
		""" Returns the world's name. """
		return self.wrapper.server.worldName
	def isServerStarted(self):
		""" Returns a boolean if the server is fully booted or not. """
		if self.wrapper.server:
			if self.wrapper.server.status == 2: return True
		return False
	def processColorCodes(self, message):
		""" Used internally to process old-style color-codes with the & symbol, and returns a JSON chat object. """
		extras = []
		bold = False
		italic = False
		underline = False
		obfuscated = False
		strikethrough = False
		color = "white"
		current = ""; it = iter(xrange(len(message)))
		for i in it:
			char = message[i]
			if char is not "&":
				current += char
			else:
				extras.append({"text": current, "color": color, "obfuscated": obfuscated, 
					"underlined": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
				current = ""
				try: code = message[i+1]
				except: break
				if code in "abcdef0123456789":
					try: color = API.colorCodes[code]
					except: color = "white"
				if code == "k": obfuscated = True
				elif code == "l": bold = True
				elif code == "m": strikethrough = True
				elif code == "n": underline = True
				elif code == "o": italic = True
				elif code == "&": current += "&"
				elif code == "r":
					bold = False
					italic = False
					underline = False
					obfuscated = False
					strikethrough = False
					color = "white"
				it.next()
		extras.append({"text": current, "color": color, "obfuscated": obfuscated, 
			"underlined": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
		return json.dumps({"text": "", "extra": extras})
	def console(self, string):
		""" Run a command in the Minecraft server's console. """
		try:
			self.wrapper.server.run(string)
		except:
			pass
	def setBlock(self, x, y, z, tileName, dataValue=0, oldBlockHandling="replace", dataTag={}):
		""" Sets a block at the specified coordinates with the specific details. Will fail if the chunk is not loaded. """
		self.wrapper.server.run("setblock %d %d %d %s %d %s %s" % (x, y, z, tileName, dataValue, oldBlockHandling, json.dumps(dataTag).replace('"', "")))
	def giveStatusEffect(self, player, effect, duration=30, amplifier=30):
		""" Gives the specified status effect to the specified target. """
		if type(effect) == int: effectConverted = str(effect)
		else:
			try: 
				effectConverted = int(effect)
			except: # a non-number was passed, so we'll figure out what status effect it was in word form
				if effect in API.statusEffects:
					effectConverted = str(API.statusEffects[effect])
				else:
					raise Exception("Invalid status effect given!")
		if int(effectConverted) > 24 or int(effectConverted) < 1:
			raise Exception("Invalid status effect given!") 
		self.wrapper.server.run("effect %s %s %d %d" % (player, effectConverted, duration, amplifier))
	def summonEntity(self, entity, x=0, y=0, z=0, dataTag={}):
		""" Summons an entity at the specified coordinates with the specified data tag. """
		self.wrapper.server.run("summon %s %d %d %d %s" % (entity, x, y, z, json.dumps(dataTag)))
	def message(self, destination="", json_message={}):
		""" WILL BE CHANGED. Used to message some specific target. """
		self.console("tellraw %s %s" % (destination, json.dumps(json_message)))
	def broadcast(self, message="", irc=False):
		""" Broadcasts the specified message to all clients connected. message can be a JSON chat object, or a string with formatting codes using the & as a prefix.
		
		Setting irc=True will also broadcast the specified message on IRC channels that Wrapper.py is connected to. Formatting might not work properly.
		"""
		if irc:
			try: self.wrapper.irc.msgQueue.append(message)
			except: pass
		if isinstance(message, dict):
			self.wrapper.server.run("tellraw @a %s" % json.dumps(message))
		else:
			self.wrapper.server.run("tellraw @a %s" % self.processColorCodes(message))
	def teleportAllEntities(self, entity, x, y, z):
		""" Teleports all of the specific entity type to the specified coordinates. """
		self.wrapper.server.run("tp @e[type=%s] %d %d %d" % (entity, x, y, z))
#	def teleportPlayer(self):
#		pass
#	def getPlayerDat(self, name):
#		pass
	def getPlayer(self, username=""):
		""" Returns the player object of the specified logged-in player. Will raise an exception if the player is not logged in. """
		try:
			return self.wrapper.server.players[str(name)]
		except:
			raise Exception("No such player %s is logged in" % name)
	def lookupUUID(self, uuid):
		""" Returns the username from the specified UUID. If the player has never logged in before and isn't in the user cache, it will poll Mojang's API. The function will raise an exception if the UUID is invalid. """
		return self.wrapper.proxy.lookupUUID(uuid)
	def getPlayers(self): # returns a list of players
		""" Returns a list of the currently connected players. """
		return self.wrapper.server.players
	# get world-based information
	def getLevelInfo(self, worldName=False):
		""" Return an NBT object of the world's level.dat. """
		if not worldName: worldName = self.wrapper.server.worldName
		if not worldName: raise Exception("Server Uninitiated")
		f = nbt.NBTFile("%s/level.dat" % worldName, "rb")
		return f["Data"]
	def getSpawnPoint(self):
		""" Returns the spawn point of the current world. """
		return (int(str(self.getLevelInfo()["SpawnX"])), int(str(self.getLevelInfo()["SpawnY"])), int(str(self.getLevelInfo()["SpawnZ"])))
	def getTime(self):
		""" Returns the time of the world in ticks. """
		return int(str(self.getLevelInfo()["Time"]))
	#def getBlock(self, x, y, z):
#		""" UNIMPLEMENTED FUNCTION. """
#		# this function doesn't really work well yet
#		self.wrapper.server.run("testforblock %d %d %d air" % (x, y, z))
#		while True:
#			event = self.api.blockForEvent("server.consoleMessage")
#			def args(i):
#				try: return event["message"].split(" ")[i]
#				except: return ""
#			if args(3) == "The" and args(4) == "block" and args(6) == "%d,%d,%d" % (x, y, z):
#				return {"block": args(8)}
	def getServer(self):
		""" Returns the server object. """
		return self.wrapper.server
class Player:
	""" Player objects contains methods and data of a currently logged-in player. This object is destroyed upon logging off. """
	def __init__(self, username, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.permissions = wrapper.permissions
		self.name = username
		self.username = self.name # just an alias - same variable
		self.loggedIn = time.time()
		
		self.uuid = self.wrapper.getUUID(username)
		self.client = None
		for client in self.wrapper.proxy.clients:
			if client.username == username:
				self.client = client
				self.uuid = client.uuid
				break
	def __str__(self):
		return self.username
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
	def processColorCodes(self, message):
		""" Used internally to process old-style color-codes with the & symbol, and returns a JSON chat object. """
		message = message.encode('ascii', 'ignore')
		extras = []
		bold = False
		italic = False
		underline = False
		obfuscated = False
		strikethrough = False
		color = "white"
		current = ""; it = iter(xrange(len(message)))
		for i in it:
			char = message[i]
			if char is not "&":
				current += char
			else:
				extras.append({"text": current, "color": color, "obfuscated": obfuscated, 
					"underlined": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
				current = ""
				code = message[i+1]
				if code in "abcdef0123456789":
					try: color = API.colorCodes[code]
					except: color = "white"
				if code == "k": obfuscated = True
				if code == "l": bold = True
				if code == "m": strikethrough = True
				if code == "n": underline = True
				if code == "o": italic = True
				if code == "r":
					bold = False
					italic = False
					underline = False
					obfuscated = False
					strikethrough = False
					color = "white"
				if code == "&":
					current += "&"
				it.next()
		extras.append({"text": current, "color": color, "obfuscated": obfuscated, 
			"underlined": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
		return json.dumps({"text": "", "extra": extras})
	def processColorCodesOld(self, message): # Not sure if this is used anymore. Might delete.
		for i in API.colorCodes:
			message = message.replace("&" + i, "\xc2\xa7" + i)
		return message
	def getPosition(self):
		""" Returns a tuple of the player's current position. """
		return self.getClient().position
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
			self.wrapper.server.run("gamemode %d %s" % (gm, self.username))
	def setResourcePack(self, url):
		""" Sets the player's resource pack to a different URL. If the user hasn't already allowed resource packs, the user will be prompted to change to the specified resource pack. Probably broken right now. """
		self.client.send(0x3f, "string|bytearray", ("MC|RPack", url))
	def isOp(self):
		""" Returns whether or not the player is currently a server operator.  """
		operators = json.loads(open("ops.json", "r").read())
		for i in operators:
			if i["uuid"] == self.uuid or i["name"] == self.username:
				return True
		return False
	# Visual notifications
	def message(self, message=""):
		if isinstance(message, dict):
			self.wrapper.server.run("tellraw %s %s" % (self.username, json.dumps(message)))
		else:
			self.wrapper.server.run("tellraw %s %s" % (self.username, self.processColorCodes(message)))
	def actionMessage(self, message=""):
		if self.getClient().version > 10:
			self.getClient().send(0x02, "string|byte", (json.dumps({"text": self.processColorCodesOld(message)}), 2))
	def setVisualXP(self, progress, level, total):
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
		""" If the player has the specified node (either directly, or inherited from a group that the player is in), it will return the value (usually True) of the node. Otherwise, it returns False. """
		if node == None: return True
		uuid = str(self.uuid)
		if uuid in self.permissions["users"]:
			for perm in self.permissions["users"][uuid]["permissions"]:	
				if node in fnmatch.filter([node], perm):
					return self.permissions["users"][uuid]["permissions"][perm]
		if uuid not in self.permissions["users"]: return False
		for group in self.permissions["users"][uuid]["groups"]:
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
	# Cross-server commands
	def connect(self, ip, address):
		""" Upon calling, the player object will become defunct and the client will be transferred to another server (provided it has offline-mode turned on). """
		self.client.connect(ip, address)