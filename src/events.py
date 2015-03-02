import traceback
class Events:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.log = wrapper.log
		self.listeners = []
		self.events = {}
	def __getitem__(self, index):
		if not type(index) == str:
			raise Exception("A string must be passed to the stuff")
		return self.events[index]
	def __setitem__(self, index, value):
		if not type(index) == str:
			raise Exception("A string must be passed to the stuff")
		self.events[index] = value
		return self.events[index]
	def __delitem__(self, index):
		if not type(index) == str:
			raise Exception("A string must be passed to the stuff")
		del self.events[index]
	def __iter__(self):
		for i in self.events:
			yield i
	def callEvent(self, event, payload):
		if event == "player.runCommand":
			if not self.wrapper.commands.playerCommand(payload): return False
		for sock in self.listeners:
			sock.append({"event": event, "payload": payload})
		try:
			for pluginID in self.events:
				if event in self.events[pluginID]:
					try:
						result = self.events[pluginID][event](payload)
						if result == None: continue
						if result != True:
							return result
					except:
						self.log.error("Plugin '%s' errored out when executing callback event '%s':" % (pluginID, event))
						for line in traceback.format_exc().split("\n"):
							self.log.error(line)
		except:
			pass # For now.
			#self.log.error("A serious runtime error occurred - if you notice any strange behaviour, please restart immediately")
			#self.log.getTraceback()
		return True
	