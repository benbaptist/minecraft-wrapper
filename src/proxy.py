import socket, threading, struct, StringIO, time, traceback, json
class Proxy:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.socket = False
		self.clients = []
	def host(self):
		while not self.socket:
			time.sleep(1)
			try:
				self.socket = socket.socket()
				self.socket.bind((self.wrapper.config["Proxy"]["bind"], self.wrapper.config["Proxy"]["proxy-port"]))
				self.socket.listen(5)
			except:
				self.socket = False
	 	while not self.wrapper.halt:
	 		try:
		 		sock, addr = self.socket.accept()
		 		client = Client(sock, addr, self.wrapper)
		 		client.connect()
		 		t = threading.Thread(target=client.handleServerToClient, args=())
		 		t.daemon = True
		 		t.start()
		 		t = threading.Thread(target=client.handleClientToServer, args=())
		 		t.daemon = True
		 		t.start()
		 		self.clients.append(client)
		 	except:
		 		client.disconnect()
class Client:
	def __init__(self, socket, addr, wrapper):
		self.client = socket
		self.addr = addr
		self.wrapper = wrapper
		self.username = ""
		self.target = ""
		self.abort = False
		
		self.position = (-1, -1, -1)
		self.gamemode = -1
	def connect(self):
		self.server = socket.socket()
		self.server.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
	def disconnect(self, message="Disconnecting"):
		self.wrapper.log.debug("Disconnecting client '%s' for reason: %s" % (self.username, message))
		self.abort = True
		try:
			self.wrapper.proxy.clients.remove(self)
		except:
			pass
		try:
			self.client.close()
			self.server.close()
		except:
			print traceback.format_exc()
	def handleServerToClient(self):
		try:
			while not self.abort:
				if self.abort: break
				objection = True
				try:
					packet = self.grabPacket(self.server)
					if packet[0] == -1:
						continue
				except:
					continue
				if packet[0] == 1:
					data = self.read("int:eid|ubyte:gamemode|byte:dimension|ubyte:difficulty|ubyte:max_players|string:level_type", packet[1])
					self.gamemode = data["gamemode"]
					self.dimension = data["dimension"]
				if packet[0] == 2:
					data = self.read("string:json_data|position:byte", packet[1])
					try:
						message = json.loads(data["json_data"])
						if message["translate"] == "chat.type.admin": # hide [Server: ] messages, as they spam when Wrapper.py does things
							objection = False
					except:
						pass
				if objection:
					self.client.send(packet[2])
		except:
			self.disconnect()
	def handleClientToServer(self):
		try:
			while not self.abort:
				if self.abort: break
				try:
					packet = self.grabPacket(self.client)
					if packet[0] == -1: continue
				except:
					continue
				objection = True 
				if packet[0] == 0:
					data = self.read("string:username", packet[1])
					if data is not None:
						if self.target == "":
							self.target = data["username"]
						elif self.username == "":
							self.username = data["username"]
							self.wrapper.log.info("%s logging in as %s" % (self.addr[0], self.username))
				if packet[0] == 1:
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
				if packet[0] == 0x04:
					data = self.read("double:x|double:y|double:z|bool:on_ground", packet[1])
					#objection = self.wrapper.callEvent("player.move", {"player": self.username, "xyz": (data["x"], data["y"], data["z"]), "on_ground": data["on_ground"]})
					if objection:
						self.position = (data["x"], data["y"], data["z"])
					else:
						self.wrapper.server.run("tp %s %d %d %d" % (self.username, data["x"], data["y"], data["z"]))
				if packet[0] == 0x06:
					data = self.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground", packet[1])
					#objection = self.wrapper.callEvent("player.move", {"player": self.username, "xyz": (data["x"], data["y"], data["z"]), "on_ground": data["on_ground"]})
					if objection:
						self.position = (data["x"], data["y"], data["z"])
					else:
						self.wrapper.server.run("tp %s %d %d %d" % (self.username, data["x"], data["y"], data["z"]))
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
				if objection:
					self.server.send(packet[2])
		except:
			print traceback.format_exc()
			self.disconnect()
	def grabPacket(self, socket):
		length = self.unpack_varInt(socket)
		id = self.unpack_varInt(socket)
		payload = StringIO.StringIO(socket.recv(length - len(self.pack_varInt(id))))
		original = ""
		original += self.pack_varInt(length)
		original += self.pack_varInt(id)
		original += payload.read()
		payload.seek(0)
		#if id is not 3: print "%s: %s" % (hex(id), payload.read())
#		payload.seek(0)
		return (id, payload, original)
	def unpack_byte(self, socket):
		return struct.unpack("B", socket.recv(1))[0]
	def unpack_varInt(self, buff):
		total = 0
		shift = 0
		val = 0x80
		while val&0x80:
			val = struct.unpack('B', buff.recv(1))[0]
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
				if type == "long": result[name] = self.read_long(socket)
				if type == "double": result[name] = self.read_double(socket)
				if type == "float": result[name] = self.read_float(socket)
				if type == "bool": result[name] = self.read_bool(socket)
				if type == "varint": result[name] = self.read_varInt(socket)
			except:
				print traceback.format_exc()
				result[name] = None
		return result
	def send(self, expression, payload, socket):
		result = ""
		for i,type in enumerate(expression.split("|")):
			try:
				pay = payload[i]
				if type == "string": result += self.send_string(pay)
				if type == "ubyte": result += self.send_ubyte(pay)
				if type == "byte": result += self.send_byte(pay)
				if type == "int": result += self.send_int(pay)
				if type == "short": result += self.send_short(pay)
				if type == "varint": result += self.send_varInt(pay)
				if type == "bytearray": result += pay
			except:
				print traceback.format_exc()
		result = self.pack_varInt(len(result)) + result
		socket.send(result)
	def send_byte(self, payload):
		return struct.pack("b", payload)
	def send_ubyte(self, payload):
	 	return struct.pack("B", payload)
	def send_string(self, payload):
		return self.send_varInt(len(payload)) + payload
	def send_int(self, payload):
		return struct.pack(">i", payload)
	def send_short(self, payload):
		return struct.pack(">h", payload)
	def send_varInt(self, payload):
		return self.pack_varInt(payload)
	def read_data(self, socket, length):
		d = socket.read(length)
		if len(d) == 0:
			self.disconnect()
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