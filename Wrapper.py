import socket, datetime, time, sys, threading, random, subprocess, os, json, signal

# Minecraft IRC Wrapper by Ben Baptist -- Version 0.3.1
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
# - fix the Wrapper not reconnecting to IRC (needs to)
# - other fixes
# version 0.3.1 changelog:
# - removed StringIO module import, it was useless
# - fixed crash while trying to send error message to IRC when backups.json was unreadable
# - Wrapper.py now kicks users and shuts down the server when it crashes
# bugs needing fixed:
# - fixing pre-1.7 servers not working (even with newMode set to False)
# to-do list:
# - maybe add some in-game commands such as /halt
# - web interface?

# configuration
class Config:
	nick = 'MinecraftIRC'
	server = 'benbaptist.com'
	port = 6667
	channels = ['#main'] # channels to join
	autoCommands = ['COMMAND 1', 'COMMAND 2'] # these commands run on start
	showChannelServer = True # This will hide the channel name from the IRC messages on the Minecraft server, thus reducing the amount of size each messages takes up on screen
	commandsShowOnIRC = False # this will output ANY user command to the IRC channel for all to see. beware if typing passwords/private messages/etc.
	newMode = True # for Minecraft 1.7 and above, set this to true, otherwise set to False for older versions
	
	backup = False # on or off switch
	backupKeep = 10 # how many backups do you wish to keep?
	backupLocation = 'backup-location' # where to keep backups. best to use empty folder.
	backupFolders = ['server.log', 'server.properties', 'world', 'world_nether', 'world_the_end', 'white-list.txt'] # specify files and folders to back up. DO NOT SPECIFY THE BACKUP FOLDER HERE. EFFECTS ARE WORSE THAN DIVIDING BY ZERO.
	backupInterval = 3600 # in seconds. 3600 seconds == one hour.
	backupNotification = True
	
	deathKick = False
	deathKickers = ['JohnnyDiesalot', 'MisterDeath']
	deathKickMessages = ['You died!']
	
	IRCControls = True # control server operations by messaging the IRC bot
	IRCPass = 'password' # this password will be used when controlling the bot
	
	autoRestart = True # automatically restart the server when it shuts down

