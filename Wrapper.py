from cStringIO import StringIO
import socket, datetime, time, sys, threading, random, subprocess, os

# Minecraft IRC Wrapper by Ben Baptist -- Version 0.2
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
# bugs needing fixed:
# - none that I can think of
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
	showChannelServer = False # This will hide the channel name from the IRC messages on the Minecraft server, thus reducing the amount of size each messages takes up on screen
	commandsShowOnIRC = False # this will output ANY user command to the IRC channel for all to see. beware if typing passwords/private messages/etc.
	
	backup = False # on or off switch
	backupKeep = 25 # how many backups do you wish to keep?
	backupLocation = 'backup-location' # this folder MUST BE EMPTY.
	backupFolders = ['server.log', 'server.properties', 'world', 'world_nether', 'world_the_end', 'white-list.txt'] # specify files and folders to back up. DO NOT SPECIFY THE BACKUP FOLDER HERE. EFFECTS ARE WORSE THAN DIVIDING BY ZERO.
	backupInterval = 3600 # in seconds. 3600 seconds == one hour.
	
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
			print message
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
				print buffer
			except socket.timeout:
				buffer = ''
				#self.sock = False
				#self.log.error('Disconnected from IRC, reconnecting')
				#return ""
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
		self.proc.stdin.write('say %s\n' % text)
	def run(self, text):
		self.proc.stdin.write('%s\n' % text)
	def startServer(self):
		while not self.halt:
			self.status = 1
			self.log.info('Starting server...')
			self.proc = subprocess.Popen(self.serverArgs.split(' ')[1:], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
			serverLogLength = os.path.getsize('server.log')
			while True:
				# backups
				if int(time.time()) is not self.currentSecond:
					self.backupInterval += 1
					self.currentSecond = int(time.time())
				if self.backupInterval == Config.backupInterval and Config.backup:
					self.backupInterval = 0
					for channel in Config.channels:
						self.send('PRIVMSG %s :Conducting backup. IRC/Server connection may lag for a bit.' % (channel))
					server.write('say Conducting backup... server and IRC/server bridge may lag...\n')
					filename = 'backup-%s.tar' % str(int(time.time()))
					server.write('save-on\n')
					server.write('save-all\n')
	
					if not os.path.exists(Config.backupLocation):
						os.mkdir(Config.backupLocation)
					
					arguments = ["tar", "cfpv", '%s/%s' % (Config.backupLocation, filename)]
					for file in Config.backupFolders:
						arguments.append(file)
					os.system(' '.join(arguments))
					server.write('say Backup Complete!\n')
					
					if len(os.listdir(Config.backupLocation)) > Config.backupKeep:
						print "Pruning old backups..."
						backupTimestamps = []
						for backupNames in os.listdir(Config.backupLocation):
							backupTimestamps.append(int(backupNames[backupNames.find('-')+1:backupNames.find('.')]))
						backupTimestamps.sort()
						markedForDeletion = []
						zonk = len(backupTimestamps)
						for i,e in enumerate(backupTimestamps):
							if zonk > Config.backupKeep:
								print "Deleting: %s" % datetime.datetime.fromtimestamp(int(e)).strftime('%Y-%m-%d %H:%M:%S')					
								markedForDeletion.append(e)
								zonk = zonk - 1
						for timestamp in markedForDeletion:
							os.remove('%s/backup-%s.tar' % (Config.backupLocation, timestamp))
				# handle IRC
				self.handle()
				if self.proc.poll() is not None:
					self.msg('Server shutting down')
					self.log.info('Server shutdown')
					if not Config.autoRestart:
						self.halt = True
					break
				if os.path.getsize('server.log') > serverLogLength:
					f = open('server.log', 'r')
					f.seek(serverLogLength)
					data = f.read()
					serverLogLength = os.path.getsize('server.log')
					f.close()
					deathPrefixes = ['fell', 'was', 'drowned', 'blew', 'wakled', 'went', 'burned', 'hit', 'tried', 'died', 'got', 'starved', 'suffocated', 'withered']
					#print "poll: %s" % str(self.proc.poll())
					for line in data.split('\n'):
						if len(line) < 1: continue
						self.line = line
						#if self.args(3) == 'Stopping' and self.args(4) == 'server':
						#	self.log.info('Server shutdown')
						#	self.halt = True
						if self.argserver(3) is not False:
							if self.argserver(3)[0] == '<':
								name = self.argserver(3)[1:self.argserver(3).find('>')]
								message = ' '.join(line.split(' ')[4:]).replace('\x1b', '').strip('[m')
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
								self.msg('%s disconnected: kicked' % (name, reason))
								self.logout(name)
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
								deathKicks = ['You died! Kicked from server.']
								randThing = Config.deathKickMessages[random.randrange(0, len(Config.deathKickMessages))]
								print Config.deathKick 
								print name in Config.deathKickers
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
	while irc.reconnect:
		input = raw_input('> ')
		#if input[0] == '/':
		#	pass
		#else:
		try:
			server.proc.stdin.write('%s\n' % input)
		except:
			break
	print "input loop ended"
time.sleep(0.5)
logger = Log()
#consoleWatchT = threading.Thread(target=consoleWatch, args=())
#consoleWatchT.start()
server = Server(sys.argv, logger)
server.startServer()
