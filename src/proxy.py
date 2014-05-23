import socket, threading, struct, StringIO, time, traceback
class Proxy:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.socket = False
	def host(self):
		while not self.socket:
			time.sleep(1)
			try:
				self.socket = socket.socket()
				self.socket.bind(("0.0.0.0", 25590))
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
		 	except:
		 		client.disconnect()
class Client:
	def __init__(self, socket, addr, wrapper):
		self.client = socket
		self.addr = addr
		self.wrapper = wrapper
		self.username = "ohai"
		self.abort = False
	def connect(self):
		self.server = socket.socket()
		self.server.connect(("localhost", 25525))
	def disconnect(self):
		try:
			self.client.close()
			self.server.close()
		except:
			pass
	def handleServerToClient(self):
		try:
			while not self.abort:
				buffer = self.server.recv(1024 * 8)
				self.client.send(buffer)
		except:
			self.disconnect()
	def handleClientToServer(self):
		try:
			while not self.abort:
				packet = self.grabPacket(self.client)
				if packet[0] == 1:
					data = self.read("string:message", packet[1])
					print data
				if packet[0] == 0x07:
					data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face", packet[1])
					print data
				#payload = packet.parse()
				objection = True
				#print payload
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
		payload = StringIO.StringIO(socket.recv(length))
		original = ""
		original += self.pack_varInt(length)
		original += self.pack_varInt(id)
		original += payload.read()
		payload.seek(0)
		#if id is not 3: print "%s: %s" % (hex(id), payload.read())
		payload.seek(0)
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
				if type == "varint": result[name] = self.read_varInt(socket)
			except:
				print traceback.format_exc()
				result[name] = None
		return result
	def read_byte(self, socket):
		return struct.unpack("b", socket.read(1))[0]
	def read_ubyte(self, socket):
		return struct.unpack("B", socket.read(1))[0]
	def read_int(self, socket):
		return struct.unpack(">i", socket.read(4))[0]
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
class Packet:
	def __init__(self, payload):
		self.payload = payload
		self.id = payload[0]
		self.original = payload[2]
	def read(self, expression):
		result = {}
		for exp in expression.split("|"):
			type = exp.split(":")[0]
			name = exp.split(":")[1]
			try:
				if type == "string": result[name] = self.string()
				if type == "ubyte": result[name] = self.ubyte()
				if type == "byte": result[name] = self.byte()
				if type == "int": result[name] = self.int()
				if type == "short": result[name] = self.short()
				if type == "varint": result[name] = self.varInt()
			except:
				result[name] = None
	def parse(self):
#		print self.payload[0]
	#	if self.payload[0] == 1:
#			return {"packet": "chat",
#				"JSON": self.string()
#			}
		if self.payload[0] == 1:
			return {"packet": "chat", "payload": self.read("string:json")}
		#if self.payload[0] == 0:
#			return {"packet": "join",
#				"eid": self.int(),
#				"gamemode": self.ubyte(),
#				"dimension": self.byte(),
#				"difficulty": self.ubyte(),
#				"max_players": self.ubyte(),
#				"level_type": self.string()
#			}
		return {"packet": "unknown"}