class Server:
	def __init__(self, args, logger):
		self.serverArgs = ' '.join(args)
		self.log = logger
		self.players = []
		self.status = 0 # 0 is off, 1 is starting, 2 is started, 3 is shutting down
		self.halt = False
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
			for channel in Config.channels:
				self.send('PRIVMSG %s :%s' % (channel, message))
		self.messages = []
		if self.args(1) == '001':
			for command in Config.autoCommands:
				self.send(command)
			for channel in Config.channels:
				self.send('JOIN %s' % channel)
			self.log.info('Connected to IRC!')
			self.state = True
		if self.args(1) == 'JOIN':
			nick = self.args(0)[1:self.args(0).find('!')]
			channel = self.args(2)[1:][:-1]
			self.log.info('%s joined %s' % (nick, channel))
			print "JOIN: %s" % channel
			if Config.showChannelServer:
				self.console('\xc2\xa76[%s] \xc2\xa7a%s \xc2\xa7fjoined\n' % (channel, nick))
			else:
				self.console('\xc2\xa7a%s \xc2\xa7fjoined\n' % nick)
		if self.args(1) == 'PART':
			nick = self.args(0)[1:self.args(0).find('!')]
			channel = self.args(2)
			self.log.info('%s parted from %s' % (nick, channel))
			if Config.showChannelServer:
				self.console('\xc2\xa76[%s] \xc2\xa7a%s \xc2\xa7fparted\n' % (channel, nick))
			else:
				self.console('\xc2\xa7a%s \xc2\xa7fparted\n' % nick)
		if self.args(1) == 'MODE':
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
						if Config.showChannelServer:
							self.console('\xc2\xa76[%s] \xc2\xa7a(%s) \xc2\xa7f%s' % (channel, nick, msg))
						else:
							self.console('\xc2\xa7a(%s) \xc2\xa7f%s' % (nick, msg))
			elif Config.IRCControls:
				self.log.info('[PRIVATE] (%s) %s' % (nick, message))
				def args(i):
					try:
						return message.split(' ')[i]
					except:
						return ""
				def msg(string):
					print "[PRIVATE] (%s) %s" % (Config.nick, string)
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
							#msg('console - toggle console output to this private message')
						elif args(0) == 'togglebackups':
							Config.backup = not Config.backup
							if Config.backup:
								msg('Backups are now on.')
							else:
								msg('Backups are now off.')
						elif args(0) == 'run':
							if args(1) == '':
								msg('Usage: run [command]')
							else:
								command = ' '.join(message.split(' ')[1:])
								self.run(command)
						elif args(0) == 'halt':
							self.halt = True
							self.run('stop')
						elif args(0) == 'restart':
							self.run('stop')
						else:
							msg('Unknown command. Type help for more commands')
					else:
						msg('Session expired, re-authorize.')
						del self.authorized[nick]
				else:
					if args(0) == 'auth':
						if args(1) == Config.IRCPass:
							msg("Authorization success! You'll remain logged in for 15 minutes.")
							self.authorized[nick] = int(time.time())
						else:
							msg("Invalid password.")
					else:
						msg('Not authorized. Type "auth password" to login.')
	def authorize(self):
		self.send('NICK %s' % Config.nick)
		self.send('USER %s 0 *: %s' % (Config.nick, Config.nick))
	def msg(self, message):
		self.messages.append(message)
	def handle(self):
		if not self.sock:
			self.log.info('Connecting to %s:%s...' % (Config.server, str(Config.port)))
			self.sock = socket.socket()
			self.sock.connect((Config.server, Config.port))
			self.sock.settimeout(0.1)
			self.authorize()
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
	def console(self, text):
		if Config.newMode:
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
	def startServer(self):
		while not self.halt:
			self.status = 1
			self.log.info('Starting server...')
			self.proc = subprocess.Popen(self.serverArgs.split(' ')[1:], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
			while True:
				# backups
#				print [int(time.time()) is not self.currentSecond, (self.currentSecond, int(time.time()))]
				if self.currentSecond == int(time.time()):
					""
				else:
					self.backupInterval += 1
					self.currentSecond = int(time.time())
				if self.backupInterval == Config.backupInterval and Config.backup:
					self.backupInterval = 0
					if len(self.backups) == 0 and os.path.exists(Config.backupLocation + "/backups.json"):
						f = open(Config.backupLocation + "/backups.json", "r")
						try:
							self.backups = json.loads(f.read())
						except:
							self.log.error("NOTE - backups.json was unreadable. This might be due to corruption. This might lead to backups never being deleted.")
							for channel in Config.channels:
								self.send('PRIVMSG %s :ERROR - backups.json is corrupted. Please contact an administer instantly, this may be critical.' % (channel))
							self.backups = []
						f.close()
					else:
						if len(os.listdir(Config.backupLocation)) > 0:
							# import old backups from previous versions of Wrapper.py
							backupTimestamps = []
							for backupNames in os.listdir(Config.backupLocation):
								try:
									backupTimestamps.append(int(backupNames[backupNames.find('-')+1:backupNames.find('.')]))
								except:
									pass
							backupTimestamps.sort()
							for backupI in backupTimestamps:
								self.backups.append((int(backupI), "backup-%s.tar" % str(backupI)))
					for channel in Config.channels:
						self.send('PRIVMSG %s :Backing up, IRC bridge will freeze and lag may occur' % (channel))
					if Config.backupNotification:
						self.console('\xc2\xa7bBacking up, IRC bridge will freeze and lag may occur')
					timestamp = int(time.time())
					filename = 'backup-%s.tar' % datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d_%H:%M:%S')
					server.write('save-on\n')
					server.write('save-all\n')
	
					if not os.path.exists(Config.backupLocation):
						os.mkdir(Config.backupLocation)
					
					arguments = ["tar", "cfpv", '%s/%s' % (Config.backupLocation, filename)]
					for file in Config.backupFolders:
						arguments.append(file)
					statusCode = os.system(' '.join(arguments))
					if Config.backupNotification:
						if statusCode == 0:
							self.console('\xc2\xa7aBackup complete!')
							for channel in Config.channels:
								self.send('PRIVMSG %s :Backup complete!' % (channel))
						else:
							self.console('\xc2\xa7cBackup potentially failed - tar exited with status code %d - contact server admin immediately' % int(statusCode))
							for channel in Config.channels:
								self.send('PRIVMSG %s :Backup potentially failed - tar exited with status code %d - contact server admin immediately' % (channel, int(statusCode)))
					self.backups.append((timestamp, 'backup-%s.tar' % datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d_%H:%M:%S')))
					
					if len(self.backups) > Config.backupKeep:
						self.log.info("Deleting old backups...")
#						for i,backup in enumerate(self.backups.sort()):
						while len(self.backups) > Config.backupKeep:
							backup = self.backups[0]
							try:
								os.remove('%s/%s' % (Config.backupLocation, backup[1]))
							except:
								print "Failed to delete"
							self.log.info("Deleting old backup: %s" % datetime.datetime.fromtimestamp(int(backup[0])).strftime('%Y-%m-%d_%H:%M:%S'))
							hink = self.backups[0][1][:]
							del self.backups[0]
					f = open(Config.backupLocation + "/backups.json", "w")
					f.write(json.dumps(self.backups))
					f.close()
#							
#						for i,e in enumerate(self.backups):
#							if zonk > Config.backupKeep:				
#								markedForDeletion.append(e)
#						for timestamp in markedForDeletion:
#							os.remove('%s/backup-%s.tar' % (Config.backupLocation, timestamp))
				# handle IRC
				self.handle()
				if self.proc.poll() is not None:
					self.msg('Server shutting down')
					self.log.info('Server shutdown')
					if not Config.autoRestart:
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
						if Config.newMode:
							if self.argserver(3)[0] == '<':
								name = self.argserver(3)[1:self.argserver(3).find('>')].replace("\xc2\xfa", "")
								message = ' '.join(line.split(' ')[4:]).replace('\x1b', '').strip('[m').replace("\xc2\xfa", "")
								self.msg('<%s> %s' % (name, message))
							elif self.argserver(4) == 'logged':
								name = self.argserver(3)[0:self.argserver(3).find('[')]
								self.msg('[%s connected]' % name)
								self.login(name)
							elif self.argserver(4) == 'lost':
								name = self.argserver(3)
								reason = self.argserver(6)
								self.msg('[%s disconnected] (%s)' % (name, reason))
								self.logout(name)
							elif self.argserver(4) == 'Kicked':
								name = self.argserver(6)
							elif self.argserver(4) == 'issued':
								name = self.argserver(3)
								command = message = ' '.join(line.split(' ')[7:])
								if Config.commandsShowOnIRC:
									self.msg('%s issued command: %s' % (name, command))
							elif self.argserver(3) == 'Done':
								self.status = 2
								self.msg('Server started')
							elif self.argserver(4) in deathPrefixes:
								self.msg(' '.join(self.line.split(' ')[3:]))
								name = self.argserver(3)
								randThing = Config.deathKickMessages[random.randrange(0, len(Config.deathKickMessages))]
								if Config.deathKick and name in Config.deathKickers:
									server.proc.stdin.write('kick %s %s\n\r' % (name, randThing))
						else: # -- FOR 1.6.4 AND PREVIOUSLY ONLY!!!!! -- 
							if self.argserver(2)[0] == '<':
								name = self.argserver(2)[1:self.argserver(2).find('>')].replace("\xc2\xfa", "")
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
								if Config.commandsShowOnIRC:
									self.msg('%s issued command: %s' % (name, command))
							elif self.argserver(2) == 'Done':
								self.status = 2
								self.msg('Server started')
							elif self.argserver(3) in deathPrefixes:
								self.msg(' '.join(self.line.split(' ')[2:]))
								name = self.argserver(2)
								randThing = Config.deathKickMessages[random.randrange(0, len(Config.deathKickMessages))]
								if Config.deathKick and name in Config.deathKickers:
									server.proc.stdin.write('kick %s %s\n\r' % (name, randThing))
				time.sleep(0.1)

class Log:
	def __init__(self):
		pass
	def timestamp(self):
		return "%s:%s:%s" % (str(datetime.datetime.time(datetime.datetime.now()).hour), str(datetime.datetime.time(datetime.datetime.now()).minute), datetime.datetime.time(datetime.datetime.now()).second)
	def info(self, string):
		print "%s [INFO] %s" % (self.timestamp(), string)
	def error(self, string):
		print "%s [ERROR] %s" % (self.timestamp(), string)

def consoleWatch():
	while not server.halt:
		input = raw_input('> ')
		if input == "/halt":
			server.run("stop")
			server.halt = True
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
captureThread = threading.Thread(target=server.capture, args=())
captureThread.daemon = True
captureThread.start()
consoleWatchT = threading.Thread(target=consoleWatch, args=())
consoleWatchT.daemon = True
consoleWatchT.start()
try:
	server.startServer()
except:
	server.halt = True
	for player in server.players:
		server.run("kick %s Wrapper.py crashed - please contact a server admin instantly" % player)
	server.run("save-all")
	server.run("stop")