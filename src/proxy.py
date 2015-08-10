# I'll probably split this file into more parts later on, like such: 
# proxy folder: __init__.py (Proxy), client.py (Client), server.py (Server), network.py (Packet), bot.py (will contain Bot, for bot code)
# this could definitely use some code-cleaning.  
import socket, threading, struct, StringIO, time, traceback, json, random, hashlib, os, zlib, binascii, uuid, md5, storage, shutil
from config import Config
from api.entity import Entity
from api.world import World
try: # Weird system for handling non-standard modules
	import encryption, requests
	IMPORT_SUCCESS = True
except:
	IMPORT_SUCCESS = False
class Proxy:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.server = wrapper.server
		self.log = wrapper.log
		self.socket = False
		self.isServer = False
		self.clients = []
		self.skins = {}
		self.skinTextures = {}
		self.uuidTranslate = {}
		self.storage = storage.Storage("proxy-data")
		
		self.privateKey = encryption.generate_key_pair()
		self.publicKey = encryption.encode_public_key(self.privateKey)
	def host(self):
		# get the protocol version from the server
		while not self.wrapper.server.state == 2:
			time.sleep(.2)
		try: self.pollServer()
		except:
			self.log.error("Proxy could not poll the Minecraft server - are you 100% sure that the ports are configured properly? Reason:")
			self.log.getTraceback()
		while not self.socket:
			try:
				self.socket = socket.socket()
				self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				self.socket.bind((self.wrapper.config["Proxy"]["proxy-bind"], self.wrapper.config["Proxy"]["proxy-port"]))
				self.socket.listen(5)
			except:
				self.log.error("Proxy mode could not bind - retrying in five seconds")
				self.log.debug(traceback.format_exc())
				self.socket = False
			time.sleep(5)
		while not self.wrapper.halt:
			try:
				sock, addr = self.socket.accept()
				client = Client(sock, addr, self.wrapper, self.publicKey, self.privateKey, self)
		 		
				t = threading.Thread(target=client.handle, args=())
				t.daemon = True
				t.start()

				self.clients.append(client)

				# Remove stale clients
				for i, client in enumerate(self.wrapper.proxy.clients):
					if client.abort:
						del self.wrapper.proxy.clients[i]
			except: # Not quite sure what's going on
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
				self.wrapper.server.version = data["version"]["name"]
				break
		sock.close()
	def getClientByServerUUID(self, id):
		for client in self.clients:
			if str(client.serverUUID) == str(id):
				self.uuidTranslate[str(id)] = str(client.uuid)
				return client
		if str(id) in self.uuidTranslate:
			return uuid.UUID(hex=self.uuidTranslate[str(id)])
	def lookupUUID(self, uuid):
		if not type(uuid) == str:
			uuid = str(uuid) # Converts UUID objects into a simple UUID string
		#if not self.storage.key("uuid-cache"):
#			self.storage.key("uuid-cache", {})
		if "uuid-cache" not in self.storage:
			self.storage["uuid-cache"] = {}
		if uuid in self.storage["uuid-cache"]:
			return self.storage["uuid-cache"][uuid]
		#with open("usercache.json", "r") as f:
		#	usercache = json.loads(f.read())
		#for i in usercache:
		#	if i["uuid"] == str(uuid):
		#		return i
		return None
	def lookupUsername(self, username):
		if "uuid-cache" not in self.storage:
			self.storage["uuid-cache"] = {}
		for uuid in self.storage["uuid-cache"]:
			if self.storage["uuid-cache"][uuid]["name"] == username:
				return uuid
		r = requests.get("https://api.mojang.com/users/profiles/minecraft/%s" % username)
		uuid = self.formatUUID(r.json()["id"])
		self.setUUID(uuid, username)
		return uuid
	def formatUUID(self, name):
		return str(uuid.UUID(bytes=name.decode("hex")))
	def setUUID(self, uuid, name):
		if not self.storage.key("uuid-cache"):
			self.storage.key("uuid-cache", {})
		self.storage.key("uuid-cache")[str(uuid)] = {"uuid": str(uuid), "name": name}
	def banUUID(self, uuid, reason="Banned by an operator", source="Server"):
		if not self.storage.key("banned-uuid"):
			self.storage.key("banned-uuid", {})
		self.storage.key("banned-uuid")[str(uuid)] = {"reason": reason, "source": source, "created": time.time(), "name": self.lookupUUID(uuid)["name"]}
	def isUUIDBanned(self, uuid): # Check if the UUID of the user is banned
		if not self.storage.key("banned-uuid"):
			self.storage.key("banned-uuid", {})
		if uuid in self.storage.key("banned-uuid"):
			return True
		else:
			return False
	def isAddressBanned(self, address): # Check if the IP address is banned
		if not self.storage.key("banned-address"):
			self.storage.key("banned-address", {})
		if address in self.storage.key("banned-address"):
			return True
		else:
			return False
	def getSkinTexture(self, uuid):
		if uuid not in self.skins: return False
		if uuid in self.skinTextures:
			return self.skinTextures[uuid]
		skinBlob = json.loads(self.skins[uuid].decode("base64"))
		if not "SKIN" in skinBlob["textures"]: # Player has no skin, so set to Alex [fix from #160] 
			skinBlob["textures"]["SKIN"] = {"url": "http://hydra-media.cursecdn.com/minecraft.gamepedia.com/f/f2/Alex_skin.png"}
		r = requests.get(skinBlob["textures"]["SKIN"]["url"])
		self.skinTextures[uuid] = r.content.encode("base64")
		return self.skinTextures[uuid]
