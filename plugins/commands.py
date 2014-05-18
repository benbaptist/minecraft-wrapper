import threading, time, random

operators = ["benbaptist"]

class Main:
	def __init__(self, api, log):
		self.api = api
		self.log = log
		self.ops = operators
		self.gamemodeTrack = {}
		
		self.version = (0, 1)
		self.description = "Adds extra commands to Wrapper.py! All commands are executed with an exclamation mark."
	def onEnable(self):
		self.log.info("ExtraCommands")
		self.api.registerEvent("player.message", self.getMsg)
	def onDisable(self):
		pass
	def getMsg(self, payload):
		def args(i): 
			try: return payload["message"][1:].split(" ")[i]
			except: return ""
		def argsAfter(i): 
			try: return " ".join(payload["message"][1:].split(" ")[i:])
			except: return ""
		if payload["message"][0] == "`":
			player = payload["player"]
			if player not in self.ops:
				print (player, self.ops)
				self.api.minecraft.console("tellraw %s {text:'You must be an operator to run these commands!',color:red}" % player)
				return ""
			command = argsAfter(0)
			self.api.minecraft.console("execute %s ~ ~ ~ %s" % (player, command))
		if payload["message"][0] == "!":
			command = args(0)
			player = payload["player"]
			if command == "clear":
				self.api.minecraft.console("clear %s" % player)
			if command == "spawn":
				self.api.minecraft.console('tp %s 10 62 310' % player)
		if payload["message"][0] == "!":
			command = args(0)
			player = payload["player"]
			if player not in self.ops:
				print (player, self.ops)
				self.api.minecraft.console("tellraw %s {text:'You must be an operator to run these commands!',color:red}" % player)
				return ""
			if command == "op":
				self.api.minecraft.console("op %s" % player)
			if command == "tp":
				self.api.minecraft.console("execute %s ~ ~ ~ tp %s" % (player, argsAfter(1)))
			if command == "ban":
				self.api.minecraft.console("execute %s ~ ~ ~ ban %s" % (player, argsAfter(1)))
			if command == "kick":
				self.api.minecraft.console("execute %s ~ ~ ~ kick %s" % (player, argsAfter(1)))
			if command == "ben":
				self.api.minecraft.console("tellraw @a {text:'Ben Baptist is my creator. All hail.', color:blue}")
			if command == "murdermobs":
				self.api.minecraft.console("kill @e[type=Zombie]")
				self.api.minecraft.console("kill @e[type=Spider]")
				self.api.minecraft.console("kill @e[type=Skeleton]")
				self.api.minecraft.console("kill @e[type=Creeper]")
			if command == "heal":
				self.api.minecraft.console("effect %s 6 1 20" % player)
				self.api.minecraft.console("effect %s 23 1 20" % player)
			if command == "ping":
				self.api.minecraft.console("tellraw %s {text:Pong,color:red,bold:true,italic:true,underlined:true}" % player)
			if command == "mobrain":
				self.api.minecraft.broadcast("&5Pitter patter, pitter patter!")
				for i in range(100):
					self.api.minecraft.console("execute @a ~ ~ ~ summon Skeleton ~%d ~%d ~%d {HealF:0.0}" % (random.randrange(-4, 4), random.randrange(2, 30), random.randrange(-4, 4)))
					self.api.minecraft.console("execute @a ~ ~ ~ summon Zombie ~%d ~%d ~%d {HealF:0.0}" % (random.randrange(-4, 4), random.randrange(2, 30), random.randrange(-4, 4)))
					self.api.minecraft.console("execute @a ~ ~ ~ summon Creeper ~%d ~%d ~%d {HealF:0.0,powered:1}" % (random.randrange(-4, 4), random.randrange(2, 30), random.randrange(-4, 4)))
			if command == "arrowrain":
				self.api.minecraft.broadcast("&4Arrow rain! Some stay dry and and others feel arrows")
				for i in range(100):
					self.api.minecraft.console("execute @a ~ ~ ~ summon Arrow ~%d ~%d ~%d" % (random.randrange(-10, 10), random.randrange(2, 30), random.randrange(-10, 10)))
				time.sleep(2)
				self.api.minecraft.console("kill @e[type=Arrow]")
			if command == "link":
				link = args(1)
				self.api.minecraft.console("tellraw @a {text:'%s', color:aqua, underlined:true, clickEvent:{action:open_url,value:'%s'}}" % (link, link))
			if command == "god" or command == "gosh":
				if len(args(1)) > 0: player = args(1)
				self.api.minecraft.console("effect %s 6 999999 255" % player)
				self.api.minecraft.console("effect %s 10 999999 20" % player)
				self.api.minecraft.console("effect %s 23 999999 255" % player)
			if command == "ungod" or command == "ungosh":
				if len(args(1)) > 0: player = args(1)
				self.api.minecraft.console("effect %s 6 0" % player)
				self.api.minecraft.console("effect %s 11 0" % player)
			if command == "kill":
				if len(args(1)) > 0: player = args(1)
				self.api.minecraft.console('kill %s' % player)
			if command == "reloadplugins":
				self.api.wrapper.reloadPlugins()
			if command == "gm":
				if player not in self.gamemodeTrack:
					self.gamemodeTrack[player] = False # survival
				self.gamemodeTrack[player] = not self.gamemodeTrack[player]
				if self.gamemodeTrack[player]:
					gm = 1
					self.api.minecraft.console("tellraw %s {text:'You are now in creative mode!',color:green}" % player)
				else:
					gm = 0
					self.api.minecraft.console("tellraw %s {text:'You are now in survival mode!',color:green}" % player)
				self.api.minecraft.console("gamemode %d %s" % (gm, player))