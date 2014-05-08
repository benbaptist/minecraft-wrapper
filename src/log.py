import time
from config import Config
class Log:
	def __init__(self):
		self.file = open("wrapper.log", "a")
	def timestamp(self):
		return time.strftime("[%H:%M:%S]")
	def write(self, payload):
		print payload
		self.file.write("%s\n" % payload)
		self.file.flush()
	def info(self, string):
		self.write("%s [Wrapper.py/INFO] %s" % (self.timestamp(), string))
	def error(self, string):
		self.write("%s [Wrapper.py/ERROR] %s" % (self.timestamp(), string))
	def debug(self, string):
		if Config.debug:
			self.write("%s [Wrapper.py/DEBUG] %s" % (self.timestamp(), string))
class PluginLog:
	def __init__(self, log, PluginName="Hello"):
		self.log = log
		self.PluginName = PluginName
	def timestamp(self):
		return time.strftime("[%H:%M:%S]")
	def write(self, payload):
		self.log.write(payload)
	def info(self, string):
		self.write("%s [%s/INFO] %s" % (self.timestamp(), self.PluginName, string))
	def error(self, string):
		self.write("%s [%s/ERROR] %s" % (self.timestamp(), self.PluginName, string))
	def debug(self, string):
		if Config.debug:
			self.write("%s [%s/DEBUG] %s" % (self.timestamp(), self.PluginName, string))