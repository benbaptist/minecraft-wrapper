# -*- coding: utf-8 -*-

import struct
import json
from time import sleep
import threading
from core.entities import Entities as Entitytypes
from core.entities import Objects as Objecttypes


class World:
    """

    World is established by console when wrapper reads "preparing ...."

    """
    def __init__(self, name, mcserver):
        self.chunks = {}

        self.name = name
        self.javaserver = mcserver
        self.log = mcserver.log

        # Entities - living beings (includes XP orbs!)
        entitylistobject = Entitytypes()
        self.entitytypes = entitylistobject.entitylist

        # objects.. non living entities, minecarts, falling sand, primed TNT. armorstands, projectiles..
        objectlistobject = Objecttypes()
        self.objecttypes = objectlistobject.objectlist

        self.entities = {}

        self.abortep = False

        t = threading.Thread(target=self._entityprocessor, name="entProc", args=())
        t.daemon = True
        t.start()

    def __str__(self):
        return self.name

    def __del__(self):
        self.abortep = True

    # region Entity Methods
    def getEntityByEID(self, eid):
        """ Returns the entity context or False if the specified entity ID doesn't exist.

        WARNING! understand that entities are very DYNAMIC.  The entity object you get
        could be modified or even deleted at any time!

        """
        try:
            return self.entities[eid]
        except Exception as e:
            self.log.trace("getEntityByEID returned False: %s", e)
            return False

    def countActiveEntities(self):
        """ return a count of all entities. """
        return len(self.entities)

    def countEntitiesInPlayer(self, playername):
        """returns a list of entity info dictionaries
            [
            {getEntityInfo(eid#1)},  # see getEntityInfo(self, eid)
            {getEntityInfo(eid#2)},
            {getEntityInfo(eid#3)},
            {getEntityInfo(...)}
            ]
        """
        ents = []
        entities = self.entities
        for v in iter(entities.values()):
            if v.clientname == playername:
                about = v.aboutEntity
                if about:
                    ents.append(about())
        return ents

    def getEntityInfo(self, eid):
        """ get dictionary of info on the specified EID.  Returns None if fails

        Sameple item:
          {
            "player": "SapperLeader2",  # the player in whose world the entity exists
            "rodeBy": false,
            "eid": 126,                 # eid of entity - if two or more players share chunks, the same creeper
            "name": "Creeper",          #   could be in the other player's client under other eids
            "Riding": false,
            "position": [
              3333,
              29,
              2847
            ],
            "type": 50,                 # the type code for Creeper
            "isObject": false,
            "uuid": "fae14015-dde6-4e07-b5e5-f27536937a79"  # uuids are only on 1.9+ , but should be unique to object
          }
        """
        try:
            return self.getEntityByEID(eid).aboutEntity()
        except AttributeError:
            return None

    def existsEntityByEID(self, eid):
        """ A way to test whether the specified eid is valid """
        if eid in self.entities:
            return True
        else:
            return False

    def killEntityByEID(self, eid, dropitems=False, finishstateof_domobloot=True, count=1):
        """ takes the entity by eid and kills the first entity of that type centered
        at the coordinates where that entity is.

        Args:
            eid - Entity EID on server
            dropitems - whether or not the entity death will drop loot
            finishstateof_domobloot - True/False - what the desired global state of DoMobLoot is on the server.
            count - used to specify more than one entity; again, centers on the specified eid location.

        """
        entityinfo = self.getEntityInfo(eid)
        if not entityinfo:
            return
        if dropitems:
            self.javaserver.console("gamerule doMobLoot true")
        else:
            self.javaserver.console("gamerule doMobLoot false")
        pos = entityinfo["position"]
        entitydesc = entityinfo["name"]
        self.javaserver.console("kill @e[type=%s,x=%d,y=%d,z=%d,c=%s]" %
                                (entitydesc, pos[0], pos[1], pos[2], count))
        if finishstateof_domobloot:
            self.javaserver.console("gamerule doMobLoot true")

    # endregion

    # region block/world methods
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
        return
    # endregion

    def _entityprocessor(self, updatefrequency=10):
        self.log.debug("_entityprocessor thread started.")
        while self.javaserver.state in (1, 2, 4) and not self.abortep:  # server is running

            self.log.trace("_entityprocessor looping.")
            sleep(updatefrequency)  # timer for adding entities

            # start looking for stale client entities
            players = self.javaserver.players
            playerlist = []
            for player in players:
                playerlist.append(player)
            for eid in self.entities.keys():
                if self.getEntityByEID(eid).clientname not in playerlist:
                    try:
                        self.entities.pop(eid, None)
                    except:
                        pass

            self.log.trace("_entityprocessor updates done.")
        self.log.debug("_entityprocessor thread closed.")


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
