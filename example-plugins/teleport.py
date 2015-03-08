import json, os, traceback, time
NAME = "teleport"
AUTHOR = "C0ugar"
ID = "net.version6.minecraft.plugins.teleport"
SUMMARY = "Teleport commands, similar with commands in Essentials for Bukkit."
DESCRIPTION = """Teleport plugin."""
WEBSITE = ""
VERSION = (0, 2)

TIMEOUT = 120

class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log

	def onEnable(self):
		self.data = {}

		self.api.registerHelp("Teleport", "Commands from the Teleport plugin", [
			("/tpa", "Request to teleport to the specified player.", "teleport"),
			("/tpahere", "Request that the specified player teleport to you.", "teleport"),
			("/tpaccept", "Accept a teleport request.", None),
			("/tpdeny", "Reject a teleport request.", None),
		])

		self.api.registerCommand("tpa", self.tpa, "teleport")
		self.api.registerCommand("tpahere", self.tpahere, "teleport")
		self.api.registerCommand("tpaccept", self.tpaccept)
		self.api.registerCommand("tpdeny", self.tpdeny)
#		self.api.registerPermission("teleport", True) # default permission

	def onDisable(self):
		pass

	def tpa(self, player, args):
		''' Request teleport to another player position '''
		self._doTeleportRequest(player, "tpa", args)

	def tpahere(self, player, args):
		''' Request another player to teleport your position '''
		self._doTeleportRequest(player, "tpahere", args)

	def tpaccept(self, player, args):
		''' Accept teleport request '''
		otherPlayer = self._doTestTeleportReply(player)
		if otherPlayer:
			player.message({"text": "Teleport request accepted.", "color": "yellow"})
			otherPlayer.message({"text": "%s accepted your teleport request." % player.username, "color": "yellow"})
			if  self.data[player.username]['direction'] == 'tpa':
				who = otherPlayer
				where = player
			else:
				who = player
				where = otherPlayer
			who.message({"text": "Teleporting to %s." % where.username, "color": "yellow"})
			pos = where.getPosition()
			self.minecraft.console("tp %s %d %d %d" % (who.username, pos[0], pos[1], pos[2]))
		if player.username in self.data:
			del self.data[player.username]

	def tpdeny(self, player, args):
		''' Reject teleport request '''
		otherPlayer = self._doTestTeleportReply(player)
		if otherPlayer:
			player.message({"text": "Teleport request denied.", "color": "yellow"})
			otherPlayer.message({"text": "%s denied your teleport request." % player.username, "color": "yellow"})
		if player.username in self.data:
			del self.data[player.username]

	def _doTeleportRequest(self, player, cmd, args):
		''' Essential tests before teleport request '''
		if len(args) == 0:
			player.message({"text": "Use /%s <playername>" % cmd, "color": "gray"})
			return
		if not player.getDimension() == 0:
			player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
			return
		try:
			otherPlayer = self.minecraft.getPlayer(args[0])
		except:
			player.message({"text": "Error: Player not found.", "color": "red"})
			return
		if player == otherPlayer:
			player.message({"text": "Error: Can't play alone", "color": "red"})
			return
		if not otherPlayer.getDimension() == 0:
			player.message({"text": "Sorry, but %s is not in this world." % otherPlayer.username, "color": "red"})
			return
		if otherPlayer.username in self.data:
			if self.data[otherPlayer.username]['requester'] == player.username and self.data[otherPlayer.username]['direction'] == cmd:
				player.message({"text": "Request is already sent to %s" % otherPlayer.username, "color": "red"})
				return
		if cmd == "tpa":
			otherPlayer.message({"text": "%s has requested to teleport to you." % player.username, "color": "gold"})
		else:
			otherPlayer.message({"text": "%s has requested that you teleport to them." % player.username, "color": "gold"})
		otherPlayer.message({"text": "To teleport, type /tpaccept.", "color": "gold"})
		otherPlayer.message({"text": "To deny this request, type /tpdeny.", "color": "gold"})
		otherPlayer.message({"text": "This request will timeout after %d deconds." % TIMEOUT, "color": "gold"})
		player.message({"text": "Request sent to %s" % otherPlayer.username, "color": "gold"})
		self.data[otherPlayer.username] = {}
		self.data[otherPlayer.username]['time'] = time.time()
		self.data[otherPlayer.username]['requester'] = player.username
		self.data[otherPlayer.username]['direction'] = cmd;

	def _doTestTeleportReply(self, player):
		''' Essential tests before teleport reply '''
		if player.username not in self.data:
			player.message({"text": "Error: You do not have a pending request", "color": "red"})
			return None
		if not player.getDimension() == 0:
			player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
			return None
		if self.data[player.username]['time'] < (time.time() - TIMEOUT):
			player.message({"text": "Error: Teleport request has timed out.", "color": "red"})
			return None
		try:
			otherPlayer = self.minecraft.getPlayer(self.data[player.username]['requester'])
		except:
			player.message({"text": "Error: You do not have a pending request", "color": "red"})
			return None
		if not otherPlayer.getDimension() == 0:
			player.message({"text": "Sorry, but %s is not in this world any more." % otherPlayer.username, "color": "red"})
			return None
		return otherPlayer
