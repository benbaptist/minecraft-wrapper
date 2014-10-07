class Main:
	def __init__(self, api, log):
		self.api = api
		self.log = log
		
		self.version = (1, 0)
		self.description = "This plugin helps demonstrate functions in Wrapper.py. :D"
	def onEnable(self):
		self.log.info("example.py is loaded!")
		self.log.error("This is an error test.")
		self.log.debug("This'll only show up if you have debug mode on.")
		
		self.api.registerEvent("player.login", self.playerLogin)
	def playerLogin(self, payload):
		self.api.minecraft.broadcast("&a&lEverybody, introduce %s to the server!" % payload["player"])
	def playerLogout(self, payload):
		self.api.minecraft.broadcast("&7&oYou will be dearly missed, %s." % payload["player"])
	def onDisable(self):
		pass