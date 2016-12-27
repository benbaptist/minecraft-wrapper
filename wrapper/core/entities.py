# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

import time
from time import time as currtime
from api.helpers import getjsonfile, putjsonfile

try:
    import requests
except ImportError:
    requests = False

# mobname = Entity.entitylist[type]["name"]
ENTITIES = {  # partial list of entities - Those sizes dont exist on the Grahams version.
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


#  Just a sample (incomplete list) - The real one should be loaded from web/local disk.
BLOCKS = {
  0: {
    "meta": {
      0: "Air"
    },
    "tilename": "air"
  },
  1: {
    "meta": {
      0: "Stone",
      1: "Granite",
      2: "Polished Granite",
      3: "Diorite",
      4: "Polished Diorite",
      5: "Andesite",
      6: "Polished Andesite"
    },
    "tilename": "stone"
  },
  2: {
    "meta": {
      0: "Grass"
    },
    "tilename": "grass"
  },
  3: {
    "meta": {
      0: "Dirt",
      1: "Coarse Dirt",
      2: "Podzol"
    },
    "tilename": "dirt"
  },
  4: {
    "meta": {
      0: "Cobblestone"
    },
    "tilename": "cobblestone"
  },
  5: {
    "meta": {
      0: "Oak Wood Plank",
      1: "Spruce Wood Plank",
      2: "Birch Wood Plank",
      3: "Jungle Wood Plank",
      4: "Acacia Wood Plank",
      5: "Dark Oak Wood Plank"
    },
    "tilename": "planks"
  },
  6: {
    "meta": {
      0: "Oak Sapling",
      1: "Spruce Sapling",
      2: "Birch Sapling",
      3: "Jungle Sapling",
      4: "Acacia Sapling",
      5: "Dark Oak Sapling"
    },
    "tilename": "sapling"
  },
  7: {
    "meta": {
      0: "Bedrock"
    },
    "tilename": "bedrock"
  },
  8: {
    "meta": {
      0: "Flowing Water"
    },
    "tilename": "flowing_water"
  },
  9: {
    "meta": {
      0: "Still Water"
    },
    "tilename": "water"
  },
  10: {
    "meta": {
      0: "Flowing Lava"
    },
    "tilename": "flowing_lava"
  },
  11: {
    "meta": {
      0: "Still Lava"
    },
    "tilename": "lava"
  },
  12: {
    "meta": {
      0: "Sand",
      1: "Red Sand"
    },
    "tilename": "sand"
  },
  13: {
    "meta": {
      0: "Gravel"
    },
    "tilename": "gravel"
  },
  14: {
    "meta": {
      0: "Gold Ore"
    },
    "tilename": "gold_ore"
  },
  15: {
    "meta": {
      0: "Iron Ore"
    },
    "tilename": "iron_ore"
  },
  16: {
    "meta": {
      0: "Coal Ore"
    },
    "tilename": "coal_ore"
  },
  17: {
    "meta": {
      0: "Oak Wood",
      1: "Spruce Wood",
      2: "Birch Wood",
      3: "Jungle Wood"
    },
    "tilename": "log"
  },
  18: {
    "meta": {
      0: "Oak Leaves",
      1: "Spruce Leaves",
      2: "Birch Leaves",
      3: "Jungle Leaves"
    },
    "tilename": "leaves"
  },
  19: {
    "meta": {
      0: "Sponge",
      1: "Wet Sponge"
    },
    "tilename": "sponge"
  },
  20: {
    "meta": {
      0: "Glass"
    },
    "tilename": "glass"
  },
  21: {
    "meta": {
      0: "Lapis Lazuli Ore"
    },
    "tilename": "lapis_ore"
  },
  22: {
    "meta": {
      0: "Lapis Lazuli Block"
    },
    "tilename": "lapis_block"
  }
}

OBJECTS = {
    1: "Boat",
    2: "Item Stack",
    3: "Area Effect Cloud",
    10: "Minecart",
    11: "Minecart (storage), 0.98, 0.7",
    12: "(unused since 1.6.x), Minecart (powered), 0.98,0.7",
    50: "Activated TNT",
    51: "EnderCrystal",
    60: "Arrow (projectile)",
    61: "Snowball (projectile)",
    62: "Egg (projectile)",
    63: "FireBall (ghast projectile)",
    64: "FireCharge (blaze projectile)",
    65: "Thrown Enderpearl",
    66: "Wither Skull (projectile)",
    67: "Shulker Bullet",
    70: "Falling Objects",
    71: "Item frames",
    72: "Eye of Ender",
    73: "Thrown Potion",
    74: "Falling Dragon Egg",
    75: "Thrown Exp Bottle",
    76: "Firework Rocket",
    77: "Leash Knot",
    78: "ArmorStand",
    90: "Fishing Float",
    91: "Spectral Arrow",
    92: "Tipped Arrow",
    93: "Dragon Fireball"
}


class Entities:
    def __init__(self):
        self.entitylist = ENTITIES
        self._getgrahamentities()

    def _getgrahamentities(self):
        frequency = 2592000  # 30 days.
        oldcopy = False
        ondisk = getjsonfile("entities", "./wrapper-data/json/")
        if ondisk:
            if (time.time() - ondisk["lastrefresh"]) > frequency:
                oldcopy = True
        if not ondisk or oldcopy is True:
            if requests:
                r = requests.get("http://minecraft-ids.grahamedgecombe.com/entities.json")
                if r.status_code == 200:
                    objects = r.json()
                    diskfile = {
                        "lastrefresh": time.time(),
                        "data": objects
                    }
                    putjsonfile(diskfile, "entities", "./wrapper-data/json/")
                    ondisk = diskfile
                else:
                    if ondisk:
                        diskfile = {
                            "lastrefresh": time.time(),
                            "data": ondisk["data"]
                        }
                        putjsonfile(diskfile, "entities", "./wrapper-data/json/")
                    else:
                        self.entitylist = ENTITIES
                        return
            else:
                self.entitylist = ENTITIES
                return
        if ondisk:
            entities = {}
            for item in ondisk["data"]:
                entities[item["type"]] = {"name": item["name"]}
            self.entitylist = entities


class Items:
    def __init__(self):
        self.itemslist = BLOCKS
        self._getgrahamitems()

    def _getgrahamitems(self):
        frequency = 2592000  # 30 days.
        oldcopy = False
        ondisk = getjsonfile("items", "./wrapper-data/json/")
        if ondisk:
            if (time.time() - ondisk["lastrefresh"]) > frequency:
                oldcopy = True
        if not ondisk or oldcopy is True:
            if requests:
                r = requests.get("http://minecraft-ids.grahamedgecombe.com/items.json")
                if r.status_code == 200:
                    objects = r.json()
                    diskfile = {
                        "lastrefresh": time.time(),
                        "data": objects
                    }
                    putjsonfile(diskfile, "items", "./wrapper-data/json/")
                    ondisk = diskfile
                else:
                    if ondisk:
                        diskfile = {
                            "lastrefresh": time.time(),
                            "data": ondisk["data"]
                        }
                        putjsonfile(diskfile, "items", "./wrapper-data/json/")
                    else:
                        self.itemslist = BLOCKS
                        return
            else:
                self.itemslist = BLOCKS
                return
        if ondisk:
            blocks = {}
            for item in ondisk["data"]:
                if item["type"] in blocks:
                    blocks[item["type"]]["meta"][item["meta"]] = item["name"]
                else:
                    blocks[item["type"]] = {"tilename": item["text_type"], "meta": {item["meta"]: item["name"]}}
            self.itemslist = blocks


class Objects:
    def __init__(self):
        self.objectlist = OBJECTS


class Entity:
    def __init__(self, eid, uuid, entitytype, entityname, position, look, isobject, playerclientname):
        self.eid = eid  # Entity ID
        self.uuid = uuid  # Entity UUID
        self.entitytype = entitytype  # Type of Entity
        self.position = position  # (x, y, z)
        self.look = look  # Head Position
        self.rodeBy = False
        self.riding = False
        self.isObject = isobject  # Boat/Minecart/other non-living Entities are objects
        self.entityname = entityname
        self.active = currtime()
        self.clientname = playerclientname

    def __str__(self):
        return self.entitytype

    def move_relative(self, position):
        """ Move the entity relative to their position, unless it is illegal.

        This only "tracks" its' position (does not set the position)

        Args:
            position:
        """
        x, y, z = position
        oldposition = [self.position[0], self.position[1], self.position[2]]
        oldposition[0] += x / (128 * 32.0)
        oldposition[1] += y / (128 * 32.0)
        oldposition[2] += z / (128 * 32.0)
        self.position = (oldposition[0], oldposition[1], oldposition[2])
        if self.rodeBy:
            self.rodeBy.position = self.position

    def teleport(self, position):
        """ Track entity teleports to a specific location. """
        self.position = (position[0] / 32, position[1] / 32, position[2] / 32)  # Fixed point numbers...
        if self.rodeBy:
            self.rodeBy.position = self.position

    def about_entity(self):
        info = {
            "eid": self.eid,
            "uuid": str(self.uuid),
            "type": self.entitytype,
            "position": [int(self.position[0]), int(self.position[1]), int(self.position[2])],
            "rodeBy": self.rodeBy,
            "Riding": self.riding,
            "isObject": self.isObject,
            "name": self.entityname,
            "player": self.clientname
        }
        return info