class Client: # handle client/game connection
	def __init__(self, socket, addr, wrapper, publicKey, privateKey, proxy):
		self.socket = socket
		self.wrapper = wrapper
		self.config = wrapper.config
		self.socket = socket
		self.publicKey = publicKey
		self.privateKey = privateKey
		self.proxy = proxy
		self.addr = addr
		
		self.abort = False
		self.log = wrapper.log
		self.tPing = time.time()
		self.server = None
		self.isServer = False
		self.isLocal = True
		self.uuid = None
		self.serverUUID = None
		self.server = None
		self.address = None
		self.handshake = False
		
		self.state = 0 # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing
		
		self.packet = Packet(self.socket, self)
		self.send = self.packet.send
		self.read = self.packet.read
		self.sendRaw = self.packet.sendRaw
		
		self.username = None
		self.gamemode = 0
		self.dimension = 0
		self.position = (0, 0, 0) # X, Y, Z 
		self.head = (0, 0) # Yaw, Pitch
		self.inventory = {}
		self.slot = 0
		self.riding = None
		self.windowCounter = 2
		self.properties = {}
		self.clientSettings = None; self.clientSettingsSent = False
		for i in range(45): self.inventory[i] = None
	def connect(self, ip=None, port=None):
		self.clientSettingsSent = False
		if not self.server == None:
			self.address = (ip, port)
		if not ip == None:
			self.server_temp = Server(self, self.wrapper, ip, port)
			try:
				self.server_temp.connect()
				self.server.close(kill_client=False)
				self.server.client = None
				self.server = self.server_temp
			except:
				self.server_temp.close(kill_client=False)
				self.server_temp = None	
				self.send(0x02, "string|byte", ("{text:'Could not connect to that server!', color:red, bold:true}", 0))
				self.address = None
				return
		else:
			self.server = Server(self, self.wrapper, ip, port)
			try:
				self.server.connect()
			except:
				self.disconnect("Proxy not connect to the server.")
		t = threading.Thread(target=self.server.handle, args=())
		t.daemon = True
		t.start()
		
		for xi in range(32):
			xi = xi - 8
			for zi in range(32):
				zi = zi - 8
				x, z = (self.position[0] / 16) + xi, (self.position[2] / 16) + zi
				#print "Sending lel chunk %d, %d" % (x, z)
				#self.send(0x21, "int|int|bool|ushort|varint", (x, z, True, 0, 0))
		
		if self.config["Proxy"]["spigot-mode"]:
			payload = "localhost\x00%s\x00%s" % (self.addr[0], self.uuid.hex)
			self.server.send(0x00, "varint|string|ushort|varint", (self.version, payload, self.config["Proxy"]["server-port"], 2))
		else:
			self.server.send(0x00, "varint|string|ushort|varint", (self.version, "localhost", self.config["Proxy"]["server-port"], 2))
		self.server.send(0x00, "string", (self.username,))
		
		if self.version > 6:
			if self.config["Proxy"]["online-mode"]:
				self.send(0x2b, "ubyte|float", (1, 0))
		
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
		try: 
			message = json.loads(message["string"])
		except: 
			pass
		
		if self.state == 3:
			self.send(0x40, "json", ({"text": message, "color": "red"},))
		else:
			self.send(0x00, "json", ({"text": message, "color": "red"},))
		
		time.sleep(1)
		self.close()
	def flush(self):
		while not self.abort:
			self.packet.flush()
			time.sleep(0.03)
	# UUID operations
	def UUIDIntToHex(self, uuid):
		uuid = uuid.encode("hex")
		uuid = "%s-%s-%s-%s-%s" % (uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:])
		return uuid
	def UUIDHexToInt(self, uuid):
		uuid = uuid.replace("-", "").decode("hex")
		return uuid
	def UUIDFromName(self, name):
		m = md5.new()
		m.update(name)
		d = bytearray(m.digest())
		d[6] &= 0x0f
		d[6] |= 0x30
		d[8] &= 0x3f
		d[8] |= 0x80
		return uuid.UUID(bytes=str(d))
	def getPlayerObject(self):
		if self.username in self.wrapper.server.players:
			return self.wrapper.server.players[self.username]
		return False
	def editsign(self, position, line1, line2, line3, line4):
		self.server.send(0x12, "position|string|string|string|string", (position, line1, line2, line3, line4))
	def message(self, string):
		self.server.send(0x01, "string", (string,))
	def parse(self, id):
		if id == 0x00: # Handshake
			if self.state == 0:
				data = self.read("varint:version|string:address|ushort:port|varint:state")
				self.version = data["version"]
				self.packet.version = self.version
				if not self.wrapper.server.protocolVersion == self.version and data["state"] == 2:
					if self.wrapper.server.protocolVersion == -1:
						self.disconnect("Proxy was unable to connect to the server.")
					else:
						self.disconnect("You're not running the same Minecraft version as the server!")
					return
				if not self.wrapper.server.state == 2:
					self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
					return
				if data["state"] in (1, 2):
					self.state = data["state"]
				else:
					self.disconnect("Invalid state '%d'" % data["state"])
				return False
			elif self.state == 1:
				sample = []
				for i in self.wrapper.server.players:
					player = self.wrapper.server.players[i]
					sample.append({"name": player.username, "id": str(player.uuid)})
					if len(sample) > 5: break
				MOTD = {"description": json.loads(self.wrapper.server.processColorCodes(self.wrapper.server.motd.replace("\\", ""))), 
					"players": {"max": self.wrapper.server.maxPlayers, "online": len(self.wrapper.server.players), "sample": sample},
					"version": {"name": self.wrapper.server.version, "protocol": self.wrapper.server.protocolVersion}
				}
				if self.wrapper.server.serverIcon:
					MOTD["favicon"] = self.wrapper.server.serverIcon
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
					if self.wrapper.server.protocolVersion < 6: # 1.7.x versions
						self.send(0x01, "string|bytearray_short|bytearray_short", (self.serverID, self.publicKey, self.verifyToken))
					else:
						self.send(0x01, "string|bytearray|bytearray", (self.serverID, self.publicKey, self.verifyToken))
				else:
					self.connect()
					self.uuid = self.UUIDFromName("OfflinePlayer:" + self.username)
					self.serverUUID = self.UUIDFromName("OfflinePlayer:" + self.username)
					self.send(0x02, "string|string", (str(self.uuid), self.username))
					self.state = 3
					self.log.info("%s logged in (IP: %s)" % (self.username, self.addr[0]))
				return False
			elif self.state == 3:
				return False
		if id == 0x01:
			if self.state == 3: # Chat
				data = self.read("string:message")
				if data is None: return False
				try:
					message = data["message"]
					if not self.isLocal and message == "/lobby":
						self.server.close(reason="Lobbification", kill_client=False)
						self.address = None
						self.connect()
						self.isLocal = True
						return False 
					if not self.isLocal == True: return True
					payload = self.wrapper.callEvent("player.rawMessage", {"player": self.getPlayerObject(), "message": data["message"]})
					if not payload: return False
					if type(payload) == str:
						message = payload
					if message[0] == "/":
						def args(i):
							try: return message.split(" ")[i]
							except: return ""
						def argsAfter(i):
							try: return message.split(" ")[i:]
							except: return ""
						if self.wrapper.callEvent("player.runCommand", {"player": self.getPlayerObject(), "command": args(0)[1:].lower(), "args": argsAfter(1)}):
							self.message(message)
							return False
						return
					self.message(message)
					return False
				except:
					print traceback.format_exc()
			elif self.state == 4: # Encryption Response Packet
				if self.wrapper.server.protocolVersion < 6:
					data = self.read("bytearray_short:shared_secret|bytearray_short:verify_token")
				else:
					data = self.read("bytearray:shared_secret|bytearray:verify_token")
				sharedSecret = encryption.decrypt_shared_secret(data["shared_secret"], self.privateKey)
				verifyToken = encryption.decrypt_shared_secret(data["verify_token"], self.privateKey)
				h = hashlib.sha1()
				h.update(self.serverID)
				h.update(sharedSecret)
				h.update(self.publicKey)
				serverId = self.packet.hexdigest(h)

				self.packet.sendCipher = encryption.AES128CFB8(sharedSecret)
				self.packet.recvCipher = encryption.AES128CFB8(sharedSecret)
				
				if not verifyToken == self.verifyToken:
					self.disconnect("Verify tokens are not the same")
					return False
				if self.config["Proxy"]["online-mode"]:
					r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s&serverId=%s" % (self.username, serverId))
					try:
						data = r.json()
						self.uuid = data["id"]
						self.uuid = "%s-%s-%s-%s-%s" % (self.uuid[:8], self.uuid[8:12], self.uuid[12:16], self.uuid[16:20], self.uuid[20:])
						self.uuid = uuid.UUID(self.uuid)
						
						if data["name"] != self.username:
							self.disconnect("Client's username did not match Mojang's record")
							return False
						for property in data["properties"]:
							if property["name"] == "textures":
								self.skinBlob = property["value"]
								self.wrapper.proxy.skins[str(self.uuid)] = self.skinBlob
						self.properties = data["properties"]
					except:
						self.disconnect("Session Server Error")
						return False
					if self.proxy.lookupUUID(self.uuid):
						newUsername = self.proxy.lookupUUID(self.uuid)["name"]
						if newUsername != self.username: 
							self.log.info("%s logged in with older name previously, falling back to %s" % (self.username, newUsername))
							self.username = newUsername
				else:
					self.uuid = uuid.uuid3(uuid.NAMESPACE_OID, "OfflinePlayer: %s" % self.username)
				# Rename UUIDs accordingly
				if self.config["Proxy"]["convert-player-files"]:
					if self.config["Proxy"]["online-mode"]:
						# Check player files, and rename them accordingly to offline-mode UUID
						worldName = self.wrapper.server.worldName
						if not os.path.exists("%s/playerdata/%s.dat" % (worldName, str(self.serverUUID))):
							if os.path.exists("%s/playerdata/%s.dat" % (worldName, str(self.uuid))):
								self.log.info("Migrating %s's playerdata file to proxy mode" % self.username)
								shutil.move("%s/playerdata/%s.dat" % (worldName, str(self.uuid)), "%s/playerdata/%s.dat" % (worldName, str(self.serverUUID)))
								with open("%s/.wrapper-proxy-playerdata-migrate" % worldName, "a") as f:
									f.write("%s %s\n" % (str(self.uuid), str(self.serverUUID)))
						# Change whitelist entries to offline mode versions
						if os.path.exists("whitelist.json"):
							data = None
							with open("whitelist.json", "r") as f:
								try: data = json.loads(f.read())
								except: pass
							if data:
								a = False; b = False
								for player in data:
									try:
										if player["uuid"] == str(self.serverUUID):
											a = True
										if player["uuid"] == str(self.uuid):
											b = True
									except: pass
								if a == False and b == True:
									self.log.info("Migrating %s's whitelist entry to proxy mode" % self.username)
									data.append({"uuid": str(self.serverUUID), "name": self.username})
									with open("whitelist.json", "w") as f:
										f.write(json.dumps(data))
									self.wrapper.server.console("whitelist reload")
									with open("%s/.wrapper-proxy-whitelist-migrate" % worldName, "a") as f:
										f.write("%s %s\n" % (str(self.uuid), str(self.serverUUID)))
					
				self.serverUUID = self.UUIDFromName("OfflinePlayer:" + self.username)
				
				if self.version > 26:
					self.packet.setCompression(256)
					
				# Ban code should go here

				if not self.wrapper.callEvent("player.preLogin", {"player": self.username, "online_uuid": self.uuid, "offline_uuid": self.serverUUID, "ip": self.addr[0]}):
					self.disconnect("Login denied.")
					return False

				self.send(0x02, "string|string", (str(self.uuid), self.username))
				self.state = 3
				
				self.connect()
				
				self.log.info("%s logged in (UUID: %s | IP: %s)" % (self.username, self.uuid, self.addr[0]))
				self.proxy.setUUID(self.uuid, self.username)
				
				return False
			elif self.state == 5: # ping packet during status request
				keepAlive = self.read("long:keepAlive")["keepAlive"]
				self.send(0x01, "long", (keepAlive,))
		if id == 0x04:
			data = self.read("double:x|double:y|double:z|bool:on_ground")
			self.position = (data["x"], data["y"], data["z"])
		if id == 0x05: # Player Look
			data = self.read("float:yaw|float:pitch|bool:on_ground")
			yaw, pitch = data["yaw"], data["pitch"]
			self.head = (yaw, pitch)
		if id == 0x06:
			data = self.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
			self.position = (data["x"], data["y"], data["z"])
			self.head = (data["yaw"], data["pitch"])
			if self.server.state is not 3: return False
		if id == 0x07: # Player Block Dig
			if not self.isLocal == True: return True
			if self.version < 6:
				data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face")
				position = (data["x"], data["y"], data["z"])
			else:
				data = self.read("byte:status|position:position|byte:face")
				position = data["position"]
			if data is None: return False 
			if data["status"] == 2:
				if not self.wrapper.callEvent("player.dig", {"player": self.getPlayerObject(), "position": position, "action": "end_break", "face": data["face"]}): return False
			if data["status"] == 0:
				if not self.gamemode == 1:
					if not self.wrapper.callEvent("player.dig", {"player": self.getPlayerObject(), "position": position, "action": "begin_break", "face": data["face"]}): return False
				else:
					if not self.wrapper.callEvent("player.dig", {"player": self.getPlayerObject(), "position": position, "action": "end_break", "face": data["face"]}): return False
			if self.server.state is not 3: return False
		if id == 0x08: # Player Block Placement
			if not self.isLocal == True: return True
			if self.version < 6:
				data = self.read("int:x|ubyte:y|int:z|byte:face|slot:item")
				position = (data["x"], data["y"], data["z"])
			else:
				data = self.read("position:position|byte:face|slot:item")
				position = data["position"]
			position = None
			if self.version > 6: position = data["position"]
			if not position == None:
				face = data["face"]
				if not self.wrapper.callEvent("player.interact", {"player": self.getPlayerObject(), "position": position}): return False
				if face == 0: # Compensate for block placement coordinates
					position = (position[0], position[1] - 1, position[2])
				elif face == 1:
					position = (position[0], position[1] + 1, position[2])
				elif face == 2:
					position = (position[0], position[1], position[2] - 1)
				elif face == 3:
					position = (position[0], position[1], position[2] + 1)
				elif face == 4:
					position = (position[0] - 1, position[1], position[2])
				elif face == 5:
					position = (position[0] + 1, position[1], position[2])
				if not self.wrapper.callEvent("player.place", {"player": self.getPlayerObject(), "position": position, "item": data["item"]}): return False
			if self.server.state is not 3: return False
		if id == 0x09: # Held Item Change
			slot = self.read("short:short")["short"]
			if self.slot > -1 and self.slot < 9:
				self.slot = slot
			else:
				return False
		if id == 0x12:   #sample
			if self.isLocal is not True: return True  # ignore signs from child wrapper/server instance
			if self.version < 6: return True  # player.createsign not implemented for older minecraft versions
			data = self.read("position:position|string:line1|string:line2|string:line3|string:line4")
			position = data["position"]
			l1 = data["line1"]
			l2 = data["line2"]
			l3 = data["line3"]
			l4 = data["line4"]
			payload = self.wrapper.callEvent("player.createsign", {"player": self.getPlayerObject(), "position": position, "line1": l1, "line2": l2, "line3": l3, "line4": l4})
			if not payload: return False
			if type(payload) == dict:
				if "line1" in payload:
					l1 = payload["line1"]  # These lines are supposedly Chat objects
				if "line2" in payload:
					l2 = payload["line2"]
				if "line3" in payload:
					l3 = payload["line3"]
				if "line4" in payload:
					l4 = payload["line4"]
			self.editsign(position, l1, l2, l3, l4)
			return False
		if id == 0x15: # Client Settings
			data = self.read("string:locale|byte:view_distance|byte:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts")
			self.clientSettings = data
		if id == 0x18: # Spectate
			data = self.read("uuid:target_player")
			for client in self.proxy.clients:
				if data["target_player"].hex == client.uuid.hex:
					print "Converting Spectate packet..."
					self.server.send(0x18, "uuid", [client.serverUUID])
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
					self.original = original
				except EOFError:
					self.close()
					break
				except:
					if Config.debug:
						print "Failed to grab packet (CLIENT):"
						print traceback.format_exc()
					self.close()
					break
				if time.time() - self.tPing > 1 and self.state == 3:
					if self.version > 32:
						self.send(0x00, "varint", (random.randrange(0, 99999),))
						if self.clientSettings and not self.clientSettingsSent:
							print "Sending self.clientSettings..."
							print self.clientSettings
							self.server.send(0x15, "string|byte|byte|bool|ubyte", (
								self.clientSettings["locale"],
								self.clientSettings["view_distance"],
								self.clientSettings["chat_mode"],
								self.clientSettings["chat_colors"],
								self.clientSettings["displayed_skin_parts"]
							))
							self.clientSettingsSent = True
					else:
						self.send(0x00, "int", (random.randrange(0, 99999),))
					self.tPing = time.time()
				if self.parse(id) and self.server:
					if self.server.state == 3:
						self.server.sendRaw(original)
		except:
			print "Error in the Client->Server method:"
			print traceback.format_exc()
