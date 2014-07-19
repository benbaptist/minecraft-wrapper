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
		 		
		 		print "client.connect()"
		 		t = threading.Thread(target=client.handle, args=())
		 		t.daemon = True
		 		t.start()
		 		print "client.handle() thread started"
		 		self.clients.append(client)
		 	except:
		 		print traceback.print_exc()
		 		try:
		 			client.disconnect()
		 		except:
		 			pass
class Client: # handle client/game connection
	def __init__(self, socket, addr, wrapper, publicKey, privateKey):
		self.socket = socket
		self.wrapper = wrapper
		self.config = wrapper.config
		self.socket = socket
		self.publicKey = publicKey
		self.privateKey = privateKey
		self.abort = False
		self.server = None
		
		self.state = 0 # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing
		
		self.packet = Packet(self.socket)
		self.send = self.packet.send
		self.read = self.packet.read
		self.sendRaw = self.packet.sendRaw
		
		self.username = None
		self.gamemode = 0
		self.dimension = 0
		self.position = (0, 0, 0)
	def connect(self):
		self.server = Server(self, self.wrapper)
		self.server.connect()
		t = threading.Thread(target=self.server.handle, args=())
		t.daemon = True
		t.start()
		
		self.server.send(0x00, "varint|string|ushort|varint", (self.version, "localhost", self.config["Proxy"]["server-port"], 2))
		self.server.send(0x00, "string", (self.username,))
#		self.server.send(0x46, "varint", (-1,))
		self.server.state = 2
	def close(self):
		self.abort = True
		self.socket.close()
		if self.server:
			self.server.abort = True
			self.server.close()
	def disconnect(self, message):
		print "Disconnecting: %s" % message
		self.close()
	def flush(self):
		while not self.abort:
			self.packet.flush()
			time.sleep(0.05)
	def parse(self, id):
		if id == 0x00:
			if self.state == 0:
				data = self.read("varint:version|string:address|ushort:port|varint:state")
				self.version = data["version"]
				print "Protocol version: %d" % self.version
				if data["state"] == 2:
					self.state = 2
				return False
			elif self.state == 1:
				MOTD = {"description": self.config["Proxy"]["motd"], 
					"players": {"max": 20, "online": len(self.wrapper.server.players)},
					"version": {"name": "14w26c", "protocol": 25}
				}
				if os.path.exists("server-icon.png"):
					f = open("server-icon.png", "r")
					serverIcon = "data:image/png;base64," + f.read().encode("base64")
					f.close()
					MOTD["favicon"] = serverIcon
				self.send(0x00, "string", (json.dumps(MOTD),))
				return False
			elif self.state == 2:
				data = self.read("string:username")
				self.username = data["username"]
				
				if self.config["Proxy"]["online-mode"]:
					self.state = 4
					self.verifyToken = encryption.generate_challenge_token()
					self.serverID = encryption.generate_server_id()
					self.send(0x01, "string|varint|bytearray|varint|bytearray", (self.serverID, len(self.publicKey), self.publicKey, len(self.verifyToken), self.verifyToken))
				else:
					self.connect()
					self.send(0x02, "string|string", ("b5c6c2f1-2cb8-30d8-807e-8a75ddf765af", self.username))
					self.state = 3
				return False
		if id == 0x01:
			if self.state == 3: # chat packet
				data = self.read("string:message")
				if data is None: return False
				try:
					if not self.wrapper.callEvent("player.rawMessage", {"player": self.username, "message": data["message"]}): return False
					if data["message"][0] == "/":
						def args(i):
							try: return data["message"].split(" ")[i]
							except: return ""
						def argsAfter(i):
							try: return data["message"].split(" ")[i:]
							except: return ""
						return self.wrapper.callEvent("player.runCommand", {"player": self.username, "command": args(0)[1:], "args": argsAfter(1)})
				except:
					print traceback.format_exc()
			elif self.state == 4: # encryption response packet
				data = self.read("bytearray:shared_secret|bytearray:verify_token")
				sharedSecret = encryption.decrypt_shared_secret(data["shared_secret"], self.privateKey)
				verifyToken = encryption.decrypt_shared_secret(data["verify_token"], self.privateKey)
				if verifyToken == self.verifyToken:
					print "VERIFY TOKENS ARE THE SAME, HOORAY!"
				else:
					print "VERIFY TOKENS WERE NOT THE SAME - KILLING"
				h = hashlib.sha1()
				h.update(self.serverID)
				h.update(sharedSecret)
				h.update(self.publicKey)
				serverId = h.hexdigest()
				r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s&serverId=%s" % (self.username, serverId))
				print "SessionServer response: %s" % r.text
				
				self.packet.sendCipher = encryption.AES128CFB8(sharedSecret)
				self.packet.recvCipher = encryption.AES128CFB8(sharedSecret)
				
				#try:
#					data = r.json()
#					uuid = data["id"]
#					self.uuid = "%s-%s-%s-%s-%s" % (uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:]) 
#				except:
#					self.disconnect("Session Server Error (no response)")
#					return False
				self.uuid = "b5c6c2f1-2cb8-30d8-807e-8a75ddf765af" # static UUID because Mojang SessionServer sux
				
				self.send(0x02, "string|string", (self.uuid, self.username))
				self.state = 3
				self.connect()
				return False
		if id == 0x04:
			data = self.read("double:x|double:y|double:z|bool:on_ground")
			#objection = self.wrapper.callEvent("player.move", {"player": self.username, "xyz": (data["x"], data["y"], data["z"]), "on_ground": data["on_ground"]})
			self.position = (data["x"], data["y"], data["z"])
			#else:
				#self.wrapper.server.run("tp %s %d %d %d" % (self.username, data["x"], data["y"], data["z"]))
		if id == 0x06:
			data = self.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
			#objection = self.wrapper.callEvent("player.move", {"player": self.username, "xyz": (data["x"], data["y"], data["z"]), "on_ground": data["on_ground"]})
			self.position = (data["x"], data["y"], data["z"])
		if id == 0x07: # block breakment
			if self.version < 6:
				data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face", packet[1])
				position = (data["x"], data["y"], data["z"])
			else:
				data = self.read("byte:status|position:position|byte:face")
				position = data["position"]
			if data is None: return False 
			if data["status"] not in (3, 4, 5):
				if not self.wrapper.callEvent("player.dig", {"player": self.username, "position": position, "status": data["status"], "face": data["face"]}): return False
		if id == 0x08: # block placement
			if self.version < 6:
				data = self.read("int:x|ubyte:y|int:z|byte:direction", packet[1])
				position = (data["x"], data["y"], data["z"])
			else:
				data = self.read("position:position|byte:direction")
				position = data["position"]
			position = data["position"]
			if data["direction"] == -1: 
				if not self.wrapper.callEvent("player.action", {"player": self.username}): return False
			if not self.wrapper.callEvent("player.place", {"player": self.username, "position": position}): return False
		#if id == 0x46: # set threshold
#			data = self.read("varint:threshold")
#			print "SET THRESHOLD TO: %s" % data
#			return False
		return True
	def handle(self):
		t = threading.Thread(target=self.flush, args=())
		t.daemon = True
		t.start()
		try:
			while not self.abort:
				try:
					id, original = self.packet.grabPacket()
				except EOFError:
					print "Client EOFError"
					self.close()
					break
				except:
					print "Failed to grab packet:"
					print traceback.format_exc()
					break
				if self.parse(id) and self.server:
					self.server.sendRaw(original)
		except:
			print "error server->client, blah"
			print traceback.format_exc()
		

class Server: # handle server connection
	def __init__(self, client, wrapper):
		self.client = client
		self.wrapper = wrapper
		self.abort = False
		
		self.state = 0 # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing
		self.packet = None
	def connect(self):
		print "Connecting to server..."
		self.socket = socket.socket()
		self.socket.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
		
		self.packet = Packet(self.socket)
		
		self.send = self.packet.send
		self.read = self.packet.read
		self.sendRaw = self.packet.sendRaw
		
		t = threading.Thread(target=self.flush, args=())
		t.daemon = True
		t.start()
	def close(self):
		self.abort = True
		self.packet = None
		self.socket.close()
		
		# I may remove this later so the client can remain connected upon server disconnection
		self.client.abort = True
		self.client.server = None
		self.client.close()
		
		print "Connection closed"
	def flush(self):
		while not self.abort:
			self.packet.flush()
			time.sleep(0.05)
	def parse(self, id):
		if id == 0x01:
			data = self.read("int:eid|ubyte:gamemode|byte:dimension|ubyte:difficulty|ubyte:max_players|string:level_type")
			self.client.gamemode = data["gamemode"]
			self.client.dimension = data["dimension"]
		if id == 0x02:
			if self.state == 2:
				self.state = 3
				return False
		if id == 0x05:
			data = self.read("int:x|int:y|int:z")
			self.wrapper.server.spawnPoint = (data["x"], data["y"], data["z"])
		if id == 0x46:
			data = self.read("varint:threshold")
			print "SET THRESHOLD TO: %s" % data["threshold"]
			return False
		return True
	def handle(self):
		try:
			while not self.abort:
				try:
					id, original = self.packet.grabPacket()
				except EOFError:
					print "Server EOFError"
					print traceback.format_exc()
					self.close()
					break
				except:
					print "Failed to grab packet:"
					print traceback.format_exc()
					break
				if self.parse(id):
					self.client.sendRaw(original)
		except:
			print "error server->client, blah"
			print traceback.format_exc()


