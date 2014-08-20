import socket, threading, struct, StringIO, time, traceback, json, random, requests, hashlib, os, zlib
try:
	import encryption
	IMPORT_SUCCESS = True
except:
	IMPORT_SUCCESS = False
class Proxy:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.socket = False
		self.isServer = False
		self.clients = []
		
		self.privateKey = encryption.generate_key_pair()
		self.publicKey = encryption.encode_public_key(self.privateKey)
	def host(self):
		# get the protocol version from the server
		while not self.wrapper.server.status == 2:
			time.sleep(.2)
		self.pollServer()
		while not self.socket:
			time.sleep(1)
			try:
				self.socket = socket.socket()
				self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				self.socket.bind((self.wrapper.config["Proxy"]["proxy-bind"], self.wrapper.config["Proxy"]["proxy-port"]))
				self.socket.listen(5)
			except:
				self.socket = False
	 	while not self.wrapper.halt:
	 		try:
		 		sock, addr = self.socket.accept()
		 		client = Client(sock, addr, self.wrapper, self.publicKey, self.privateKey)
		 		
		 		t = threading.Thread(target=client.handle, args=())
		 		t.daemon = True
		 		t.start()

				self.clients.append(client)
		 		print "HICKERY DOOD"
		 		print self.clients		 		
		 		
		 		# remove stale clients
		 		for i, client in enumerate(self.wrapper.proxy.clients):
					if client.abort:
						print "Removed stale client for %s" % client.username
						del self.wrapper.proxy.clients[i]
		 	except:
		 		print traceback.print_exc()
		 		try:
		 			client.disconnect("Some error")
		 		except:
		 			pass
	def pollServer(self):
		sock = socket.socket()
		sock.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
		packet = Packet(sock, self)
		
		packet.send(0x00, "varint|string|ushort|varint", (5, "localhost", self.wrapper.config["Proxy"]["server-port"], 1))
		packet.send(0x00, "", ())
		packet.flush()
		
		while True:
			id, original = packet.grabPacket()
			if id == 0x00:
				data = json.loads(packet.read("string:response")["response"])
				self.wrapper.server.protocolVersion = data["version"]["protocol"]
				break
		sock.close()
class Client: # handle client/game connection
	def __init__(self, socket, addr, wrapper, publicKey, privateKey):
		self.socket = socket
		self.wrapper = wrapper
		self.config = wrapper.config
		self.socket = socket
		self.publicKey = publicKey
		self.privateKey = privateKey
		self.abort = False
		self.tPing = time.time()
		self.server = None
		self.isServer = False
		
		self.state = 0 # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing
		
		self.packet = Packet(self.socket, self)
		self.send = self.packet.send
		self.read = self.packet.read
		self.sendRaw = self.packet.sendRaw
		
		self.username = None
		self.gamemode = 0
		self.dimension = 0
		self.position = (0, 0, 0)
		self.inventory = {}
		self.slot = 0
		self.windowCounter = 2
		for i in range(45): self.inventory[i] = None
	def connect(self):
		self.server = Server(self, self.wrapper)
		self.server.connect()
		t = threading.Thread(target=self.server.handle, args=())
		t.daemon = True
		t.start()
		
		self.server.send(0x00, "varint|string|ushort|varint", (self.version, "localhost", self.config["Proxy"]["server-port"], 2))
		self.server.send(0x00, "string", (self.username,))
#		self.server.send(0x46, "varint", (-1,))
#		self.server.packet.compression = True
#		self.packet.compression = True
		self.server.state = 2
	def close(self):
		self.abort = True
		try:
			self.socket.close()
		except:
			pass
		if self.server:
			self.server.abort = True
			self.server.close()
		for i, client in enumerate(self.wrapper.proxy.clients):
			if client.username == self.username:
				del self.wrapper.proxy.clients[i]
	def disconnect(self, message):
		print "Disconnecting client: %s" % message
		if self.state == 3:
			self.send(0x40, "json", ({"text": message, "color": "red"},))
		else:
			self.send(0x00, "json", ({"text": message, "color": "red"},))
		time.sleep(1)
		self.close()
	def flush(self):
		while not self.abort:
#			try:
			self.packet.flush()
		#	except:
