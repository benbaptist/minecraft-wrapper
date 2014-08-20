import socket, threading, struct, StringIO, time, traceback, json, encryption, random, requests, hashlib, os
class Proxy:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.socket = False
		self.clients = []
		
		self.privateKey = encryption.generate_key_pair()
		self.publicKey = encryption.encode_public_key(self.privateKey)
	def host(self):
		while not self.socket:
			time.sleep(1)
			try:
				self.socket = socket.socket()
				self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				self.socket.bind((self.wrapper.config["Proxy"]["bind"], self.wrapper.config["Proxy"]["proxy-port"]))
				self.socket.listen(5)
			except:
				self.socket = False
	 	while not self.wrapper.halt:
	 		try:
		 		sock, addr = self.socket.accept()
		 		client = Client(sock, addr, self.wrapper, self.publicKey, self.privateKey)
		 		
		 		t = threading.Thread(target=client.handleClientToServer, args=())
		 		t.daemon = True
		 		t.start()
		 		self.clients.append(client)
		 	except:
		 		print traceback.print_exc()
		 		try:
		 			client.disconnect()
		 		except:
		 			pass
class Client:
	def __init__(self, socket, addr, wrapper, publicKey, privateKey):
		self.client = socket
		self.server = False
		self.clientBuffer = StringIO.StringIO()
		self.serverBuffer = StringIO.StringIO()
		self.addr = addr
		self.wrapper = wrapper
		self.username = ""
		self.target = ""
		self.authed = True
		self.abort = False
		self.state = 0
		self.serverState = 0
		self.publicKey = publicKey
		self.privateKey = privateKey
		self.recvCipher = False
		self.sendCipher = False
		
		self.gamemode = -1
		self.position = (-1, -1, -1)
		
		self.serverToClient = []
		self.clientToServer = []
		
		self.lastKeepalive = time.time()
	def connect(self):
		self.server = socket.socket()
		self.server.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
	def disconnect(self, message="Disconnecting due to an unknown reason"):
		print traceback.format_exc()
		self.wrapper.log.debug("Disconnecting client '%s' for reason: %s" % (self.username, message))
		self.abort = True
	#	try:
#			self.send(0x40, "string", (json.dumps({"text": message}),), self.client, client=True)
#		except:
#			pass
		try:
			self.wrapper.proxy.clients.remove(self)
		except:
			pass
		try:
			self.client.close()
			self.server.close()
		except:
			pass
	def readClientToServer(self):
		buffer = self.client.recv(9999999)
		if self.recvCipher:
			return StringIO.StringIO(self.recvCipher.decrypt(buffer))
		else:
			return StringIO.StringIO(buffer)
	def handleServerToClient(self):
		try:
			while not self.abort:
				if self.abort: break
				objection = True
				try:
					packet = self.grabPacket(self.server)
				except:
#					self.disconnect()
					break
#				print "S>C ID %s: %s" % (packet[0], packet[1].read().encode("hex"))
				packet[1].seek(0)
				if packet[0] == 0:
					if self.state == 3:
						data = self.read("int:keepalive", packet[1])
#						self.send(0x00, "int", (data["keepalive"],), self.server)
#						print "responded to server-side ping packet: %d" % data["keepalive"]
						objection = False
				if packet[0] == 1:
					if self.state == 1:
						print packet[1].read()
