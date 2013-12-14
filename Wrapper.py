import socket, datetime, time, sys, threading, random, subprocess, os, json, signal, traceback, ConfigParser, ast

# Minecraft IRC Wrapper by Ben Baptist -- Version 0.4.0
# benbaptist.com
# 
# version 0.1 changelog:
# - added .players command
# - join/part messages in-game from IRC
# - ability to type into the server console
# - autoCommands are run BEFORE joining channels
# - changed message format
# - changed login/logout format
# - fixed kicks not logged
# version 0.2 changelog:
# - rewrote most of it into one thread, fixing many quirks (e.g. the wrapper.py not shutting down after the server stops, etc.)
# - death kicker
# - auto restart function when the server shuts down
# - automatic backup system that auto-deletes older backups (needs a bit of work)
# - control server from IRC
# - fixed line wrapping a bit
# version 0.3 changelog:
# - doesn't read from server.log anymore; actually reads from console properly, thus fixing minor issues in certain setups (e.g. if server logging was done in a different file)
# - 1.7 support
# 	 ^ added a newMode configuration option for those still using pre-1.7 servers
# - new backup system - stores backup information in backups.json)
#   ^ backup notifications can be turned off, as well
# - fix the Wrapper not reconnecting to IRC 
# - other fixes
# version 0.3.1 changelog:
# - removed StringIO module import, it was useless
# - fixed crash while trying to send error message to IRC when backups.json was unreadable
# - Wrapper.py now kicks users and shuts down the server when it crashes
# version 0.3.2 changelog:
# - fixed save-off during backup
# - achievements are now logged
# - obstruct usernames in IRC to refrain from pinging
# - other small fixes
# - version 0.4.0 changelog:
# - 
# bugs needing fixed:
# - fixing pre-1.7 servers not working (even with pre1.7Mode set to True)
# to-do list:
# - maybe add some in-game commands such as /halt
# - web interface?
# - somehow do achievement (done )
# - proxy system
# - ability to turn off IRC mode
# - ability to stop server without shutting down wrapper - for fine server control
# - potentially implement region fixer in wrapper.py
# - update version of minecraft server automatically

# configuration
DEFAULT_CONFIG = """[General]
pre-1.7-mode = False
command = java -jar minecraft_server.1.7.2.jar nogui
auto-restart = True

[Backups]
enabled = False
backup-folders = ['server.log', 'server.properties', 'world', 'world_nether', 'world_the_end', 'white-list.txt']
backup-interval = 3600
backup-notification = True
backup-location = backup-directory
backups-keep = 10

[IRC]
enabled = False
server = benbaptist.com
port = 6667
nick = MinecraftServ
channels = ['#main']
show-channel-server = True
autorun-irc-commands = ['COMMAND 1', 'COMMAND 2']
control-from-irc = True
obstruct-nicknames = False
control-irc-pass = password
forward-commands-to-irc = False

[Death]
kick-on-death = False
users-to-kick = ['username1', 'username2', 'remove these usernames to kick ALL users upon death']
death-kick-messages = ['You died!']
"""