#				print "Error while flushing to client"
#				print traceback.format_exc()
#				self.close()
			time.sleep(0.05)
	def parse(self, id):
		if id == 0x00:
			if self.state == 0:
				data = self.read("varint:version|string:address|ushort:port|varint:state")
				self.version = data["version"]
				self.wrapper.server.protocolVersion = self.version
				self.packet.version = self.version
				if data["state"] in (1, 2):
					self.state = data["state"]
				else:
					self.disconnect("Invalid state '%d'" % data["state"])
				return False
			elif self.state == 1:
				MOTD = {"description": self.config["Proxy"]["motd"], 
					"players": {"max": 20, "online": len(self.wrapper.server.players)},
					"version": {"name": self.wrapper.server.version, "protocol": self.wrapper.server.protocolVersion}
				}
				if os.path.exists("server-icon.png"):
					f = open("server-icon.png", "r")
					serverIcon = "data:image/png;base64," + f.read().encode("base64")
					f.close()
					MOTD["favicon"] = serverIcon
				self.send(0x00, "string", (json.dumps(MOTD),))
				self.state = 5
				return False
			elif self.state == 2:
				data = self.read("string:username")
				self.username = data["username"]
				
				if self.config["Proxy"]["online-mode"]:
					self.state = 4
					self.verifyToken = encryption.generate_challenge_token()
					self.serverID = encryption.generate_server_id()
					self.send(0x01, "string|bytearray|bytearray", (self.serverID, self.publicKey, self.verifyToken))
				else:
					self.connect()
					self.send(0x02, "string|string", ("b5c6c2f1-2cb8-30d8-807e-8a75ddf765af", self.username))
					self.state = 3
				return False
			elif self.state == 3:
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
				h = hashlib.sha1()
				h.update(self.serverID)
				h.update(sharedSecret)
				h.update(self.publicKey)
				serverId = h.hexdigest()
				r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s&serverId=%s" % (self.username, serverId))
#				print "SessionServer response: %s" % r.text
				
				self.packet.sendCipher = encryption.AES128CFB8(sharedSecret)
				self.packet.recvCipher = encryption.AES128CFB8(sharedSecret)
				
				if not verifyToken == self.verifyToken:
					self.disconnect("Verify tokens are not the same")
					return False
				try:
					data = r.json()
					uuid = data["id"]
					self.uuid = "%s-%s-%s-%s-%s" % (uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:])
					
					if not data["name"] == self.username:
						self.disconnect("Client's username did not match Mojang's record")
						return False 
					for property in data["properties"]:
						if property["name"] == "textures":
							self.skinBlob = property["value"]
				except:
					self.disconnect("Session Server Error (this is not your fault - keep reconnecting until it works)")
					return False
				#self.uuid = "b5c6c2f1-2cb8-30d8-807e-8a75ddf765af" # static UUID because Mojang SessionServer sux
				
				self.send(0x02, "string|string", (self.uuid, self.username))
				self.state = 3
				self.connect()
				return False
			elif self.state == 5: # ping packet during status request
				keepAlive = self.read("long:keepAlive")["keepAlive"]
				self.send(0x01, "long", (keepAlive,))
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
			if self.server.state is not 3: return False
		if id == 0x07: # Player Block Dig
			if self.version < 6:
				data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face")
				position = (data["x"], data["y"], data["z"])
			else:
				data = self.read("byte:status|position:position|byte:face")
				position = data["position"]
			if data is None: return False 
			if data["status"] == 2:
				if not self.wrapper.callEvent("player.dig", {"player": self.username, "position": position, "action": "end_break", "face": data["face"]}): return False
			if data["status"] == 0:
				if not self.wrapper.callEvent("player.dig", {"player": self.username, "position": position, "action": "begin_break", "face": data["face"]}): return False
			if self.server.state is not 3: return False
		if id == 0x08: # Player Block Placement
			if self.version < 6:
				data = self.read("int:x|ubyte:y|int:z|byte:direction|slot:item")
				position = (data["x"], data["y"], data["z"])
			else:
				data = self.read("position:position|byte:direction|slot:item")
				position = data["position"]
			position = data["position"]
			if position == None:
				if not self.wrapper.callEvent("player.action", {"player": self.username}): return False
			else:
				if not self.wrapper.callEvent("player.place", {"player": self.username, "position": position, "item": data["item"]}): return False
			if self.server.state is not 3: return False
		if id == 0x09: # Held Item Change
			slot = self.read("short:short")["short"]
			if self.slot > -1 and self.slot < 9:
				self.slot = slot
			else:
				return False
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
					self.close()
					break
				except:
					print "Failed to grab packet (CLIENT):"
					print traceback.format_exc()
					self.close()
					break
				if time.time() - self.tPing > 1 and self.state == 3:
					if self.version > 32:
						self.send(0x00, "varint", (random.randrange(0, 99999),))
					else:
						self.send(0x00, "int", (random.randrange(0, 99999),))
					self.tPing = time.time()
				if self.parse(id) and self.server:
					self.server.sendRaw(original)
		except:
			print "error client->server, blah"
			print traceback.format_exc()
		

