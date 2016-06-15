# -*- coding: utf-8 -*-

from time import time as currtime
try:
    import requests
except ImportError:
    requests = False


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
        return str(self.entitytype)

    def moveRelative(self, position):
        """ Move the entity relative to their position, unless it is illegal.

        This only "tracks" its' position (does not set the position)

        Args:
            position:
        """
        x, y, z = position
        oldposition = [self.position[0], self.position[1], self.position[2]]
        oldposition[0] += x / 32.0
        oldposition[1] += y / 32.0
        oldposition[2] += z / 32.0
        self.position = (oldposition[0], oldposition[1], oldposition[2])
        if self.rodeBy:
            self.rodeBy.position = self.position

    def teleport(self, position):
        """ Track entity teleports to a specific location. """
        self.position = (position[0] / 32, position[1] / 32, position[2] / 32)  # Fixed point numbers...
        if self.rodeBy:
            self.rodeBy.position = self.position

    def aboutEntity(self):
        info = {
            "eid": self.eid,
            "uuid": self.uuid,
            "type": self.entitytype,
            "position": self.position,
            "look": self.look,
            "rodeBy": self.rodeBy,
            "Riding": self.riding,
            "isObject": self.isObject,
            "name": self.entityname,
            "player": self.clientname
        }
        return info