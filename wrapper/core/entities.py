# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.


from time import time as currtime
from api.helpers import putjsonfile
from utils.entities import ENTITIES, PRE1_11_RENAMES
from utils.items import BLOCKS

try:
    import requests
except ImportError:
    requests = False

# Sample
# ENTITIES = {
#    "1": {
#        "name": "item"
#    },
#    "2": {
#        "name": "xp_orb"
#    },
#    "3": {
#        "name": "area_effect_cloud" ...


#  Sample
# BLOCKS = {
#  0: {
#    "meta": {
#      0: "Air"
#    },
#    "tilename": "air"
#  },
#  1: {
#    "meta": {
#      0: "Stone",
#      1: "Granite",
#      2: "Polished Granite",
#      3: "Diorite",
#      4: "Polished Diorite",
#      5: "Andesite",
#      6: "Polished Andesite"
#    },
#    "tilename": "stone"
#  }, ...

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


class Entities(object):
    def __init__(self, apply_pre1_11=False):
        self.entitylist = ENTITIES
        if apply_pre1_11:
            self.apply_pre1_11()
        # provide a readout file for the user's reference.
        putjsonfile(self.entitylist, "entities", "./wrapper-data/json/")

    def apply_pre1_11(self):
        for entities in self.entitylist:
            if self.entitylist[entities]["name"] in PRE1_11_RENAMES:
                self.entitylist[entities]["name"] = PRE1_11_RENAMES[self.entitylist[entities]["name"]]
            else:
                component = self.entitylist[entities]["name"].split("_")
                component = [item.capitalize() for item in component]
                concatenated = "".join(component)
                self.entitylist[entities]["name"] = concatenated


class Items(object):
    def __init__(self):
        self.itemslist = BLOCKS


class Objects(object):
    """Objects are actually probably a part of entities"""
    def __init__(self):
        self.objectlist = OBJECTS


class Entity(object):
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


def _test():
    pass
    # from api.helpers import getjsonfile, putjsonfile

    # "http://minecraft-ids.grahamedgecombe.com/items.json"
    # "http://minecraft-ids.grahamedgecombe.com/entities.json"

    # (save items/entities on disk)

    # x = getjsonfile("ents", "/home/surest/github/Wrapper/wrapper/utils")
    # putjsonfile(x, "ents", "/home/surest/github/Wrapper/wrapper/utils",
    #             indent_spaces=4)

    # blocks = {}
    # for item in x:
    #    if item["type"] in blocks:
    #        blocks[item["type"]]["meta"][item["meta"]] = item["name"]
    #    else:
    #        blocks[item["type"]] = {"tilename": item["text_type"],
    #                                "meta": {item["meta"]: item["name"]}}

    # entities = {}
    # for item in x:
    #     entities[item["type"]] = {"name": item["text_type"], "alt_name":
    #                               item["name"]}

    # putjsonfile(entities, "processed",
    #     "/home/surest/github/Wrapper/wrapper/utils", indent_spaces=4)

    # x = Entities()
    # x.apply_pre1_11()
    # putjsonfile(x.entitylist, "processed",
    #             "/home/surest/github/Wrapper/wrapper/utils", indent_spaces=4)

if __name__ == "__main__":
    _test()
