import time, struct, os, StringIO, datetime, json
NAME = "SmallBrother"
ID = "com.benbaptist.plugins.smallbrother"
VERSION = (0, 1)
SUMMARY = "SmallBrother is a lightweight logging plugin for Wrapper.py!"
DESCRIPTION = SUMMARY + "\n\nThe name comes from the old Bukkit plugin, BigBrother.\n\nSee /sb help for usage on how to use SmallBrother."
# all block actions are logged in a user's own file named after their UUID. 
# block action format: block (ushort), damage value (byte), position (long / 8 bytes)
class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log
		
		self.time = 0		
		self.toggled = []
	def onEnable(self):
		self.api.registerEvent("player.dig", self.breakBlock)
		self.api.registerEvent("player.place", self.placeBlock)
		self.api.registerEvent("timer.second", self.timer)
		
		self.api.registerEvent("server.started", self.onServerStart)
		
		self.api.registerCommand("sb", self._sb)
		if self.minecraft.isServerStarted():
			self.onServerStart({})
	def onDisable(self):
		self.logger.flush()
	def onServerStart(self, payload):
		self.logger = Logger(self.minecraft.getWorldName())
		self.logger.init()
	def timer(self, payload):
		self.time += 1
		if self.time == 60 * 2:
			self.logger.flush()
			self.time = 0
	def breakBlock(self, payload):#		print self.minecraft.getServer().world.getBlock(payload["position"])
		player = payload["player"]
		x, y, z = payload["position"]
		uuid = player.uuid
		if player.name in self.toggled:
			actions = self.lookupBlock(x, y, z)
			found = False
			for action in actions:
				self.displayEntry(player, action)
			if len(actions) < 1:
				player.message({"text": "Could not find any actions in the specified area.", "color": "red"})
			else:
				player.message({"text": "End of list.", "color": "red", "bold": True})
			return False
		else:
			self.logger.dig_block(uuid, x, y, z, -1, 0)
	def placeBlock(self, payload):
		if payload["item"] == None: return
		player = payload["player"]
		x, y, z = payload["position"]
		uuid = player.uuid
		if player.name in self.toggled:
			actions = self.lookupBlock(x, y, z)
			found = False
			for action in actions:
				self.displayEntry(player, action)
			if len(actions) < 1:
				player.message({"text": "Could not find any actions in the specified area.", "color": "red"})
			else:
				player.message({"text": "End of list.", "color": "red", "bold": True})
			return False
		else:
			if payload["item"]["id"] < 255:
				self.logger.place_block(uuid, x, y, z, payload["item"]["id"], payload["item"]["damage"])
	def localize(self, p):
		return (((p[0] / 2048.0) - int(p[0] / 2048.0)) * 2048, p[1], ((p[2] / 2048.0) - int(p[2] / 2048.0)) * 2048)
	def deny(self, player):
		if player.isOp(): return True
		else:
			player.message("&cYou are not authorized to run this command. Shoo!")
			return False
	def _sb(self, player, args):
		if not self.deny(player): return
		if len(args) > 0:
			subcommand = args[0]
			if subcommand == "area":
				radius = args[1] # squareRadius, not circular. not really a true radius.
				
				player.message("&cApologies, but this command has not been implemented yet.")
			elif subcommand == "toggle":
				if player.username in self.toggled:
					self.toggled.remove(player.username)
					player.message("&c&lSmallBrother: &r&cTurned off check mode.")
				else:
					self.toggled.append(player.username)
					player.message("&c&lSmallBrother: &r&bTurned on check mode. Left/right click on a block to check the history.")
			elif subcommand == "block":
				x, y, z = int(args[1]), int(args[2]), int(args[3])
				actions = self.lookupBlock(x, y, z)
				found = False
				for action in actions:
					self.displayEntry(player, action)
				if len(actions) < 1:
					player.message({"text": "Could not find any actions in the specified area.", "color": "red"})
				else:
					player.message({"text": "End of list.", "color": "red", "bold": True})
			elif subcommand == "_debug_parse_region_data":
				x, y, z = player.getPosition()
				chunk = ChunkReader(int(x/1024), int(z/1024), self.logger.worldName)
				actions = chunk.load()
				for i in actions:
					player.message(str(i))
			elif subcommand == "help":
				player.message("&lSmallBrother's commands:")
				commands = {"toggle": {"text": "Toggles breaking or placing blocks that check for events in the block that you placed or broke.", "args": ""},
				"area": {"text": "Scan the square radius around the player for events.", "args": "<squareRadius>"},
					"block": {"text": "Checks those specific coordinates for action.", "args": "<x> <y> <z>"}}
				for i in commands:
					com = commands[i]
					player.message("&b&l/sb %s &r&c&o%s: &r&a%s" % (i, com["args"], com["text"]))
			else:
				player.message("&c&lSmallBrother: &r&cUnknown sub-command '%s'. Please see /sb help for a list of sub-commands." % subcommand)
		else:
			player.message("&a&lSmallBrother v1.0")
			player.message("&aFor help with SmallBrother's commands, run /sb help.")
	def displayEntry(self, player, action):
		j = []
		timestamp = datetime.datetime.fromtimestamp(int(action[1])).strftime('%Y-%m-%d %H:%M:%S')
		uuid, type, payload = action[0], action[2], action[3]
		playerName = self.minecraft.lookupUUID(uuid)["name"]
		if playerName == None: playerName == uuid
		j.append({"text": "[%s] " % timestamp, "color": "gray"})
		j.append({"text": playerName + " ", "color": "dark_aqua", "hoverEvent": {"action":"show_text", "value":uuid}})
		if type in ("place_block", "dig_block"):
			if type == "place_block": 
				j.append({"text": "placed "})
			elif type == "dig_block": 
				j.append({"text": "broke "})
			item = json.dumps({"id":payload["block"],"Damage":0,"Count":1,"tag":{}}).replace('"', "")
			j.append({"text": payload["block"], "color": "dark_red", "hoverEvent": {"action":"show_item", "value": item}})
		player.message({"text":"","extra":j})
	def getLoggedUUIDs(self):
		l = os.listdir(self.logger.getPath() + "region")
		a = []
		for i in l:
			if len(i) > 25:
				a.append(i)
		return a