class Config:
	version = "0.4.0"
	debug = True
	def __init__(self, log):
		self.log = log
		self.config = {}
		self.exit = False
	def loadConfig(self):
		if not os.path.exists("wrapper.properties"):
			f = open("wrapper.properties", "w")
			f.write(DEFAULT_CONFIG)
			f.close()
			self.exit = True
		open("wrapper.properties", "a").close()
		self.parser = ConfigParser.ConfigParser()
		self.parser.readfp(open("wrapper.properties"))

		sections = ["General", "Backups", "IRC", "Death"]
		defaults = {"General":{
			"command": "java -jar minecraft_server.jar",
			"auto-restart": True,
			"pre-1.7-mode": False
		},		
		"IRC":{ 
			"enabled": True, 
			"nick": "MinecraftIRC", 
			"server": "benbaptist.com", 
			"port": 6667, 
			"channels": ["#main"], 
			"obstruct-nicknames": False,
			"autorun-irc-commands": ['COMMAND 1', 'COMMAND 2'],
			"show-channel-server": True,
			"forward-commands-to-irc": False,
			"control-from-irc": False,
			"control-irc-pass": "password"
		},
		"Backups":{ 
			"enabled": True,
			"backups-keep": 10,
			"backup-location": "backup-directory",
			"backup-folders": ['server.log', 'server.properties', 'world', 'world_nether', 'world_the_end', 'white-list.txt'],
			"backup-interval": 3600,
			"backup-notification": True
		},
		"Death":{
			"kick-on-death": False,
			"death-kick-messages": ["You died!"],
			"users-to-kick": ["username1", "username2", "remove these usernames to kick ALL users upon death"]
		}}
		
		for section in sections:
			try:
				keys = self.parser.items(section)
				self.config[section] = {}
				for key in keys:
					try:
						self.config[section][key[0]] = ast.literal_eval(key[1])
					except:
						self.config[section][key[0]] = key[1]
			except:
				traceback.print_exc()
				self.parser.add_section(section)
				self.log.debug("Adding section [%s] to configuration" % section)
				self.config[section] = {}
				self.exit = True
		
		for section in defaults:
			for item in defaults[section]:
				if item not in self.config[section]:
					self.config[section][item] = defaults[section][item]
					self.parser.set(section, item, defaults[section][item])
					self.log.debug("key %s in section %s not in wrapper.properties - adding" % (item, section))
					self.exit = True
				else:
					for key in keys:
						try:
							self.config[section][key[0]] = ast.literal_eval(key[1])
						except:
							self.config[section][key[0]] = key[1]
#					self.config[section][item] = self.parser.get(section, item)
		self.save()
		if self.exit:
			self.log.info("Updated wrapper.properties with new entries - edit configuration if needed and start again")
			sys.exit()
	def save(self):
		self.parser.write(open("wrapper.properties", "wb"))

