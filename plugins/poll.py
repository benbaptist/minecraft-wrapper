# -- Poll Plugin -- 

import threading, time, random, json, os
class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log
		
		self.version = (0, 1)
		self.description = "Poll position"
	def onEnable(self):
		self.api.registerEvent("player.message", self.command)
		self.api.registerEvent("player.join", self.join)
		
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
	def command(self, payload): # sloppy debug stuff. :P
		def args(i):
			try: return payload["message"].split(" ")[i]
			except: return ""
		def argsAfter(i):
			try: return " ".join(payload["message"].split(" ")[i:])
			except: return ""
		command = args(0)[1:]
		player = self.minecraft.getPlayer(payload["player"])
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