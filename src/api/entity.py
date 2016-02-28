ENTITIES = { # Unfinished list of entities
	48: {"Name": "Mob"},
	49: {"Name": "Monster"},
	50: {"Name": "Creeper", "size": (0.6, 1.8)},
	51: {"Name": "Skeleton", "size": (0.6, 1.8)},
	52: {"Name": "Spider", "size": (1.4, 0.9)},
	53: {"Name": "Giant Zombie", "size": (3.6, 10.8)}, 
	54: {"Name": "Zombie", "size": (0.6, 1.8)},
	55: {"Name": "Slime", "size": (0.6, 0.6)},
	56: {"Name": "Ghast", "size": (4, 4)},
	57: {"Name": "Zombie Pigman", "size": (0.6, 1.8)},
	58: {"Name": "Enderman", "size": (0.6, 2.9)},
	90: {"Name": "Pig"},
	91: {"Name": "Sheep"},
	92: {"Name": "Cow"},
	93: {"Name": "Chicken"},
	94: {"Name": "Squid"}
}


class Entity:
	def __init__(self, eid, uuid, entitytype, position, look, isObject):
		self.eid = eid # Entity ID
		self.uuid = uuid # Entity UUID
		self.entitytype = entitytype # Type of Entity
		self.position = position # (x, y, z)
		self.look = look # Head Position
		self.rodeBy = False
		self.riding = False
		self.isObject = isObject # Boat/Minecart/other non-living Entities are objects
		if entitytype in ENTITIES and not self.isObject:
			self.entitytype = ENTITIES[entitytype]
			# print("entity type is: %s" % str(self.entitytype["Name"]))

	def __str__(self):
		return str(self.entitytype)
	def moveRelative(self, position):
		""" Move the entity relative to their position, unless it is illegal. """
		x, y, z = position
		oldPosition = [self.position[0], self.position[1], self.position[2]]
		oldPosition[0] += x / 32.0
		oldPosition[1] += y / 32.0
		oldPosition[2] += z / 32.0
		self.position = (oldPosition[0], oldPosition[1], oldPosition[2])
		if self.rodeBy:
			self.rodeBy.position = self.position 
	def teleport(self, position):
		""" Teleport the entity to a specific location. """
		self.position = (position[0] / 32, position[1] / 32, position[2] / 32)
		if self.rodeBy:
			self.rodeBy.position = self.position