class Server: # handle server connection
	def __init__(self, client, wrapper):
		self.client = client
		self.wrapper = wrapper
		self.abort = False
		self.isServer = True
		
		self.state = 0 # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing
		self.packet = None
		self.version = self.wrapper.server.protocolVersion
		self.log = wrapper.log
	def connect(self):
		self.socket = socket.socket()
		self.socket.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
		
		self.packet = Packet(self.socket, self)
		self.packet.version = self.client.version
		self.username = self.client.username
		
		self.send = self.packet.send
		self.read = self.packet.read
		self.sendRaw = self.packet.sendRaw
		
		t = threading.Thread(target=self.flush, args=())
		t.daemon = True
		t.start()
	def close(self, reason="Disconnected"):
		self.abort = True
		self.packet = None
		try:
			self.socket.close()
		except:
			pass
		
		# I may remove this later so the client can remain connected upon server disconnection
#		self.client.send(0x02, "string|byte", (json.dumps({"text": "Disconnected from server. Reason: %s" % reason, "color": "red"}),0))
#		self.abort = True
#		self.client.connect()
		self.client.abort = True
		self.client.server = None
		self.client.close()
	def flush(self):
		while not self.abort:
			self.packet.flush()
		#	try:
#				self.packet.flush()
#			except:
#				print "Error while flushing, stopping"
#				print traceback.format_exc()
#				self.close()
#				break
			time.sleep(0.05)
	def parse(self, id):
		if id == 0x00:
			if self.state < 3:
				message = self.read("string:string")
				self.log.info("Disconnected from Server: %s" % message["string"])
			elif self.state == 3:
				if self.client.version > 7:
					self.send(0x00, "varint", (self.read("int:i")["i"],))
				return False
		if id == 0x01:
			data = self.read("int:eid|ubyte:gamemode|byte:dimension|ubyte:difficulty|ubyte:max_players|string:level_type")
			self.client.gamemode = data["gamemode"]
			self.client.dimension = data["dimension"]
		if id == 0x02:
			if self.state == 2:
				self.state = 3
				return False
			elif self.state == 3:
				data = json.loads(self.read("string:json")["json"])
				try: 
					if data["translate"] == "chat.type.admin": return False
				except: pass
		if id == 0x03:
			if self.state == 2:
				data = self.read("varint:threshold")
				self.packet.compression = True
				self.packet.compressThreshold = data["threshold"]
#				self.client.send(0x03, "varint", (data["threshold"],))
			#	self.client.packet.compression = True
#				self.client.packet.compressThreshold = data["threshold"]
				print "SET COMPRESSION"
				time.sleep(1)
				return False
		if id == 0x05:
			data = self.read("int:x|int:y|int:z")
			self.wrapper.server.spawnPoint = (data["x"], data["y"], data["z"])
		if id == 0x2b: # change game state
			data = self.read("ubyte:reason|float:value")
			if data["reason"] == 3:
				self.client.gamemode = data["value"]
		if id == 0x2f:
			data = self.read("byte:wid|short:slot|slot:data")
			if data["wid"] == 0:
				self.client.inventory[data["slot"]] = data["data"]
		if id == 0x40:
			message = json.loads(self.read("string:string"))
			self.log.info("Disconnected from Server: %s" % message["message"])
			self.disconnect(message)
#			return False
	#	if id == 0x46:
