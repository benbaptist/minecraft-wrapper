import socket, datetime, time, sys, threading, random, subprocess, os, json, signal, traceback, api, StringIO, ConfigParser, backups, sys, codecs, ctypes, platform, ast
try: 
	import resource
	IMPORT_RESOURCE_SUCCESS = True
except: IMPORT_RESOURCE_SUCCESS = False
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
		
		if "serverState" not in self.wrapper.storage:
			self.wrapper.storage["serverState"] = True
		self.players = {}
		self.state = 0 # 0 is off, 1 is starting, 2 is started, 3 is shutting down, 4 is idle, 5 is frozen
		self.bootTime = time.time()
		self.boot = self.wrapper.storage["serverState"]
		self.proc = False
		self.rebootWarnings = 0
		self.pollSize = 0
		self.data = []
		
		if not self.wrapper.storage["serverState"]:
			self.log.warn("NOTE: Server was in 'STOP' state last time Wrapper.py was running. To start the server, run /start.")
			time.sleep(5)
		
		# Server Information 
		self.worldName = None
		self.worldSize = 0
		self.maxPlayers = 20
		self.protocolVersion = -1 # -1 until proxy mode checks the server's MOTD on boot
		self.version = None
		self.world = None
		self.motd = None
		self.timeofday = -1  # -1 until a player logs on and server sends a time update
		self.onlineMode = True
		self.serverIcon = None
		
		self.reloadProperties()
		
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
	def start(self, save=True):
		""" Start the Minecraft server """
		self.boot = True
		if save:
			self.wrapper.storage["serverState"] = True
	def restart(self, reason="Restarting Server"):
		""" Restart the Minecraft server, and kick people with the specified reason """
		self.log.info("Restarting Minecraft server with reason: %s" % reason)
		self.changeState(3, reason)
		for player in self.players:
			self.console("kick %s %s" % (player, reason))
		self.console("stop")
	def stop(self, reason="Stopping Server", save=True):
		""" Stop the Minecraft server, prevent it from auto-restarting and kick people with the specified reason """
		self.log.info("Stopping Minecraft server with reason: %s" % reason)
		self.changeState(3, reason)
		self.boot = False
		if save:
			self.wrapper.storage["serverState"] = False
		for player in self.players:
			self.console("kick %s %s" % (player, reason))
		self.console("stop")
	def kill(self, reason="Killing Server"):
		""" Forcefully kill the server. It will auto-restart if set in the configuration file """
		self.log.info("Killing Minecraft server with reason: %s" % reason)
		self.changeState(0, reason)
		self.proc.kill()
	def freeze(self, reason="Server is now frozen. You may disconnect momentarily."):
		""" Freeze the server with `kill -STOP`. Can be used to stop the server in an emergency without shutting it down, so it doesn't write corrupted data - e.g. if the disk is full, you can freeze the server, free up some disk space, and then unfreeze 
		
		'reason' argument is printed in the chat for all currently-connected players, unless you specify None. """
		if reason:
			self.log.info("Freezing server with reason: %s" % reason)
			try: self.broadcast("&c%s" % reason)
			except: pass
			time.sleep(0.5)
		else:
			self.log.info("Freezing server...")
		self.changeState(5)
		os.system("kill -STOP %d" % self.proc.pid)
	def unfreeze(self):
		""" Unfreeze the server with `kill -CONT`. Counterpart to .freeze(reason) """
		self.log.info("Unfreezing server...")
		self.broadcast("&aServer unfrozen.")
		self.changeState(2)
		os.system("kill -CONT %d" % self.proc.pid)
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
			if "color" in j: total += getColorCode(j["color"])
			if "text" in j: total += j["text"]
			if "string" in j: total += j["string"]
			return total
		total += handleChunk(json)
		if "extra" in json:
			for i in json["extra"]:
				total += handleChunk(i)
		return total.encode("utf8")
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
			self.players[username].abort = True
			del self.players[username]
	def getPlayer(self, username):
		""" Returns a player object with the specified name, or False if the user is not logged in/doesn't exist """
		if username in self.players:
			return self.players[username]
		return False
	def reloadProperties(self):
		# Load server icon
		if os.path.exists("server-icon.png"):
			f = open("server-icon.png", "rb")
			self.serverIcon = "data:image/png;base64," + f.read().encode("base64")
			f.close()
		# Read server.properties and extract some information out of it
		if os.path.exists("server.properties"):
			s = StringIO.StringIO() # Stupid StringIO doesn't support __exit__()
			config = open("server.properties", "r").read()
			s.write("[main]\n" + config)
			s.seek(0)
			try:
				self.properties = ConfigParser.ConfigParser(allow_no_value = True)
				self.properties.readfp(s)
				self.worldName = self.properties.get("main", "level-name")
				self.motd = self.properties.get("main", "motd")
				self.maxPlayers = int(self.properties.get("main", "max-players"))
				self.onlineMode = self.properties.get("main", "online-mode")
				if self.onlineMode == "false": self.onlineMode = False
				else: self.onlineMode = True
			except:
				self.log.getTraceback()
	def console(self, command):
		""" Execute a console command on the server """
		try: self.proc.stdin.write("%s\n" % command)
		except: pass #self.log.getTraceback()
	def changeState(self, state, reason=None):
		""" Change the boot state of the server, with a reason message """
		self.state = state
		if self.state == 0: self.wrapper.callEvent("server.stopped", {"reason": reason})
		if self.state == 1: self.wrapper.callEvent("server.starting", {"reason": reason})
		if self.state == 2: self.wrapper.callEvent("server.started", {"reason": reason})
		if self.state == 3: self.wrapper.callEvent("server.stopping", {"reason": reason})
		self.wrapper.callEvent("server.state", {"state": state, "reason": reason})
	def getServerType(self):
		if "spigot" in self.config["General"]["command"].lower():
			return "spigot"
		elif "bukkit" in self.config["General"]["command"].lower():
			return "bukkit"
		else:
			return "vanilla"
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
			self.proc = False
			if not self.boot:
				time.sleep(0.1)
				continue
			self.changeState(1)
			self.log.info("Starting server...")
			self.reloadProperties()
			self.proc = subprocess.Popen(self.args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
			self.players = {}	
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
	def getMemoryUsage(self):
		""" Returns allocated memory in bytes """
		if not IMPORT_RESOURCE_SUCCESS: return None
		if not os.name == "posix": return None
		if self.proc == False: return None
		try:
			with open("/proc/%d/statm" % self.proc.pid, "r") as f:
				bytes = int(f.read().split(" ")[1]) * resource.getpagesize()
		except: return None
		return bytes
	def getStorageAvailable(self, folder):
		""" Returns the disk space for the working directory in bytes """
		if platform.system() == "Windows":
			free_bytes = ctypes.c_ulonglong(0)
			ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
			return free_bytes.value
		else:
			st = os.statvfs(folder)
			return st.f_bavail * st.f_frsize
	def getWorldSize(self):
		""" Returns the size of the currently used world folder in bytes """
		return self.worldSize
	def stripSpecial(self, text):
		a = ""; it = iter(xrange(len(text)))
		for i in it:
			char = text[i]
			if char == "\xc2":
				try: 
					it.next()
					it.next()
				except:
					pass 
			else: 
				a += char
		return a
	def readConsole(self, buff):
		""" Internally-use function that parses a particular console line """
		def args(i):
			try: return line.split(" ")[i]
			except: return ""
		def argsAfter(i):
			try: return " ".join(line.split(" ")[i:])
			except: return ""
		if not self.wrapper.callEvent("server.consoleMessage", {"message": buff}): return False
		if self.getServerType() == "spigot":
			line = " ".join(buff.split(" ")[2:])
		else:
			line = " ".join(buff.split(" ")[3:])
		print buff
		deathPrefixes = ["fell", "was", "drowned", "blew", "walked", "went", "burned", "hit", "tried", 
			"died", "got", "starved", "suffocated", "withered"]
		if not self.config["General"]["pre-1.7-mode"]:
			if len(args(0)) < 1: return
			if args(0) == "Done": # Confirmation that the server finished booting
				self.changeState(2)
				self.log.info("Server started")
				self.bootTime = time.time()
			elif args(0) == "Preparing" and args(1) == "level": # Getting world name
				self.worldName = args(2).replace('"', "")
				self.world = World(self.worldName, self)
			elif args(0)[0] == "<": # Player Message
				name = self.stripSpecial(args(0)[1:-1])
				message = self.stripSpecial(argsAfter(1))
				original = argsAfter(0)
				self.wrapper.callEvent("player.message", {"player": self.getPlayer(name), "message": message, "original": original})
			elif args(1) == "logged": # Player Login
				name = self.stripSpecial(args(0)[0:args(0).find("[")])
				self.login(name)
			elif args(1) == "lost": # Player Logout
				name = args(0)
				self.logout(name)
			elif args(0) == "*":
				name = self.stripSpecial(args(1))
				message = self.stripSpecial(argsAfter(2))
				self.wrapper.callEvent("player.action", {"player": self.getPlayer(name), "action": message})
			elif args(0)[0] == "[" and args(0)[-1] == "]": # /say command
				if self.getServerType != "vanilla": return # Unfortunately, Spigot and Bukkit output things that conflict with this
				name = self.stripSpecial(args(0)[1:-1])
				message = self.stripSpecial(argsAfter(1))
				original = argsAfter(0)
				self.wrapper.callEvent("server.say", {"player": name, "message": message, "original": original})
			elif args(1) == "has" and args(5) == "achievement": # Player Achievement
				name = self.stripSpecial(args(0))
				achievement = argsAfter(6)
				self.wrapper.callEvent("player.achievement", {"player": name, "achievement": achievement})
			elif args(1) in deathPrefixes: # Player Death
				name = self.stripSpecial(args(0))
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
		if not self.config["IRC"]["show-irc-join-part"]: return
		self.messageFromChannel(channel, "&a%s &rjoined the channel" % nick)
	def onChannelPart(self, payload):
		channel, nick = payload["channel"], payload["nick"]
		if not self.config["IRC"]["show-irc-join-part"]: return
		self.messageFromChannel(channel, "&a%s &rparted the channel" % nick)
	def onChannelMessage(self, payload):
		channel, nick, message = payload["channel"], payload["nick"], payload["message"]
		final = ""
		for i,chunk in enumerate(message.split(" ")):
			if not i == 0: final += " "
			try: 
				if chunk[0:7] in ("http://", "https://"): final += "&b&n&@%s&@&r" % chunk
				else: final += chunk
			except: final += chunk
		self.messageFromChannel(channel, "&a<%s> &r%s" % (nick, final))
	def onChannelAction(self, payload):
		channel, nick, action = payload["channel"], payload["nick"], payload["action"]
		self.messageFromChannel(channel, "&a* %s &r%s" % (nick, action))
	def onChannelQuit(self, payload):
		channel, nick, message = payload["channel"], payload["nick"], payload["message"]
		if not self.config["IRC"]["show-irc-join-part"]: return
		self.messageFromChannel(channel, "&a%s &rquit: %s" % (nick, message))
	def onTick(self, payload):
		""" Called every second, and used for handling cron-like jobs """
		if self.config["General"]["timed-reboot"]:
			if time.time() - self.bootTime > self.config["General"]["timed-reboot-seconds"]:
				if self.config["General"]["timed-reboot-warning-minutes"] > 0:
					if self.rebootWarnings - 1 < self.config["General"]["timed-reboot-warning-minutes"]:
						l = (time.time() - self.bootTime - self.config["General"]["timed-reboot-seconds"]) / 60
						if l > self.rebootWarnings:
							self.rebootWarnings += 1
							if int(self.config["General"]["timed-reboot-warning-minutes"] - l + 1) > 0:
								self.broadcast("&cServer will be rebooting in %d minute(s)!" % int(self.config["General"]["timed-reboot-warning-minutes"] - l + 1))
						return
				self.restart("Server is conducting a scheduled reboot. The server will be back momentarily!")
				self.bootTime = time.time()
				self.rebootWarnings = 0
		if time.time() - self.pollSize > 120:
			if self.worldName == None: return True
			self.pollSize = time.time()
			size = 0
			for i in os.walk(self.worldName):
				for f in os.listdir(i[0]):
					size += os.path.getsize(os.path.join(i[0], f))
			self.worldSize = size
