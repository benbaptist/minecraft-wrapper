# -- Speedboost -- 
# version 1.0
# written by benbaptist

NAME = "Speedboost"
ID = "com.benbaptist.plugins.speedboost"
SUMMARY = "Gives all players a speedboost when someone dies."
VERSION = (1, 0)
class Main:
	def __init__(self, api, log):
		self.api = api
		self.log = log
	def onEnable(self):
		self.api.registerEvent("player.death", self.death)
	def onDisable(self):
		pass
	def death(self, payload):
		name = payload["player"]
		death = payload["death"]
		self.api.minecraft.console("effect @a 1 30 5")
		self.api.minecraft.broadcast("&6&lEveryone was given a temporary speedboost!")