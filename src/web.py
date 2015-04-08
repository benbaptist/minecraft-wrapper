# Yeah, I know. The code is awful. Probably not even a HTTP-compliant web server anyways. I just wrote it at like 3AM in like an hour.
import socket, traceback, zipfile, threading, time, json, random, urlparse, storage, log, urllib, os, md5
from api import API
try:
	import pkg_resources, requests
	IMPORT_SUCCESS = True
except:
	IMPORT_SUCCESS = False
class Web:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.api = API(wrapper, "Web", internal=True)
		self.log = log.PluginLog(self.wrapper.log, "Web")
		self.config = wrapper.config
		self.socket = False
		self.data = storage.Storage("web", self.log)
		if "keys" not in self.data: self.data["keys"] = []
		#if not self.config["Web"]["web-password"] == None:
#			self.log.info("Changing web-mode password because web-password was changed in wrapper.properties")
#			self.data["password"] = md5.md5(self.config["Web"]["web-password"]).hexdigest()
#			self.config["Web"]["web-password"] = None
#			self.wrapper.configManager.save()
		
		self.api.registerEvent("server.consoleMessage", self.onServerConsole)
		self.api.registerEvent("player.message", self.onPlayerMessage)
		self.api.registerEvent("player.login", self.onPlayerJoin)
		self.api.registerEvent("player.logout", self.onPlayerLeave)
		self.api.registerEvent("irc.message", self.onChannelMessage)
		self.consoleScrollback = []
		self.chatScrollback = []
		self.memoryGraph = []
		self.loginAttempts = 0
		self.lastAttempt = 0
		self.disableLogins = 0
		
	#	t = threading.Thread(target=self.updateGraph, args=())
#		t.daemon = True
#		t.start()
	def onServerConsole(self, payload):
		while len(self.consoleScrollback) > 1000:
			try:
				del self.consoleScrollback[0]
			except: break
		self.consoleScrollback.append((time.time(), payload["message"]))
	def onPlayerMessage(self, payload):
		while len(self.chatScrollback) > 200:
			try:
				del self.chatScrollback[0]
			except: break
		self.chatScrollback.append((time.time(), {"type": "player", "payload": {"player": payload["player"].username, "message": payload["message"]}}))
	def onPlayerJoin(self, payload):
		print payload
		while len(self.chatScrollback) > 200:
			try:
				del self.chatScrollback[0]
			except: break
		self.chatScrollback.append((time.time(), {"type": "playerJoin", "payload": {"player": payload["player"].username}}))
	def onPlayerLeave(self, payload):
		print payload
		while len(self.chatScrollback) > 200:
			try: del self.chatScrollback[0]
			except: break
		self.chatScrollback.append((time.time(), {"type": "playerLeave", "payload": {"player": payload["player"].username}}))
	def onChannelMessage(self, payload):
		while len(self.chatScrollback) > 200:
			try: del self.chatScrollback[0]
			except: break
		self.chatScrollback.append((time.time(), {"type": "irc", "payload": payload}))
	def updateGraph(self):
		while not self.wrapper.halt:
			while len(self.memoryGraph) > 200:
				del self.memoryGraph[0]
			if self.wrapper.server.getMemoryUsage():
				self.memoryGraph.append([time.time(), self.wrapper.server.getMemoryUsage()])
			time.sleep(1)
	def checkLogin(self, password):
		if time.time() - self.disableLogins < 60: return False # Threshold for logins
		if password == self.wrapper.config["Web"]["web-password"]: return True
		self.loginAttempts += 1
		if self.loginAttempts > 10 and time.time() - self.lastAttempt < 60:
			self.disableLogins = time.time()
			self.log.warn("Disabled login attempts for one minute")
		self.lastAttempt = time.time()
	def makeKey(self, rememberMe):
		a = ""; z = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@-_"
		for i in range(64):
			a += z[random.randrange(0, len(z))]
