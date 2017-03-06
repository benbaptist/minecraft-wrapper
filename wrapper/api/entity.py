# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from time import sleep
import threading
from core.entities import Entities as Entitytypes

# move to different future  objects module?
from core.entities import Objects as Objecttypes


# noinspection PyPep8Naming
class EntityControl(object):
    """
    .. code:: python

        def __init__(self, mcserver)

    ..

    This class is accessed using
            .. code:: python

                <object> = self.api.minecraft.getEntityControl()
                <object>.<class_method>
            ..

    Valid only with a functioning server.

    Entity controls are established by console when wrapper
    reads "preparing ...."

    """

    def __init__(self, mcserver):
        self.chunks = {}

        self._javaserver = mcserver
        self._log = mcserver.log

        # Entities - living beings (includes XP orbs!)
        pre1_11 = self._javaserver.version_compute < 11100
        entitylistobject = Entitytypes(pre1_11)
        self.entitytypes = entitylistobject.entitylist

        # objects.. non living entities, minecarts, falling sand,
        # primed TNT. armorstands, projectiles..
        # not directly used here.. but is referenced by parse_cb for
        # 'parse_play_spawn_object'
        # move to different future  objects module?
        objectlistobject = Objecttypes()
        self.objecttypes = objectlistobject.objectlist

        # load config settings
        self.entityControl = self._javaserver.config["Entities"][
            "enable-entity-controls"]
        self.entityProcessorFrequency = self._javaserver.config["Entities"][
            "entity-update-frequency"]
        self.thiningFrequency = self._javaserver.config["Entities"][
            "thinning-frequency"]
        self.startThinningThreshshold = self._javaserver.config["Entities"][
            "thinning-activation-threshhold"]
        # self.kill_aura_radius = self.javaserver.config["Entities"][
        #   "player-thinning-radius"]

        self.entities = {}
        self._abortep = False

        # entity processor thread
        t = threading.Thread(target=self._entity_processor,
                             name="entProc", args=())
        t.daemon = True
        t.start()

        # entity killer thread
        if self.entityControl:
            ekt = threading.Thread(target=self._entity_thinner,
                                   name="entKill", args=())
            ekt.daemon = True
            ekt.start()

    def __del__(self):
        self._abortep = True

    # noinspection PyBroadException
    def getEntityByEID(self, eid):
        """
        Returns the entity context or False if the specified entity
        ID doesn't exist.

        CAUTION understand that entities are very DYNAMIC.  The
        entity object you get could be modified or even deleted
        at any time!

        """
        try:
            return self.entities[eid]
        except Exception:  # as e:
            # self.log.debug("getEntityByEID returned False: %s", e)
            return False

    def countActiveEntities(self):
        """
        return an integer count of all entities.

        """
        return len(self.entities)

    def countEntitiesInPlayer(self, playername):
        """
        returns a list of entity info dictionaries

            see getEntityInfo(self, eid)

            :sample:
                .. code:: python

                    [
                        {<getEntityInfo(eid#1)>},
                        {<getEntityInfo(eid#2)>},
                        {<getEntityInfo(eid#3)>},
                        {<getEntityInfo(...)>}
                    ]

                ..

            (Pycharm return definition)
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
        """
        Get a dictionary of info on the specified EID.  Returns
        None if fails

        :Sample item:
            .. code:: python

                {
                    # the player in whose world the entity exists
                    "player": "SapperLeader2",
                    "rodeBy": False,
                    # eid of entity - if two or more players share
                    # chunks, this could be the same creeper in
                    # both player's world/client. It would be in the
                    # other player's client under  another eid, of
                    # course...
                    "eid": 126,
                    "name": "Creeper",
                    "Riding": False,
                    "position": [
                        3333,
                        29,
                        2847
                    ],
                    # the type code for Creeper
                    "type": 50,
                    "isObject": False,
                    # uuids are only on 1.9+ , but should be unique to object
                    "uuid": "fae14015-dde6-4e07-b5e5-f27536937a79"
                }
            ..

        """
        try:
            return self.getEntityByEID(eid).aboutEntity()
        except AttributeError:
            return None

    def existsEntityByEID(self, eid):
        """
        Test whether the specified eid is valid

        """
        if eid in self.entities:
            return True
        else:
            return False

    def killEntityByEID(self, eid, dropitems=False, count=1):
        """
        Takes the entity by eid and kills the first entity of
        that type centered at the coordinates where that entity is.

        :Args:
            :eid: Entity EID on server
            :dropitems: whether or not the entity death will drop
             loot.  Only works if gamerule doMobDrops is true.
            :count: used to specify more than one entity; again,
             centers on the specified eid location.

        """
        entityinfo = self.getEntityInfo(eid)
        if not entityinfo:
            return

        pos = entityinfo["position"]
        entitydesc = entityinfo["name"]
        if dropitems:
            # kill them (get loots if server has doMobDrops set to true)
            self._javaserver.console(
                "kill @e[type=%s,x=%d,y=%d,z=%d,c=%s]" % (
                    entitydesc, pos[0], pos[1], pos[2], count))
        else:
            # send them into void (no loots)
            self._javaserver.console(
                "tp @e[type=%s,x=%d,y=%d,z=%d,c=%s] ~ -500 ~" % (
                    entitydesc, pos[0], pos[1], pos[2], count))

    def _entity_processor(self):
        self._log.debug("_entityprocessor thread started.")
        timer = float(0)
        # server is running
        while self._javaserver.state in (1, 2, 4) and not self._abortep:
            timer += .1
            sleep(.1)
            # timer for removing stale entities we want a FAST response
            # to server shutdowns (activate while loop frequently)
            if timer < float(self.entityProcessorFrequency):
                continue
            timer = float(0)

            # start looking for stale client entities
            players = self._javaserver.players
            playerlist = []
            for player in players:
                playerlist.append(player)
            entity_eids = list(self.entities.keys())
            for eid in entity_eids:
                if self.getEntityByEID(eid).clientname not in playerlist:
                    # noinspection PyBroadException
                    try:
                        self.entities.pop(eid, None)
                    except:
                        pass
        self._log.debug("_entityprocessor thread closed.")

    # each entity IS a dictionary, so...
    # noinspection PyTypeChecker
    def _entity_thinner(self):
        self._log.debug("_entity_thinner thread started.")
        timer = float(0)

        # while server is running
        while self._javaserver.state in (1, 2, 4) and not self._abortep:

            timer += .1
            sleep(.1)
            # timer for removing stale entities we want a FAST response
            # to server shutdowns (activate while loop frequently)
            if timer < float(self.thiningFrequency):
                continue
            timer = float(0)

            if self.countActiveEntities() < self.startThinningThreshshold:
                # don't bother, server load is light.
                continue

            # gather player list
            players = self._javaserver.players
            playerlist = []
            for player in players:
                playerlist.append(player)

            # loop through playerlist
            for playerclient in playerlist:
                players_position = self._javaserver.getplayer(
                    playerclient).getPosition()
                his_entities = self.countEntitiesInPlayer(playerclient)
                if len(his_entities) < self.startThinningThreshshold:
                    # don't worry with this player, his load is light.
                    continue

                # now we need to count each entity type
                counts = {}
                for entity in his_entities:
                    if entity["name"] in counts:
                        counts[entity["name"]] += 1
                    else:
                        counts[entity["name"]] = 1  # like {"Cow": 1}

                for mob_type in counts:
                    if "thin-%s" % mob_type in self._javaserver.config[
                            "Entities"]:
                        maxofthiskind = self._javaserver.config[
                            "Entities"]["thin-%s" % mob_type]
                        if counts[mob_type] >= maxofthiskind:

                            # turn off console_spam
                            server_msg = "Teleported %s to" % mob_type
                            if server_msg not in self._javaserver.spammy_stuff:
                                self._javaserver.spammy_stuff.append(
                                    "Teleported %s to" % mob_type)

                            # can't be too agressive with killing because
                            # entitycount might be off/lagging
                            # kill half of any mob above this number
                            killcount = (counts[mob_type] - maxofthiskind) // 2
                            if killcount > 1:
                                self._kill_around_player(
                                    players_position, "%s" % mob_type,
                                    killcount)

        self._log.debug("_entity_thinner thread closed.")

    def _kill_around_player(self, position, entity_name, count):
        pos = position
        # send those creatures away
        self._log.debug("killing %d %s" % (count, entity_name))
        self._javaserver.console(
            "tp @e[type=%s,x=%d,y=%d,z=%d,c=%s] ~ -500 ~" %
            (entity_name, pos[0], pos[1], pos[2], count))
