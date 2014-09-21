import socket, datetime, time, sys, threading, random, subprocess, os, json, signal, traceback, api, world
class Server:
	def __init__(self, args, log, config, wrapper):
		self.log = log
		self.config = config
		self.wrapper =  wrapper
		self.players = {}
		self.status = 0 # 0 is off, 1 is starting, 2 is started, 3 is shutting down
		self.start = True
		self.sock = False
		self.currentSecond = 0
		self.backupInterval = 0
		self.uuid = {}
		self.data = ""
		self.backups = []
		
		self.worldName = None
		self.protocolVersion = 5 # the protocol version is unknown until the first proxy mode connection is made
		self.version = None
		self.world = world.World()
	def login(self, user):
		try:
			if user not in self.players:
				time.sleep(1)
				self.players[user] = api.Player(user, self.wrapper)
		except:
			traceback.print_exc()
	def logout(self, user):
		if self.wrapper.proxy:
			for client in self.wrapper.proxy.clients:
				client.send(0x38, "varint|varint|uuid", (4, 1, self.players[user].uuid))
		if user in self.players:
			del self.players[user]
	def argserver(self, i):
		try: return self.line.split(" ")[i]
		except: return ""
	def argsAfter(self, i):
		try: return " ".join(self.line.split(" ")[i:])
		except: return ""
	def getName(self):
		return "Minecraft Server"
	# -- IRC functions -- #
	def msg(self, message):
		if self.config["IRC"]["enabled"]:
			self.wrapper.irc.msgQueue.append(message)
	def filterName(self, name):
		if self.config["IRC"]["obstruct-nicknames"]:
			return "_" + name[1:]
		else:
			return name 
	# -- server management -- #
	def announce(self, text):
		for channel in self.config["IRC"]["channels"]:
			self.send('PRIVMSG %s :%s' % (channel, text))
#		self.console()
	def console(self, text):
#		if not self.config["General"]["pre-1.7-mode"]:
		self.run("tellraw @a %s" % json.dumps(text, encoding='utf-8'))