#			a += chr(random.randrange(97, 122))
		if rememberMe:
			print "Will remember!"
		self.data["keys"].append([a, time.time(), rememberMe])
		return a
	def validateKey(self, key):
		for i in self.data["keys"]:
			expireTime = 2592000
			if len(i) > 2:
				if not i[2]: expireTime = 21600
			if i[0] == key and time.time() - i[1] < expireTime: # Validate key and ensure it's under a week old
				self.loginAttempts = 0
				return True
		return False
	def removeKey(self, key):
		for i,v in enumerate(self.data["keys"]):
			if v[0] == key:
				del self.data["keys"][i]
	def wrap(self):
		while not self.wrapper.halt:
			try:
				if self.bind():
					self.listen()
				else:
					self.log.error("Could not bind web to %s:%d - retrying in 5 seconds" % (self.config["Web"]["web-bind"], self.config["Web"]["web-port"]))
			except:
				for line in traceback.format_exc().split("\n"):
					self.log.error(line)
			time.sleep(5)
	def bind(self):
		if self.socket is not False:
			self.socket.close()
		try:
			self.socket = socket.socket()
			self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.socket.bind((self.config["Web"]["web-bind"], self.config["Web"]["web-port"]))
			self.socket.listen(5)
			return True
		except:
			return False
	def listen(self):
		self.log.info("Web Interface bound to %s:%d" % (self.config["Web"]["web-bind"], self.config["Web"]["web-port"]))
		while not self.wrapper.halt:
			sock, addr = self.socket.accept()
#			self.log.debug("(WEB) Connection %s started" % str(addr))
			client = Client(self.wrapper, sock, addr, self)
			t = threading.Thread(target=client.wrap, args=())
			t.daemon = True
			t.start()