class Server: # Handle Server Connection
	def __init__(self, client, wrapper, ip=None, port=None):
		self.client = client
		self.wrapper = wrapper
		self.ip = ip
		self.port = port
		self.abort = False
		self.isServer = True
		self.proxy = wrapper.proxy
		self.lastPacketIDs = []
		
		self.state = 0 # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing
		self.packet = None
		self.version = self.wrapper.server.protocolVersion
		self.log = wrapper.log
		self.safe = False
		self.eid = None
	def connect(self):
		self.socket = socket.socket()
		if self.ip == None:
			self.socket.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
		else:
			self.socket.connect((self.ip, self.port))
			self.client.isLocal = False
		
		self.packet = Packet(self.socket, self)
		self.packet.version = self.client.version
		self.username = self.client.username
		
		self.send = self.packet.send
		self.read = self.packet.read
		self.sendRaw = self.packet.sendRaw
		
		t = threading.Thread(target=self.flush, args=())
		t.daemon = True
		t.start()
	def close(self, reason="Disconnected", kill_client=True):
		if Config.debug:
			print "Last packet IDs (Server->Client) before disconnection:"
			print self.lastPacketIDs
		self.abort = True
		self.packet = None
		try:
			self.socket.close()
		except:
			pass
		if self.client.isLocal == False and kill_client:
			self.client.isLocal = True
			self.client.send(0x02, "string|byte", ("{text:'Disconnected from server: %s', color:red}" % reason.replace("'", "\\'"), 0))
			self.client.send(0x2b, "ubyte|float", (1, 0))
			self.client.connect()
			return
		
		# I may remove this later so the client can remain connected upon server disconnection
