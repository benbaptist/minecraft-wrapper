import socket, traceback, time, threading
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
		self.channels = channels
		self.log = log
		self.timeout = False
		self.msgQueue = []
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
	def connect(self):
		self.socket = socket.socket()
		self.socket.connect((self.address, self.port))
		self.socket.setblocking(120)
		
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
	def handle(self):
		while self.socket:
			try:
				buffer = self.socket.recv(1024)
				if buffer == "":
					self.log.error("Disconnected from IRC")
					self.socket = False
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
			for message in self.msgQueue:
				for channel in self.channels:
					self.send("PRIVMSG %s :%s" % (channel, message))
			self.msgQueue = []
			time.sleep(0.1)
	def filterName(self, name):
		if self.config["IRC"]["obstruct-nicknames"]:
			return "_" + name[1:]
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
			self.log.info("Connected to IRC!")
			self.state = True
		if self.args(1) == "JOIN":
			nick = self.args(0)[1:self.args(0).find("!")]
			channel = self.args(2)[1:][:-1]
			self.log.info("%s joined %s" % (nick, channel))
			self.console(channel, [{"text": nick, "color": "green"}, {"text": " joined the channel", "color": "white"}])
			self.wrapper.callEvent("irc.channelJoin", {"user": nick, "channel": channel})
		if self.args(1) == "PART":
			nick = self.args(0)[1:self.args(0).find("!")]
			channel = self.args(2)
			self.log.info("%s parted from %s" % (nick, channel))
			self.console(channel, [{"text": nick, "color": "green"}, {"text": " left the channel", "color": "white"}])
			self.wrapper.callEvent("irc.channelPart", {"user": nick, "channel": channel})
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
		if self.args(0) == "QUIT":
			nick = self.args(0)[1:self.args(0).find("!")]
			message = " ".join(self.line.split(" ")[2:])[1:].strip("\n").strip("\r")
			
			self.wrapper.callEvent("irc.quit", {"user": nick, "quit": message})
			self.rawConsole({"text": nick, "color": "green", extra:[{"text": " quit", "color": "white"}]})
		if self.args(1) == "PRIVMSG":
			channel = self.args(2)
			nick = self.args(0)[1:self.args(0).find("!")]
			message = " ".join(self.line.split(" ")[3:])[1:].strip("\n").strip("\r")
			
			if channel[0] == "#":
				self.wrapper.callEvent("irc.channelMessage", {"user": nick, "channel": channel, "message": message})
				if message.strip() == ".players":
					users = ""
					for user in self.server.players:
						users += "%s " % user
					self.send("PRIVMSG %s :There are currently %s users on the server: %s" % (channel, len(self.server.players), users))
				elif message.strip() == ".about":
					self.send("PRIVMSG %s :Wrapper.py version %s" % (channel, Config.version))
				else:
					self.log.info('[%s] (%s) %s' % (channel, nick, message))
					message = message.decode("utf-8", "ignore")
					self.console(channel, [{"text": "(%s) " % nick, "color": "green"}, {"text": message, "color": "white"}])
			elif self.config["IRC"]["control-from-irc"]:
				self.log.info('[PRIVATE] (%s) %s' % (nick, message))
				def args(i):
					try:
						return message.split(" ")[i]
					except:
						return ""
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
							msg("Wrapper.py version %s by benbaptist" % Config.version)
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
								self.server.run(command)
						elif args(0) == 'halt':
							self.wrapper.halt = True
							self.server.run("stop")
							self.server.status = 3
						elif args(0) == 'restart':
							self.server.run('stop')
							self.server.status = 3
						elif args(0) == 'stop':
							self.server.run('stop')
							self.server.start = False
							self.server.status = 3
							msg("Server stopping")
						elif args(0) == 'start':
							self.server.start = True
							msg("Server starting")
						elif args(0) == 'kill':
							self.server.status = 0
							self.server.proc.kill()
							msg("Server terminated.")
						elif args(0) == 'status':
							if self.server.status == 2:
								msg("Server is running.")
							elif self.server.status == 1:
								msg("Server is currently starting/frozen.")
							elif self.server.status == 0:
								msg("Server is stopped. Type 'start' to fire it back up.")
							elif self.server.status == 3:
								msg("Server is in the process of shutting down/restarting.")
							else:
								msg("Server is in unknown state. This is probably a Wrapper.py bug - report it!")
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
						msg('Not authorized. Type "auth [password]" to login.')
	def args(self, i):
		try:
			return self.line.split(" ")[i]
		except:
			pass