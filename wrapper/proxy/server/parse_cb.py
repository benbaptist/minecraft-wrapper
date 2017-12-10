# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import json

from proxy.entity.entitybasics import Entity
from proxy.utils.constants import *

# Py3-2
import sys
PY3 = sys.version_info > (3,)
if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range


# noinspection PyMethodMayBeStatic
class ParseCB(object):
    """
    ParseSB parses client bound packets that are coming from the server.
    """
    def __init__(self, server, packet):
        self.server = server
        self.log = self.server.log
        self.client = server.client
        self.pktCB = self.server.pktCB
        self.pktSB = self.server.pktSB
        self.proxy = server.client.proxy
        self.packet = packet
        self.ent_control = self.proxy.entity_control

    # Items that need parsed and re-sent with proper offline/online UUID
    # translation.

    def parse_play_player_list_item(self):
        """This must be parsed and modified to make sure UUIDs match.
        Otherwise weird things can happen likee players not seeing
        each other or duplicate names on the tab list, etc."""
        if self.server.version >= PROTOCOL_1_8START:
            head = self.packet.readpkt([VARINT, VARINT])
            # ("varint:action|varint:length")
            lenhead = head[1]
            action = head[0]
            z = 0
            while z < lenhead:
                serveruuid = self.packet.readpkt([UUID])[0]
                playerclient = self.proxy.getclientbyofflineserveruuid(
                    serveruuid)
                if not playerclient:
                    z += 1
                    continue
                try:
                    # Not sure how could this fail. All clients have a uuid.
                    uuid = playerclient.uuid
                except Exception as e:
                    # uuid = playerclient
                    self.log.exception("playerclient.uuid failed in "
                                       "playerlist item (%s)", e)
                    z += 1
                    continue
                z += 1
                if action == 0:
                    properties = playerclient.properties
                    raw = b""
                    for prop in properties:
                        raw += self.client.packet.send_string(prop["name"])
                        raw += self.client.packet.send_string(prop["value"])
                        if "signature" in prop:
                            raw += self.client.packet.send_bool(True)
                            raw += self.client.packet.send_string(
                                prop["signature"])
                        else:
                            raw += self.client.packet.send_bool(False)
                    raw += self.client.packet.send_varint(0)
                    raw += self.client.packet.send_varint(0)
                    raw += self.client.packet.send_bool(False)
                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM,
                        [VARINT, VARINT, UUID, STRING, VARINT, RAW],
                        (0, 1, playerclient.uuid, playerclient.username,
                         len(properties), raw))

                elif action == 1:
                    data = self.packet.readpkt([VARINT])

                    # noinspection PyUnusedLocal
                    # todo should we be using this to set client gamemode?
                    gamemode = data[0]
                    # ("varint:gamemode")
                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM,
                        [VARINT, VARINT, UUID, VARINT],
                        (1, 1, uuid, data[0]))
                    # print(1, 1, uuid, gamemode)
                elif action == 2:
                    data = self.packet.readpkt([VARINT])
                    ping = data[0]
                    # ("varint:ping")
                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM,
                        [VARINT, VARINT, UUID, VARINT],
                        (2, 1, uuid, ping))
                elif action == 3:
                    data = self.packet.readpkt([BOOL])
                    # ("bool:has_display")
                    hasdisplay = data[0]
                    if hasdisplay:
                        data = self.packet.readpkt([STRING])
                        displayname = data[0]
                        # ("string:displayname")
                        self.client.packet.sendpkt(
                            self.pktCB.PLAYER_LIST_ITEM,
                            [VARINT, VARINT, UUID, BOOL, STRING],
                            (3, 1, uuid, True, displayname))

                    else:
                        self.client.packet.sendpkt(
                            self.pktCB.PLAYER_LIST_ITEM,
                            [VARINT, VARINT, UUID, VARINT],
                            (3, 1, uuid, False))

                elif action == 4:
                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM,
                        [VARINT, VARINT, UUID],
                        (4, 1, uuid))

                return False
        else:  # version < 1.7.9 needs no processing
            return True
        return True

    def parse_play_spawn_player(self):  # embedded UUID -must parse.
        # This packet  is used to spawn other players into a player
        # client's world.  if this packet does not arrive, the other
        #  player(s) will not be visible to the client
        if self.server.version < PROTOCOL_1_8START:
            dt = self.packet.readpkt([VARINT, STRING, REST])
        else:
            dt = self.packet.readpkt([VARINT, UUID, REST])
        # 1.7.6 "varint:eid|string:uuid|rest:metadt")
        # 1.8 "varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|
        #     byte:pitch|short:item|rest:metadt")
        # 1.9 "varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|
        #     yte:pitch|rest:metadt")

        # We dont need to read the whole thing.
        clientserverid = self.proxy.getclientbyofflineserveruuid(dt[1])
        if clientserverid.uuid:
            if self.server.version < PROTOCOL_1_8START:
                self.client.packet.sendpkt(
                    self.pktCB.SPAWN_PLAYER,
                    [VARINT, STRING, RAW],
                    (dt[0], str(clientserverid.uuid), dt[2]))
            else:
                self.client.packet.sendpkt(
                    self.pktCB.SPAWN_PLAYER,
                    [VARINT, UUID, RAW],
                    (dt[0], clientserverid.uuid, dt[2]))
            return False
        return True

    # Wrapper events and info section:

    def parse_play_chat_message(self):
        data, position = self.packet.readpkt(self.pktCB.CHAT_MESSAGE[PARSER])
        # position (1.8+ only)
        # 0: chat (chat box), 1: system message (chat box), 2: above hotbar

        # Over-ride OP help display
        if "/op <player>" in data:
            new_usage = "player> [-s SUPER-OP] [-o OFFLINE] [-l <level>]"
            message = data.replace("player>", new_usage)
            data = message

        payload = self.proxy.eventhandler.callevent(
            "player.chatbox", {"playername": self.client.username,
                               "json": data})
        """ eventdoc
            <group> Proxy <group>

            <description> Chat message sent from the server to the client.
            <description>

            <abortable> Yes <abortable>

            <comments>
            - The message will not reach the client if the event is returned False.
            - If json chat (dict) or text is returned, that value will be sent 
            to the client instead.
            <comments>
            
            <payload>
            "playername": client username
            "json": json or string data
            <payload>

        """

        # reject the packet outright .. no chat gets sent to the client
        if payload is False:
            return False

        # if payload returns a dictionary, convert it to string and
        # substitute for data
        elif type(payload) == dict:
            data = json.dumps(payload)

        # if payload (plugin dev) returns a string-only object...
        elif type(payload) == str:
            data = payload

        self.client.packet.sendpkt(self.pktCB.CHAT_MESSAGE[PKT],
                                   self.pktCB.CHAT_MESSAGE[PARSER],
                                   (data, position))
        return False

    def parse_play_player_poslook(self):
        """This packet is not actually sent very often.  Maybe on respawns
        or position corrections."""
        # CAVEAT - The client and server bound packet formats are different!
        data = self.packet.readpkt(self.pktCB.PLAYER_POSLOOK[PARSER])
        relativemarker = data[5]
        # print("PPLOOK_DATA = ", data, type(data[0]), type(data[1]),
        #       type(data[2]), type(data[3]), type(data[4]), type(data[5]))
        # fill player position if this is absolute position (or a pre 1.8 server)
        if relativemarker == 0 or self.server.version < PROTOCOL_1_8START:
            self.client.position = (data[0], data[1], data[2])
        return True

    def parse_play_use_bed(self):
        data = self.packet.readpkt([VARINT, POSITION])
        if data[0] == self.client.server_eid:
            self.proxy.eventhandler.callevent(
                "player.usebed",
                {"playername": self.client.username, "position": data[1]})

            """ eventdoc
                <group> Proxy <group>

                <description> Sent when server send client to bedmode.
                <description>

                <abortable> No - Notification only. <abortable>

                <comments>
                <comments>

                <payload>
                "playername": client username
                "position": position of bed
                <payload>

            """
        return True

    def parse_play_join_game(self):
        data = self.packet.readpkt(self.pktCB.JOIN_GAME[PARSER])

        self.client.server_eid = data[0]
        self.client.gamemode = data[1]
        self.client.dimension = data[2]
        return True

    def parse_play_spawn_position(self):
        data = self.packet.readpkt([POSITION])
        self.client.position = data[0]
        self.proxy.eventhandler.callevent(
            "player.spawned", {"playername": self.client.username,
                               "position": data})

        """ eventdoc
            <group> Proxy <group>

            <description> Sent when server advises the client of its spawn position.
            <description>

            <abortable> No - Notification only. <abortable>

            <comments>
            <comments>

            <payload>
            "playername": client username
            "position": position
            <payload>

        """
        return True

    def parse_play_respawn(self):
        data = self.packet.readpkt([INT, UBYTE, UBYTE, STRING])
        # "int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
        self.client.gamemode = data[2]
        self.client.dimension = data[0]
        return True

    def parse_play_change_game_state(self):
        data = self.packet.readpkt([UBYTE, FLOAT])
        # ("ubyte:reason|float:value")
        if data[0] == 3:
            self.client.gamemode = data[1]
        return True

    def parse_play_disconnect(self):
        message = self.packet.readpkt([JSON])
        self.server.close_server("Server kicked %s with PLAY disconnect: %s" %
                                 (self.client.username, message))
        # client connection will determine if player needs to be kicked
        return False

    def parse_play_time_update(self):
        data = self.packet.readpkt([LONG, LONG])
        # "long:worldage|long:timeofday")
        # There could be a number of clients trying to update this at once
        # noinspection PyBroadException
        try:
            self.proxy.srv_data.timeofday = data[1]
        except:
            pass
        return True

    # Window processing/ inventory tracking

    def parse_play_open_window(self):
        # This works together with SET_SLOT to maintain
        #  accurate inventory in wrapper
        data = self.packet.readpkt(self.pktCB.OPEN_WINDOW[PARSER])
        self.client.currentwindowid = data[0]
        self.client.noninventoryslotcount = data[3]
        return True

    def parse_play_set_slot(self):
        # ("byte:wid|short:slot|slot:data")
        data = self.packet.readpkt(self.pktCB.SET_SLOT[PARSER])
        # todo - not sure how we  are dealing with slot counts
        # inventoryslots = 35
        # inventoryslots = 36  # 1.9 minecraft with shield / other hand

        # this is only sent on startup when server sends WID = 0 with 45/46
        # tems and when an item is moved into players inventory from
        # outside (like a chest or picking something up) After this, these
        # are sent on chest opens and so forth, each WID incrementing
        # by +1 per object opened.  The slot numbers that correspond to
        # player's hotbar will depend on what window is opened...  the
        # last 10 (for 1.9) or last 9 (for 1.8 and earlier) will be the
        # player hotbar ALWAYS. to know how many packets and slots total
        # to expect, we have to parse server-bound pktCB.OPEN_WINDOW.

        if data[0] == 0:
            self.client.inventory[data[1]] = data[2]

        if data[0] < 0:
            return True

        # This part updates our inventory from additional
        #  windows the player may open
        if data[0] == self.client.currentwindowid:
            currentslot = data[1]

            # noinspection PyUnusedLocal
            slotdata = data[2]  # TODO nothing is done with slot data

            if currentslot >= self.client.noninventoryslotcount:
                # any number of slot above the
                # pktCB.OPEN_WINDOW declared self.(..)slotcount
                # is an inventory slot for us to update.
                self.client.inventory[
                    currentslot - self.client.noninventoryslotcount + 9
                ] = data[2]
        return True

    # Entity processing sections.  Needed to track entities and EIDs

    def parse_play_spawn_object(self):
        # objects are entities and are GC-ed by detroy entities packet
        if not self.ent_control:
            return True  # return now if no object tracking
        if self.server.version < PROTOCOL_1_9START:
            dt = self.packet.readpkt(
                [VARINT, NULL, BYTE, INT, INT, INT, BYTE, BYTE])
            dt[3], dt[4], dt[5] = dt[3] / 32, dt[4] / 32, dt[5] / 32
            # "varint:eid|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw")
        else:
            dt = self.packet.readpkt(
                [VARINT, UUID, BYTE, DOUBLE, DOUBLE, DOUBLE, BYTE, BYTE])
            # "varint:eid|uuid:objectUUID|byte:type_|int:x|int:y|int:z|
            #     byte:pitch|byte:yaw|int:info|
            # short:velocityX|short:velocityY|short:velocityZ")
        entityuuid = dt[1]

        # we have to check these first, lest the object type be new
        # and cause an exception.
        if dt[2] in self.ent_control.objecttypes:
            objectname = self.ent_control.objecttypes[
                dt[2]]
            newobject = {dt[0]: Entity(dt[0], entityuuid, dt[2], objectname,
                                       (dt[3], dt[4], dt[5],), (dt[6], dt[7]),
                                       True, self.client.username)}

            self.ent_control.entities.update(newobject)
        return True

    def parse_play_spawn_mob(self):
        if not self.ent_control:
            return True
        if self.server.version < PROTOCOL_1_9START:
            dt = self.packet.readpkt(
                [VARINT, NULL, UBYTE, INT, INT, INT, BYTE, BYTE, BYTE, REST])
            dt[3], dt[4], dt[5] = dt[3] / 32, dt[4] / 32, dt[5] / 32
            # "varint:eid|ubyte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|"
            # "byte:head_pitch|...
            # STOP PARSING HERE: short:velocityX|short:velocityY|
            #     short:velocityZ|rest:metadata")
        else:
            dt = self.packet.readpkt([VARINT, UUID, UBYTE, DOUBLE, DOUBLE,
                                      DOUBLE, BYTE, BYTE, BYTE, REST])

            # ("varint:eid|uuid:entityUUID|ubyte:type_|int:x|int:y|int:z|"
            # "byte:pitch|byte:yaw|byte:head_pitch|
            # STOP PARSING HERE: short:velocityX|short:velocityY|
            #     short:velocityZ|rest:metadata")

        entityuuid = dt[1]

        # if the dt[2] mob type is not in our defined entity types,
        # it won't be tracked.. however, the undefined mob will not
        # cause an exception.
        if dt[2] in self.ent_control.entitytypes:
            mobname = self.ent_control.entitytypes[
                dt[2]]["name"]
            newmob = {dt[0]: Entity(dt[0], entityuuid, dt[2], mobname,
                                    (dt[3], dt[4], dt[5],),
                                    (dt[6], dt[7], dt[8]),
                                    False, self.client.username)}

            self.ent_control.entities.update(newmob)
        return True

    def parse_play_entity_relative_move(self):
        if not self.ent_control:
            return True
        if self.server.version < PROTOCOL_1_8START:  # 1.7.10 - 1.7.2
            data = self.packet.readpkt([INT, BYTE, BYTE, BYTE])

        # FutureVersion > elif self.version > mcpacket.PROTOCOL_1_7_9:  1.8 ++
        else:
            data = self.packet.readpkt([VARINT, BYTE, BYTE, BYTE])
        # ("varint:eid|byte:dx|byte:dy|byte:dz")

        entupd = self.ent_control.getEntityByEID(
            data[0])
        if entupd:
            entupd.move_relative((data[1], data[2], data[3]))
        return True

    def parse_play_entity_teleport(self):
        if not self.ent_control:
            return True
        if self.server.version < PROTOCOL_1_8START:  # 1.7.10 and prior
            data = self.packet.readpkt([INT, INT, INT, INT, REST])
        elif PROTOCOL_1_8START <= self.server.version < PROTOCOL_1_9START:
            data = self.packet.readpkt([VARINT, INT, INT, INT, REST])
        else:
            data = self.packet.readpkt([VARINT, DOUBLE, DOUBLE, DOUBLE, REST])
            data[1], data[2], data[3] = data[1] * 32, \
                data[2] * 32, data[3] * 32

        # ("varint:eid|int:x|int:y|int:z|byte:yaw|byte:pitch")

        entupd = self.ent_control.getEntityByEID(
            data[0])
        if entupd:
            entupd.teleport((data[1], data[2], data[3]))
        return True

    def parse_play_attach_entity(self):
        if not self.ent_control:
            return True
        data = []
        leash = True  # False to detach
        if self.server.version < PROTOCOL_1_8START:
            data = self.packet.readpkt([INT, INT, BOOL])
            leash = data[2]
        if self.server.version >= PROTOCOL_1_9START:
            data = self.packet.readpkt([INT, INT])
            if data[1] == -1:
                leash = False
        entityeid = data[0]  # rider, leash holder, etc
        vehormobeid = data[1]  # vehicle, leashed entity, etc

        if entityeid == self.client.server_eid:
            if not leash:
                self.proxy.eventhandler.callevent(
                    "entity.unmount", {"playername": self.client.username,
                                       "vehicle_id": vehormobeid,
                                       "leash": leash})
                """ eventdoc
                    <group> Proxy <group>

                    <description> Sent when player attaches to entity.
                    <description>

                    <abortable> No - Notification only. <abortable>

                    <comments>
                    <comments>

                    <payload>
                    "playername": client username
                    "vehicle_id": EID of vehicle or MOB
                    "leash": leash True/False
                    <payload>

                """
                self.log.debug("player unmount called for %s", self.client.username)
                self.client.riding = None
            else:
                self.proxy.eventhandler.callevent(
                    "entity.mount", {"playername": self.client.username,
                                     "vehicle_id": vehormobeid,
                                     "leash": leash})
                """ eventdoc
                    <group> Proxy <group>

                    <description> Sent when player detaches/unmounts entity.
                    <description>

                    <abortable> No - Notification only. <abortable>

                    <comments>
                    <comments>

                    <payload>
                    "playername": client username
                    "vehicle_id": EID of vehicle or MOB
                    "leash": leash True/False
                    <payload>

                """
                self.client.riding = vehormobeid
                self.log.debug("player mount called for %s on eid %s",
                               self.client.username, vehormobeid)
                if not self.ent_control:
                    return
                entupd = self.ent_control.getEntityByEID(
                    vehormobeid)
                if entupd:
                    self.client.riding = entupd
                    entupd.rodeBy = self.client
        return True

    def parse_play_destroy_entities(self):
        # Get rid of dead entities so that python can GC them.
        # TODO - not certain this works correctly (errors -
        # eids not used and too broad exception)
        if not self.ent_control:
            return True

        # noinspection PyUnusedLocal
        eids = []  # todo what was this for??
        if self.server.version < PROTOCOL_1_8START:
            # make sure we get iterable integer
            entitycount = bytearray(self.packet.readpkt([BYTE])[0])[0]
            parser = [INT]
        else:
            # TODO - error when more than 256 entities?
            rawread = self.packet.readpkt([VARINT])
            entitycount = rawread[0]
            parser = [VARINT]

        for _ in range(entitycount):
            eid = self.packet.readpkt(parser)[0]
            # noinspection PyBroadException
            if eid in self.ent_control.entities:
                self.ent_control.entities.pop(eid, None)

        return True