#		return os.listdir(self.logger.getPath() + "region")
	def lookupBlock(self, x, y, z):
		actions = []
		for uuid in self.getLoggedUUIDs():
			chunk = Reader(uuid, self.logger.worldName)
			for action in chunk.load():
				timestamp, type, payload = action
				if type in ("place_block", "dig_block"):
					if payload["position"] == (x, y, z):
						actions.append([uuid, timestamp, type, payload])
		return actions
class Reader:
	def __init__(self, uuid, worldName):
		self.uuid = uuid
		self.worldName = worldName
		self.actions = []
	def load(self):
		if os.path.exists(self.getPath() + "region/%s" % self.uuid):
			self.file = open(self.getPath() + "region/%s" % self.uuid, "r")
			self.parse()
		return self.actions
	def getPath(self):
		return "%s/SmallBrother/" % self.worldName
	def getPayload(self):
		length = struct.unpack("B", self.file.read(1))[0]
		payload = self.file.read(length)
		if len(payload) == 0:
			raise EOFError
		return StringIO.StringIO(payload)
	def getPacket(self):
		self.packet = self.getPayload()
		id = self.read_byte()
		timestamp = self.read_double()
		return id, timestamp
	def read_byte(self):
		return struct.unpack("b", self.packet.read(1))[0]
	def read_ubyte(self):
		return struct.unpack("B", self.packet.read(1))[0]
	def read_short(self):
		return struct.unpack("h", self.packet.read(2))[0]
	def read_ushort(self):
		return struct.unpack("H", self.packet.read(2))[0]
	def read_int(self):
		return struct.unpack("i", self.packet.read(4))[0]
	def read_double(self):
		return struct.unpack("d", self.packet.read(8))[0]
	def read_position(self):
		return (self.read_int(), self.read_ubyte(), self.read_int())
	def read(self, expressions):
		data = {}
		for i in expressions.split("|"):
			name, type = i.split(":")
			if type == "byte": data[name] = self.read_byte()
			if type == "ubyte": data[name] = self.read_ubyte()
			if type == "short": data[name] = self.read_short()
			if type == "ushort": data[name] = self.read_ushort()
			if type == "double": data[name] = self.read_double()
			if type == "position": data[name] = self.read_position()
		return data
	def parse(self):
		while True:
			try:
				id, timestamp = self.getPacket()
			except:
				break
			# list format: time, type, payload
			if id == 0x02:
				data = self.read("position:position|block:short|damage:byte")
				self.actions.append([timestamp, "place_block", data])
			if id == 0x03:
				data = self.read("position:position|block:short|damage:byte")
				self.actions.append([timestamp, "dig_block", data])