class Client:
	def __init__(self, wrapper, socket, addr, web):
		self.wrapper = wrapper
		self.socket = socket
		self.addr = addr
		self.web = web
		self.request = ""
		self.log = wrapper.log
		self.api = wrapper.api
		self.socket.setblocking(30)
	def read(self, filename):
		return pkg_resources.resource_stream(__name__, "html/%s" % filename).read()
	def write(self, message):
		self.socket.send(message)
	def headers(self, status="200 Good", contentType="text/html", location=""):
		self.write("HTTP/1.0 %s\n" % status)
		if len(location) < 1:
			self.write("Content-Type: %s\n" % contentType)
		
		if len(location) > 0:
			self.write("Location: %s\n" % location)
		
		self.write("\n")
	def close(self):
		try:
			self.socket.close()
			#self.log.debug("(WEB) Connection %s closed" % str(self.addr))
		except:
			pass
	def wrap(self):
		try: self.handle()
		except:
			self.log.error("Internal error while handling web mode request:")
			self.log.getTraceback()
			self.headers(status="300 Internal Server Error")
			self.write("<h1>300 Internal Server Error</h1>")
			self.close()
	def handleAction(self, request):
		def args(i): 
			try: return request.split("/")[1:][i]
			except: return ""
		def get(i): 
			for a in args(1).split("?")[1].split("&"):
				if a[0:a.find("=")]:
					return urllib.unquote(a[a.find("=")+1:])
			return ""
		info = self.runAction(request)
		if info == False:
			return {"status": "error", "payload": "unknown_key"}
		elif info == EOFError:
			return {"status": "error", "payload": "permission_denied"}
		else:
			return {"status": "good", "payload": info}
	def safePath(self, path):
		os.getcwd()
	def runAction(self, request):
		def args(i): 
			try: return request.split("/")[1:][i]
			except: return ""
		def get(i):
			for a in args(1).split("?")[1].split("&"):
				if a[0:a.find("=")] == i:
					return urllib.unquote(a[a.find("=")+1:])
			return ""
		action = args(1).split("?")[0]
		if action == "stats":
			if not self.wrapper.config["Web"]["public-stats"]: return EOFError
			players = []
			for i in self.wrapper.server.players:
				players.append({"name": i, "loggedIn": self.wrapper.server.players[i].loggedIn, "uuid": str(self.wrapper.server.players[i].uuid)})
			return {"playerCount": len(self.wrapper.server.players), "players": players}
		if action == "login":
			password = get("password")
			rememberMe = get("remember-me")
			if rememberMe == "true": rememberMe = True
			else: rememberMe = False
			if self.web.checkLogin(password):
				key = self.web.makeKey(rememberMe)
				self.log.warn("%s logged in to web mode (remember me: %s)" % (self.addr[0], rememberMe))
				return {"session-key": key}
			else:
				self.log.warn("%s failed to login" % self.addr[0])
			return EOFError
		if action == "is_admin":
			if self.web.validateKey(get("key")): return {"status": "good"}
			return EOFError
		if action == "logout":
			if self.web.validateKey(get("key")):
				self.web.removeKey(get("key"))
				self.log.warn("[%s] Logged out." % self.addr[0])
				return "goodbye"
			return EOFError
		if action == "read_server_props":
			if not self.web.validateKey(get("key")): return EOFError
			return open("server.properties", "r").read()
		if action == "save_server_props":
			if not self.web.validateKey(get("key")): return EOFError
			props = get("props")
			if not props: return False
			if len(props) < 10: return False
			with open("server.properties", "w") as f:
				f.write(props)
			return "ok"
		if action == "listdir":
			if not self.web.validateKey(get("key")): return EOFError
			if not self.wrapper.config["Web"]["web-allow-file-management"]: return EOFError
			safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWYXZ0123456789_-/ "
			pathUnfiltered = get("path"); path = ""
			for i in pathUnfiltered:
				if i in safe: path+=i
			if path == "": path = "."
			files = []; folders = []; listdir = os.listdir(path); listdir.sort()
			for p in listdir:
				fullpath = path + "/" + p
				if p[-1] == "~": continue
				if p[0] == ".": continue
				if os.path.isdir(fullpath):
					folders.append({"filename": p, "count": len(os.listdir(fullpath))})
				else:
					files.append({"filename": p, "size": os.path.getsize(fullpath)})
			return {"files": files, "folders": folders}
		if action == "rename_file":
			if not self.web.validateKey(get("key")): return EOFError
			if not self.wrapper.config["Web"]["web-allow-file-management"]: return EOFError
			file = get("path"); rename = get("rename")
			if os.path.exists(file):
				try: os.rename(file, rename)
				except:
					print traceback.format_exc() 
					return False
				return True
			return False
		if action == "delete_file":
			if not self.web.validateKey(get("key")): return EOFError
			if not self.wrapper.config["Web"]["web-allow-file-management"]: return EOFError
			file = get("path");
			if os.path.exists(file):
				try:
					if os.path.isdir(file):
						os.removedirs(file)
					else: 
						os.remove(file)
				except:
					print traceback.format_exc()  
					return False
				return True
			return False
		if action == "halt_wrapper":
			if not self.web.validateKey(get("key")): return EOFError
			self.wrapper.shutdown()
		if action == "get_player_skin":
			if not self.web.validateKey(get("key")): return EOFError
			if self.wrapper.proxy == False: return {"error": "Proxy mode not enabled."}
			uuid = get("uuid")
			if uuid in self.wrapper.proxy.skins:
				skin = self.wrapper.proxy.getSkinTexture(uuid)
				if skin: return skin
				else: return None
			else: return None
		if action == "admin_stats":
			if not self.web.validateKey(get("key")): return EOFError
			if self.wrapper.server == False: return
			refreshTime = float(get("last_refresh"))
			players = []
			for i in self.wrapper.server.players:
				player = self.wrapper.server.players[i]
				players.append({
					"name": i, 
					"loggedIn": player.loggedIn, 
					"uuid": str(player.uuid),
					"isOp": player.isOp()
				})
			plugins = []
			for id in self.wrapper.plugins:
				plugin = self.wrapper.plugins[id]
				if plugin["good"]:
					if plugin["description"]: description = plugin["description"]
					else: description = None
					plugins.append({
						"name": plugin["name"],
						"version": plugin["version"],
						"description": description,
						"summary": plugin["summary"],
						"author": plugin["author"],
						"website": plugin["website"],
						"version": (".".join([str(_) for _ in plugin["version"]])),
						"id": id,
						"good": True
					})
				else:
					plugins.append({
						"name": plugin["name"],
						"good": False
					})
			consoleScrollback = []
			for line in self.web.consoleScrollback:
				if line[0] > refreshTime:
					consoleScrollback.append(line[1])
			chatScrollback = []
			for line in self.web.chatScrollback:
				if line[0] > refreshTime:
					print line[1]
					chatScrollback.append(line[1])
			memoryGraph = []
			for line in self.web.memoryGraph:
				if line[0] > refreshTime:
					memoryGraph.append(line[1])
			#totalPlaytime = {}
