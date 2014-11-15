import math, struct, json
class World:
	def __init__(self, name, server):
		self.chunks = {}
		self.entities = {}
		self.name = name
		self.server = server
	def __str__(self):
		return self.name
	def getBlock(self, pos):
		x, y, z = pos
		chunkX, chunkZ = int(x / 16), int(z / 16)
		localX, localZ = (x/16.0 - x/16) * 16, (z/16.0 - z/16) * 16
		#print chunkX, chunkZ, localX, y, localZ
		return self.chunks[chunkX][chunkZ].getBlock(localX, y, localZ)
	def setChunk(self, x, z, chunk):
		if x not in self.chunks: self.chunks[x] = {}
		self.chunks[x][z] = chunk
	def getEntityByEID(self, eid):
		""" Returns the entity context, or None if the specified entity ID doesn't exist. """
		if eid in self.entities: return self.entities[eid]
	def setBlock(self, x, y, z, tilename, damage=0, mode="replace", data={}):
		self.server.console("setblock %d %d %d %s %d %s %s" % (x, y, z, tilename, damage, mode, json.dumps(data)))
	def fill(self, position1, position2, tilename, damage=0, mode="destroy", data={}):
		""" Fill a 3D cube with a certain block.
		
		Modes: destroy, hollow, keep, outline"""
		if mode not in ("destroy", "hollow", "keep", "outline"):
			raise Exception("Invalid mode: %s" % mode)
		x1, y1, z1 = position1
		x2, y2, z2 = position2
		if self.server.protocolVersion < 6:
			raise Exception("Must be running Minecraft 1.8 or above to use the world.fill() method.")
		else:
			self.server.console("fill %d %d %d %d %d %d %s %d %s %s" % (x1, y1, z1, x2, y2, z2, tilename, damage, mode, json.dumps(data)))
	def replace(self, position1, position2, tilename1, damage1, tilename2, damage2=0):
		""" Replace specified blocks within a 3D cube with another specified block. """
		x1, y1, z1 = position1
		x2, y2, z2 = position2
		if self.server.protocolVersion < 6:
			raise Exception("Must be running Minecraft 1.8 or above to use the world.replace() method.")
		else:
			self.server.console("fill %d %d %d %d %d %d %s %d replace %s %d" % (x1, y1, z1, x2, y2, z2, tilename2, damage2, tilename1, damage1))
class Chunk:
	def __init__(self, bytearray, x, z):
		self.ids = struct.unpack("<" + ("H" * (len(bytearray) / 2)), bytearray)
		self.x = x
		self.z = z
		#for i,v in enumerate(bytearray):
#			y = math.ceil(i/256)
#			if y not in self.blocks: self.blocks[y] = {}
#			z = int((i/256.0 - int(i/256.0)) * 16)
#			if z not in self.blocks[y]: self.blocks[y][z] = {}
#			x = (((i/256.0 - int(i/256.0)) * 16) - z) * 16
#			if x not in self.blocks[y][z]: self.blocks[y][z][x] = i
	def getBlock(self, x, y, z):
		#print x, y, z
		i = int((y * 256) + (z * 16) +x)
		id = self.ids[i]
		return id