import json, time, StringIO, nbt, items
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
	def __init__(self, wrapper, name=""):
		self.wrapper = wrapper
		self.name = name
		self.minecraft = Minecraft(wrapper)
		self.server = wrapper.server
	def registerCommand(self, name, callback):
		self.wrapper.log.debug("[%s] Registered command '%s'" % (self.name, name))
		if self.name not in self.wrapper.commands: self.wrapper.commands[self.name] = {}
		self.wrapper.commands[self.name][name] = callback
	def registerEvent(self, eventType, callback):
		self.wrapper.log.debug("[%s] Registered event '%s'" % (self.name, eventType))
		if self.name not in self.wrapper.events: self.wrapper.events[self.name] = {}
		self.wrapper.events[self.name][eventType] = callback
	def blockForEvent(self, eventType):
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
		self.wrapper.callEvent(event, payload)
	def getPluginContext(self, pluginID):
		if pluginID in self.wrapper.plugins:
			return self.wrapper.plugins[pluginID]
		else:
			raise Exception("Plugin %s does not exist!")
class Minecraft:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		
		self.blocks = items.Blocks
	def getWorldName(self):
		return self.wrapper.server.worldName
	def isServerStarted(self):
		if self.wrapper.server:
			if self.wrapper.server.status == 2: return True
		return False
	def processColorCodes(self, message):
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
		try:
			self.wrapper.server.run(string)
		except:
			pass
	def setBlock(self, x, y, z, tileName, dataValue=0, oldBlockHandling="replace", dataTag={}):
		self.wrapper.server.run("setblock %d %d %d %s %d %s %s" % (x, y, z, tileName, dataValue, oldBlockHandling, json.dumps(dataTag).replace('"', "")))
	def giveStatusEffect(self, player, effect, duration=30, amplifier=30):
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
		self.wrapper.server.run("summon %s %d %d %d %s" % (entity, x, y, z, json.dumps(dataTag)))
	def message(self, destination="", json_message={}):
		self.console("tellraw %s %s" % (destination, json.dumps(json_message)))
	def broadcast(self, message="", irc=True):
		if isinstance(message, dict):
			self.wrapper.server.run("tellraw @a %s" % json.dumps(message))
		else:
			self.wrapper.server.run("tellraw @a %s" % self.processColorCodes(message))
	def changeResourcePack(self, name, url):
		if self.getPlayer(name).client is False:
			raise Exception("User %s is not connected via proxy" % name)
		else:
			self.getPlayer(name).client.send(0x3f, "string|bytearray", ("MC|RPack", url))
	def teleportAllEntities(self, entity, x, y, z):
		self.wrapper.server.run("tp @e[type=%s] %d %d %d" % (entity, x, y, z))
	def teleportPlayer(self):
		pass
	def getPlayerDat(self, name):
		pass
	def getPlayer(self, name=""):
		try:
			return self.wrapper.server.players[str(name)]
		except:
			raise Exception("No such player %s is logged in" % name)
	def getPlayers(self): # returns a list of players
		return self.wrapper.server.players
	# get world-based information
	def getLevelInfo(self, worldName=False):
		if not worldName: worldName = self.wrapper.server.worldName
		if not worldName: raise Exception("Server Uninitiated")
		f = nbt.NBTFile("%s/level.dat" % worldName, "rb")
		return f["Data"]
	def getSpawnPoint(self):
		return (int(str(self.getLevelInfo()["SpawnX"])), int(str(self.getLevelInfo()["SpawnY"])), int(str(self.getLevelInfo()["SpawnZ"])))
	def getTime(self):
		return int(str(self.getLevelInfo()["Time"]))
	def getBlock(self, x, y, z):
		# this function doesn't really work well yet
		self.wrapper.server.run("testforblock %d %d %d air" % (x, y, z))
		while True:
			event = self.api.blockForEvent("server.consoleMessage")
			def args(i):
				try: return event["message"].split(" ")[i]
				except: return ""
			if args(3) == "The" and args(4) == "block" and args(6) == "%d,%d,%d" % (x, y, z):
				return {"block": args(8)}
	def getServer(self):
		return self.wrapper.server
class Player:
	def __init__(self, username, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.name = username
		self.username = self.name # just an alias - same variable
		self.loggedIn = time.time()
		
		self.uuid = self.wrapper.getUUID(username)
		self.client = None
		for client in self.wrapper.proxy.clients:
			if client.username == username:
				self.client = client
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
	def processColorCodesOld(self, message):
		for i in API.colorCodes:
			message = message.replace("&" + i, "\xc2\xa7" + i)
		return message
	def getPosition(self):
		return self.getClient().position
	def getGamemode(self):
		return self.getClient().gamemode
	def getDimension(self):
		return self.getClient().dimension
	def setGamemode(self, gm=0):
		if gm in (0, 1, 2, 3):
			self.client.gamemode = gm
			self.wrapper.server.run("gamemode %d %s" % (gm, self.username))
	def setResourcePack(self, url):
		self.client.send(0x3f, "string|bytearray", ("MC|RPack", url))
	def isOp(self):
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
	# Abilities & visual
	def setPlayerFlying(self, fly): # UNFINISHED FUNCTION
		if fly:
			self.getClient().send(0x13, "byte|float|float", (255, 1, 1))
		else:
			self.getClient().send(0x13, "byte|float|float", (0, 1, 1))
	# Inventory-related actions
	def getItemInSlot(self, slot):
		return self.getClient().inventory[slot]
	def getHeldItem(self):
		return self.getClient().inventory[36 + self.getClient().slot]