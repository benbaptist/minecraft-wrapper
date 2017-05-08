# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.


# noinspection PyPep8Naming
class EntityControl(object):
    """
    .. code:: python

        def __init__(self, proxy)

    ..

    This class is accessed using
            .. code:: python

                <object> = self.api.minecraft.getEntityControl()
                <object>.<class_method>
            ..

    Valid only with a functioning server.

    Entity controls are established by the proxy

    """

    # entire class is a duplicate of proxy's entity control (
    # we are using this for the docs).
    def __init__(self, proxy):
        pass

    def getEntityByEID(self, eid):
        """
        Returns the entity context or False if the specified entity
        ID doesn't exist.

        CAUTION understand that entities are very DYNAMIC.  The
        entity object you get could be modified or even deleted
        at any time!

        """
        pass

    def countActiveEntities(self):
        """
        return an integer count of all entities.

        """
        pass

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
        pass

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
        pass

    def existsEntityByEID(self, eid):
        """
        Test whether the specified eid is valid

        """
        pass

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
        pass
