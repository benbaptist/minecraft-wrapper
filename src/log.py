import time, traceback, os, gzip, shutil, threading
from config import Config
class Log:
	def __init__(self):
		#self.file = open("wrapper.log", "a")
		self.file = None
		self.rotateLogs()
		self.buffer = ""
		
		t = threading.Thread(target=self.loop, args=())
		t.daemon = True
		t.start()
	def rotateLogs(self):
		if not os.path.exists("logs"): os.mkdir("logs")
		if not os.path.exists("logs/wrapper"): os.mkdir("logs/wrapper")
		if os.path.exists("wrapper.log"):
			with open("wrapper.log", "r") as f:
				originalLog = f.read()
			with gzip.open("logs/wrapper/oldWrapper.log.gz", "w") as f:
				f.write(originalLog)
			os.remove("wrapper.log")
		if self.file:
			self.file.close()
		self.file = None
		if os.path.exists("logs/wrapper/current.log"):
			with open("logs/wrapper/current.log", "r") as f:
				logData = f.read()
				f.close()
			with gzip.open("logs/wrapper/%s.log.gz" % time.strftime("%Y-%m-%d_%H-%M-%S"), "w") as f:
				f.write(logData)
		self.file = open("logs/wrapper/current.log", "w")
	def loop(self):
		day = time.strftime("%d")
		while True:
			if day != time.strftime("%d"):
				print "Day changed, rotating logs..."
				day = time.strftime("%d")
				self.rotateLogs()
			time.sleep(1)
	def timestamp(self):
		return time.strftime("[%Y-%m-%d %H:%M:%S]")
	def write(self, payload):
		try:
			if self.file:
				if len(self.buffer) > 0:
					self.file.write(self.buffer)
					self.buffer = ""
				self.file.write(("%s\n" % payload).encode("utf8"))
				self.file.flush()
			else:
				self.buffer += ("%s\n" % payload).encode("utf8")
		except:
			print "Failure to write string - possibly due to writing while rotating log files"
			print payload
			print traceback.format_exc()
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