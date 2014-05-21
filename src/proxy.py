import socket, threading, struct, StringIO, time
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
				buffer = self.server.recv(1024)
				self.client.send(buffer)
		except:
			self.disconnect()
	def handleClientToServer(self):
		try:
			while not self.abort:
				packet = Packet(self.grabPacket(self.client))
				payload = packet.parse()
				objection = True
				if payload["packet"] == "chat": # chat packet
					objection = self.wrapper.callEvent("player.rawMessage", {"player": self.username, "message": payload["JSON"]})
				if objection:
					self.server.send(packet.original)
		except:
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
		if id is not 3: print "%s: %s" % (id, payload.read().encode('hex'))
		payload.seek(0)
		return (id, payload, original)
	def unpack_byte(self, socket):
		return struct.unpack("B", socket.recv(1))[0]
	def unpack_varInt(self, socket):
		d = 0
		for i in range(5):
			b = self.unpack_byte(socket)
			d |= (b & 0x7F) << 7*i
			if not b & 0x80:
				break
		return d
	def pack_byte(self, d):
		return struct.pack("B", d)
	def pack_varInt(self, d):
		o = ""
		while True:
			b = d & 0x7F
			d >>= 7
			o += self.pack_byte(b | (0x80 if d > 0 else 0))
			if d == 0:
				break
		return o
class Packet:
	def __init__(self, payload):
		self.payload = payload
		self.id = payload[0]
		self.original = payload[2]
	def byte(self):
		return struct.unpack("B", self.payload[1].read(1))[0]
	def varInt(self):
		d = 0
		for i in range(5):
			b = self.byte()
			d |= (b & 0x7F) << 7*i
			if not b & 0x80:
				break
		return d
	def string(self):
		return self.payload[1].read(self.varInt())
	def parse(self):
		if self.payload[0] == 1:
			return {"packet": "chat",
				"JSON": self.string()
			}
		return {"packet": "unknown"}