class Logger:
	def __init__(self, worldName):
		self.worldName = worldName
		self.queue = {}
	def init(self):
		if not os.path.exists(self.getPath()):
			os.mkdir(self.getPath())
		if not os.path.exists(self.getPath() + "region"):
			os.mkdir(self.getPath() + "region")
	def __del__(self):
		self.flush()
	def cleanup(self):
		pass
	def getPath(self):
		return "%s/SmallBrother/" % self.worldName
#	def getUUIDFile(self, x, z, uuid):
#		if not "%d_%d" % (x, z) in self.obj:
#			if not os.path.exists(self.getPath() + "%d_%d" % (x, z)):
#				os.mkdir(self.getPath() + "%d_%d" % (x, z))
#			if not os.path.exists(self.getPath() + "%d_%d/%s" % (x, z, uuid)):
#				f = open(self.getPath() + "%d_%d/%s" % (x, z, uuid), "w")
#				f.close()
#			self.obj["%d_%d" % (x, z)] = open(self.getPath() + "%d_%d/%s" % (x, z, uuid), "wb")
#		return self.obj["%d_%d" % (x, z)]
#	def flush(self):
#		for i in 
#	def write(self, x, z, uuid, data):
#		if not "%d_%d_%s" % (x, z, uuid) in self.obj:
#			self.obj["%d_%d_%s" % (x, z, uuid)] = []
#		self.obj["%d_%d_%s" % (x, z, uuid)].append(data)
	def flush(self):
		for uuid in self.queue:
			path = self.getPath() + "region/%s" % uuid
			with open(path, "a") as f:
				for packet in self.queue[uuid]:
					f.write(packet)
		self.queue = {}
	def push(self, uuid, payload):
		if not uuid in self.queue:
			self.queue[uuid] = []
		self.queue[uuid].append(self.pack_byte(len(payload)) + payload)
	def write(self, id, expressions, payload):
		b = self.pack_byte(id)
		b += self.pack_double(time.time())
		for i,v in enumerate(expressions.split("|")):
			type, value = v, payload[i]
			if type == "byte": b += self.pack_byte(value)
			if type == "short": b += self.pack_short(value)
			if type == "ushort": b += self.pack_ushort(value)
			if type == "int": b += self.pack_int(value)
			if type == "string": b += self.pack_string(value)
			if type == "double": b += self.pack_double(value)
			if type == "bytearray": b += self.pack_bytearray(value)
			if type == "position": b += self.pack_position(value)
		return b
	# packets
	def place_block(self, uuid, x, y, z, blockid, damage):
		self.push(uuid, self.write(0x02, "position|short|byte", ((x, y, z), blockid, damage)))
	def dig_block(self, uuid, x, y, z, blockid, damage):
		self.push(uuid, self.write(0x03, "position|short|byte", ((x, y, z), blockid, damage)))
	def open_chest(self, x, y, z):
		return self.write(0x04, "int|int|int", (x, y, z))
	def close_chest(self, x, y, z):
		return self.write(uuid, 0x05, "int|int|int", (x, y, z))
	def chest_action(self, x, y, z, action, slot, itemid, damage):
		return self.write(uuid, 0x04, "position|byte|byte|short|short", ((x, y, z), action, slot, itemid, damage))
	# binary functions
	def pack_byte(self, b):
		return struct.pack("b", b)
	def pack_ubyte(self, b):
		return struct.pack("B", b)
	def pack_double(self, b):
		return struct.pack("d", b)
	def pack_short(self, b):
		return struct.pack("h", b)
	def pack_ushort(self, b):
		return struct.pack("H", b)
	def pack_int(self, b):
		return struct.pack("i", b)
	def pack_bytearray(self, b):
		return self.pack_ushort(len(b)) + b
	def pack_string(self, b):
		return self.pack_ushort(len(b.encode("utf-8"))) + b.encode("utf-8")
	def pack_position(self, b):
		return self.pack_int(b[0]) + self.pack_ubyte(b[1]) + self.pack_int(b[2])
		