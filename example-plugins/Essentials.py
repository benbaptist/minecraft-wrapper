import json, os, random, traceback
NAME = "Essentials"
AUTHOR = "Ben Baptist"
ID = "com.benbaptist.plugins.essentials"
SUMMARY = "Essential commands and other features."
DESCRIPTION = """Essentials plugin for Wrapper.py, loosely based off of Essentials for Bukkit."""
WEBSITE = ""
VERSION = (1, 1)
BLONKS = False
class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log
		self.powertool = []
#		if "warps" not in self.data: self.data["warps"] = {}
	def onEnable(self):
		self.data = self.api.getStorage("worldly", True)
		
		# HELP
		self.api.registerHelp("Essentials", "Commands from the Essentials plugin", [
			("/gm [gamemode]", "Switch your personal gamemode. If no arguments are provided, it'll toggle you between survival and creative quickly. 'gamemode' can be either the name or the number.", "essentials.gm"),
			("/heal", "Heals the health and hunger of the player.", "essentials.heal"),
			("/i <TileName>[:Data] [Count]", "Gives the player the requested item and puts it directly in their inventory.", "essentials.give", "essentials.give"),
			("/warp [warp]", "Teleports the player to the specified warp. If no warp is specified, it'll list the available warps.", "essentials.warp"),
			("/setwarp <warp>", "Sets the specified warp at the current location of the player.", "essentials.setwarp"),
			("/powertool", "Toggles powertool mode. In powertool mode, the player can destroy blocks instantly without being in creative.", "essentials.powertool"),
			("/motd", "Display the MOTD.", "essentials.motd"),
			("/setmotd <MOTD ...>", "Set the MOTD.", "essentials.setmotd"),
			("/spawn", "Teleports you to spawn.", "essentials.spawn"),
			("/whois", "Displays information about you. Mostly for debugging purposes or weird admin stuff. Eventually, this command will show info about other players.", "essentials.whois"),
			("/sudo <username> <command ...>", "Runs a command as the specified user.", "essentials.sudo")
		])
		
		# DEFAULTS
		if "warps" not in self.data: self.data["warps"] = {}
		
		# api.registerPermission() is used to set these permissions to ON by default, rather than off
		self.api.registerPermission("essentials.warp", True) # I need to do essentials.listwarps too 
		self.api.registerPermission("essentials.motd", True)
		self.api.registerPermission("essentials.getpos", True)
		
		self.api.registerCommand("setwarp", self.setwarp, "essentials.setwarp")
		self.api.registerCommand("warp", self.warp, "essentials.warp")
		self.api.registerCommand("motd", self.motd, "essentials.motd")
		self.api.registerCommand("setmotd", self.setmotd, "essentials.setmotd")
		self.api.registerCommand("echo", self.echo, "essentials.echo")
		self.api.registerCommand("blowblowblow", self.blowblowblow)
		self.api.registerCommand("killall", self.killall, "essentials.killall")
		self.api.registerCommand("gm", self.gm, "essentials.gm")
