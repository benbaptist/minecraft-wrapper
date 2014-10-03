class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log
		
		self.name = "Template Plugin"
		self.id = "com.benbaptist.plugins.template"
		self.version = (1, 0)
		self.description = "This plugin does nothing at all! :D"
	def onEnable(self):
		pass
	def onDisable(self):
		pass