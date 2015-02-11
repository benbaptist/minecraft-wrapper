import time, traceback
from config import Config
class Log:
	def __init__(self):
		self.file = open("wrapper.log", "a")
	def timestamp(self):
		return time.strftime("[%Y-%m-%d %H:%M:%S]")
	def write(self, payload):
		self.file.write(("%s\n" % payload).encode("utf8"))
		self.file.flush()
	def prefix(self, type="INFO", string=""):
		for line in string.split("\n"):
			self.write("%s [Wrapper.py/%s] %s" % (self.timestamp(), type, line)) 
			print("%s [Wrapper.py/%s] %s" % (time.strftime("[%H:%M:%S]"), type, line))
	def info(self, string):
		self.prefix("INFO", string)
	def warn(self, string):
		self.prefix("WARN", string)
	def error(self, string):
		self.prefix("ERROR", string)
	def debug(self, string):
		if Config.debug:
			self.prefix("DEBUG", string)
	def getTraceback(self):
		for line in traceback.format_exc().split("\n"):
			if len(line.strip()) > 0: # Remove empty lines
				self.error(line)
class PluginLog:
	def __init__(self, log, PluginName="Hello"):
		self.log = log
		self.PluginName = PluginName
	def timestamp(self):
		return time.strftime("[%Y-%m-%d %H:%M:%S]")
	def write(self, payload):
		self.log.write(payload)
	def prefix(self, type="INFO", string=""):
		for line in string.split("\n"):
			self.write("%s [%s/%s] %s" % (self.PluginName, self.timestamp(), type, line)) 
			print("%s [%s/%s] %s" % (self.PluginName, time.strftime("[%H:%M:%S]"), type, line))
	def info(self, string):
		self.prefix("INFO", string)
	def warn(self, string):
		self.prefix("WARN", string)
	def error(self, string):
		self.prefix("ERROR", string)
	def debug(self, string):
		if Config.debug:
			self.prefix("DEBUG", string)
	def getTraceback(self):
		for line in traceback.format_exc().split("\n"):
			if len(line.strip()) > 0: # Remove empty lines
				self.error(line)