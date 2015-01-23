NAME = "WorldEdit"
ID = "com.benbaptist.plugins.fake-worldedit"
VERSION = (0, 1)
AUTHOR = "Ben Baptist"
WEBSITE = "http://wrapper.benbaptist.com/"
SUMMARY = "Edit the world with this WorldEdit clone. (Original WorldEdit for Bukkit by sk89q)"
DESCRIPTION = """This is a clone of the WorldEdit plugin by sk89q on Bukkit for Wrapper.py.
 
It contains most of the same syntax, though not all of the commands have been implemented just yet.

It's currently limited by /fill's 32768-block limit, which is no longer really much of a problem."""
import traceback
class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log
		
		self.players = {}
	def onEnable(self):
		self.api.registerCommand("/wand", self.command_wand, "worldedit.wand")
		self.api.registerCommand("/set", self.command_set, "worldedit.set")
		self.api.registerCommand("/fill", self.command_fill, "worldedit.fill")
		self.api.registerCommand("/replace", self.command_replace, "worldedit.replace")
		self.api.registerCommand("/hfill", self.command_hollow_fill, "worldedit.hfill")
		self.api.registerCommand("/pos1", self.command_pos1, "worldedit.pos1")
		self.api.registerCommand("/pos2", self.command_pos2, "worldedit.pos2")
		self.api.registerEvent("player.place", self.action_rightclick)
		self.api.registerEvent("player.dig", self.action_leftclick)
	def onDisable(self):
		pass
	def getMemoryPlayer(self, name):
		if name not in self.players:
			self.players[name] = {"sel1": None, "sel2": None}
		return self.players[name]
	# events
	def action_leftclick(self, payload):
		player = payload["player"]
		if player.hasPermission("worldedit.pos1"):
			p = self.getMemoryPlayer(player.username)
			item = player.getHeldItem()
			if item == None: return
			if item["id"] == 271:
				p["sel1"] = payload["position"]
				player.message("&dPoint one selected.")
				return False
	def action_rightclick(self, payload):
		player = payload["player"]
		if player.hasPermission("worldedit.pos2"):
			p = self.getMemoryPlayer(player.username)
			try:
				if payload["item"]["id"] == 271:
					p["sel2"] = payload["position"]
					player.message("&dPoint two selected.")
					return False
			except:
				pass
	# commands
	def _auth(self, player): # No longer needed since we use permissions now
		return True
		#if player.isOp(): return True 
		#player.message("&cApologies, but you need to be administer to run this command. If you believe that this is a mistake, please contact the server admin or file a bug report if you are the server owner.")
		#return False
	def command_wand(self, player, args):
		if not self._auth(player): return False
		self.minecraft.console("give %s wooden_axe 1" % player.username)
		player.message("&bRight click two areas with this wooden axe tool to select a region.") 
	def command_fill(self, player, args):
		if not self._auth(player): return False
		if len(args) > 1:
			try:
				block = args[0]
				size = int(args[1]) / 2
				pos = player.getPosition()
				self.minecraft.getWorld().fill((pos[0] - size, pos[1] - size, pos[2] - size), (pos[0] + size, pos[1] + size, pos[2] + size), block)
#				self.minecraft.console("execute %s ~ ~ ~ fill ~%d ~%d ~%d ~%d ~%d ~%d %s" % (player.username, size, size, size, -size, -size, -size, block))
			except:
				print traceback.format_exc()
				player.message("&cError: <TileName> must be a string and <SquareRadius> must be an integer.")
		else:
			player.message("&cUsage: //fill <TileName> <SquareRadius>")
	def command_hollow_fill(self, player, args):
		if not self._auth(player): return False
		if len(args) > 1:
			try:
				block = args[0]
				size = int(args[1]) / 2
				pos = player.getPosition()
				self.minecraft.getWorld().fill((pos[0] - size, pos[1] - size, pos[2] - size), (pos[0] + size, pos[1] + size, pos[2] + size), block, 0, "hollow")
			except:
				print traceback.format_exc()
				player.message("&cError: <TileName> must be a string and <SquareRadius> must be an integer.")
		else:
			player.message("&cUsage: //hfill <TileName> <SquareRadius>")
	def command_replace(self, player, args):
		if not self._auth(player): return False
		if len(args) > 1:
			try:
				block1 = args[0]
				block2 = args[1]
				p = self.getMemoryPlayer(player.username)
				if p["sel1"] and p["sel2"]:
					self.minecraft.getWorld().replace(p["sel1"], p["sel2"], block1, 0, block2, 0)
				else:
					player.message("&cPlease select two regions with the wooden axe tool. Use //wand to obtain one.")
			except:
				print traceback.format_exc()
				player.message("&cSorry, something went wrong.")
		else:
			player.message("&cUsage: //replace <from-block> <to-block>")
	def command_set(self, player, args):
		if not self._auth(player): return False
		p = self.getMemoryPlayer(player.username)
		dataValue = 0
		if len(args) == 2: dataValue = int(args[1])
		if len(args) > 0:
			if p["sel1"] and p["sel2"]:
				pos = " ".join(([str(i) for i in p["sel1"]]))
				pos += " "
				pos += " ".join(([str(i) for i in p["sel2"]]))
				self.minecraft.console("fill %s %s %d" % (pos, args[0], dataValue))
			else:
				player.message("&cPlease select two regions with the wooden axe tool. Use //wand to obtain one.")
		else:
			player.message("&cUsage: //set <TileName> [dataValue]")
	def command_pos1(self, player, args):
		if not self._auth(player): return False
		p = self.getMemoryPlayer(player.username)
		if len(args) == 0:
			p["sel1"] = player.getPosition()
		player.message({"text": "Set position 1 to %s." % (str(player.getPosition())), "color": "light_purple"})
	def command_pos2(self, player, args):
		if not self._auth(player): return False
		p = self.getMemoryPlayer(player.username)
		if len(args) == 0:
			p["sel2"] = player.getPosition()
		player.message({"text": "Set position 2 to %s." % (str(player.getPosition())), "color": "light_purple"})