class Server:
	def __init__(self, args, logger):
		self.log = logger
		self.players = []
		self.status = 0 # 0 is off, 1 is starting, 2 is started, 3 is shutting down
		self.halt = False
		self.server = True
		self.sock = False
		self.messages = []
		self.timeout = 0
		self.currentSecond = 0
		self.backupInterval = 0
		self.authorized = {}
		self.data = ""
		self.backups = []
	def login(self, user):
		if user not in self.players:
			self.players.append(user)
	def logout(self, user):
		for i,u in enumerate(self.players):
			if u == user:
				del self.players[i]
	def argserver(self, i):
		try:
			return self.line.split(' ')[i]
		except:
			return False
	def write(self, string):
		try:
			server.proc.stdin.write(string)
		except:
			pass
	# -- IRC functions -- #
	def filterName(self, name):
		if self.config["IRC"]["obstruct-nicknames"]:
			return "_" + name[1:]
		else:
			return name 
	def send(self, string):
		try:
			self.sock.send('%s\n' % string)
			return True
		except socket.error:
			self.log.error("Socket error while sending -- disconnected")
			self.sock = False
			return False
	def args(self, i):
		try:
			return self.buffer.split(' ')[i]
		except:
			pass
	def everyNth(self, str, j):
		a = []
		z = 0
		b = 0
		a.append('')
		for i in str:
			a[b] += i
			if z == j:
				z = 0
				b+=1
				a.append('')
			else:
				z+=1
		return a
	def parse(self):
		for message in self.messages:
			for channel in self.config["IRC"]["channels"]:
				self.send('PRIVMSG %s :%s' % (channel, message))
		self.messages = []
		if self.args(1) == "001":
			for command in self.config["IRC"]["autorun-irc-commands"]:
				self.send(command)
			for channel in self.config["IRC"]["channels"]:
				self.send('JOIN %s' % channel)
			self.log.info("Connected to IRC")
			self.state = True
		if self.args(1) == "JOIN":
			nick = self.args(0)[1:self.args(0).find('!')]
			channel = self.args(2)[1:][:-1]
			self.log.info('%s joined %s' % (nick, channel))
			print "JOIN: %s" % channel
			if self.config["IRC"]['show-channel-server']:
				self.console('\xc2\xa76[%s] \xc2\xa7a%s \xc2\xa7fjoined\n' % (channel, nick))
			else:
				self.console('\xc2\xa7a%s \xc2\xa7fjoined\n' % nick)
		if self.args(1) == "PART":
			nick = self.args(0)[1:self.args(0).find('!')]
			channel = self.args(2)
			self.log.info('%s parted from %s' % (nick, channel))
			if self.config["IRC"]["show-channel-server"]:
				self.console('\xc2\xa76[%s] \xc2\xa7a%s \xc2\xa7fparted\n' % (channel, nick))
			else:
				self.console('\xc2\xa7a%s \xc2\xa7fparted\n' % nick)
		if self.args(1) == "MODE":
			try:
				nick = self.args(0)[1:self.args(0).find('!')]
				channel = self.args(2)
				modes = self.args(3)
				user = self.args(4)[:-1]
				self.console('\xc2\xa76[%s] \xc2\xa7a%s \xc2\xa7freceived modes %s from %s' % (channel, user, modes, nick))
			except:
				pass
		if self.args(0) == 'PING':
			self.send('PONG %s' % self.args(1))
		if self.args(1) == 'PRIVMSG':
			channel = self.args(2)
			nick = self.args(0)[1:self.args(0).find('!')]
			message = ' '.join(self.buffer.split(' ')[3:])[1:].strip('\n').strip('\r')
			
			if channel[0] == '#':
				if message.strip() == '.players':
					users = ''
					for user in server.players:
						users += '%s ' % user
					self.send('PRIVMSG %s :There are currently %s users on the server: %s' % (channel, len(server.players), users))
				else:
					self.log.info('[%s] (%s) %s' % (channel, nick, message))
					for msg in self.everyNth(message, 80):
						if self.config["IRC"]["show-channel-server"]:
							self.console('\xc2\xa76[%s] \xc2\xa7a(%s) \xc2\xa7f%s' % (channel, nick, msg))
						else:
							self.console('\xc2\xa7a(%s) \xc2\xa7f%s' % (nick, msg))
			elif self.config["IRC"]["control-from-irc"]:
				self.log.info('[PRIVATE] (%s) %s' % (nick, message))
				def args(i):
					try:
						return message.split(' ')[i]
					except:
						return ""
				def msg(string):
					print "[PRIVATE] (%s) %s" % (self.config["IRC"]["nick"], string)
					self.send('PRIVMSG %s :%s' % (nick, string))
				if nick in self.authorized:
					if int(time.time()) - self.authorized[nick] < 900:
						if args(0) == 'hi':
							msg('Hey there!')
						elif args(0) == 'help':
							msg('run [command] - run command on server')
							msg('togglebackups - temporarily turn backups on or off. this setting is not permanent and will be lost on restart')
							msg('halt - shutdown server and Wrapper.py, will not auto-restart')
							msg('restart - automatically shuts down and restarts the server')
							msg('Wrapper.py version %s by benbaptist' % Config.version)
							#msg('console - toggle console output to this private message')
						elif args(0) == 'togglebackups':
							self.config["Backups"]["enabled"] = not self.config["Backups"]["enabled"]
							if self.config["Backups"]["enabled"]:
								msg('Backups are now on.')
							else:
								msg('Backups are now off.')
							configure.save()
						elif args(0) == 'run':
							if args(1) == '':
								msg('Usage: run [command]')
							else:
								command = " ".join(message.split(' ')[1:])
								self.run(command)
						elif args(0) == 'halt':
							self.halt = True
							self.run('stop')
						elif args(0) == 'restart':
							self.run('stop')
						elif args(0) == "about":
							msg("Wrapper.py by benbaptist - version %s" % Config.version)
						else:
							msg('Unknown command. Type help for more commands')
					else:
						msg("Session expired, re-authorize.")
						del self.authorized[nick]
				else:
					if args(0) == 'auth':
						if args(1) == self.config["IRC"]["control-irc-pass"]:
							msg("Authorization success! You'll remain logged in for 15 minutes.")
							self.authorized[nick] = int(time.time())
						else:
							msg("Invalid password.")
					else:
						msg('Not authorized. Type "auth password" to login.')
	def authorize(self):
		self.send('NICK %s' % self.config["IRC"]["nick"])
		self.send('USER %s 0 *: %s' % (self.config["IRC"]["nick"], self.config["IRC"]["nick"]))
	def msg(self, message):
		self.messages.append(message)
	def handle(self):
		if not self.sock:
			try:
				self.log.info('Connecting to %s:%s...' % (self.config["IRC"]["server"], str(self.config["IRC"]["port"])))
				self.sock = socket.socket()
				self.sock.connect((self.config["IRC"]["server"], int(self.config["IRC"]["port"])))
				self.sock.settimeout(0.1)
				self.authorize()
			except:
				self.log.error("Could not connect - reconnecting")
				time.sleep(1)
		else:
			try:
				buffer = self.sock.recv(1024)
				if buffer == "":
					self.log.error("Disconnected from IRC")
					self.sock = False
					return False
			except socket.timeout:
				buffer = ""
			except:
				buffer = ""
			if len(buffer) == 0:
				self.timeout += 1
				if self.timeout == 60:
					self.send('PING :%s' % self.randomString())
			for line in buffer.split('\n'):
				self.buffer = line
				self.timeout = 0
				self.parse()
	# -- server management -- #
	def announce(self, text):
		for channel in self.config["IRC"]["channels"]:
			self.send('PRIVMSG %s :%s' % (channel, text))
		self.console()
	def console(self, text):
		if not self.config["General"]["pre-1.7-mode"]:
			self.proc.stdin.write('tellraw @a %s\n' % json.dumps({"text": text}))
		else:
			self.proc.stdin.write('say %s\n' % text)
	def run(self, text):
		self.proc.stdin.write('%s\n' % text)
	def capture(self):
		while not self.halt:
			time.sleep(0.05)
			try:
				data = self.proc.stdout.readline()
				if len(data) > 0:
					self.data += data
			except:
				print "error"
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
	def startServer(self):
		while not self.halt:
			if not self.server:
				time.sleep(1)
				continue
			self.status = 1
			self.log.info("Starting server...")
			self.proc = subprocess.Popen(self.serverArgs, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
			while True:
				# backups
				if self.currentSecond == int(time.time()):
					""
				else:
					self.backupInterval += 1
					self.currentSecond = int(time.time())
				if self.backupInterval == self.config["Backups"]["backup-interval"] and self.config["Backups"]["enabled"]:
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
					for channel in self.config["IRC"]["channels"]:
						self.send('PRIVMSG %s :Backing up, IRC bridge will freeze and lag may occur' % (channel))
					if self.config["Backups"]["backup-notification"]:
						self.console('\xc2\xa7bBacking up, IRC bridge will freeze and lag may occur')
					timestamp = int(time.time())
					filename = 'backup-%s.tar' % datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d_%H:%M:%S')
					server.write('save-all\n')
					server.write('save-off\n')
					time.sleep(0.5)
	
					if not os.path.exists(str(self.config["Backups"]["backup-location"])):
						os.mkdir(self.config["Backups"]["backup-location"])
					
					arguments = ["tar", "cfpv", '%s/%s' % (self.config["Backups"]["backup-location"], filename)]
					for file in self.config["Backups"]["backup-folders"]:
						arguments.append(file)
					statusCode = os.system(' '.join(arguments))
					server.write('save-on\n')
					if self.config["Backups"]["backup-notification"]:
						if statusCode == 0:
							self.console('\xc2\xa7aBackup complete!')
							for channel in self.config["IRC"]["channels"]:
								self.send('PRIVMSG %s :Backup complete!' % (channel))
						else:
							pass
							#self.console('\xc2\xa7cBackup potentially failed - tar exited with status code %d - contact server admin immediately' % int(statusCode))
							#for channel in self.config["IRC"]["channels"]:
							#	self.send('PRIVMSG %s :Backup potentially failed - tar exited with status code %d - contact server admin immediately' % (channel, int(statusCode)))
					self.backups.append((timestamp, 'backup-%s.tar' % datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d_%H:%M:%S')))
					
					if len(self.backups) > self.config["Backups"]["backups-keep"]:
						self.log.info("Deleting old backups...")
#						for i,backup in enumerate(self.backups.sort()):
						while len(self.backups) > self.config["Backups"]["backups-keep"]:
							backup = self.backups[0]
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
				# handle IRC
				if self.config["IRC"]["enabled"]:
					self.handle()
				if self.proc.poll() is not None:
					self.msg("Server shutdown")
					self.log.info('Server shutdown')
					if not self.config["General"]["auto-restart"]:
						self.halt = True
					break
				if len(self.data) > 0:
					data = self.data[:]
					self.data = ""
				else:
					data = ""
				deathPrefixes = ['fell', 'was', 'drowned', 'blew', 'walked', 'went', 'burned', 'hit', 'tried', 'died', 'got', 'starved', 'suffocated', 'withered']
				for line in data.split('\n'):
					if len(line) < 1: continue
					self.line = line
					print line
					if self.argserver(3) is not False:
						if not self.config["General"]["pre-1.7-mode"]:
							if self.argserver(3)[0] == "<":
								name = self.formatForIRC(self.filterName(self.argserver(3)[1:self.argserver(3).find('>')].replace("\xc2\xfa", "")))
								message = self.formatForIRC(" ".join(line.split(' ')[4:]).replace('\x1b', '').strip('[m').replace("\xc2\xfa", ""))
								self.msg("<%s> %s" % (name, message))
							elif self.argserver(4) == "logged":
								name = self.formatForIRC(self.filterName(self.argserver(3)[0:self.argserver(3).find('[')]))
								self.msg("[%s connected]" % name)
								self.login(name)
							elif self.argserver(4) == 'lost':
								name = self.filterName(self.argserver(3))
								self.msg("[%s disconnected]" % (name))
								self.logout(name)
							elif self.argserver(4) == 'issued':
								name = self.filterName(self.argserver(3))
								command = message = ' '.join(line.split(' ')[7:])
								if self.config["IRC"]["forward-commands-to-irc"]:
									self.msg("%s issued command: %s" % (name, command))
							elif self.argserver(3) == 'Done':
								self.status = 2
								self.msg("Server started")
							elif self.argserver(4) in deathPrefixes:
								self.msg(' '.join(self.line.split(' ')[3:]))
								name = self.filterName(self.argserver(3))
								deathMessage = self.config["Death"]["death-kick-messages"][random.randrange(0, len(self.config["Death"]["death-kick-messages"]))]
								if self.config["Death"]["kick-on-death"] and name in self.config["Death"]["users-to-kick"]:
									server.proc.stdin.write('kick %s %s\n\r' % (name, deathMessage))
							elif self.argserver(3) == "*":
								name = self.filterName(self.argserver(4))
								message = message = ' '.join(line.split(' ')[5:])
								self.msg("* %s %s" % (name, message))
							elif self.argserver(4) == "has" and self.argserver(8) == "achievement":
								name = self.filterName(self.argserver(3))
								achievement = ' '.join(line.split(' ')[9:])
								self.msg("%s has just earned the achievement %s" % (name, achievement))
						else: # -- FOR 1.6.4 AND PREVIOUSLY ONLY!!!!! -- 
							if self.argserver(2)[0] == '<':
								name = self.filterName(self.argserver(2)[1:self.argserver(2).find('>')].replace("\xc2\xfa", ""))
								message = ' '.join(line.split(' ')[3:]).replace('\x1b', '').strip('[m').replace("\xc2\xfa", "")
								self.msg('<%s> %s' % (name, message))
							elif self.argserver(3) == 'logged':
								name = self.argserver(2)[0:self.argserver(2).find('[')]
								self.msg('[%s connected]' % name)
								self.login(name)
							elif self.argserver(3) == 'lost':
								name = self.argserver(2)
								reason = self.argserver(5)
								self.msg('[%s disconnected] (%s)' % (name, reason))
								self.logout(name)
							elif self.argserver(3) == 'Kicked':
								name = self.argserver(6)
								self.msg('[%s disconnected] (kicked)' % name)
								self.logout(name)
							elif self.argserver(3) == 'issued':
								name = self.argserver(2)
								command = message = ' '.join(line.split(' ')[6:])
								if self.config["forwardCommandsToIRC"]:
									self.msg('%s issued command: %s' % (name, command))
							elif self.argserver(2) == 'Done':
								self.status = 2
								self.msg('Server started')
							elif self.argserver(3) in deathPrefixes:
								self.msg(' '.join(self.line.split(' ')[2:]))
								name = self.argserver(2)
								randThing = self.config["deathKickMessages"][random.randrange(0, len(self.config["deathKickMessages"]))]
								if self.config["deathKick"] and name in self.config["deathKickers"]:
									server.proc.stdin.write('kick %s %s\n\r' % (name, randThing))
				time.sleep(0.1)

class Log:
	def __init__(self):
		pass
	def timestamp(self):
		return time.strftime("[%H:%M:%S]")
		#return "%s:%s:%s" % (str(datetime.datetime.time(datetime.datetime.now()).hour), str(datetime.datetime.time(datetime.datetime.now()).minute), datetime.datetime.time(datetime.datetime.now()).second)
	def info(self, string):
		print "%s [Wrapper.py/INFO] %s" % (self.timestamp(), string)
	def error(self, string):
		print "%s [Wrapper.py/ERROR] %s" % (self.timestamp(), string)
	def debug(self, string):
		if Config.debug:
			print "%s [Wrapper.py/DEBUG] %s" % (self.timestamp(), string)

def consoleWatch():
	while not server.halt:
		input = raw_input('> ')
		if input == "/halt":
			server.run("stop")
			server.halt = True
		elif input == "/stop":
			server.run("stop")
			server.server = False
		elif input == "/start":
			server.server = True
		elif input == "/restart":
			server.run("stop")
		else:
			try:
				server.proc.stdin.write('%s\n' % input)
			except:
				break
def instantEnd(signal, frame):
	server.halt = True
	sys.exit()
signal.signal(signal.SIGINT, instantEnd)
logger = Log()
server = Server(sys.argv, logger)
configure = Config(logger)
configure.loadConfig()
if len(sys.argv) < 2:
	server.serverArgs = configure.config["General"]["command"].split(" ")
else:
	server.serverArgs = sys.argv[1:]
server.config = configure.config
captureThread = threading.Thread(target=server.capture, args=())
captureThread.daemon = True
captureThread.start()
consoleWatchT = threading.Thread(target=consoleWatch, args=())
consoleWatchT.daemon = True
consoleWatchT.start()
try:
	server.startServer()
except:
	logger.error("Wrapper.py crashed - stopping sever to be safe")
	for line in traceback.format_exc().split("\n"):
		logger.error(line)
	server.halt = True
	try:
		for player in server.players:
			server.run("kick %s Wrapper.py crashed - please contact a server admin instantly" % player)
		server.run("save-all")
		server.run("stop")
	except:
		pass
