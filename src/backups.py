# Plans for this: separate backup code into its own method, allow for plugins to control backups more freely.
# I also should probably not use irc=True when broadcasting, and instead should just rely on events and having server.py and irc.py print messages themselves
# for the sake of consistency.
import datetime, time, sys, threading, random, subprocess, os, json, signal, api, platform
class Backups:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.config = wrapper.config
		self.log = wrapper.log
		self.api = api.API(wrapper, "Backups", internal=True)
		
		self.interval = 0
		self.time = time.time()
		self.backups = []
		self.api.registerEvent("timer.second", self.onTick)
	def broadcast(self, message):
		self.api.minecraft.broadcast(message, irc=False)
	def console(self, msg):
		self.api.minecraft.console(msg)
	def onTick(self, payload):
		self.interval += 1
		if not self.config["Backups"]["enabled"]: return
		if time.time() - self.time > self.config["Backups"]["backup-interval"]:
			self.time = time.time()
			if not os.path.exists(self.config["Backups"]["backup-location"]):
				os.mkdir(self.config["Backups"]["backup-location"])
			if len(self.backups) == 0 and os.path.exists(self.config["Backups"]["backup-location"] + "/backups.json"):
				with open(self.config["Backups"]["backup-location"] + "/backups.json", "r") as f:
					try: self.backups = json.loads(f.read())
					except:
						self.log.error("NOTE - backups.json was unreadable. It might be corrupted. Backups will no longer be automatically pruned.")
						self.wrapper.callEvent("wrapper.backupFailure", {"reasonCode": 4, "reasonText": "backups.json is corrupted. Please contact an administer instantly, as this may be critical."})
						self.backups = []
			else:
				if len(os.listdir(self.config["Backups"]["backup-location"])) > 0:
					# import old backups from previous versions of Wrapper.py
					backupTimestamps = []
					for backupNames in os.listdir(self.config["Backups"]["backup-location"]):
						try:
							backupTimestamps.append(int(backupNames[backupNames.find('-')+1:backupNames.find('.')]))
						except:
							pass
					backupTimestamps.sort()
					for backupI in backupTimestamps:
						self.backups.append((int(backupI), "backup-%s.tar" % str(backupI)))
			timestamp = int(time.time())
			self.console("save-all")
			self.console("save-off")
			time.sleep(0.5)
	
			if not os.path.exists(str(self.config["Backups"]["backup-location"])):
				os.mkdir(self.config["Backups"]["backup-location"])
			
			filename = "backup-%s.tar" % datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d_%H.%M.%S")
			if self.config["Backups"]["backup-compression"]:
				filename += ".gz"
				arguments = ["tar", "czf", "%s/%s" % (self.config["Backups"]["backup-location"].replace(" ", "\\ "), filename)]
			else:
				arguments = ["tar", "cfpv", "%s/%s" % (self.config["Backups"]["backup-location"], filename)]
			
			# Check if tar is installed
			which = "where" if platform.system() == "Windows" else "which"
			if not subprocess.call([which, "tar"]) == 0:
				self.wrapper.callEvent("wrapper.backupFailure", {"reasonCode": 1, "reasonText": "Tar is not installed. Please install tar before trying to make backups."})
				self.log.error("The backup could not begin, because tar does not appear to be installed!")
				self.log.error("If you are on a Linux-based system, please install it through your preferred package manager.")
				self.log.error("If you are on Windows, you can find GNU/Tar from this link: http://goo.gl/SpJSVM")
				return
			
			if not self.wrapper.callEvent("wrapper.backupBegin", {"file": filename}):
				self.log.warn("A backup was scheduled, but was cancelled by a plugin!")
				return
			if self.config["Backups"]["backup-notification"]:
				self.broadcast("&cBacking up... lag may occur!")
			
			for file in self.config["Backups"]["backup-folders"]:
				if os.path.exists(file):
					arguments.append(file)
				else:
					self.log.warn("Backup file '%s' does not exist - cancelling backup" % file)
					self.wrapper.callEvent("wrapper.backupFailure", {"reasonCode": 3, "reasonText": "Backup file '%s' does not exist." % file})
					return 
			statusCode = os.system(" ".join(arguments))
			self.console("save-on")
			if self.config["Backups"]["backup-notification"]:
				self.broadcast("&aBackup complete!")
			self.wrapper.callEvent("wrapper.backupEnd", {"file": filename, "status": statusCode})
			self.backups.append((timestamp, filename))
			
			if len(self.backups) > self.config["Backups"]["backups-keep"]:
				self.log.info("Deleting old backups...")
				while len(self.backups) > self.config["Backups"]["backups-keep"]:
					backup = self.backups[0]
					if not self.wrapper.callEvent("wrapper.backupDelete", {"file": filename}): break
					try:
						os.remove('%s/%s' % (self.config["Backups"]["backup-location"], backup[1]))
					except:
						print "Failed to delete"
					self.log.info("Deleting old backup: %s" % datetime.datetime.fromtimestamp(int(backup[0])).strftime('%Y-%m-%d_%H:%M:%S'))
					hink = self.backups[0][1][:]
					del self.backups[0]
			f = open(self.config["Backups"]["backup-location"] + "/backups.json", "w")
			f.write(json.dumps(self.backups))
			f.close()	
			
			if not os.path.exists(self.config["Backups"]["backup-location"] + "/" + filename):
				self.wrapper.callEvent("wrapper.backupFailure", {"reasonCode": 2, "reasonText": "Backup file didn't exist after the tar command executed - assuming failure."})