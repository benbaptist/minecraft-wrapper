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
	58: {"Name": "Enderman", "size": (0.6, 2.9)}
}
class Entity:
	def __init__(self, id, type, position, look, isObject):
		self.id = id # Entity ID
		self.type = type # Type of Entity
		self.position = position # (x, y, z)
		self.look = look # Head Position
		
		if type in ENTITIES: self.type = ENTITIES[type]
		self.isObject = isObject # Boat/Minecart/other non-living Entities are objects
	def __str__(self):
		return str(self.type)
	def move(self, position):
		""" Move the entity relative to their position, unless it is illegal. """
		#self.position = position