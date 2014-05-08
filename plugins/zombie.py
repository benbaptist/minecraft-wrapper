# -- Zombie Plugin -- 
# version 0.1
# written by benbaptist

# this plugin makes people killed by zombies and skeletons leave behind an undead version of themselves.

# this is the only person that can run the debug commands 'spawnzombie' and 'spawnskeleton'.
op = "benbaptist" 

import threading, time, random, struct
class Main:
	def __init__(self, api, log):
		self.api = api
		self.log = log
		
		self.version = (0, 1)
		self.description = "Actual players killed by zombies and skeletons leave behind undead versions of themselves!"
	def onEnable(self):
		self.log.info("Zombie is on")
		self.api.registerEvent("player.message", self.fake)
		self.api.registerEvent("player.death", self.death)
	def onDisable(self):
		pass
	def zombie(self, name):
		self.api.minecraft.console("execute %s ~ ~ ~ summon Zombie ~ ~ ~ {CustomName:undead_%s,DropChances:[1.0f,1.0f,1.0f,1.0f],Equipment:[{id:268,ench:[{id:21,lvl:50},{id:16,lvl:3},{id:34,lvl:15}]},{id:277},{id:277},{id:277},{id:397,Damage:3,SkullOwner:%s}],CanPickUpLoot:True}" % (name, name, name))
		self.api.minecraft.console("effect @e[name=undead_%s] 11 2555 2" % name)
		self.api.minecraft.console("effect @e[name=undead_%s] 5 2555 1" % name)
	def skeleton(self, name):
		self.api.minecraft.console("execute %s ~ ~ ~ summon Skeleton ~ ~ ~ {CustomName:Skeleton %s,HealF:2.0,Equipment:[{id:261,ench:[{id:47,lvl:4}]},{id:277},{id:277},{id:277},{id:397,Damage:3,SkullOwner:%s}],CanPickUpLoot:True}" % (name, name, name))
	def fake(self, payload): # sloppy debug stuff. :P
		if payload["message"] == "spawnzombie" and payload["player"] == op:
			self.zombie(payload["player"])
		if payload["message"] == "spawnskeleton" and payload["player"] == op:
			self.skeleton(payload["player"])
	def death(self, payload):
		name = payload["player"]
		death = payload["death"]
		if death == "was slain by Zombie" and random.randrange(0, 4) == 2:
			self.zombie(name)
			self.api.minecraft.broadcast("&6&l%s has been turned into a zombie!" % (name))
		if death == "was shot by Skeleton" and random.randrange(0, 4) == 2:
			self.skeleton(name)
			self.api.minecraft.broadcast("&6&l%s has been turned into a skeleton!" % (name))