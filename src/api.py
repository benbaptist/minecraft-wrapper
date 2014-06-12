import json, time, StringIO
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
		"&r": "\xc2\xa7r",
		"&k": "\xc2\xa7k", # obfuscated
		"&l": "\xc2\xa7l", # bold
		"&m": "\xc2\xa7m", # strikethrough
		"&n": "\xc2\xa7n", # underline
		"&o": "\xc2\xa7o", # italic
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
class Minecraft:
	def __init__(self, wrapper):
		self.wrapper = wrapper
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
					"underline": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
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
				it.next()
		extras.append({"text": current, "color": color, "obfuscated": obfuscated, 
			"underline": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
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
	def broadcast(self, message=""):
		if isinstance(message, dict):
			self.wrapper.server.run("tellraw @a %s" % json.dumps(message))
		else:
			self.wrapper.server.run("tellraw @a %s" % self.processColorCodes(message))
	def changeResourcePack(self, name, url):
		if self.getPlayer(name).client is False:
			raise Exception("User %s is not connected via proxy" % name)
		else:
			self.getPlayer(name).client.send("varint|string|short|bytearray", (0x3f, "MC|RPack", len(url), url), self.getPlayer(name).client.client) 
	def teleportAllEntities(self, entity, x, y, z):
		self.wrapper.server.run("tp @e[type=%s] %d %d %d" % (entity, x, y, z))
	def teleportPlayer(self):
		pass
	def getPlayerDat(self, name):
		pass
	def getPlayer(self, name=""):
		try:
			return self.wrapper.server.players[name]
		except:
			raise Exception("No such player %s is logged in" % name)
	def getLevelInfo(self, worldName=""):
		pass
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
class Player:
	def __init__(self, username, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.name = username
		self.username = self.name # just an alias - same variable
		self.loggedIn = time.time()
		
		self.uuid = self.wrapper.getUUID(username)
		for client in self.wrapper.proxy.clients:
			if client.username == username:
				self.client = client
				break
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
					"underline": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
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
			"underline": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
		return json.dumps({"text": "", "extra": extras})
	def getPosition(self):
		return self.client.position
	def getGamemode(self):
		return self.client.gamemode
	def setGamemode(self, gm=0):
		if gm in (0, 1, 2, 3):
			self.client.gamemode = gm
			self.wrapper.server.run("gamemode %s %d" % (self.username, gm))
	def setResourcePack(self, url):
		print self.client.send("varint|string|short|bytearray", (0x3f, "MC|RPack", len(url), url), self.client.client)
	def isOp(self):
		operators = json.loads(open("ops.json", "r").read())
		for i in operators:
			if i["uuid"] == self.uuid or i["name"] == self.username:
				return True
		return False
	def message(self, message=""):
		if isinstance(message, dict):
			self.wrapper.server.run("tellraw %s %s" % (self.username, json.dumps(message)))
		else:
			self.wrapper.server.run("tellraw %s %s" % (self.username, self.processColorCodes(message)))
