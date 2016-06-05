# -*- coding: utf-8 -*-

import struct
import json
from copy import deepcopy
from time import sleep
import threading
from core.entities import Entities as Entitytypes


class World:
    """

    World is established by console when wrapper reads "preparing ...."

    """
    def __init__(self, name, mcserver):
        self.chunks = {}

        self.name = name
        self.javaserver = mcserver
        self.log = mcserver.log
        entitylistobject = Entitytypes()
        self.entitytypes = entitylistobject.entitylist

        self.entities = {}
        self.addentities = {}  # dictionary of entity data
        self.delentities = []  # list of eids

        self.abortep = False
        self.entity_blockprocessor = False
        self.entity_blockaccess = False

        t = threading.Thread(target=self._entityprocessor, name="entProc", args=())
        t.daemon = True
        t.start()

    def __str__(self):
        return self.name

    def __del__(self):
        self.abortep = True

    def _entityprocessor(self, updatefrequency=5):
        self.log.trace("_entityprocessor thread started.")
        while self.javaserver.state in (1, 2, 4) and not self.abortep:  # server is running

            self.log.trace("_entityprocessor looping.")
            sleep(updatefrequency)  # timer for adding entities
            self.entity_blockaccess = True
            self.log.trace("_entityprocessor starting updates.")
            # the next 4 steps are not atomic.. we could lose a record between them.. ah well!
            # the only way to avoid that is to have routines block even for updates to addentities
            newadditions = deepcopy(self.addentities)
            self.addentities = {}
            entriestoremove = self.delentities
            self.delentities = []

            self.entities.update(newadditions)
            for k in entriestoremove:
                self.entities.pop(k, None)

            self.entity_blockaccess = False
            self.log.trace("_entityprocessor updates done.")
        self.log.trace("_entityprocessor thread closed.")

    def getBlock(self, pos):
        x, y, z = pos
        chunkx, chunkz = int(x / 16), int(z / 16)
        localx, localz = (x / 16.0 - x / 16) * 16, (z / 16.0 - z / 16) * 16
        # print chunkx, chunkz, localx, y, localz
        return self.chunks[chunkx][chunkz].getBlock(localx, y, localz)

    def setChunk(self, x, z, chunk):
        if x not in self.chunks:
            self.chunks[x] = {}
        self.chunks[x][z] = chunk

    def getEntityByEID(self, eid):
        """ Returns the entity context or None if the specified entity ID doesn't exist.

        WARNING! understand that entities are very DYNAMIC.  The entity object you get
        could be modified or even deleted at any time! it is prudent to copy the entity
        context if you need some data out of it. check for it's validity before
        writing back to it (or expect possible errors).

        """
        if eid in self.entities:
            return self.entities[eid]

    def copyEntityByEID(self, eid):
        """ Returns a copy or None if the specified entity ID doesn't exist.

        used to get a copy of the eid record

        """
        if eid in self.entities:
            return deepcopy(self.entities[eid])

    def addEntity(self, copyof_entity):
        """
        Args:
            copyof_entity = copy of entity obtained with copyEntityByEID.  Also used internally by
            wrapper.proxy.serverconnection.py to add the entity objects it creates.

        used in conjuction with copyEntityByEid.  Takes the copy you made and overwrites the existing
            entity (or -recreates it).  The actual update may happen several seconds later when the
            _entityprocessor runs the updates.


        """
        self.addentities.update(copyof_entity)

    def ExistsEntityByEID(self, eid):
        """ A way to test whether the specified eid is still valid """
        if eid in self.entities:
            return True

    def killEntityByEID(self, eid, dropitems=False, finishstateof_domobloot=True, count=1):
        """ takes the entity by eid and kills the first entity of that type centered
        at the coordinates where that entity is.

        Args:
            eid - Entity EID on server
            dropitems - whether or not the entity death will drop loot
            finishstateof_domobloot - True/False - what the desired global state of DoMobLoot is on the server.
            count - used to specify more than one entity; again, centers on the specified eid location.

        """
        if dropitems:
            self.javaserver.console("gamerule doMobLoot true")
        else:
            self.javaserver.console("gamerule doMobLoot false")
        entity = self.copyEntityByEID(eid)
        pos = entity.position
        entitydesc = entity.entityname
        self.javaserver.console("kill @e[type=%s,x=%d,y=%d,z=%d,c=%d]" %
                                (entitydesc, pos[0], pos[1], pos[2], count))
        if finishstateof_domobloot:
            self.javaserver.console("gamerule doMobLoot True")

    def setBlock(self, x, y, z, tilename, damage=0, mode="replace", data=None):
        if not data:
            data = {}
        self.javaserver.console("setblock %d %d %d %s %d %s %s" % (
            x, y, z, tilename, damage, mode, json.dumps(data)))

    def fill(self, position1, position2, tilename, damage=0, mode="destroy", data=None):
        """ Fill a 3D cube with a certain block.

        Modes: destroy, hollow, keep, outline"""
        if not data:
            data = {}
        if mode not in ("destroy", "hollow", "keep", "outline"):
            raise Exception("Invalid mode: %s" % mode)
        x1, y1, z1 = position1
        x2, y2, z2 = position2
        if self.javaserver.protocolVersion < 6:
            raise Exception("Must be running Minecraft 1.8 or above to use the world.fill() method.")
        else:
            self.javaserver.console("fill %d %d %d %d %d %d %s %d %s %s" % (
                x1, y1, z1, x2, y2, z2, tilename, damage, mode, json.dumps(data)))

    def replace(self, position1, position2, tilename1, damage1, tilename2, damage2=0):
        """ Replace specified blocks within a 3D cube with another specified block. """
        x1, y1, z1 = position1
        x2, y2, z2 = position2
        if self.javaserver.protocolVersion < 6:
            raise Exception(
                "Must be running Minecraft 1.8 or above to use the world.replace() method.")
        else:
            self.javaserver.console("fill %d %d %d %d %d %d %s %d replace %s %d" % (
                x1, y1, z1, x2, y2, z2, tilename2, damage2, tilename1, damage1))


class Chunk:

    def __init__(self, bytesarray, x, z):
        self.ids = struct.unpack("<" + ("H" * (len(bytesarray) / 2)), bytesarray)
        self.x = x
        self.z = z
        # for i,v in enumerate(bytesarray):
        #   y = math.ceil(i/256)
        #   if y not in self.blocks: self.blocks[y] = {}
        #   z = int((i/256.0 - int(i/256.0)) * 16)
        #   if z not in self.blocks[y]: self.blocks[y][z] = {}
        #   x = (((i/256.0 - int(i/256.0)) * 16) - z) * 16
        #   if x not in self.blocks[y][z]: self.blocks[y][z][x] = i

    def getBlock(self, x, y, z):
        # print x, y, z
        i = int((y * 256) + (z * 16) + x)
        bid = self.ids[i]
        return bid
