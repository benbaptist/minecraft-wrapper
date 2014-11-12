import socket, datetime, time, sys, threading, random, subprocess, os, json, signal, traceback, api, StringIO, ConfigParser, backups, sys, codecs
from api.player import Player
from api.world import World
class Server:
	def __init__(self, args, log, config, wrapper):
		self.log = log
		self.config = config
		self.wrapper =  wrapper
		self.args = args
		self.api = api.API(wrapper, "Server", internal=True)
		self.backups = backups.Backups(wrapper)
		
		self.players = {}
		self.state = 0 # 0 is off, 1 is starting, 2 is started, 3 is shutting down
		self.bootTime = time.time()
		self.boot = True
		self.data = []
		
		# Server Information 
		self.worldName = None
		self.protocolVersion = -1 # -1 until proxy mode checks the server's MOTD on boot
		self.version = None
		self.world = None
		
		# Read server.properties and extract some information out of it
		if os.path.exists("server.properties"):
			s = StringIO.StringIO() # Stupid StringIO doesn't support __exit__()
			config = open("server.properties", "r").read()
			s.write("[main]\n" + config)
			s.seek(0)
			self.properties = ConfigParser.ConfigParser(allow_no_value = True)
			self.properties.readfp(s)
			self.worldName = self.properties.get("main", "level-name")
		
		self.api.registerEvent("irc.message", self.onChannelMessage)
		self.api.registerEvent("irc.action", self.onChannelAction)
		self.api.registerEvent("irc.join", self.onChannelJoin)
		self.api.registerEvent("irc.part", self.onChannelPart)
		self.api.registerEvent("irc.quit", self.onChannelQuit)
		self.api.registerEvent("timer.second", self.onTick)
	def init(self):
		""" Start up the listen threads for reading server console output """
		captureThread = threading.Thread(target=self.__stdout__, args=())
		captureThread.daemon = True
		captureThread.start()
		captureThread = threading.Thread(target=self.__stderr__, args=())
		captureThread.daemon = True
		captureThread.start()
	def start(self):
		""" Start the Minecraft server """
		self.boot = True
	def restart(self, reason="Restarting Server"):
		""" Restart the Minecraft server, and kick people with the specified reason """
		self.log.info("Restarting Minecraft server with reason: %s" % reason)
		self.changeState(3)
		for player in self.players:
			self.console("kick %s %s" % (player, reason))
		self.console("stop")
	def stop(self, reason="Stopping Server"):
		""" Stop the Minecraft server, prevent it from auto-restarting and kick people with the specified reason """
		self.log.info("Stopping Minecraft server with reason: %s" % reason)
		self.changeState(3)
		self.boot = False
		for player in self.players:
			self.console("kick %s %s" % (player, reason))
		self.console("stop")
	def broadcast(self, message=""):
		""" Broadcasts the specified message to all clients connected. message can be a JSON chat object, or a string with formatting codes using the & as a prefix """
		if isinstance(message, dict):
			if self.config["General"]["pre-1.7-mode"]:
				self.console("say %s" % self.chatToColorCodes(message))
			else:
				self.console("tellraw @a %s" % json.dumps(message))
		else:
			if self.config["General"]["pre-1.7-mode"]:
				self.console("say %s" % self.chatToColorCodes(json.loads(self.processColorCodes(message))))
			else:
				self.console("tellraw @a %s" % self.processColorCodes(message))
	def chatToColorCodes(self, json):
		total = ""
		def getColorCode(i):
			for l in api.API.colorCodes:
				if api.API.colorCodes[l] == i:
					return "\xa7\xc2" + l
			return ""
		def handleChunk(j):
			total = ""
			if "color" in j: total += getColorCode(j["color"]).decode("ascii")
			if "text" in j: total += j["text"].decode("ascii")
			return total
		total += handleChunk(json)
		if "extra" in json:
			for i in json["extra"]:
				total += handleChunk(i)
		return total
	def processColorCodes(self, message):
		""" Used internally to process old-style color-codes with the & symbol, and returns a JSON chat object. """
		message = message.encode('ascii', 'ignore')
		extras = []
		bold = False
		italic = False
		underline = False
		obfuscated = False
		strikethrough = False
		url = False
		color = "white"
		current = ""; it = iter(xrange(len(message)))
		for i in it:
			char = message[i]
			if char is not "&":
				if char == " ": url = False
				current += char
			else:
				if url: clickEvent = {"action": "open_url", "value": current}
				else: clickEvent = {}
				extras.append({"text": current, "color": color, "obfuscated": obfuscated, 
					"underlined": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough, "clickEvent": clickEvent})
				current = ""
				try: code = message[i+1]
				except: break
				if code in "abcdef0123456789":
					try: color = api.API.colorCodes[code]
					except: color = "white"
				if code == "k": obfuscated = True
				elif code == "l": bold = True
				elif code == "m": strikethrough = True
				elif code == "n": underline = True
				elif code == "o": italic = True
				elif code == "&": current += "&"
				elif code == "@": url = not url
				elif code == "r":
					bold = False
					italic = False
					underline = False
					obfuscated = False
					strikethrough = False
					url = False
					color = "white"
				it.next()
		extras.append({"text": current, "color": color, "obfuscated": obfuscated, 
			"underlined": underline, "bold": bold, "italic": italic, "strikethrough": strikethrough})
		return json.dumps({"text": "", "extra": extras})
	def login(self, username):
		""" Called when a player logs in """
		try:
			if username not in self.players:
				self.players[username] = api.Player(username, self.wrapper)
			self.wrapper.callEvent("player.login", {"player": self.getPlayer(username)})
		except:
			self.log.getTraceback()
	def logout(self, username):
		""" Called when a player logs out """
		self.wrapper.callEvent("player.logout", {"player": self.getPlayer(username)})
		if self.wrapper.proxy:
			for client in self.wrapper.proxy.clients:
				uuid = self.players[username].uuid
		if username in self.players:
			del self.players[username]
	def getPlayer(self, username):
		""" Returns a player object with the specified name, or False if the user is not logged in/doesn't exist """
		if username in self.players:
			return self.players[username]
		return False
	def console(self, command):
		""" Execute a console command on the server """
		try: self.proc.stdin.write("%s\n" % command)
		except: pass #self.log.getTraceback()
	def changeState(self, state):
		""" Change the boot state of the server """
		self.state = state
		if self.state == 0: self.wrapper.callEvent("server.stopped", None)
		if self.state == 1: self.wrapper.callEvent("server.starting", None)
		if self.state == 2: self.wrapper.callEvent("server.started", None)
		if self.state == 3: self.wrapper.callEvent("server.stopping", None)
		self.wrapper.callEvent("server.state", {"state": state})
	def __stdout__(self):
		while not self.wrapper.halt:
			try:
				data = self.proc.stdout.readline()
				for line in data.split("\n"):
					if len(line) < 1: continue
					self.data.append(line)
			except:
				time.sleep(0.1)
				continue
	def __stderr__(self):
		while not self.wrapper.halt:
			try:
				data = self.proc.stderr.readline()
				if len(data) > 0:
					for line in data.split("\n"):
						self.data.append(line.replace("\r", ""))
			except:
				time.sleep(0.1)
				continue
	def __handle_server__(self):
		""" Internally-used function that handles booting the server, parsing console output, and etc. """
		while not self.wrapper.halt:
			if not self.boot:
				time.sleep(0.1)
				continue
			self.changeState(1)
			self.log.info("Starting server...")
			self.wrapper.callEvent("server.start", {})
			self.proc = subprocess.Popen(self.args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)	
			while True:
				time.sleep(0.1)
				if self.proc.poll() is not None:
					self.changeState(0)
					if not self.config["General"]["auto-restart"]:
						self.wrapper.halt = True
					self.log.info("Server stopped")
					break
				for line in self.data:
					try: self.readConsole(line.replace("\r", ""))
					except: self.log.getTraceback()
				self.data = []
	def stripSpecial(self, text):
		a = ""; b = 0
		while len(a) < len(text):
			i = text[b]
			if i == "\xa7": b += 2
			else: 
				a += i
				b += 1
		return a
	def readConsole(self, line):
		""" Internally-use function that parses a particular console line """
		def args(i):
			try: return line.split(" ")[i]
			except: return ""
		def argsAfter(i):
			try: return " ".join(line.split(" ")[i:])
			except: return ""
		if not self.wrapper.callEvent("server.consoleMessage", {"message": line}): return False
		print line
		deathPrefixes = ["fell", "was", "drowned", "blew", "walked", "went", "burned", "hit", "tried", 
			"died", "got", "starved", "suffocated", "withered"]
		if not self.config["General"]["pre-1.7-mode"]:
			if len(args(3)) < 1: return
			if args(3) == "Done": # Confirmation that the server finished booting
				self.changeState(2)
				self.log.info("Server started")
				self.bootTime = time.time()
			elif args(3) == "Preparing" and args(4) == "level": # Getting world name
				self.worldName = args(5).replace('"', "")
				self.world = World(self.worldName)
			elif args(3)[0] == "<": # Player Message
				name = self.stripSpecial(args(3)[1:-1])
				message = self.stripSpecial(argsAfter(4))
				original = argsAfter(3)
				self.wrapper.callEvent("player.message", {"player": self.getPlayer(name), "message": message, "original": original})
			elif args(4) == "logged": # Player Login
				name = self.stripSpecial(args(3)[0:args(3).find("[")])
				self.login(name)
			elif args(4) == "lost": # Player Logout
				name = args(3)
				self.logout(name)
			elif args(3) == "*":
				name = self.stripSpecial(args(4))
				message = self.stripSpecial(argsAfter(5))
				self.wrapper.callEvent("player.action", {"player": self.getPlayer(name), "action": message})
			elif args(3)[0] == "[" and args(3)[-1] == "]": # /say command
				name = self.stripSpecial(args(3)[1:-1])
				message = self.stripSpecial(argsAfter(4))
				original = argsAfter(3)
				self.wrapper.callEvent("server.say", {"player": name, "message": message, "original": original})
			elif args(4) == "has" and args(8) == "achievement": # Player Achievement
				name = self.stripSpecial(args(3))
				achievement = argsAfter(9)
				self.wrapper.callEvent("player.achievement", {"player": name, "achievement": achievement})
			elif args(4) in deathPrefixes: # Player Death
				name = self.stripSpecial(args(3))
				deathMessage = self.config["Death"]["death-kick-messages"][random.randrange(0, len(self.config["Death"]["death-kick-messages"]))]
				if self.config["Death"]["kick-on-death"] and name in self.config["Death"]["users-to-kick"]:
					self.console("kick %s %s" % (name, deathMessage))
				self.wrapper.callEvent("player.death", {"player": self.getPlayer(name), "death": argsAfter(4)})
		else:
			if len(args(3)) < 1: return
			if args(3) == "Done": # Confirmation that the server finished booting
				self.changeState(2)
				self.log.info("Server started")
				self.bootTime = time.time()
			elif args(3) == "Preparing" and args(4) == "level": # Getting world name
				self.worldName = args(5).replace('"', "")
				self.world = World(self.worldName)
			elif args(3)[0] == "<": # Player Message
				name = self.stripSpecial(args(3)[1:-1])
				message = self.stripSpecial(argsAfter(4))
				original = argsAfter(3)
				self.wrapper.callEvent("player.message", {"player": self.getPlayer(name), "message": message, "original": original})
			elif args(4) == "logged": # Player Login
				name = self.stripSpecial(args(3)[0:args(3).find("[")])
				self.login(name)
			elif args(4) == "lost": # Player Logout
				name = args(3)
				self.logout(name)
			elif args(3) == "*":
				name = self.stripSpecial(args(4))
				message = self.stripSpecial(argsAfter(5))
				self.wrapper.callEvent("player.action", {"player": self.getPlayer(name), "action": message})
			elif args(3)[0] == "[" and args(3)[-1] == "]": # /say command
				name = self.stripSpecial(args(3)[1:-1])
				message = self.stripSpecial(argsAfter(4))
				original = argsAfter(3)
				if name == "Server": return
				self.wrapper.callEvent("server.say", {"player": name, "message": message, "original": original})
			elif args(4) == "has" and args(8) == "achievement": # Player Achievement
				name = self.stripSpecial(args(3))
				achievement = argsAfter(9)
				self.wrapper.callEvent("player.achievement", {"player": name, "achievement": achievement})
			elif args(4) in deathPrefixes: # Player Death
				name = self.stripSpecial(args(3))
				deathMessage = self.config["Death"]["death-kick-messages"][random.randrange(0, len(self.config["Death"]["death-kick-messages"]))]
				if self.config["Death"]["kick-on-death"] and name in self.config["Death"]["users-to-kick"]:
					self.console("kick %s %s" % (name, deathMessage))
				self.wrapper.callEvent("player.death", {"player": self.getPlayer(name), "death": argsAfter(4)})
	# Event Handlers
	def messageFromChannel(self, channel, message):
		if self.config["IRC"]["show-channel-server"]:
			self.broadcast("&6[%s] %s" % (channel, message))
		else:
			self.broadcast(message)
	def onChannelJoin(self, payload):
		channel, nick = payload["channel"], payload["nick"]
		self.messageFromChannel(channel, "&a%s &rjoined the channel" % nick)
	def onChannelPart(self, payload):
		channel, nick = payload["channel"], payload["nick"]
		self.messageFromChannel(channel, "&a%s &rparted the channel" % nick)
	def onChannelMessage(self, payload):
		channel, nick, message = payload["channel"], payload["nick"], payload["message"]
		final = ""
		for i,chunk in enumerate(message.split(" ")):
			if not i == 0: final += " "
			try: 
				if chunk[0:7] == "http://": final += "&b&n&@%s&@&r" % chunk
				else: final += chunk
			except: final += chunk
		self.messageFromChannel(channel, "&a<%s> &r%s" % (nick, final))
	def onChannelAction(self, payload):
		channel, nick, action = payload["channel"], payload["nick"], payload["action"]
		self.messageFromChannel(channel, "&a* %s &r%s" % (nick, action))
	def onChannelQuit(self, payload):
		channel, nick, message = payload["channel"], payload["nick"], payload["message"]
		self.messageFromChannel(channel, "&a%s &rquit: %s" % (nick, message))
	def onTick(self, payload):
		""" Called every second, and used for handling cron-like jobs """
		if self.config["General"]["timed-reboot"]:
			if time.time() - self.bootTime > self.config["General"]["timed-reboot-seconds"]:
				self.restart("Server is conducting a scheduled reboot. The server will be back momentarily!")
				self.bootTime = time.time()