class Packet: # PACKET PARSING CODE
	def __init__(self, socket):
		self.socket = socket
		
		self.recvCipher = None
		self.sendCipher = None
		self.compression = False
		
		self.buffer = StringIO.StringIO()
		self.query = []
	def grabPacket(self):
		length = self.unpack_varInt()
		if self.compression:
			dataLength = self.unpack_varInt()
		payload = self.recv(length)
		self.buffer = StringIO.StringIO(payload)
		id = self.read_varInt()
		
		original = self.pack_varInt(length)
		original += payload
		
		return (id, original)
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
	def unpack_varInt(self):
		total = 0
		shift = 0
		val = 0x80
		while val&0x80:
			val = struct.unpack('B', self.recv(1))[0]
			total |= ((val&0x7F)<<shift)
			shift += 7
		if total&(1<<31):
			total = total - (1<<32)
		return total
	def flush(self):
		for packet in self.query:
			if self.sendCipher is None:
				self.socket.send(packet)
			else:
				self.socket.send(self.sendCipher.encrypt(packet))
		self.query = []
	def sendRaw(self, payload):
		self.query.append(payload)
	# -- SENDING AND PARSING PACKETS -- #
	def read(self, expression):
		result = {}
		for exp in expression.split("|"):
			type = exp.split(":")[0]
			name = exp.split(":")[1]
			try:
				if type == "string": result[name] = self.read_string()
				if type == "ubyte": result[name] = self.read_ubyte()
				if type == "byte": result[name] = self.read_byte()
				if type == "int": result[name] = self.read_int()
				if type == "short": result[name] = self.read_short()
				if type == "ushort": result[name] = self.read_ushort()
				if type == "long": result[name] = self.read_long()
				if type == "double": result[name] = self.read_double()
				if type == "float": result[name] = self.read_float()
				if type == "bool": result[name] = self.read_bool()
				if type == "varint": result[name] = self.read_varInt()
				if type == "bytearray": result[name] = self.read_bytearray()
				if type == "position": result[name] = self.read_position()
			except:
				print traceback.format_exc()
				result[name] = None
		return result
	def send(self, id, expression, payload):
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
		if self.compression:
			result = self.pack_varInt(len(result)) + self.pack_varInt(-1) + result
		else:
			result = self.pack_varInt(len(result)) + result
			
		print "W>C ID %s: %s" % (chr(id).encode("hex"), result.encode("hex"))
		self.sendRaw(result)
		return result
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
	def recv(self, length):
		d = self.socket.recv(length)
		if len(d) == 0 and length is not len(d):
#			print d, length
			raise EOFError("Actual length of packet was not as long as expected!")
		if self.recvCipher is None:
			return d
		return self.recvCipher.decrypt(d)
	def read_data(self, length):
		d = self.buffer.read(length)
		if len(d) == 0:
			self.disconnect("Received no data - connection closed")
			return ""
		return d
	def read_byte(self):
		return struct.unpack("b", self.read_data(1))[0]
	def read_ubyte(self):
		return struct.unpack("B", self.read_data(1))[0]
	def read_long(self):
		return struct.unpack(">q", self.read_data(8))[0]
	def read_float(self):
		return struct.unpack(">f", self.read_data(4))[0]
	def read_int(self):
		return struct.unpack(">i", self.read_data(4))[0]
	def read_double(self):
		return struct.unpack(">d", self.read_data(8))[0]
	def read_bool(self):
		if self.read_data(1) == 0x01: return True
		else: return False
	def read_short(self):
		return struct.unpack(">h", self.read_data(2))[0]
	def read_ushort(self):
		return struct.unpack(">H", self.read_data(2))[0]
	def read_bytearray(self):
		return self.read_data(self.read_varInt())
	def read_position(self):
		position = self.read_long()
		position = (position >> 38, (position >> 26) & 0xFFF, position & 0x3FFFFFF)
		return position
	def read_varInt(self):
		total = 0
		shift = 0
		val = 0x80
		while val&0x80:
			val = struct.unpack('B', self.read_data(1))[0]
			total |= ((val&0x7F)<<shift)
			shift += 7
		if total&(1<<31):
			total = total - (1<<32)
		return total
	def read_string(self):
		return self.read_data(self.read_varInt())