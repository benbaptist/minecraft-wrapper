import math, struct
class World:
	def __init__(self):
		self.chunks = {}
		self.entities = {}
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