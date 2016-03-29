import json, nbt, items, os, uuid, sys
reload(sys)
class Minecraft:
	""" This class contains functions related to in-game features directly. These methods are located at self.api.minecraft. """
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.log = wrapper.log
		self._encoding=wrapper.config["General"]["encoding"]
		sys.setdefaultencoding(self._encoding)
		self.blocks = items.Blocks
	def isServerStarted(self):
		""" Returns a boolean if the server is fully booted or not. """
		if self.getServer():
			if self.getServer().state == 2: return True
		return False
	def getTimeofDay(self, format=0):
		# 0 = ticks, 1 = Military, else = civilian AM/PM, return -1 if no one on or server not started
		if self.isServerStarted() is True:
			servertimeofday = self.getServer().timeofday
			ticktime = servertimeofday % 24000
			if format == 0 or ticktime == -1: return ticktime
			mth = (ticktime + 6000)/10
			if mth > 2399:
				mth =- 2400
			mins = int(float(mth % 100) * float(.6))
			mth = (mth / 100)
			if format == 1: return "%02d:%02d" % (mth, mins)
			if mth > 12:
				ampm = "PM"
				cth = mth - 12
			else:
				ampm = "AM"
				cth = mth
			return "%d:%02d %s" % (cth, mins, ampm)
		return -1

	def getAllPlayers(self):
		""" Returns a dict containing all players ever connected to the server """
		if self.wrapper.isOnlineMode(): online = True
		else: online = False
		players = {}
		for uuidf in os.listdir("wrapper-data/players"):
			puuid = uuidf.rsplit(".", 1)[0]
			if puuid in ("None", "False"):
				os.remove("wrapper-data/players/" + uuidf)  # remove any old bad objects
				continue
			username = self.wrapper.getUsername(puuid)
			if type(username) != str: continue
			if online:
				if str(self.wrapper.UUIDFromName(username)) == puuid: continue
			with open("wrapper-data/players/" + uuidf) as f:
				data = f.read()
			try:
				players[uuid] = json.loads(data,self._encoding)
			except:
				self.log.error("Failed to load player data '%s'" % puuid)
				self.log.getTraceback()
				os.remove("wrapper-data/players/" + uuidf)
		return players
	def console(self, string):
		""" Run a command in the Minecraft server's console. """
		try:
			self.getServer().console(string)
		except:
			pass
	def setBlock(self, x, y, z, tileName, dataValue=0, oldBlockHandling="replace", dataTag={}):
		""" Sets a block at the specified coordinates with the specific details. Will fail if the chunk is not loaded. """
		self.console("setblock %d %d %d %s %d %s %s" % (x, y, z, tileName, dataValue, oldBlockHandling, json.dumps(dataTag,self._encoding).replace('"', "")))
	def giveStatusEffect(self, player, effect, duration=30, amplifier=30):
		""" Gives the specified status effect to the specified target. """
		if type(effect) == int: effectConverted = str(effect)
		else:
			try: 
				effectConverted = int(effect)
			except: # a non-number was passed, so we'll figure out what status effect it was in word form
				if effect in self.wrapper.api.statusEffects:
					effectConverted = str(self.wrapper.api.statusEffects[effect])
				else:
					raise Exception("Invalid status effect given!")
		if int(effectConverted) > 24 or int(effectConverted) < 1:
			raise Exception("Invalid status effect given!") 
		self.console("effect %s %s %d %d" % (player, effectConverted, duration, amplifier))
	def summonEntity(self, entity, x=0, y=0, z=0, dataTag={}):
		""" Summons an entity at the specified coordinates with the specified data tag. """
		self.console("summon %s %d %d %d %s" % (entity, x, y, z, json.dumps(dataTag,self._encoding)))
	def message(self, destination="", json_message={}):
		""" **THIS METHOD WILL BE CHANGED.** Used to message some specific target. """
		self.console("tellraw %s %s" % (destination, json.dumps(json_message,self._encoding)))
	def broadcast(self, message="", irc=False):
		""" Broadcasts the specified message to all clients connected. message can be a JSON chat object, or a string with formatting codes using the & as a prefix.
		
		Setting irc=True will also broadcast the specified message on IRC channels that Wrapper.py is connected to. Formatting might not work properly.
		"""
		if irc:
			try: self.wrapper.irc.msgQueue.append(message)
			except: pass
		try: self.wrapper.server.broadcast(message)
		except: pass
	def teleportAllEntities(self, entity, x, y, z):
		""" Teleports all of the specific entity type to the specified coordinates. """
		self.console("tp @e[type=%s] %d %d %d" % (entity, x, y, z))
#	def teleportPlayer(self):
#		pass
#	def getPlayerDat(self, name):
#		pass
	def getPlayer(self, username=""):
		""" Returns the player object of the specified logged-in player. Will raise an exception if the player is not logged in. """
		try:
			return self.wrapper.server.players[str(username)]
		except:
			raise Exception("No such player %s is logged in" % username)
	def lookupUUID(self, uuid):
		""" Returns the username from the specified UUID. If the player has never logged in before and isn't in the user cache, it will poll Mojang's API. The function will raise an exception if the UUID is invalid. """
		return self.wrapper.lookupUsernamebyUUID(str(uuid))
	def getPlayers(self): # returns a list of players
		""" Returns a list of the currently connected players. """
		return self.getServer().players
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
#		self.console("testforblock %d %d %d air" % (x, y, z))
#		while True:
#			event = self.api.blockForEvent("server.consoleMessage")
#			def args(i):
#				try: return event["message"].split(" ")[i]
#				except: return ""
#			if args(3) == "The" and args(4) == "block" and args(6) == "%d,%d,%d" % (x, y, z):
#				return {"block": args(8)}
	def getServer(self):
		""" Returns the server context. """
		return self.wrapper.server
	def getWorld(self):
		""" Returns the world context. """
		return self.getServer().world 
	def getWorldName(self):
		""" Returns the world's name. """
		return self.getServer().worldName