#						data = self.read("string:json|string:bonk", packet[1])
#						print data
						objection = False
						self.state = 3
					else:
						data = self.read("int:eid|ubyte:gamemode|byte:dimension|ubyte:difficulty|ubyte:max_players|string:level_type", packet[1])
						self.gamemode = data["gamemode"]
						self.dimension = data["dimension"]
						self.eid = data["eid"]
				if packet[0] == 2:
					if self.serverState == 0:
						data = self.read("string:uuid|string:username", packet[1])
						print "server sent this: %s" % data
						self.serverState = 1
						self.state = 3
						objection = False
					elif self.serverState == 1:
						data = self.read("string:json_data|position:byte", packet[1])
						try:
							message = json.loads(data["json_data"])
							if message["translate"] == "chat.type.admin": # hide [Server: ] messages, as they spam when Wrapper.py does things
								objection = False
						except:
							pass
				if self.state is not 3: objection = False
				if objection:
					if self.sendCipher:
						self.serverToClient.append(self.sendCipher.encrypt(packet[2]))
					else:
						self.serverToClient.append(packet[2])
				for packet in self.serverToClient:
					self.client.send(packet)
				self.serverToClient = []
		except:
			print traceback.format_exc()
			self.disconnect("s>c")
	def handleClientToServer(self):
		try:
			while not self.abort:
				if self.abort: break
				objection = True
				try:
					packet = self.grabPacketClient(self.client)
				except:
					self.disconnect("Error while reading packet - disconnecting")
					break
				if self.state is not 3: objection = False
				print "C>S ID %s: %s" % (packet[0], packet[1].read().encode("hex"))
				packet[1].seek(0)
				if self.state == 3 and time.time() - self.lastKeepalive > 1:
					self.send(0x00, "int", (random.randrange(0, 99999999),), self.client, client=True)
					self.lastKeepalive = time.time()
				if packet[0] == 0:
					if self.state == 0:
						data = self.read("varint:version|string:address|ushort:port|varint:state", packet[1])
#						data = self.read("string:address", packet[1])
						self.target = data["address"]
						self.state = data["state"]
						self.version = data["version"]
						print "Protocol version: %d" % self.version
						print "Switching to state %d" % self.state
						if self.state == 2:
							self.wrapper.log.info("Connecting to server...")
							self.connect()
	 						t = threading.Thread(target=self.handleServerToClient, args=())
			 				t.daemon = True
			 				t.start()
			 				self.send(0x00, "varint|string|ushort|varint", (self.version, "localhost", self.wrapper.config["Proxy"]["server-port"], 2), self.server)
						objection = False
					elif self.state == 1:
						data = self.read("none:none", packet[1])
						MOTD = {"description": self.wrapper.config["Proxy"]["motd"], 
							"players": {"max": 20, "online": len(self.wrapper.server.players)},
							"version": {"name": "14w26c", "protocol": 25}
						}
						if os.path.exists("server-icon.png"):
							f = open("server-icon.png", "r")
							serverIcon = "data:image/png;base64," + f.read().encode("base64")
							f.close()
							MOTD["favicon"] = serverIcon
						self.send(0x00, "string", (json.dumps(MOTD),), self.client, client=True)
						#self.send(0x00, "string", ('{"description":"Servers","players":{"max":20,"online":%d},"version":{"name":"14w26c","protocol":25}}' % (len(self.wrapper.server.players)),), self.client, client=True)
						objection = False
					elif self.state == 2:
						data = self.read("string:username", packet[1])
						self.username = data["username"]
						self.wrapper.log.info("%s logging in as %s" % (self.addr[0], self.username))
						
						self.state = 4
				 		
				 	#	def ch():
