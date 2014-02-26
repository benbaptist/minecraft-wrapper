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