import json, os, traceback
NAME = "home"
AUTHOR = "Cougar"
ID = "net.version6.minecraft.plugins.home"
SUMMARY = "Home commands"
DESCRIPTION = """Home plugin."""
WEBSITE = ""
VERSION = (0, 2)

class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log

	def onEnable(self):
		self.data = self.api.getStorage("home", True)

		self.api.registerHelp("Home", "Commands from the Home plugin", [
			("/sethome", "Save curremt position as home", None),
			("/home", "Teleports you to your home set by /sethome", None),
		])

		self.api.registerCommand("sethome", self.sethome)
		self.api.registerCommand("home", self.home)

	def onDisable(self):
		self.data.save()

	def sethome(self, player, args):
		if not player.getDimension() == 0:
			player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
			return
		player.message({"text": "Home location set. Use /home to return here", "color": "green"})
		self.data[player.username] = player.getPosition()

	def home(self, player, args):
		if not player.getDimension() == 0:
			player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
			return
		username = player.username
		if username not in self.data:
			player.message({"text": "Home is not set. Use /sethome.", "color": "red"})
			return
		player.message({"text": "Teleporting you to your home.", "color": "green"})
		self.api.minecraft.console("tp %s %d %d %d" % (username, self.data[username][0], self.data[username][1], self.data[username][2]))
