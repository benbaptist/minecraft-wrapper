import json, os, threading, time
class Storage:
	def __init__(self, name, log=None):
		self.log = log
		self.name = name
		
		self.data = {}
		self.load()
		self.flush = False
		self.abort = False
		self.time = time.time()
		
		t = threading.Thread(target=self.periodicSave, args=())
		t.daemon = True
		t.start()
	def __del__(self):
		print "STORAGE OBJECT '%s' BEING DESTROYED - SAVING" % self.name
		self.abort = True
		self.save()
	def periodicSave(self):
		while not self.abort:
			if time.time() - self.time > 60 * 5:
				if self.flush:
					print "Automatic save for %s" % self.name
					self.save()
					self.time = time.time()
			time.sleep(1)
	def load(self):
		if not os.path.exists(".wrapper-data/json"):
			try: os.mkdir(".wrapper-data")
			except: pass 
			os.mkdir(".wrapper-data/json")
		if not os.path.exists(".wrapper-data/json/%s.json" % self.name):
			self.save()
		with open(".wrapper-data/json/%s.json" % self.name, "r") as f:
			self.data = json.loads(f.read())
		self.flush = False
	def save(self):
		if not os.path.exists(".wrapper-data"):
			os.mkdir(".wrapper-data")
		with open(".wrapper-data/json/%s.json" % self.name, "w") as f:
			f.write(json.dumps(self.data))
		self.flush = False
	def key(self, key, value=None):
		if value == None:
			return self.getKey(key)
		else:
			self.setKey(key, value)
	def getKey(self, key):
		if key in self.data:
			return self.data[key]
		else:
			return None
	def setKey(self, key, value=None):
		if value == None:
			if key in self.data: del self.data[key]
		else:
			self.data[key] = value
		self.flush = True