#				 			return chr(random.randrange(0, 255))
#				 		verifyToken = "".join([ch() for i in range(4)])
						self.verifyToken = encryption.generate_challenge_token()
				 		print "verify token: %s" % self.verifyToken
				 		self.serverID = encryption.generate_server_id()
				 		self.send(0x01, "string|varint|bytearray|varint|bytearray", (self.serverID, len(self.publicKey), self.publicKey, len(self.verifyToken), self.verifyToken), self.client)
						objection = False
					elif self.state == 3:
						data = self.read("int:keepalive", packet[1])
						objection = False
				if packet[0] == 1:
					if self.state == 1:
						data = self.read("long:time", packet[1])
						self.send(0x01, "long", (data["time"],), self.client, client=True)
						self.disconnect()
					elif self.state == 4:
						data = self.read("bytearray:shared_secret|bytearray:verify_token", packet[1])
						sharedSecret = encryption.decrypt_shared_secret(data["shared_secret"], self.privateKey)
						verifyToken = encryption.decrypt_shared_secret(data["verify_token"], self.privateKey)
						if verifyToken == self.verifyToken:
							print "VERIFY TOKENS ARE THE SAME, HOORAY!"
						else:
							print "VERIFY TOKENS WERE NOT THE SAME - KILLING"
							self.disconnect("Invalid Verify Token")
							break
						h = hashlib.sha1()
						h.update(self.serverID)
						h.update(sharedSecret)
						h.update(self.publicKey)
						serverId = h.hexdigest()
						r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s&serverId=%s" % (self.username, serverId))
						print "SessionServer response: %s" % r.text
						
						# initiate cyphers
						self.sendCipher = encryption.AES128CFB8(sharedSecret)
						self.recvCipher = encryption.AES128CFB8(sharedSecret)
						
						try:
							data = r.json()
							uuid = data["id"]
							self.uuid = "%s-%s-%s-%s-%s" % (uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:]) 
						except:
							self.disconnect("Session Server Error (no response)")
							break
						
						self.state = 5
						self.send(0x00, "string", (self.username,), self.server)
				 		self.send(0x02, "string|string", (self.uuid, self.username), self.client, client=True)
				 		objection = False
					elif self.authed:
						data = self.read("string:message", packet[1])
						if data is not None:
							try:
								#if data["message"] == "tomato":
								#	self.send("varint|string|short|bytearray", (0x3f, "MC|RPack", len("http://benbaptist.com/s/ResourcePackTest.zip"), "http://benbaptist.com/s/ResourcePackTest.zip"), self.client) 
								objection = self.wrapper.callEvent("player.rawMessage", {"player": self.username, "message": data["message"]})
								if objection and data["message"][0] == "/":
									def args(i):
										try: return data["message"].split(" ")[i]
										except: return ""
									def argsAfter(i):
										try: return data["message"].split(" ")[i:]
										except: return ""
									objection = self.wrapper.callEvent("player.runCommand", {"player": self.username, "command": args(0)[1:], "args": argsAfter(1)})
							except:
								pass
					else:
						length = self.read_short(packet[1])
						shared_secret = packet[1].read(length)
						length = self.read_short(packet[1])
						verify_token = packet[1].read(length)
						print (shared_secret, verify_token)
				if packet[0] == 0x04:
					data = self.read("double:x|double:y|double:z|bool:on_ground", packet[1])
					#objection = self.wrapper.callEvent("player.move", {"player": self.username, "xyz": (data["x"], data["y"], data["z"]), "on_ground": data["on_ground"]})
					if objection:
						self.position = (data["x"], data["y"], data["z"])
					#else:
						#self.wrapper.server.run("tp %s %d %d %d" % (self.username, data["x"], data["y"], data["z"]))
				if packet[0] == 0x06:
					data = self.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground", packet[1])
					#objection = self.wrapper.callEvent("player.move", {"player": self.username, "xyz": (data["x"], data["y"], data["z"]), "on_ground": data["on_ground"]})
					if objection:
						self.position = (data["x"], data["y"], data["z"])
					#else:
					#	self.wrapper.server.run("tp %s %d %d %d" % (self.username, data["x"], data["y"], data["z"]))
				if packet[0] == 0x07:
					#data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face", packet[1])
					data = self.read("byte:status|long:position|byte:face", packet[1])
					position = (data["position"] >> 38, (data["position"] >> 26) & 0xFFF, data["position"] & 0x3FFFFFF)
					if data is not None and data["status"] not in (3, 4, 5):
						objection = self.wrapper.callEvent("player.dig", {"player": self.username, "xyz": position, "status": data["status"], "face": data["face"]})
				if packet[0] == 0x08:
					data = self.read("long:position|byte:direction", packet[1])
					position = (data["position"] >> 38, (data["position"] >> 26) & 0xFFF, data["position"] & 0x3FFFFFF)
					if data is not None:
						objection = self.wrapper.callEvent("player.place", {"player": self.username, "xyz": position})
				#payload = packet.parse()
				#if payload["packet"] == "chat": # chat packet
				#	objection = self.wrapper.callEvent("player.rawMessage", {"player": self.username, "message": payload["payload"]["json"]})
				if objection and self.server is not False:
					self.clientToServer.append(packet[2])
				else:
					print "Objected C>S: %d" % packet[0]
				for packet in self.clientToServer:
					try:
						self.server.send(packet)
					except:
						pass
				self.clientToServer = []
		except:
			print traceback.format_exc()
			self.disconnect("c>s")
	def grabPacket(self, socket):
		length = self.unpack_varInt(socket)
		id = self.unpack_varInt(socket)
		if length is not 1:
			data = socket.recv(length - len(self.pack_varInt(id)))
		else:
			data = ""
