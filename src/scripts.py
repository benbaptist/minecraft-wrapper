import api, os, stat
scripts = {"server-start.sh": """ # This script is called just before the server starts. 
# It's safe to make changes to the world file, server.properties, etc. since the server has not started yet.
# Arguments passed to this script: None
""",
"server-stop.sh": """ # This script is called right after the server has stopped. 
# It's safe to make changes to the world file, server.properties, etc. since the server is completely shutdown.
# Arguments passed to this script: None
""",
"backup-begin.sh": """ # This script is called when a backup starts.
# Note that the backup hasn't started yet at the time of calling this script, and thus the file is non-existent.
# Arguments passed to this script: None
""",
"backup-finish.sh": """ # This script is called when a backup has finished.
# Arguments passed to this script: backup-filename
"""}
class Scripts:
	def __init__(self, wrapper):
		self.api = api.API(wrapper, "Scripts", internal=True)
		self.wrapper = wrapper
		
		# Register the events
		self.api.registerEvent("server.start", self._startServer)
		self.api.registerEvent("server.stopped", self._stopServer)
		self.api.registerEvent("wrapper.backupBegin", self._backupBegin)
		self.api.registerEvent("wrapper.backupEnd", self._backupEnd)
		
		self.createDefaultScripts()
	def createDefaultScripts(self):
		if not os.path.exists("wrapper-data"): os.mkdir("wrapper-data")
		if not os.path.exists("wrapper-data/scripts"): os.mkdir("wrapper-data/scripts")
		for script in scripts:
			path = "wrapper-data/scripts/%s" % script
			if not os.path.exists(path):
				with open(path, "w") as f:
					f.write(scripts[script])
				os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
	# Events
	def _startServer(self, payload):
		os.system("wrapper-data/scripts/server-start.sh")
	def _stopServer(self, payload):
		os.system("wrapper-data/scripts/server-stop.sh")
	def _backupBegin(self, payload):
		os.system("wrapper-data/scripts/backup-begin.sh %s" % payload["file"])
	def _backupEnd(self, payload):
		os.system("wrapper-data/scripts/backup-finish.sh %s" % payload["file"])
	