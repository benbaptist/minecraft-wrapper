import socket, traceback, time, threading, api, globals, random
from config import Config
class IRC:
	def __init__(self, server, config, log, wrapper, address, port, nickname, channels):
		self.socket = False
		self.server = server
		self.config = config
		self.wrapper = wrapper
		self.address = address
		self.port = port
		self.nickname = nickname
		self.originalNickname = nickname[0:]
		self.nickAttempts = 0
		self.channels = channels
		self.log = log
		self.timeout = False
		self.ready = False
		self.msgQueue = []
		
		self.api = api.API(self.wrapper, "IRC")
		self.api.registerEvent("server.starting", self.onServerStarting)
		self.api.registerEvent("server.started", self.onServerStarted)
		self.api.registerEvent("server.stopping", self.onServerStopping)
		self.api.registerEvent("server.stopped", self.onServerStopped)
		self.api.registerEvent("player.login", self.onPlayerLogin)
		self.api.registerEvent("player.message", self.onPlayerMessage)
		self.api.registerEvent("player.action", self.onPlayerAction)
		self.api.registerEvent("player.logout", self.onPlayerLogout)
		self.api.registerEvent("player.achievement", self.onPlayerAchievement)
		self.api.registerEvent("player.death", self.onPlayerDeath)
		self.api.registerEvent("server.say", self.onPlayerSay)
	def init(self):
		while not self.wrapper.halt:
			try:
				self.log.info("Connecting to IRC...")
				self.connect()
				t = threading.Thread(target=self.queue, args=())
				t.daemon = True
				t.start()
				self.handle()
			except:
				for line in traceback.format_exc().split("\n"):
					self.log.error(line)
				self.disconnect("Error in Wrapper.py - restarting")
			self.log.info("Disconnected from IRC")
			time.sleep(5)
	def connect(self):
		self.nickname = self.originalNickname[0:]
		self.socket = socket.socket()
		self.socket.connect((self.address, self.port))
		self.socket.setblocking(120)
		
		self.auth()
	def auth(self):
		self.send("NICK %s" % self.nickname)
		self.send("USER %s 0 * :%s" % (self.nickname, self.nickname))
	def disconnect(self, message):
		try:
			self.send("QUIT :%s" % message)
			self.socket.close()
			self.socket = False
		except:
			pass
	def send(self, payload):
		if self.socket:
			self.socket.send("%s\n" % payload)
		else:
			return False
	def onPlayerLogin(self, payload):
		player = self.filterName(payload["player"])
		self.msgQueue.append("[%s connected]" % player)
	def onPlayerLogout(self, payload):
		player = self.filterName(payload["player"])
		self.msgQueue.append("[%s disconnected]" % player)
	def onPlayerMessage(self, payload):
		player = self.filterName(payload["player"])
		message = payload["message"]
		self.msgQueue.append("<%s> %s" % (player, message))
	def onPlayerAction(self, payload):
		player = self.filterName(payload["player"])
		action = payload["action"]
		self.msgQueue.append("* %s %s" % (player, action))
	def onPlayerSay(self, payload):
		player = self.filterName(payload["player"])
		message = payload["message"]
		self.msgQueue.append("[%s] %s" % (player, message))
	def onPlayerAchievement(self, payload):
		player = self.filterName(payload["player"])
		achievement = payload["achievement"]
		self.msgQueue.append("%s has just earned the achievement %s" % (player, achievement))
	def onPlayerDeath(self, payload):
		player = self.filterName(payload["player"])
		death = payload["death"]
		self.msgQueue.append("%s %s" % (player, death))
	def onServerStarting(self, payload):
		self.msgQueue.append("Server starting...")
	def onServerStarted(self, payload):
		self.msgQueue.append("Server started!")
	def onServerStopping(self, payload):
		self.msgQueue.append("Server stopping...")
	def onServerStopped(self, payload):
		self.msgQueue.append("Server stopped!")
	def handle(self):
		while self.socket:
			try:
				buffer = self.socket.recv(1024)
				if buffer == "":
					self.log.error("Disconnected from IRC")
					self.socket = False
					self.ready = False
					break
			except socket.timeout:
				if self.timeout:
					self.socket = False
					break
				else:
					self.send("PING :%s" % self.randomString())
					self.timeout = True
				buffer = ""
			except:
				buffer = ""
			for line in buffer.split("\n"):
				self.line = line
				self.parse()
	def queue(self):
		while self.socket:
			if not self.ready: 
				time.sleep(0.1)
				continue
			for i,message in enumerate(self.msgQueue):
				for channel in self.channels:
					self.send("PRIVMSG %s :%s" % (channel, message))
				del self.msgQueue[i]
			self.msgQueue = []
			time.sleep(0.1)
	def filterName(self, name):
		if self.config["IRC"]["obstruct-nicknames"]:
			return "_" + str(name)[1:]
		else:
			return name 
	def rawConsole(self, payload):
		self.server.console(payload)
	def console(self, channel, payload):
		if self.config["IRC"]["show-channel-server"]:
			self.rawConsole({"text": "[%s] " % channel, "color": "gold", "extra": payload})
		else:
			self.rawConsole({"extra": payload})
	def parse(self):
		if self.args(1) == "001":
			for command in self.config["IRC"]["autorun-irc-commands"]:
				self.send(command)
			for channel in self.channels:
				self.send("JOIN %s" % channel)
			self.ready = True
			self.log.info("Connected to IRC!")
			self.state = True
			self.nickAttempts = 0
		if self.args(1) == "433":
			self.log.info("Nickname '%s' already in use." % self.nickname)
			self.nickAttempts += 1
			if self.nickAttempts > 2:
				name = bytearray(self.nickname)
				for i in range(3):
					name[len(self.nickname) / 3 * i] = chr(random.randrange(97, 122))
				self.nickname = str(name)
			else: self.nickname = self.nickname + "_"
			self.auth()
			self.log.info("Attemping to use nickname '%s'." % self.nickname)
		if self.args(1) == "JOIN":
			nick = self.args(0)[1:self.args(0).find("!")]
			channel = self.args(2)[1:][:-1]
			self.log.info("%s joined %s" % (nick, channel))
			self.wrapper.callEvent("irc.join", {"nick": nick, "channel": channel})
		if self.args(1) == "PART":
			nick = self.args(0)[1:self.args(0).find("!")]
			channel = self.args(2)
			self.log.info("%s parted %s" % (nick, channel))
			self.wrapper.callEvent("irc.part", {"nick": nick, "channel": channel})
		if self.args(1) == "MODE":
			try:
				nick = self.args(0)[1:self.args(0).find('!')]
				channel = self.args(2)
				modes = self.args(3)
				user = self.args(4)[:-1]
				self.console(channel, [{"text": user, "color": "green"}, {"text": " received modes %s from %s" % (modes, nick), "color": "white"}])
			except:
				pass
		if self.args(0) == "PING":
			self.send("PONG %s" % self.args(1))
		if self.args(1) == "QUIT":
			nick = self.args(0)[1:self.args(0).find("!")]
			message = " ".join(self.line.split(" ")[2:])[1:].strip("\n").strip("\r")
			
			self.wrapper.callEvent("irc.quit", {"nick": nick, "message": message, "channel": None})
		if self.args(1) == "PRIVMSG":
			channel = self.args(2)
			nick = self.args(0)[1:self.args(0).find("!")]
			message = " ".join(self.line.split(" ")[3:])[1:].strip("\n").strip("\r")
			
			def args(i):
				try: return message.split(" ")[i]
				except: return ""
			def argsAfter(i):
				try: return " ".join(message.split(" ")[i:])
				except: return ""
			
			if channel[0] == "#":
				if message.strip() == ".players":
					users = ""
					for user in self.server.players:
						users += "%s " % user
					self.send("PRIVMSG %s :There are currently %s users on the server: %s" % (channel, len(self.server.players), users))
				elif message.strip() == ".about":
					self.send("PRIVMSG %s :Wrapper.py Version %s" % (channel, self.wrapper.getBuildString()))
				else:
					message = message.decode("utf-8", "ignore")
					if args(0) == "\x01ACTION":
						self.wrapper.callEvent("irc.action", {"nick": nick, "channel": channel, "action": argsAfter(1)[:-1]})
						self.log.info("[%s] * %s %s" % (channel, nick, argsAfter(1)[:-1]))
					else:
						self.wrapper.callEvent("irc.message", {"nick": nick, "channel": channel, "message": message})
						self.log.info("[%s] <%s> %s" % (channel, nick, message))
			elif self.config["IRC"]["control-from-irc"]:
				self.log.info("[PRIVATE] (%s) %s" % (nick, message))
				def msg(string):
					print "[PRIVATE] (%s) %s" % (self.config["IRC"]["nick"], string)
					self.send("PRIVMSG %s :%s" % (nick, string))
				try:
					self.authorized
				except:
					self.authorized = {}
				if nick in self.authorized:
					if int(time.time()) - self.authorized[nick] < 900:
						if args(0) == 'hi':
							msg('Hey there!')
						elif args(0) == 'help':
							# eventually I need to make help only one or two lines, to prevent getting kicked/banned for spam
							msg("run [command] - run command on server")
							msg("togglebackups - temporarily turn backups on or off. this setting is not permanent and will be lost on restart")
							msg("halt - shutdown server and Wrapper.py, will not auto-restart")
							msg("kill - force server restart without clean shutdown - only use when server is unresponsive")
							msg("start/restart/stop - start the server/automatically stop and start server/stop the server without shutting down Wrapper")
							msg('status - show status of the server')
							msg("Wrapper.py Version %s by benbaptist" % self.wrapper.getBuildString())
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
								self.server.console(command)
						elif args(0) == 'halt':
							self.wrapper.halt = True
							self.server.run("stop")
							self.server.state = 3
						elif args(0) == 'restart':
							self.server.run('stop')
							self.server.state = 3
						elif args(0) == 'stop':
							self.server.run('stop')
							self.server.start = False
							self.server.state = 3
							msg("Server stopping")
						elif args(0) == 'start':
							self.server.start = True
							msg("Server starting")
						elif args(0) == 'kill':
							self.server.state = 0
							self.server.proc.kill()
							msg("Server terminated.")
						elif args(0) == 'status':
							if self.server.state == 2: msg("Server is running.")
							elif self.server.state == 1: msg("Server is currently starting/frozen.")
							elif self.server.state == 0: msg("Server is stopped. Type 'start' to fire it back up.")
							elif self.server.state == 3: msg("Server is in the process of shutting down/restarting.")
							else: msg("Server is in unknown state. This is probably a Wrapper.py bug - report it! (state #%d)" % self.server.state)
						elif args(0) == "about":
							msg("Wrapper.py by benbaptist - version %s (build #%d)" % (Config.version, globals.build))
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
						msg('Not authorized. Type "auth [password]" to login.')
	def args(self, i):
		try:
			return self.line.split(" ")[i]
		except:
			pass