#			totalPlayers = self.web.api.minecraft.getAllPlayers()
#			for uu in totalPlayers:
#				if not "logins" in totalPlayers[uu]: 
#					continue
#				playerName = self.web.wrapper.getUsername(uu)
#				totalPlaytime[playerName] = [0, 0]
#				for i in totalPlayers[uu]["logins"]:
#					totalPlaytime[playerName][0] += totalPlayers[uu]["logins"][i] - int(i)
#					totalPlaytime[playerName][1] += 1
			def secondsToHuman(seconds):
				result = "None at all!"; plural = "s"
				if seconds > 0:
					result = "%d seconds" % seconds
				if seconds > 59:
					if (seconds/60) == 1: plural = ""
					result = "%d minute%s" % (seconds/60, plural)
				if seconds > 3599:
					if (seconds/3600) == 1: plural = ""
					result = "%d hour%s" % (seconds/3600, plural)
				if seconds > 86400:
					if (seconds/86400) == 1: plural = ""
					result = "%s day%s" % (str(seconds/86400.0), plural)
				return result
			topPlayers = []
			#for i,username in enumerate(totalPlaytime):
#				topPlayers.append((totalPlaytime[username][0], secondsToHuman(totalPlaytime[username][0]), totalPlaytime[username][1], username))
#				if i == 9: break
#			topPlayers.sort(); topPlayers.reverse()
			return {"playerCount": [len(self.wrapper.server.players), self.wrapper.server.maxPlayers], 
				"players": players,
				"plugins": plugins,
				"server_state": self.wrapper.server.state,
				"wrapper_build": self.wrapper.getBuildString(),
				"console": consoleScrollback,
				"chat": chatScrollback,
				"level_name": self.wrapper.server.worldName,
				"server_version": self.wrapper.server.version,
				"motd": self.wrapper.server.motd,
				"refresh_time": time.time(),
				"server_name": self.wrapper.config["General"]["server-name"],
				"server_memory": self.wrapper.server.getMemoryUsage(),
				"server_memory_graph": memoryGraph,
				"world_size": self.wrapper.server.worldSize,
				"disk_avail": self.wrapper.server.getStorageAvailable("."),
				"topPlayers": topPlayers
			}
		if action == "console":
			if not self.web.validateKey(get("key")): return EOFError
			self.wrapper.server.console(get("execute"))
			self.log.warn("[%s] Executed: %s" % (self.addr[0], get("execute")))
			return True
		if action == "chat":
			if not self.web.validateKey(get("key")): return EOFError
			message = get("message")
			self.web.chatScrollback.append((time.time(), {"type": "raw", "payload": "[WEB ADMIN] " + message}))
			self.wrapper.server.broadcast("&c[WEB ADMIN]&r " + message)
			return True
		if action == "kick_player":
			if not self.web.validateKey(get("key")): return EOFError
			player = get("player")
			reason = get("reason")
			self.log.warn("[%s] %s was kicked with reason: %s" % (self.addr[0], player, reason))
			self.wrapper.server.console("kick %s %s" % (player, reason))
			return True
		if action == "ban_player":
			if not self.web.validateKey(get("key")): return EOFError
			player = get("player")
			reason = get("reason")
			self.log.warn("[%s] %s was banned with reason: %s" % (self.addr[0], player, reason))
			self.wrapper.server.console("ban %s %s" % (player, reason))
			return True
		if action == "change_plugin":
			if not self.web.validateKey(get("key")): return EOFError
			plugin = get("plugin")
			state = get("state")
			if state == "enable":
				if plugin in self.wrapper.storage["disabled_plugins"]:
					self.wrapper.storage["disabled_plugins"].remove(plugin)
					self.log.warn("[%s] Enabled plugin '%'" % (self.addr[0], plugin))
					self.wrapper.reloadPlugins()
			else:
				if not plugin in self.wrapper.storage["disabled_plugins"]:
					self.wrapper.storage["disabled_plugins"].append(plugin)
					self.log.warn("[%s] Disabled plugin '%'" % (self.addr[0], plugin))
					self.wrapper.reloadPlugins()
		if action == "reload_plugins":
			if not self.web.validateKey(get("key")): return EOFError
			self.wrapper.reloadPlugins()
			return True
		if action == "server_action":
			if not self.web.validateKey(get("key")): return EOFError
			type = get("action")
			if type == "stop":
				reason = get("reason")
				self.wrapper.server.stop(reason)
				self.log.warn("[%s] Server stop with reason: %s" % (self.addr[0], reason))
				return "success"
			elif type == "restart":
				reason = get("reason")
				self.wrapper.server.restart(reason)
				self.log.warn("[%s] Server restart with reason: %s" % (self.addr[0], reason))
				return "success"
			elif type == "start":
				reason = get("reason")
				self.wrapper.server.start()
				self.log.warn("[%s] Server started" % (self.addr[0]))
				return "success"
			elif type == "kill":
				self.wrapper.server.kill()
				self.log.warn("[%s] Server killed." % self.addr[0])
				return "success"
			return {"error": "invalid_server_action"}
		return False
	def getContentType(self, filename):
		ext = filename[filename.rfind("."):][1:]
		if ext == "js": return "application/javascript"
		if ext == "css": return "text/css"
		if ext in ("txt", "html"): return "text/html"
		if ext in ("ico"): return "image/x-icon"
		return "application/octet-stream"
	def get(self, request):
		#print "GET request: %s" % request
		def args(i): 
			try: return request.split("/")[1:][i]
			except: return ""
		if request == "/":
			file = "index.html"
		elif args(0) == "action":
			try:
				self.write(json.dumps(self.handleAction(request)))
			except:
				self.headers(status="300 Internal Server Error")
				print traceback.format_exc()
			self.close()
			return False
		else:
			file = request.replace("..", "").replace("%", "").replace("\\", "")
		if file == "/admin.html":
			self.headers(status="301 Go Away", location="/admin")
			return False
		if file == "/login.html":
			self.headers(status="301 Go Away", location="/login")
			return False
		if file == ".":
			self.headers(status="400 Bad Request")
			self.write("<h1>BAD REQUEST</h1>")
			self.close()
			return False
		try:
			if file == "/admin": file = "admin.html" 
			if file == "/login": file = "login.html" 
			data = self.read(file)
			self.headers(contentType=self.getContentType(file))
			self.write(data)
		except:
			self.headers(status="404 Not Found")
			self.write("<h1>404 Not Found</h4>")
		self.close()
	def handle(self):
		while True:
			try:
				data = self.socket.recv(1024)
				if len(data) < 1:
					self.close()
					return
				self.buffer = data.split("\n")
			except:
				self.close()
				#self.log.debug("(WEB) Connection %s closed" % str(self.addr))
				break
			if len(self.buffer) < 1:
				print "Web connection closed suddenly" 
				return False
			for line in self.buffer:
				def args(i): 
					try: return line.split(" ")[i]
					except: return ""
				def argsAfter(i): 
					try: return " ".join(line.split(" ")[i:])
					except: return ""
				if args(0) == "GET":
					self.get(args(1))
				if args(0) == "POST":
					self.request = args(1)
					self.headers(status="400 Bad Request")
					self.write("<h1>Invalid request. Sorry.</h1>")