#		if len(data) == 0:
#			raise Exception("Pipe broken")
		payload = StringIO.StringIO(data)
		original = ""
		original += self.pack_varInt(length)
		original += self.pack_varInt(id)
		original += payload.read()
		payload.seek(0)
		return (id, payload, original)
	def grabPacketClient(self, sock):
		length = self.unpack_varInt(sock, encrypt=True)
		id = self.unpack_varInt(sock, encrypt=True)
		if length is not 1:
			data = self.recv(length - len(self.pack_varInt(id)), sock, encrypt=True)
		else:
			data = ""
#		if len(data) == 0:
#			raise Exception("Pipe broken")
		payload = StringIO.StringIO(data)
		original = ""
		original += self.pack_varInt(length)
		original += self.pack_varInt(id)
		original += data
		payload.seek(0)
		return (id, payload, original)
	def recv(self, length, sock, encrypt=False):
		data = sock.recv(length)
		if length > 0 and len(data) == 0:
			return ""
		if self.recvCipher is False or encrypt == False:
			return data
		return self.recvCipher.decrypt(data)
	#def grabPacketClient(self, socket):
#		length = self.unpack_varInt(socket)
#		data = socket.recv(length)
#		if self.recvCipher:
#			print "Decrypted client-sent packet"
#			data = StringIO.StringIO(self.recvCipher.decrypt(data))
#		else:
#			print "Just a regular packet"
#			data = StringIO.StringIO(data)
#		id = self.read_varInt(data)
#		print "Packet ID: %d" % id
#		#data.seek(0)
##		if len(data) == 0:
##			raise Exception("Pipe broken")
#		original = ""
#		original += self.pack_varInt(length)
#		original += self.pack_varInt(id)
#		original += data.read()
#		data.seek(0)
#		return (id, data, original)
	#def grabPacketClient(self, socket):