#		self.client.send(0x02, "string|byte", (json.dumps({"text": "Disconnected from server. Reason: %s" % reason, "color": "red"}),0))
#		self.abort = True
#		self.client.connect()
		if kill_client:
			self.client.abort = True
			self.client.server = None
			self.client.close()
	def getPlayerByEID(self, eid):
		for client in self.wrapper.proxy.clients:
			try:
				if client.server.eid == eid: return self.getPlayerContext(client.username)
			except: print "client.server.eid failed, but that's alright!"
		return False
	def getPlayerContext(self, username):
		try: return self.wrapper.server.players[username]
		except: return False
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
			time.sleep(0.03)
	def parse(self, id, original):
		if id == 0x00:
			if self.state < 3:
				message = self.read("string:string")
				self.log.info("Disconnected from server: %s" % message["string"])
				self.client.disconnect(message)
				return False
			elif self.state == 3:
				if self.client.version > 7:
					id = self.read("varint:i")["i"]
					if not id == None:
						self.send(0x00, "varint", (id,))
				return False
		if id == 0x01:
			if self.state == 3: # Join Game
				data = self.read("int:eid|ubyte:gamemode|byte:dimension|ubyte:difficulty|ubyte:max_players|string:level_type")
				oldDimension = self.client.dimension
				self.client.gamemode = data["gamemode"]
				self.client.dimension = data["dimension"]
				self.eid = data["eid"]  # This is the EID of the player on this particular server - not always the EID that the client is aware of 
				if self.client.handshake:
					dimensions = [-1, 0, 1]
					if oldDimension == self.client.dimension:
						for l in dimensions:
							if l != oldDimension:
								dim = l
								break
						self.client.send(0x07, "int|ubyte|ubyte|string", (l, data["difficulty"], data["gamemode"], data["level_type"]))
					self.client.send(0x07, "int|ubyte|ubyte|string", (self.client.dimension, data["difficulty"], data["gamemode"], data["level_type"]))
					#self.client.send(0x01, "int|ubyte|byte|ubyte|ubyte|string|bool", (self.eid, self.client.gamemode, self.client.dimension, data["difficulty"], data["max_players"], data["level_type"], False))
					self.eid = data["eid"]
					self.safe = True
					return False
				else:
					self.client.eid = data["eid"]
					self.safe = True
				self.client.handshake = True
				
				print "Sending 0x2B..."
				self.client.send(0x2B, "ubyte|float", (3, self.client.gamemode))
			elif self.state == 2:
				self.client.disconnect("Server is online mode. Please turn it off in server.properties.\n\nWrapper.py will handle authentication on its own, so do not worry about hackers.")
				return False
		if id == 0x02:
			if self.state == 2: # Login Success - UUID & Username are sent in this packet
				self.state = 3
				return False
			elif self.state == 3:
				try:
					data = json.loads(self.read("string:json")["json"])
				except: return
				if not self.wrapper.callEvent("player.chatbox", {"player": self.client.getPlayerObject(), "json": data}): return False
				try: 
					if data["translate"] == "chat.type.admin": return False
				except: pass
		if id == 0x03:
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			if self.state == 2: # Set Compression 
				data = self.read("varint:threshold")
				if not data["threshold"] == -1:
					self.packet.compression = True
					self.packet.compressThreshold = data["threshold"]
				else:
					self.packet.compression = False
					self.packet.compressThreshold = -1
				return False
		if id == 0x05: # Spawn Position
			data = self.read("position:spawn")
			self.wrapper.server.spawnPoint = data["spawn"]
		if id == 0x07: # Respawn Packet
			data = self.read("int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
			self.client.gamemode = data["gamemode"]
			self.client.dimension = data["dimension"]
		if id == 0x08: # Player Position and Look
			data = self.read("double:x|double:y|double:z|float:yaw|float:pitch")
			x, y, z, yaw, pitch = data["x"], data["y"], data["z"], data["yaw"], data["pitch"]
			self.client.position = (x, y, z)
		if id == 0x0a: # Use Bed
			data = self.read("varint:eid|position:location")
			if data["eid"] == self.eid:
				self.client.send(0x0a, "varint|position", (self.client.eid, data["location"]))
				return False
		if id == 0x0b: # Animation
			data = self.read("varint:eid|ubyte:animation")
			if data["eid"] == self.eid:
				self.client.send(0x0b, "varint|ubyte", (self.client.eid, data["animation"]))
				return False
		if id == 0x0c: # Spawn Player
			data = self.read("varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|short:item|rest:metadata")
			if self.proxy.getClientByServerUUID(data["uuid"]):
				self.client.send(0x0c, "varint|uuid|int|int|int|byte|byte|short|raw", (
					data["eid"],
					self.proxy.getClientByServerUUID(data["uuid"]).uuid,
					data["x"],
					data["y"],
					data["z"],
					data["yaw"],
					data["pitch"],
					data["item"],
					data["metadata"]))
				return False
		if id == 0x0e: # Spawn Object
			data = self.read("varint:eid|byte:type|int:x|int:y|int:z|byte:pitch|byte:yaw")
			eid, type, x, y, z, pitch, yaw = data["eid"], data["type"], data["x"], data["y"], data["z"], data["pitch"], data["yaw"]
			if not self.wrapper.server.world: return
			self.wrapper.server.world.entities[data["eid"]] = Entity(eid, type, (x, y, z), (pitch, yaw), True)
		if id == 0x0f: # Spawn Mob
			if self.version > 53: 
				data = self.read("varint:eid|uuid:euuid|ubyte:type|int:x|int:y|int:z|byte:pitch|byte:yaw|byte:head_pitch")
			else:
				data = self.read("varint:eid|ubyte:type|int:x|int:y|int:z|byte:pitch|byte:yaw|byte:head_pitch")
			eid, type, x, y, z, pitch, yaw, head_pitch = data["eid"], data["type"], data["x"], data["y"], data["z"], data["pitch"], data["yaw"], data["head_pitch"]
			if not self.wrapper.server.world: return
			self.wrapper.server.world.entities[data["eid"]] = Entity(eid, type, (x, y, z), (pitch, yaw, head_pitch), False)
	#	if id == 0x21: # Chunk Data
#			if self.client.packet.compressThreshold == -1:
#				print "CLIENT COMPRESSION ENABLED"
#				self.client.packet.setCompression(256)
		if id == 0x23: # Block Change
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("position:location|varint:id")
		if id == 0x1a: # Entity Status
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("int:eid|byte:status")
			if data["eid"] == self.eid:
				self.client.send(0x1a, "int|byte", (self.client.eid, data["status"]))
				return False
		if id == 0x15: # Entity Relative Move
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("varint:eid|byte:dx|byte:dy|byte:dz")
			if not self.wrapper.server.world: return
			if not self.wrapper.server.world.getEntityByEID(data["eid"]) == None:
				self.wrapper.server.world.getEntityByEID(data["eid"]).moveRelative((data["dx"], data["dy"], data["dz"]))
		if id == 0x18: # Entity Teleport
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("varint:eid|int:x|int:y|int:z|byte:yaw|byte:pitch")
			if not self.wrapper.server.world: return
			if not self.wrapper.server.world.getEntityByEID(data["eid"]) == None:
				self.wrapper.server.world.getEntityByEID(data["eid"]).teleport((data["x"], data["y"], data["z"]))
		if id == 0x1b: # Attach Entity
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("int:eid|int:vid|bool:leash")
			eid, vid, leash = data["eid"], data["vid"], data["leash"]
			player = self.getPlayerByEID(eid)
			if player == None: return
			if eid == self.eid:
				if vid == -1:
					self.wrapper.callEvent("player.unmount", {"player": player})
					self.client.riding = None
				else:
					self.wrapper.callEvent("player.mount", {"player": player, "vehicle_id": vid, "leash": leash})
					if not self.wrapper.server.world: return
					self.client.riding = self.wrapper.server.world.getEntityByEID(vid)
					self.wrapper.server.world.getEntityByEID(vid).rodeBy = self.client
				if eid != self.client.eid:
					self.client.send(0x1b, "int|int|bool", (self.client.eid, vid, leash))
					return False
		if id == 0x1c: # Entity Metadata
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("varint:eid|rest:metadata")
			if data["eid"] == self.eid:
				self.client.send(0x1c, "varint|raw", (self.client.eid, data["metadata"]))
				return False
		if id == 0x1d: # Entity Effect
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("varint:eid|byte:effect_id|byte:amplifier|varint:duration|bool:hide")
			if data["eid"] == self.eid:
				self.client.send(0x1d, "varint|byte|byte|varint|bool", (self.client.eid, data["effect_id"], data["amplifier"], data["duration"], data["hide"]))
				return False
		if id == 0x1e: # Remove Entity Effect
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("varint:eid|byte:effect_id")
			if data["eid"] == self.eid:
				self.client.send(0x1e, "varint|byte", (self.client.eid, data["effect_id"]))
				return False
		if id == 0x20: # Entity Properties
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("varint:eid|rest:properties")
			if data["eid"] == self.eid:
				self.client.send(0x20, "varint|raw", (self.client.eid, data["properties"]))
				return False
		if id == 0x26: # Map Chunk Bulk
			if self.version > 6:
				data = self.read("bool:skylight|varint:chunks")
				chunks = []
				for i in range(data["chunks"]):
					meta = self.read("int:x|int:z|ushort:primary")
					chunks.append(meta)
				for i in range(data["chunks"]):
					meta = chunks[i]
					bitmask = bin(meta["primary"])[2:].zfill(16)
					primary = []
					for i in bitmask:
						if i == "0": primary.append(False)
						if i == "1": primary.append(True)
					chunkColumn = bytearray()
					for i in primary:
						if i == True:
							chunkColumn += bytearray(self.packet.read_data(16*16*16 * 2)) # packetanisc
							if self.client.dimension == 0:
								metalight = bytearray(self.packet.read_data(16*16*16))
							if data["skylight"]:
								skylight = bytearray(self.packet.read_data(16*16*16))
						else:
							chunkColumn += bytearray(16*16*16 * 2) # Null Chunk
				#self.wrapper.server.world.setChunk(meta["x"], meta["z"], world.Chunk(chunkColumn, meta["x"], meta["z"]))
				#print "Reading chunk %d,%d" % (meta["x"], meta["z"])
		if id == 0x2b: # Change Game State
			data = self.read("ubyte:reason|float:value")
			if data["reason"] == 3:
				self.client.gamemode = data["value"]
		if id == 0x2f: # Set Slot
			if self.version < 6: return True # Temporary! These packets need to be filtered for cross-server stuff.
			data = self.read("byte:wid|short:slot|slot:data")
			if data["wid"] == 0:
				self.client.inventory[data["slot"]] = data["data"]
		if id == 0x30: # Window Items
			data = self.read("byte:wid|short:count")
			if data["wid"] == 0:
				for slot in range(1, data["count"]):
					data = self.read("slot:data")
					self.client.inventory[slot] = data["data"]
		if id == 0x40:
			message = self.read("json:json")["json"]
			self.log.info("Disconnected from server: %s" % message)
			if self.client.isLocal == False:
				self.close()
			else:
				self.client.disconnect(message)
			return False
		if id == 0x38:
			if self.version > 6:
				head = self.read("varint:action|varint:length")
				z = 0
				while z < head["length"]:
					serverUUID = self.read("uuid:uuid")["uuid"]
					client = self.client.proxy.getClientByServerUUID(serverUUID)
					try: uuid = client.uuid
					except:
						uuid = client
						z += 1
					if not client:
						z += 1
						continue
					z += 1
					if head["action"] == 0:
						properties = client.properties
						raw = ""
						for i in properties:
							raw += self.client.packet.send_string(i["name"]) # name
							raw += self.client.packet.send_string(i["value"]) # value
							if "signature" in i:
								raw += self.client.packet.send_bool(True)
								raw += self.client.packet.send_string(i["signature"]) # signature
							else:
								raw += self.client.packet.send_bool(False)
						raw += self.client.packet.send_varInt(0)
						raw += self.client.packet.send_varInt(0)
						raw += self.client.packet.send_bool(False)
						self.client.send(0x38, "varint|varint|uuid|string|varint|raw", (0, 1, client.uuid, client.username, len(properties), raw))
					elif head["action"] == 1:
						data = self.read("varint:gamemode")
						self.client.send(0x38, "varint|varint|uuid|varint", (1, 1, uuid, data["gamemode"]))
					elif head["action"] == 2:
						data = self.read("varint:ping")
						self.client.send(0x38, "varint|varint|uuid|varint", (2, 1, uuid, data["ping"]))
					elif head["action"] == 3:
						data = self.read("bool:has_display")
						if data["has_display"]:
							data = self.read("string:displayname")
							self.client.send(0x38, "varint|varint|uuid|bool|string", (3, 1, uuid, True, data["displayname"]))
						else:
							self.client.send(0x38, "varint|varint|uuid|varint", (3, 1, uuid, False))
					elif head["action"] == 4:
						self.client.send(0x38, "varint|varint|uuid", (4, 1, uuid))
					return False
		return True
	def handle(self):
		try:
			while not self.abort:
				try:
					id, original = self.packet.grabPacket()
					self.lastPacketIDs.append((hex(id), len(original)))
					if len(self.lastPacketIDs) > 10:
						for i,v in enumerate(self.lastPacketIDs):
							del self.lastPacketIDs[i]
							break
				except EOFError:
					print traceback.format_exc()
					self.close()
					break
				except:
					if Config.debug:
						print "Failed to grab packet (SERVER)"
						print traceback.format_exc()
					return
				if self.client.abort:
					self.close()
					break
				if self.parse(id, original) and self.safe:
					self.client.sendRaw(original)
		except:
			if Config.debug:
				print "Error in the Server->Client method:"
				print traceback.format_exc()
			self.close()

class Packet: # PACKET PARSING CODE
	def __init__(self, socket, obj):
		self.socket = socket
		
		self.obj = obj
		
		self.recvCipher = None
		self.sendCipher = None
		self.compressThreshold = -1
		self.version = 5
		self.bonk = False
		self.abort = False
		
		self.buffer = StringIO.StringIO()
		self.queue = []
	def close(self):
		self.abort = True
	def hexdigest(self, sh):
		d = long(sh.hexdigest(), 16)
		if d >> 39 * 4 & 0x8:
			return "-%x" % ((-d) & (2 ** (40 * 4) - 1))
		return "%x" % d
	def grabPacket(self):
		length = self.unpack_varInt()
#		if length == 0: return None
#		if length > 256:
#			print "Length: %d" % length
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
	def setCompression(self, threshold):
#		self.sendRaw("\x03\x80\x02")
		self.send(0x03, "varint", (threshold,))
		self.compressThreshold = threshold
		#time.sleep(1.5)
	def flush(self):
		for p in self.queue:
			packet = p[1]
			id = struct.unpack("B", packet[0])[0]
			if p[0] > -1: #  p[0] > -1:
				if len(packet) > self.compressThreshold:
					packetCompressed = self.pack_varInt(len(packet)) + zlib.compress(packet)
					packet = self.pack_varInt(len(packetCompressed)) + packetCompressed
				else:
					packet = self.pack_varInt(0) + packet
					packet = self.pack_varInt(len(packet)) + packet
			else:
				packet = self.pack_varInt(len(packet)) + packet
		#	if not self.obj.isServer:
#				print packet.encode("hex")
			if self.sendCipher is None:
				self.socket.send(packet)
			else:
				self.socket.send(self.sendCipher.encrypt(packet))
		self.queue = []
	def sendRaw(self, payload):
		if not self.abort:
			self.queue.append((self.compressThreshold, payload))
	# -- SENDING AND PARSING PACKETS -- #
	def read(self, expression):
		result = {}
		for exp in expression.split("|"):
			type = exp.split(":")[0]
			name = exp.split(":")[1]
			if type == "string": result[name] = self.read_string()
			if type == "json": result[name] = self.read_json()
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
			if type == "bytearray_short": result[name] = self.read_bytearray_short()
			if type == "position": result[name] = self.read_position()
			if type == "slot": result[name] = self.read_slot()
			if type == "uuid": result[name] = self.read_uuid()
			if type == "metadata": result[name] = self.read_metadata()
			if type == "rest": result[name] = self.read_rest()
		return result
	def send(self, id, expression, payload):
		result = ""
		result += self.send_varInt(id)
		if len(expression) > 0:
			for i,type in enumerate(expression.split("|")):
				pay = payload[i]
				if type == "string": result += self.send_string(pay)
				if type == "json": result += self.send_json(pay)
				if type == "ubyte": result += self.send_ubyte(pay)
				if type == "byte": result += self.send_byte(pay)
				if type == "int": result += self.send_int(pay)
				if type == "short": result += self.send_short(pay)
				if type == "ushort": result += self.send_ushort(pay)
				if type == "varint": result += self.send_varInt(pay)
				if type == "float": result += self.send_float(pay)
				if type == "double": result += self.send_double(pay)
				if type == "long": result += self.send_long(pay)
				if type == "bytearray": result += self.send_bytearray(pay)
				if type == "bytearray_short": result += self.send_bytearray_short(pay)
				if type == "uuid": result += self.send_uuid(pay)
				if type == "metadata": result += self.send_metadata(pay)
				if type == "bool": result += self.send_bool(pay)
				if type == "position": result += self.send_position(pay)
				if type == "raw": result += pay
		self.sendRaw(result)
		return result
	# -- SENDING DATA TYPES -- #
	def send_byte(self, payload):
		return struct.pack("b", payload)
	def send_ubyte(self, payload):
		return struct.pack("B", payload)
	def send_string(self, payload):
		return self.send_varInt(len(payload)) + payload.encode("utf8")
	def send_json(self, payload):
		return self.send_string(json.dumps(payload))
	def send_int(self, payload):
		return struct.pack(">i", payload)
	def send_long(self, payload):
		return struct.pack(">q", payload)
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
	def send_bytearray_short(self, payload):
		return self.send_short(len(payload)) + payload
	def send_uuid(self, payload):
		return payload.bytes
	def send_position(self, payload):
		x, y, z = payload
		return struct.pack(">Q", ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF))
	def send_metadata(self, payload):
		b = ""
		for index in payload:
			type = payload[index][0]
			value = payload[index][1]
			header = (type << 5) | index
			b += self.send_ubyte(header)
			if type == 0: b += self.send_byte(value)
			if type == 1: b += self.send_short(value)
			if type == 2: b += self.send_int(value)
			if type == 3: b += self.send_float(value)
			if type == 4: b += self.send_string(value)
			if type == 5: 
				print "WIP 5"
			if type == 6:
				print "WIP 6"
			if type == 6:
				print "WIP 7"
		b += self.send_ubyte(0x7f)
		return b
	def send_bool(self, payload):
		if payload == False: return self.send_byte(0)
		if payload == True: return self.send_byte(1)
	# -- READING DATA TYPES -- #
	def recv(self, length):
		if length > 200:
			d = ""
			while len(d) < length:
				m = length - len(d)
				if m > 5000: m = 5000
				d += self.socket.recv(m)
		else:
			d = self.socket.recv(length)
			if len(d) == 0:
				raise EOFError("Packet was zero length, disconnecting")
