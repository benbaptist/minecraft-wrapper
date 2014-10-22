# Plans for this: separate backup code into its own method, allow for plugins to control backups more freely.
# I also should probably not use irc=True when broadcasting, and instead should just rely on events and having server.py and irc.py print messages themselves
# for the sake of consistency.
import datetime, time, sys, threading, random, subprocess, os, json, signal, api
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
		self.api.minecraft.broadcast(message, irc=True)
	def console(self, msg):
		self.api.minecraft.console(msg)
	def onTick(self, payload):
		self.interval += 1
		if not self.config["Backups"]["enabled"]: return
		if time.time() - self.time > self.config["Backups"]["backup-interval"]:
			self.time = time.time()
			if not self.wrapper.callEvent("wrapper.backupBegin", None):
				self.log.warn("A backup was scheduled, but was cancelled by a plugin!")
				return
			if not os.path.exists(self.config["Backups"]["backup-location"]):
				os.mkdir(self.config["Backups"]["backup-location"])
			if len(self.backups) == 0 and os.path.exists(self.config["Backups"]["backup-location"] + "/backups.json"):
				with open(self.config["Backups"]["backup-location"] + "/backups.json", "r") as f:
					try: self.backups = json.loads(f.read())
					except:
						self.log.error("NOTE - backups.json was unreadable. This might be due to corruption. This might lead to backups never being deleted.")
						for channel in self.config["IRC"]["channels"]:
							self.send("PRIVMSG %s :ERROR - backups.json is corrupted. Please contact an administer instantly, this may be critical." % (channel))
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
			if self.config["Backups"]["backup-notification"]:
				self.broadcast("&cBacking up... lag may occur!")
			timestamp = int(time.time())
			filename = "backup-%s.tar" % datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d_%H:%M:%S")
			self.console("save-all")
			self.console("save-off")
			time.sleep(0.5)
	
			if not os.path.exists(str(self.config["Backups"]["backup-location"])):
				os.mkdir(self.config["Backups"]["backup-location"])
			
			arguments = ["tar", "cfpv", '%s/%s' % (self.config["Backups"]["backup-location"], filename)]
			for file in self.config["Backups"]["backup-folders"]:
				if os.path.exists(file):
					arguments.append(file)
				else:
					self.log.error("Backup file '%s' does not exist - will not backup" % file)
			statusCode = os.system(" ".join(arguments))
			self.console("save-on")
			if self.config["Backups"]["backup-notification"]:
				self.broadcast("&aBackup complete!")
				self.wrapper.callEvent("wrapper.backupEnd", {"backupFile": filename, "status": statusCode})
			self.backups.append((timestamp, 'backup-%s.tar' % datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d_%H:%M:%S')))
			
			if len(self.backups) > self.config["Backups"]["backups-keep"]:
				self.log.info("Deleting old backups...")
				while len(self.backups) > self.config["Backups"]["backups-keep"]:
					backup = self.backups[0]
					if not self.wrapper.callEvent("wrapper.backupDelete", {"backupFile": filename}): break
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