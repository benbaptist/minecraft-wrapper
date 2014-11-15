# Unfinished web UI code. Yeah, I know. The code is awful. Probably not even a HTTP-compliant web server anyways. I just wrote it at like 3AM in like an hour.
import socket, traceback, zipfile, threading, time, json, random, urlparse, storage, log
from api import API
try:
	import pkg_resources
	IMPORT_SUCCESS = True
except:
	IMPORT_SUCCESS = False
class Web:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.api = API(wrapper, "Web")
		self.log = log.PluginLog(self.wrapper.log, "Web")
		self.config = wrapper.config
		self.socket = False
		self.data = storage.Storage("web", self.log)
		if "keys" not in self.data: self.data["keys"] = []
		
		self.api.registerEvent("server.consoleMessage", self.onServerConsole)
		self.consoleScrollback = []
		self.loginAttempts = 0
		self.lastAttempt = 0
		self.disableLogins = 0
	def onServerConsole(self, payload):
		while len(self.consoleScrollback) > 30:
			del self.consoleScrollback[0]
		self.consoleScrollback.append(payload["message"])
	def makeKey(self):
		a = ""; z = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@-_"
		for i in range(32):
			a += z[random.randrange(0, len(z))]
#			a += chr(random.randrange(97, 122))
		self.data["keys"].append([a, time.time()])
		return a
	def validateKey(self, key):
		if time.time() - self.disableLogins < 2000: return False # Threshold for logins
		for i in self.data["keys"]:
			if i[0] == key and time.time() - i[1] < 604800: # Validate key and ensure it's under a week old
				self.loginAttempts = 0
				return True
		self.loginAttempts += 1
		if self.loginAttempts > 10 and time.time() - self.lastAttempt < 30:
			self.disableLogins = time.time()
		self.lastAttempt = time.time()
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
					return a[a.find("=")+1:]
			return ""
		info = self.runAction(request)
		if info == False:
			return {"status": "error", "payload": "unknown_key"}
		elif info == EOFError:
			return {"status": "error", "payload": "permission_denied"}
		else:
			return {"status": "good", "payload": info}
	def runAction(self, request):
		def args(i): 
			try: return request.split("/")[1:][i]
			except: return ""
		def get(i):
			for a in args(1).split("?")[1].split("&"):
				if a[0:a.find("=")] == i:
					return a[a.find("=")+1:].replace("%20", " ")
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
			if password == self.wrapper.config["Web"]["web-password"]:
				key = self.web.makeKey()
				self.log.warn("%s logged in to web mode" % self.addr[0])
				return {"session-key": key}
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
		if action == "admin_stats":
			if not self.web.validateKey(get("key")): return EOFError
			if self.wrapper.server == False: return
			players = []
			for i in self.wrapper.server.players:
				players.append({"name": i, "loggedIn": self.wrapper.server.players[i].loggedIn, "uuid": str(self.wrapper.server.players[i].uuid)})
			return {"playerCount": len(self.wrapper.server.players), 
				"players": players, 
				"server_state": self.wrapper.server.state,
				"wrapper_build": self.wrapper.getBuildString(),
				"console": self.web.consoleScrollback,
				"level-name": self.wrapper.server.worldName,
				"server-version": self.wrapper.server.version}
		if action == "console":
			if not self.web.validateKey(get("key")): return EOFError
			self.wrapper.server.console(get("execute"))
			self.log.warn("[%s] Executed: %s" % (self.addr[0], get("execute")))
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
				self.log.warn("[%s] Server start with reason: %s" % (self.addr[0], reason))
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
		if file == "admin": file = "admin.html" # alias /admin as /admin.html
		if file == ".":
			self.headers(status="400 Bad Request")
			self.write("<h1>BAD REQUEST</h1>")
			self.close()
			return False
		try:
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
				self.buffer = self.socket.recv(1024).split("\n")
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
	def handleold(self):
		while True:
			try:
				self.buffer = self.socket.recv(1024).split("\n")
			except:
				self.close()
				#self.log.debug("(WEB) Connection %s closed" % str(self.addr))
				break
			if len(self.buffer) < 1:
				print "connection closed" 
				return False
			for line in self.buffer:
				def args(i): 
					try: return line.split(" ")[i]
					except: return ""
				def argsAfter(i): 
					try: return " ".join(line.split(" ")[i:])
					except: return ""
				if args(0) == "GET":
					self.request = args(1)
					#self.log.info("(WEB) Request [%s] GET %s" % (str(self.addr[0]), self.request))
				if args(0) == "POST":
					self.request = args(1)
					self.headers(status="400 Bad Request")
					self.write("<h1>Invalid request. Sorry.</h1>")
					#self.log.info("(WEB) Request [%s] POST %s" % (str(self.addr[0]), self.request))
					return False
				if args(0) == "Cookie:":
					self.cookies = argsAfter(1)
				if line == "":
					break
			if self.request.find("?") is not -1:
				self.path = self.request[0:self.request.find("?")].split("/")[1:]
			else:
				self.path = self.request.split("/")[1:]
			self.arguments = self.request[self.request.find("?")+1:].split("&")
			if self.request == "/" or self.request == "/index.html":
				if self.wrapper.config["Web"]["public-stats"]:
					self.headers()
					self.write(self.read("/index.html").replace("[server_name]", self.wrapper.server.getName()))
				else:
					self.headers(location="/admin", status="301 Moved Permanently")
			elif self.request == "/admin":
				self.headers()
				self.write(self.read("admin.html"))
			elif self.request == "/favicon.ico":
				self.headers(contentType="image/x-icon")
				self.write(self.read("favicon.ico"))
			elif self.request == "/RobotoCondensed-Light.ttf":
				self.headers(contentType="application/octet-stream")
				self.write(self.read("RobotoCondensed-Light.ttf"))
			elif self.path[0] == "action":
				actionData = self.runAction()
				self.headers()
				self.write(json.dumps(actionData))
			else:
				self.headers(status="404 Not Found")
				self.write(self.read("404.html"))
			self.close()