#		while length > len(d):
#			print "Need %d more" % length - len(d)
#			d += self.socket.recv(length - len(d))
#			if not length == len(d):
#				print "ACTUAL PACKET NOT LONG %d %d" % (length, len(d))
#				print "Read more: %d" % len(self.socket.recv(1024))
			#raise EOFError("Actual length of packet was not as long as expected!")
		if self.recvCipher is None:
			return d
		return self.recvCipher.decrypt(d)
	def read_data(self, length):
		d = self.buffer.read(length)
		if len(d) == 0 and length is not 0:
			self.obj.disconnect("Received no data or less data than expected - connection closed")
			return ""
		return d
	def read_byte(self):
		return struct.unpack("b", self.read_data(1))[0]
	def read_ubyte(self):
		return struct.unpack("B", self.read_data(1))[0]
	def read_long(self):
		return struct.unpack(">q", self.read_data(8))[0]
	def read_ulong(self):
		return struct.unpack(">Q", self.read_data(8))[0]
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
	def read_bytearray_short(self):
		return self.read_data(self.read_short())
	def read_position(self):
		position = struct.unpack(">Q", self.read_data(8))[0]
		if position == 0xFFFFFFFFFFFFFFFF: return None
		x = int(position >> 38)
		if (x & 0x2000000): x = (x & 0x1FFFFFF) - 0x2000000
		y = int((position >> 26) & 0xFFF)
		if (y & 0x800): y = (y & 0x4FF) - 0x800
		z = int(position & 0x3FFFFFF)
		if (z & 0x2000000): z = (z & 0x1FFFFFF) - 0x2000000
		return (x, y, z)
	def read_slot(self):
		id = self.read_short()
		if not id == -1:
			count = self.read_ubyte()
			damage = self.read_short()
			nbtCount = self.read_byte()
			nbt = self.read_data(nbtCount)
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
	def read_uuid(self):
		i = self.read_data(16)
		i = uuid.UUID(bytes=i)
		return i
	def read_string(self):
		return self.read_data(self.read_varInt())
	def read_json(self):
		return json.loads(self.read_string())
	def read_rest(self):
		return self.read_data(1024 * 1024)
	def read_metadata(self):
		data = {}
		while True:
			a = self.read_ubyte()
			if a == 0x7f: return data
			index = a & 0x1f
			type = a >> 5
			if type == 0:
				data[index] = (0, self.read_byte())
			if type == 1: 
				data[index] = (1, self.read_short())
			if type == 2: 
				data[index] = (2, self.read_int())
			if type == 3: 
				data[index] = (3, self.read_float())
			if type == 4: 
				data[index] = (4, self.read_string())
			if type == 5: 
				data[index] = (5, self.read_slot())
			if type == 6: 
				data[index] = (6, (self.read_int(), self.read_int(), self.read_int()))
			#if type == 7: 
			#	data[index] = ("float", (self.read_int(), self.read_int(), self.read_int()))
		return data