#			data = self.read("varint:threshold")
#			print "SET THRESHOLD TO: %s" % data["threshold"]
#			self.packet.compression = True
#			self.packet.compressThreshold = data["threshold"]
#			self.client.send(0x46, "varint", (data["threshold"],))
#			self.client.packet.compression = True
#			self.client.packet.compressThreshold = data["threshold"]
#			return False
		return True
	def handle(self):
		try:
			while not self.abort:
				try:
					id, original = self.packet.grabPacket()
				except EOFError:
					print traceback.format_exc()
					self.close()
					break
				except:
					print "Failed to grab packet (SERVER):"
					print traceback.format_exc()
					#self.disconnect("Internal Wrapper.py Error")
#					break
				if self.client.abort:
					self.close()
					break
				try:
					if self.parse(id):
						self.client.sendRaw(original)
				except:
					self.log.debug("Could not parse packet, connection may crumble:")
					self.log.debug(traceback.format_exc())
		except:
			print "error server->client, blah"
			print traceback.format_exc()


class Packet: # PACKET PARSING CODE
	def __init__(self, socket, obj):
		self.socket = socket
		
		self.obj = obj
		
		self.recvCipher = None
		self.sendCipher = None
		self.compressThreshold = -1
		self.version = 5
		
		self.buffer = StringIO.StringIO()
		self.queue = []
	def grabPacket(self):
		length = self.unpack_varInt()
		dataLength = 0
		if not self.compressThreshold == -1:
			dataLength = self.unpack_varInt()
			length = length - len(self.pack_varInt(dataLength))
		payload = self.recv(length)
		if dataLength > 0:
			payload = zlib.decompress(payload)
		self.buffer = StringIO.StringIO(payload)
		id = self.read_varInt()
		return (id, payload)
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
		for p in self.queue:
			packet = p[1]
			if p[0] > -1:
				if len(packet) > self.compressThreshold:
					raise Exception("COMPRESSING SUX")
					packetCompressed = self.pack_varInt(len(packet)) + zlib.compress(packet)
					packet = self.pack_varInt(len(packetCompressed)) + packetCompressed
				else:
					packet = self.pack_varInt(0) + packet
					packet = self.pack_varInt(len(packet)) + packet
			else:
				packet = self.pack_varInt(len(packet)) + packet
			if self.sendCipher is None:
				self.socket.send(packet)
			else:
				self.socket.send(self.sendCipher.encrypt(packet))
		self.queue = []
	def sendRaw(self, payload):
		self.queue.append((self.compressThreshold, payload))
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
				if type == "slot": result[name] = self.read_slot()
			except:
				print traceback.format_exc()
				result[name] = None
		return result
	def send(self, id, expression, payload):
		result = ""
		result += self.send_varInt(id) 
		if len(expression) > 0:
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
					if type == "json": result += self.send_json(pay)
					if type == "bytearray": result += self.send_bytearray(pay)
				except:
					print traceback.format_exc()
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
	def send_bytearray(self, payload):
		return self.send_varInt(len(payload)) + payload
	def send_json(self, payload):
		return self.send_string(json.dumps(payload))
		
	# -- READING DATA TYPES -- #
	def recv(self, length):
		d = self.socket.recv(length)
		if len(d) == 0 and length is not len(d):
			raise EOFError("Actual length of packet was not as long as expected!")
		if self.recvCipher is None:
			return d
		return self.recvCipher.decrypt(d)
	def read_data(self, length):
		d = self.buffer.read(length)
#		if len(d) == 0 and length is not 0:
#			self.disconnect("Received no data - connection closed")
#			return ""
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
	def read_short_bytearray(self):
		return self.read_data(self.read_short())
	def read_position(self):
		position = self.read_long()
		if position == -1: return None
		position = (position >> 38, (position >> 26) & 0xFFF, position & 0x3FFFFFF)
		return position
	def read_slot(self):
		id = self.read_short()
		if not id == -1:
			count = self.read_ubyte()
			damage = self.read_short()
			return {"id": id, "count": count, "damage": damage}
#				nbtLength = self.read_short()
#				print count ,damage, nbtLength
#				if nbtLength > 0: nbt = self.read_data(nbtLength)
#				else: nbt = ""
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