#		else:
#			self.run("say %s" % text)
	def run(self, text):
		try:
			self.proc.stdin.write("%s\n" % text)
		except:
			pass
	def capture(self):
		while not self.wrapper.halt:
			try:
				data = self.proc.stdout.readline()
				if len(data) > 0:
					self.data += data
			except:
				continue
	def formatForIRC(self, string):
		colorCodes = {"0": "1", 
			"1": "2",
			"2": "3", 
			"3": "10",
			"4": "4",
			"5": "6",
			"6": "5",
			"7": "15",
			"8": "14",
			"9": "11",
			"a": "9", 
			"b": "13", 
			"c": "4", 
			"d": "6", 
			"e": "8", 
			"f": "0",
			"k": "1",
			"l": "",
			"m": "",
			"n": "",
			"o": ""}
		converted = ""
		skipNext = False
		for i,char in enumerate(string):
			if skipNext: # wow this code just got really lazy and dumb looking
				skipNext = False
				continue
			if char == "\xa7":
				color = string[i + 1]
				converted = converted[0:-1]
				if color == "r":
					converted += "\x0f"
				else:
					converted += "\x03%s" % colorCodes[color]
				skipNext = True
			else:
				converted += char
		return converted
	def stripSpecialIRCChars(self, value):
		for i in range(16):
			value = value.replace("\x03%d" % i, "")
		value = value.replace("\x0f", "")
		return value
	def startServer(self):
		while not self.wrapper.halt:
			if not self.start:
				time.sleep(0.1)
				continue
			self.players = {}
			self.status = 1
			self.log.info("Starting server...")
			self.wrapper.callEvent("server.start", {})
			self.proc = subprocess.Popen(self.serverArgs, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
			while True:
				# timer & backup
				if self.currentSecond == int(time.time()): # don't make fun of me for this
					pass
				else:
					self.backupInterval += 1
					self.currentSecond = int(time.time())
					self.wrapper.callEvent("timer.second", {})
				if self.backupInterval == self.config["Backups"]["backup-interval"] and self.config["Backups"]["enabled"] and self.wrapper.callEvent("wrapper.backupBegin", {}):
					self.backupInterval = 0
					if not os.path.exists(self.config["Backups"]["backup-location"]):
						os.mkdir(self.config["Backups"]["backup-location"])
					if len(self.backups) == 0 and os.path.exists(self.config["Backups"]["backup-location"] + "/backups.json"):
						f = open(self.config["Backups"]["backup-location"] + "/backups.json", "r")
						try:
							self.backups = json.loads(f.read())
						except:
							self.log.error("NOTE - backups.json was unreadable. This might be due to corruption. This might lead to backups never being deleted.")
							for channel in self.config["IRC"]["channels"]:
								self.send("PRIVMSG %s :ERROR - backups.json is corrupted. Please contact an administer instantly, this may be critical." % (channel))
							self.backups = []
						f.close()
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
						self.msg("Backing up, IRC bridge will freeze and lag may occur")
						self.console("\xc2\xa7bBacking up, IRC bridge will freeze and lag may occur")
					timestamp = int(time.time())
					filename = "backup-%s.tar" % datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d_%H:%M:%S")
					self.run("save-all")
					self.run("save-off")
					time.sleep(0.5)
	
					if not os.path.exists(str(self.config["Backups"]["backup-location"])):
						os.mkdir(self.config["Backups"]["backup-location"])
					
					arguments = ["tar", "cfpv", '%s/%s' % (self.config["Backups"]["backup-location"], filename)]
					for file in self.config["Backups"]["backup-folders"]:
						if os.path.exists(file):
							arguments.append(file)
						self.log.error("Backup file '%s' does not exist - will not backup")
					statusCode = os.system(" ".join(arguments))
					self.run("save-on")
					if self.config["Backups"]["backup-notification"]:
						self.console("\xc2\xa7aBackup complete!")
						self.msg("Backup complete!")
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
				
				if self.proc.poll() is not None:
					self.status = 0
					self.msg("Server shutdown")
					self.log.info("Server shutdown")
					if not self.config["General"]["auto-restart"]:
						self.halt = True
						sys.exit(0)
					break
				if len(self.data) > 0:
					data = self.data[:]
					self.data = ""
				else:
					data = ""
				
				# parse server console output
				deathPrefixes = ['fell', 'was', 'drowned', 'blew', 'walked', 'went', 'burned', 'hit', 'tried', 
					'died', 'got', 'starved', 'suffocated', 'withered']
				for line in data.split('\n'):
					if len(line) < 1: continue
					self.line = line
					self.wrapper.callEvent("server.consoleMessage", {"message": line})
					print line
					if self.argserver(3) is not False:
						try:
		#					if not self.config["General"]["pre-1.7-mode"]:
								if self.argserver(3)[0] == "<":
									name = self.formatForIRC(self.filterName(self.argserver(3)[1:self.argserver(3).find('>')]))
									message = self.formatForIRC(" ".join(line.split(' ')[4:]).replace('\x1b', '').replace("\xc2\xfa", ""))
#									self.msg("<%s> %s" % (name, message))
									self.wrapper.callEvent("player.message", {"player": self.stripSpecialIRCChars(name), "message": message})
								elif self.argserver(3) == "Preparing" and self.argserver(4) == "level":
									self.worldName = self.argserver(5).replace('"', "")
								elif self.argserver(4) == "logged":
									name = self.formatForIRC(self.filterName(self.argserver(3)[0:self.argserver(3).find('[')]))
									self.msg("[%s connected]" % name)
									self.login(name)
									self.wrapper.callEvent("player.join", {"player": name})
								elif self.argserver(4) == 'lost':
									name = self.filterName(self.argserver(3))
									self.msg("[%s disconnected]" % (name))
									self.logout(name)
									self.wrapper.callEvent("player.logout", {"player": name})
								elif self.argserver(4) == 'issued': # this kinda doesn't work anymore unless you have a bukkit plugin.
									name = self.filterName(self.argserver(3))
									command = message = ' '.join(line.split(' ')[7:])
									if self.config["IRC"]["forward-commands-to-irc"]:
										self.msg("%s issued command: %s" % (name, command))
								elif self.argserver(1) == "[User" and self.argserver(4) == "UUID":
									uuid = self.argserver(9)
									username = self.argserver(7)
									
									self.uuid[username] = uuid
								elif self.argserver(3) == 'Done':
									self.status = 2
									self.msg("Server started")
									self.log.info("Server started")
									self.wrapper.callEvent("server.started", {})
								elif self.argserver(3) == 'Starting' and self.argserver(4) == "minecraft":
									self.version = self.argserver(7)
								elif self.argserver(4) in deathPrefixes:
									self.msg(' '.join(self.line.split(' ')[3:]))
									name = self.filterName(self.argserver(3))
									deathMessage = self.config["Death"]["death-kick-messages"][random.randrange(0, len(self.config["Death"]["death-kick-messages"]))]
									if self.config["Death"]["kick-on-death"] and name in self.config["Death"]["users-to-kick"]:
										server.proc.stdin.write('kick %s %s\n\r' % (name, deathMessage))
									self.wrapper.callEvent("player.death", {"player": self.stripSpecialIRCChars(name), "death": self.argsAfter(4)})
								elif self.argserver(3) == "*":
									name = self.formatForIRC(self.filterName(self.argserver(4)))
									message = message = ' '.join(line.split(' ')[5:])
									self.msg("* %s %s" % (name, message))
									self.wrapper.callEvent("player.action", {"player": name, "action": message})
								elif self.argserver(4) == "has" and self.argserver(8) == "achievement":
									name = self.filterName(self.argserver(3))
									achievement = ' '.join(line.split(' ')[9:])
									self.msg("%s has just earned the achievement %s" % (name, achievement))
									self.wrapper.callEvent("player.achievement", {"player": name, "achievement": achievement})
						#	else: # -- FOR 1.6.4 AND PREVIOUSLY ONLY!!!!! -- 
#								if self.argserver(2)[0] == '<':
#									name = self.filterName(self.argserver(2)[1:self.argserver(2).find('>')].replace("\xc2\xfa", ""))
#									message = ' '.join(line.split(' ')[3:]).replace('\x1b', '').replace("\xc2\xfa", "")
#									self.msg('<%s> %s' % (name, message))
#								elif self.argserver(3) == 'logged':
#									name = self.argserver(2)[0:self.argserver(2).find('[')]
#									self.msg('[%s connected]' % name)
#									self.login(name)
#								elif self.argserver(3) == 'lost':
#									name = self.argserver(2)
#									reason = self.argserver(5)
#									self.msg('[%s disconnected] (%s)' % (name, reason))
#									self.logout(name)
#								elif self.argserver(3) == 'Kicked':
#									name = self.argserver(6)
#									self.msg('[%s disconnected] (kicked)' % name)
#									self.logout(name)
#								elif self.argserver(3) == 'issued':
#									name = self.argserver(2)
#									command = message = ' '.join(line.split(' ')[6:])
#									if self.config["forwardCommandsToIRC"]:
#										self.msg('%s issued command: %s' % (name, command))
#								elif self.argserver(2) == 'Done':
#									self.status = 2
#									self.msg('Server started')
#								elif self.argserver(3) in deathPrefixes:
#									self.msg(' '.join(self.line.split(' ')[2:]))
#									name = self.argserver(2)
#									randThing = self.config["deathKickMessages"][random.randrange(0, len(self.config["deathKickMessages"]))]
#									if self.config["deathKick"] and name in self.config["deathKickers"]:
#										self.run("kick %s %s" % (name, randThing))
						except:
							pass
				time.sleep(0.1)
	# functions useful for the API
	def stop(self, message="Server going down for maintenance"):
		self.start = False
		for name in self.players:
			self.run("kick %s %s" % (name, message))
		time.sleep(0.2)
		self.run("stop")