#		self.api.registerCommand("time", self.time)
		self.api.registerCommand("getpos", self.getpos, "essentials.getpos")
		self.api.registerCommand("heal", self.heal, "essentials.heal")
		self.api.registerCommand("echoaction", self.echoaction, "essentials.echoaction")
		self.api.registerCommand("powertool", self._powertool, "essentials.powertool")
		self.api.registerCommand("i", self.i, "essentials.give")
		self.api.registerCommand("spawn", self.spawn, "essentials.spawn")
		self.api.registerCommand("block", self.block, "essentials.block")
		self.api.registerCommand("whois", self.whois, "essentials.whois")
		self.api.registerCommand("sudo", self.sudo, "essentials.sudo")
		self.api.registerEvent("player.login", self.login)
		self.api.registerEvent("player.dig", self.click)
	def onDisable(self):
		self.data.save()
	def deny(self, player):
		player.message({"text": "Permission denied to use this command.", "color": "red"})
	def getMOTD(self, name):
		return self.data["motd"]["msg"].replace("[[name]]", name)
	# events
	def login(self, payload):
		self.motd(payload["player"], None)
	def click(self, payload):
		player = payload["player"]
		if player.username in self.powertool:
			x, y, z = payload["position"]
			self.minecraft.console("setblock %d %d %d air 0 destroy" % (x, y, z))
	# commands
	def echo(self, player, args):
		if player.isOp():
			player.message(" ".join(args))
	def echoaction(self, player, args):
		if player.isOp():
			player.actionMessage(" ".join(args))
	def _powertool(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		if player.username in self.powertool:
			self.powertool.remove(player.username)
			player.message("&cPowertool disabled.")
		else:
			self.powertool.append(player.username)
			player.message("&aPowertool enabled!")
	def motd(self, player, args):
		if "motd" not in self.data:
			self.data["motd"] = {"msg": "&aWelcome to the server, [[name]]!", "enabled": True}
		player.message(self.getMOTD(player.username))
	def setmotd(self, player, args):
		if player.isOp():
			if len(args) > 0:
				self.data["motd"]["msg"] = " ".join(args)
				player.message("&aSet MOTD to message: &r%s" % " ".join(args))
		else:
			self.deny(player)
	def setwarp(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		if len(args) == 1:
			warp = args[0]
			player.message({"text": "Created warp '%s'." % warp, "color": "green"})
			self.data["warps"][warp] = player.getPosition()
		else:
			player.message({"text": "Usage: /setwarp [name]", "color": "red"})
	def blowblowblow(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		# Totally not a secret op-only command that can only be executed if BLONKS is set to True :P
		if BLONKS:
			for i in range(25):
				self.api.minecraft.console("execute %s ~ ~ ~ summon PrimedTnt ~%d ~ ~%d" % (player.name, random.randrange(-10, 10), random.randrange(-10, 10)))
		else:
			player.message("&cThis command never existed. Doesn't exist. I mean... what?")
	def warp(self, player, args):
		if len(args) == 1:
			warp = args[0]
			if warp not in self.data["warps"]:
				player.message({"text": "Warp '%s' doesn't exist." % warp, "color": "red"}) 
				return False
			player.message({"text": "Teleporting you to '%s'." % warp, "color": "green"})
			self.api.minecraft.console("tp %s %d %d %d" % (player.username, self.data["warps"][warp][0], self.data["warps"][warp][1], self.data["warps"][warp][2]))
		else:
			player.message({"text": "List of warps: %s" % ", ".join(self.data["warps"]), "color": "red"})
	def killall(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		self.api.minecraft.console("execute %s ~ ~ ~ kill @e[type=!Player,r=30]" % player.name)
		player.message({"text":"Killed all entities within a 30-block radius.", "color": "red"})
	def gm(self, player, args):
		gamemodes = {0: "survival", 1: "creative", 2: "adventure", 3: "spectator"}
		if not player.isOp():
			self.deny(player)
			return False
		if len(args) > 0:
			if args[0] in ("0", "1", "2", "3"):
				player.setGamemode(int(args[0]))
			elif args[0].lower() in ("survival", "creative", "adventure", "spectator"):
				for i in gamemodes:
					if gamemodes[i] == args[0].lower(): player.setGamemode(i)
		else:
			if player.getGamemode() in (2, 3):
				player.setGamemode(1)
			elif player.getGamemode() == 1:
				player.setGamemode(0)
			elif player.getGamemode() == 0:
				player.setGamemode(1)
		player.message({"text":"Changed gamemode to %s." % gamemodes[player.getGamemode()], "color": "green"})
	def time(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		if len(args) == 0:
			player.message("&aThe time is &70:00AM.")
	def getpos(self, player, args):
		if not player.isOp() and len(args) == 1:
			self.deny(player)
			return False
		if len(args) == 1:
			otherPlayer = self.minecraft.getPlayer(args[0])
			player.message({"text": "%s's position: %s" % (args[0], str(otherPlayer.getPosition())), "color": "yellow"})
		else:
			player.message({"text": "Your position: %s" % str(player.getPosition()), "color": "yellow"})
	def heal(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		player.message({"text": "Delicious health!", "color": "yellow"})
		self.api.minecraft.console("effect %s 6 20 20" % player.name)
		self.api.minecraft.console("effect %s 23 20 20" % player.name)
	def i(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		if len(args) > 0:
			tilename = args[0]
			damage = 0
			count = 64
			tags = "{}"
			if len(args) > 1: 
				try: count = int(args[1])
				except: count = 64
			if len(args) > 2: 
				try: tags = " ".join(args[2:])
				except: 
					player.message("&cERROR: JSON Error")
					return
			if not tilename.find(":") == -1:
				damage = tilename[tilename.find(":")+1:]
				try:
					damage = int(damage)
				except:
					player.message("&cERROR: Damage value is not an integer.")
					return
				tilename = tilename[0:tilename.find(":")]
			try:
				tilename = int(tilename)
				if tilename in self.minecraft.blocks:
					tilename = self.minecraft.blocks[tilename]["TileName"]
				else:
					player.message("&cERROR: Invalid ID %d" % tilename)
					return
			except: 
				print traceback.format_exc()
			self.minecraft.console("give %s %s %d %d %s" % (player.name, tilename, count, damage, tags))
		else:
			player.message("&cUsage: /i <TileName>[:data] [amount] [dataTag]")
	def spawn(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		spawn = self.minecraft.getSpawnPoint()
		player.message("&aTeleporting you to spawn...")
		self.minecraft.console("tp %s %d %d %d" % (player.username, spawn[0], spawn[1], spawn[2]))
	def block(self, player, args):
		if not player.isOp():
			self.deny(player)
			return False
		if len(args) == 3:
			player.message(str(self.minecraft.getServer().world.getBlock((int(args[0]), int(args[1]), int(args[2])))))
		else:
			player.message("&cUsage: /block <x> <y> <z>")
	def whois(self, player, args):
		player.message("&7You are %s. You are in dimension %d, in gamemode %d and are currently located at %s." % (player.username, player.getDimension(), player.getGamemode(), player.getPosition()))
	def sudo(self, player, args):
		if len(args) > 1:
			self.minecraft.getPlayer(args[0]).execute(" ".join(args[1:]))
		else:
			player.message("&cUsage: /sudo <username> <command ...>")