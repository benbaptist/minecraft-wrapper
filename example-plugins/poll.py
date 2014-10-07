# -- Poll Plugin --
NAME = "Poll"
ID = "com.benbaptist.plugins.vote"
SUMMARY = "Voting plugin for Wrapper.py!"
VERSION = (1, 0)
DESCRIPTION = """I need to make this plugin use more modern Wrapper.py APIs - currently it is a bad example.

For one, it uses the old player.message event to capture 
fake !commands instead of using .registerCommand() for real /slash commands.
It's also not using the new storage API for making per-world and global 
storage of JSON information easy.

Plus, it's not really well written overall. It could be cleaner, probably.
"""

import time, json, os
class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log
	def onEnable(self):
		self.api.registerEvent("player.message", self.command)
		self.api.registerEvent("player.join", self.join)
		
		self.api.registerEvent("irc.channelMessage", self.IRCCommand)
		
		self.loadPolls()
	def onDisable(self):
		self.save()
	def loadPolls(self):
		if not os.path.exists("poll_plugin.json"):
			with open("poll_plugin.json", "w") as f:
				f.write("{}")
		f = open("poll_plugin.json", "r")
		self.data = f.read()
		try:
			self.data = json.loads(self.data)
		except:
			self.data = {}
		f.close()
		
		if "polls" not in self.data:
			self.data["polls"] = {}
		if "broadcast_new_polls" not in self.data:
			self.data["broadcast_new_polls"] = True
		if "latest_poll" not in self.data:
			self.data["latest_poll"] = None
		
		self.save()
	def save(self):
		with open("poll_plugin.json", "w") as f:
			f.write(json.dumps(self.data))
	def getResults(self, pollObject):
		count = {}
		for player in pollObject["results"]:
			value = pollObject["results"][player]
			if value not in count: count[value] = 0
			count[value] += 1
		return count
	def IRCCommand(self, payload):
		def args(i):
			try: return payload["message"].split(" ")[i]
			except: return ""
		def argsAfter(i):
			try: return " ".join(payload["message"].split(" ")[i:])
			except: return ""
		try:
			if not payload["message"][0] == "!": return
		except: return
		command = args(0)[1:]
		if command == "test":
			self.api.wrapper.irc.msgQueue.append("Hello there! Test")
		if command == "results":
			poll = args(1)
			if len(poll) > 0:
				if poll in self.data["polls"]:
					pollObject = self.data["polls"][poll]
					results = self.getResults(pollObject)
					self.api.wrapper.irc.msgQueue.append("The poll results for '%s': " % poll)
					for i in results:
						self.api.wrapper.irc.msgQueue.append("%s: %s vote(s)" % (pollObject["options"][i], results[i]))
				else:
					self.api.wrapper.irc.msgQueue.append("Error: Poll '%s' does not exist." % poll)
			else:
				self.api.wrapper.irc.msgQueue.append("Usage: !results <pollName>")
	def command(self, payload): # sloppy debug stuff. :P
		def args(i):
			try: return payload["message"].split(" ")[i]
			except: return ""
		def argsAfter(i):
			try: return " ".join(payload["message"].split(" ")[i:])
			except: return ""
		try:
			if not payload["message"][0] == "!": return
		except: return
		command = args(0)[1:]
		player = self.minecraft.getPlayer(payload["player"])
		if command == "results":
			poll = args(1)
			if len(poll) > 0:
				if poll in self.data["polls"]:
					pollObject = self.data["polls"][poll]
					results = self.getResults(pollObject)
					player.message("&a&oThe poll results for '%s': " % poll)
					for i in results:
						player.message("&b%s: &6%s vote(s)" % (pollObject["options"][i], results[i]))
				else:
					player.message("&cError: Poll '%s' does not exist." % poll)
			else:
				player.message("&cUsage: !results <pollName>")
		if command == "vote":
			poll = args(1)
			value = args(2)
			if len(poll) > 0:
				if poll in self.data["polls"]:
					if len(value) > 0:
						try:
							value = int(value)
							pollObject = self.data["polls"][poll]
							if value > -1 and value < len(pollObject["options"]):
								if player.username in pollObject["results"]:
									player.message("&a&lChanged your vote from '&o&6%s&r&a&l' to '&o&6%s&r&a&l'!" % (pollObject["options"][pollObject["results"][player.username]], pollObject["options"][value]))
								else:
									player.message("&a&lThanks for voting on '&o&6%s&r&a&l'!" %  pollObject["options"][value])
								pollObject["results"][player.username] = value
							else:
								player.message("&cError: Invalid option: &l%d" % value)
							self.save()
						except:						
							player.message("&cError: Invalid value.")
					else:
						player.message("&aAvailable options for voting:")
						for i,option in enumerate(self.data["polls"][poll]["options"]):
							player.message("&e%d: &b%s" % (i, option))
						player.message("&aTo vote on one of the options, do !vote %s 0-%d" % (poll, len(self.data["polls"][poll]["options"]) - 1))
				else:
					player.message("&cError: Poll '%s' does not exist!" % poll)
			else:
				player.message("&cUsage: !vote <pole> [value]")
				player.message("&cIf you don't provide a value, you will get a list of available values.")
		if command == "setpoll" and player.isOp():
			poll = args(1)
			options = argsAfter(2).replace("&", "&&").split(",")
			if len(poll) > 0 and len(options) > 0:
				player.message("&aCreated new poll '%s' with the following options:" % poll)
				for i,v in enumerate(options):
					player.message("&e%d:&b %s" % (i, v))
				self.data["polls"][poll] = {"options": options, "results": {}}
				self.data["latest_poll"] = poll
				self.save()
			else:
				player.message("&cUsage: !setpoll <poleName> <option1>,<option2>,<option3>,etc.")
				player.message("&cThe options are separated by commas. &l&opoleName is case sensitive and cannot have spaces!&r&c Best to make it undercase.")
	def join(self, payload):
		name = payload["player"]
		player = self.minecraft.getPlayer(name)
		if self.data["broadcast_new_polls"]:
			if not self.data["latest_poll"] == None:
				player.message("&a&lWelcome back, &6%s&a.&r&a Check out the latest poll: &3%s." % (name, self.data["latest_poll"]))
				player.message("&c(run the !vote command for help)")