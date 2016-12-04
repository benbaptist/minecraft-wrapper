# -*- coding: utf-8 -*-

from time import sleep
import threading
from core.entities import Entities as Entitytypes
from core.entities import Objects as Objecttypes


# noinspection PyPep8Naming
class EntityControl:
    """

    Entity controls are established by console when wrapper reads "preparing ...."

    """
    def __init__(self, mcserver):
        self.chunks = {}

        self.javaserver = mcserver
        self.log = mcserver.log

        # Entities - living beings (includes XP orbs!)
        entitylistobject = Entitytypes()
        self.entitytypes = entitylistobject.entitylist

        # objects.. non living entities, minecarts, falling sand, primed TNT. armorstands, projectiles..
        objectlistobject = Objecttypes()
        self.objecttypes = objectlistobject.objectlist

        # load config settings
        self.entity_control = self.javaserver.config["Entities"]["enable-entity-controls"]
        self.entity_processor_frequency = self.javaserver.config["Entities"]["entity-update-frequency"]
        self.thining_frequency = self.javaserver.config["Entities"]["thinning-frequency"]
        self.server_start_thinning_threshshold = self.javaserver.config["Entities"]["thinning-activation-threshhold"]
        # self.kill_aura_radius = self.javaserver.config["Entities"]["player-thinning-radius"]

        self.entities = {}
        self.abortep = False

        # entity processor thread
        t = threading.Thread(target=self._entity_processor, name="entProc", args=())
        t.daemon = True
        t.start()

        # entity killer thread
        if self.entity_control:
            ekt = threading.Thread(target=self._entity_thinner, name="entKill", args=())
            ekt.daemon = True
            ekt.start()

    def __del__(self):
        self.abortep = True

    # noinspection PyBroadException
    def getEntityByEID(self, eid):
        """ Returns the entity context or False if the specified entity ID doesn't exist.

        WARNING! understand that entities are very DYNAMIC.  The entity object you get
        could be modified or even deleted at any time!

        """
        try:
            return self.entities[eid]
        except Exception:  # as e:
            # self.log.debug("getEntityByEID returned False: %s", e)
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
                      @:type Dict
        """
        ents = []
        entities = self.entities
        for v in iter(entities.values()):
            if v.clientname == playername:
                about = v.about_entity
                if about:
                    ents.append(about())
        return ents

    def getEntityInfo(self, eid):
        """ get dictionary of info on the specified EID.  Returns None if fails

        Sample item:
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

    def killEntityByEID(self, eid, dropitems=False, count=1):
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

        pos = entityinfo["position"]
        entitydesc = entityinfo["name"]
        if dropitems:
            # kill them (get loots if enabled doMobDrops)
            self.javaserver.console("kill @e[type=%s,x=%d,y=%d,z=%d,c=%s]" %
                                    (entitydesc, pos[0], pos[1], pos[2], count))
        else:
            # send them into void (no loots)
            self.javaserver.console("tp @e[type=%s,x=%d,y=%d,z=%d,c=%s] ~ -500 ~" %
                                    (entitydesc, pos[0], pos[1], pos[2], count))

    def _entity_processor(self):
        self.log.debug("_entityprocessor thread started.")
        while self.javaserver.state in (1, 2, 4) and not self.abortep:  # server is running

            sleep(self.entity_processor_frequency)  # timer for removing stale entities

            # start looking for stale client entities
            players = self.javaserver.players
            playerlist = []
            for player in players:
                playerlist.append(player)
            for eid in self.entities.keys():
                if self.getEntityByEID(eid).clientname not in playerlist:
                    # noinspection PyBroadException
                    try:
                        self.entities.pop(eid, None)
                    except:
                        pass
        self.log.debug("_entityprocessor thread closed.")

    # each entity IS a dictionary, so...
    # noinspection PyTypeChecker
    def _entity_thinner(self):
        self.log.debug("_entity_thinner thread started.")
        while self.javaserver.state in (1, 2, 4) and not self.abortep:  # server is running

            sleep(self.thining_frequency)  # timer
            if self.countActiveEntities() < self.server_start_thinning_threshshold:
                continue  # don't bother, server load is light.

            # gather player list
            players = self.javaserver.players
            playerlist = []
            for player in players:
                playerlist.append(player)

            # loop through playerlist
            for playerclient in playerlist:
                players_position = self.javaserver.getplayer(playerclient).getPosition()
                his_entities = self.countEntitiesInPlayer(playerclient)
                if len(his_entities) < self.server_start_thinning_threshshold:
                    # don't worry with this player, his load is light.
                    continue

                # now we need to count each entity type,
                counts = {}
                for entity in his_entities:
                    if entity["name"] in counts:
                        counts[entity["name"]] += 1
                    else:
                        counts[entity["name"]] = 1  # like {"Cow": 1}

                for mob_type in counts:
                    if "thin-%s" % mob_type in self.javaserver.config["Entities"]:
                        maxofthiskind = self.javaserver.config["Entities"]["thin-%s" % mob_type]
                        if counts[mob_type] >= maxofthiskind:
                            # turn off console_spam
                            if "Teleported %s to" % mob_type not in self.javaserver.spammy_stuff:
                                self.javaserver.spammy_stuff.append("Teleported %s to" % mob_type)

                            # can't be too agressive with killing because entitycount might be off/lagging
                            # kill half of any mob above this number
                            killcount = (counts[mob_type] - maxofthiskind) // 2
                            if killcount > 1:
                                self._kill_around_player(players_position, "%s" % mob_type, killcount)

        self.log.debug("_entity_thinner thread closed.")

    def _kill_around_player(self, position, entity_name, count):

        pos = position
        # send those creatures away
        self.log.debug("killing %d %s" % (count, entity_name))
        self.javaserver.console("tp @e[type=%s,x=%d,y=%d,z=%d,c=%s] ~ -500 ~" %
                                (entity_name, pos[0], pos[1], pos[2], count))
