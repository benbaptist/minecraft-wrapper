import socket, traceback, zipfile, threading, time, json, random, urlparse
from api import API
try:
	import pkg_resources
	IMPORT_SUCCESS = True
except:
	IMPORT_SUCCESS = False
class Web:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.log = wrapper.log
		self.config = wrapper.config
		self.socket = False
		self.keys = []
	def makeKey(self):
		a = ""; z = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@-_"
		for i in range(32):
			a += z[random.randrange(0, len(z))]
#			a += chr(random.randrange(97, 122))
		self.keys.append(a)
		return a
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
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			self.headers(status="300 Internal Server Error")
			self.write("<h1>300 Internal Server Error</h1>")
			self.close()
	def runAction(self):
		def args(i): 
			try: return self.request.split("/")[1:][i]
			except: return ""
		def get(i): 
			for a in args(1).split("?")[1].split("&"):
				if a[0:a.find("=")]:
					return a[a.find("=")+1:]
			return ""
		action = args(1).split("?")[0]
		if action == "test":
			return {"type": "test", "value": "YAY"}
		if action == "stats":
			if not self.wrapper.config["Web"]["public-stats"]:
				return {"type": "error", "error": "permission_denied"}
			players = []
			for i in self.wrapper.server.players:
				players.append({"name": i, "loggedIn": self.wrapper.server.players[i].loggedIn})
			return {"type": "stats", "playerCount": len(self.wrapper.server.players), "players": players}
		if action == "login":
			password = get("password")
			if password == self.wrapper.config["Web"]["web-password"]:
				key = self.web.makeKey()
				return {"type": "login", "value": key}
		return {"type": "error", "error": "unknown_key"}
	def getContentType(self, filename):
		ext = filename[filename.rfind("."):][1:]
		if ext == "js": return "application/javascript"
		if ext == "css": return "text/css"
		if ext in ("txt", "html"): return "text/html"
		if ext in ("ico"): return "image/x-icon"
		return "application/octet-stream"
	def get(self):
		request = self.request
		if request == "/":
			file = "index.html"
		elif request == "action":
			try:
				self.write(json.dumps(self.runAction()))
			except:
				self.headers(status="300 Internal Server Error")
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
					self.get()
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