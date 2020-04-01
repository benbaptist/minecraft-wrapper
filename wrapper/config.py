import json
import os

# Ben's Configurator v1.2
# Copyright benbaptist.com 2019

class DummyLogger:
	def info(self): pass
	def debug(self): pass
	def error(self): pass
	def warning(self): pass
	def traceback(self): pass

class Config:
	def __getitem__(self, index):
		if not (type(index) in (str, bytes)):
			raise Exception("a str/bytes must be passed")
		return self.data[index]
	def __setitem__(self, index, value):
		if not (type(index) in (str, bytes)):
			raise Exception("a str/bytes must be passed")
		self.data[index] = value
		return self.data[index]
	def __delattr__(self, index):
		if not (type(index) in (str, bytes)):
			raise Exception("a str/bytes must be passed")
		del self.data[index]
	def __delitem__(self, index):
		if not (type(index) in (str, bytes)):
			raise Exception("a str/bytes must be passed")
		del self.data[index]
	def __iter__(self):
		for i in self.data:
			yield i

	def __init__(self, path, template={}, log=DummyLogger()):
		self.path = path
		self.template = template
		self.log = log

		# Changes to True when a config file was updated with new entries, from the template
		self.updated_from_template = False

		if os.path.exists(path):
			self.log.debug("Reading config %s" % self.path)
			with open(path, "r") as f:
				self.data = json.loads(f.read())
		else:
			self.data = {}

		def check(obj, temp, recur=["root"]):
			self.log.debug("Checking '%s'" % "/".join(recur))
			for t in temp:
				if t not in obj:
					self.updated_from_template = True
					obj[t] = temp[t]
					self.log.debug(
						"Populating '%s/%s'"
						% ("/".join(recur), t)
					)
				else:
					if type(temp[t]) == dict:
						check(obj[t], temp[t], recur + [t])

		check(self.data, template)

		# for i in template:
		# 	if i not in self.data:
		# 		self.updated_from_template = True
		# 		self.log.debug("Populating '%s'" % i)
		# 		self.data[i] = template[i]

		self.save()

	def save(self):
		with open(self.path, "w") as f:
			f.write(
				json.dumps(self.data, sort_keys=True, indent=4, separators=(',', ': '))
			)