#		length = self.read_varInt(socket)
#		id = self.read_varInt(socket)
#		#length = self.unpack_varInt(socket, client=True)
#		#id =  self.unpack_varInt(socket, client=True)
#		if length is not 1:
#			data = socket.read(length - len(self.pack_varInt(id)))
#		else:
#			data = ""
#		payload = StringIO.StringIO(data)
#		original = ""
#		original += self.pack_varInt(length)
#		original += self.pack_varInt(id)
#		original += payload.read()
#		payload.seek(0)
#		return (id, payload, original)
	def unpack_byte(self, sock, encrypt=False):
		return struct.unpack("B", self.recv(1, sock, encrypt))[0]
	def unpack_varInt(self, sock, encrypt=False):
		total = 0
		shift = 0
		val = 0x80
		while val&0x80:
			val = struct.unpack('B', self.recv(1, sock, encrypt))[0]
			total |= ((val&0x7F)<<shift)
			shift += 7
		if total&(1<<31):
			total = total - (1<<32)
		return total
	def pack_byte(self, d):
		return struct.pack("B", d)
	def pack_varInt(self, val):
		total = b''
		if val < 0:
			val = (1<<32)+val
		while val>=0x80:
			bits = val&0x7F
			val >>= 7
			total += struct.pack('B', (0x80|bits))
		bits = val&0x7F
		total += struct.pack('B', bits)
		return total
		
	# -- SENDING AND PARSING PACKETS -- #
	def read(self, expression, socket):
		result = {}
		for exp in expression.split("|"):
			type = exp.split(":")[0]
			name = exp.split(":")[1]
			try:
				if type == "string": result[name] = self.read_string(socket)
				if type == "ubyte": result[name] = self.read_ubyte(socket)
				if type == "byte": result[name] = self.read_byte(socket)
				if type == "int": result[name] = self.read_int(socket)
				if type == "short": result[name] = self.read_short(socket)
				if type == "ushort": result[name] = self.read_ushort(socket)
				if type == "long": result[name] = self.read_long(socket)
				if type == "double": result[name] = self.read_double(socket)
				if type == "float": result[name] = self.read_float(socket)
				if type == "bool": result[name] = self.read_bool(socket)
				if type == "varint": result[name] = self.read_varInt(socket)
				if type == "bytearray": result[name] = self.read_bytearray(socket)
			except:
				print traceback.format_exc()
				result[name] = None
		return result
	def send(self, id, expression, payload, socket, client=False):
		result = ""
		result += self.send_ubyte(id)
		for i,type in enumerate(expression.split("|")):
			try:
				pay = payload[i]
				if type == "string": result += self.send_string(pay)
				if type == "ubyte": result += self.send_ubyte(pay)
				if type == "byte": result += self.send_byte(pay)
				if type == "int": result += self.send_int(pay)
				if type == "short": result += self.send_short(pay)
				if type == "ushort": result += self.send_ushort(pay)
				if type == "varint": result += self.send_varInt(pay)
				if type == "float": result += self.send_float(pay)
				if type == "double": result += self.send_double(pay)
				if type == "bytearray": result += pay
			except:
				print traceback.format_exc()
		result = self.pack_varInt(len(result)) + result
		if client and self.sendCipher:
			print "Packing Encrypted Packet"
			socket.send(self.sendCipher.encrypt(result))
		else:
			socket.send(result)
		print "W>C ID %s: %s" % (chr(id).encode("hex"), result.encode("hex"))
	# -- SENDING DATA TYPES -- #
	def send_byte(self, payload):
		return struct.pack("b", payload)
	def send_ubyte(self, payload):
	 	return struct.pack("B", payload)
	def send_string(self, payload):
		return self.send_varInt(len(payload)) + payload.encode("utf8")
	def send_int(self, payload):
		return struct.pack(">i", payload)
	def send_short(self, payload):
		return struct.pack(">h", payload)
	def send_ushort(self, payload):
		return struct.pack(">H", payload)
	def send_float(self, payload):
		return struct.pack(">f", payload)
	def send_double(self, payload):
		return struct.pack(">d", payload)
	def send_varInt(self, payload):
		return self.pack_varInt(payload)
		
	# -- READING DATA TYPES -- #
	def read_data(self, socket, length):
		d = socket.read(length)
		if len(d) == 0:
			self.disconnect("Received no data - connection closed")
			return False
		return d
	def read_byte(self, socket):
		return struct.unpack("b", self.read_data(socket, 1))[0]
	def read_ubyte(self, socket):
		return struct.unpack("B", self.read_data(socket, 1))[0]
	def read_long(self, socket):
		return struct.unpack(">q", self.read_data(socket, 8))[0]
	def read_float(self, socket):
		return struct.unpack(">f", self.read_data(socket, 4))[0]
	def read_int(self, socket):
		return struct.unpack(">i", self.read_data(socket, 4))[0]
	def read_double(self, socket):
		return struct.unpack(">d", self.read_data(socket, 8))[0]
	def read_bool(self, socket):
		if socket.read(1) == 0x01: return True
		else: return False
	def read_short(self, socket):
		return struct.unpack(">h", socket.read(2))[0]
	def read_ushort(self, socket):
		return struct.unpack(">H", socket.read(2))[0]
	def read_bytearray(self, socket):
		return socket.read(self.read_varInt(socket))
	def read_varInt(self, buff):
		total = 0
		shift = 0
		val = 0x80
		while val&0x80:
			val = struct.unpack('B', buff.read(1))[0]
			total |= ((val&0x7F)<<shift)
			shift += 7
		if total&(1<<31):
			total = total - (1<<32)
		return total
	def read_string(self, socket):
		return socket.read(self.read_varInt(socket))