# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import json

from core.entities import Entity
from proxy.constants import *

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
        self.client = server.client
        self.pktCB = self.server.pktCB
        self.pktSB = self.server.pktSB
        self.wrapper = server.client.wrapper
        self.proxy = server.client.proxy
        self.log = server.client.wrapper.log
        self.packet = packet

    def parse_play_combat_event(self):
        """ just parsed for testing for now """
        pass
        # 1.9 packet, conditionally parsed
        # print("\nSTART COMB_PARSE\n")
        # data = self.packet.readpkt([VARINT, ])
        # print("\nread COMB_PARSE\n")
        # if data[0] == 2:
        #    # print("\nread COMB_PARSE2\n")
        #    #player_i_d = self.packet.readpkt([VARINT, ])
        #    # print("\nread COMB_PARSE3\n")
        #    #e_i_d = self.packet.readpkt([INT, ])
        #    # print("\nread COMB_PARSE4\n")
        #    #strg = self.packet.readpkt([STRING, ])

        #    # print("\nplayerEID=%s\nEID=%s\n" % (player_i_d, e_i_d))
        #    # print("\nTEXT=\n%s\n" % strg)

        #    # return True
        return True

    def parse_play_chat_message(self):
        data, position = self.packet.readpkt(self.pktCB.CHAT_MESSAGE[PARSER])
        # position (1.8+ only)
        # 0: chat (chat box), 1: system message (chat box), 2: above hotbar

        # Over-ride OP help display
        if "/op <player>" in data:
            new_usage = "player> [-s SUPER-OP] [-o OFFLINE] [-l <level>]"
            message = data.replace("player>", new_usage)
            data = message

        payload = self.wrapper.events.callevent(
            "player.chatbox", {"player": self.client.getplayerobject(),
                               "json": data})
        '''
        :decription: Chat message sent from server to the client.

        :Event: Can be hidden by returning False.  New `data` can be returned
        to change what is sent to client.
        '''

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

    def parse_play_join_game(self):
        data = self.packet.readpkt(self.pktCB.JOIN_GAME[PARSER])

        self.client.server_eid = data[0]
        self.client.gamemode = data[1]
        self.client.dimension = data[2]
        return True

    def parse_play_time_update(self):
        data = self.packet.readpkt([LONG, LONG])
        # "long:worldage|long:timeofday")
        self.wrapper.javaserver.timeofday = data[1]
        return True

    def parse_play_spawn_position(self):
        data = self.packet.readpkt([POSITION])
        #  javaserver.spawnPoint doesn't exist.. this
        # is player spawnpoint anyway... ?
        # self.wrapper.javaserver.spawnPoint = data[0]
        self.client.position = data[0]
        self.wrapper.events.callevent("player.spawned",
                                      {"player": self.client.getplayerobject(),
                                       "position": data})
        '''
        :decription: When server advises the client of its' (player's)
         spawn position.

        :Event: Notification only.
        '''
        return True

    def parse_play_respawn(self):
        data = self.packet.readpkt([INT, UBYTE, UBYTE, STRING])
        # "int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
        self.client.gamemode = data[2]
        self.client.dimension = data[0]
        return True

    def parse_play_player_poslook(self):
        # CAVEAT - The client and server bound packet formats are different!
        if self.server.version < PROTOCOL_1_8START:
            data = self.packet.readpkt(
                [DOUBLE, DOUBLE, DOUBLE, FLOAT, FLOAT, BOOL])
        elif PROTOCOL_1_7_9 < self.server.version < PROTOCOL_1_9START:
            data = self.packet.readpkt(
                [DOUBLE, DOUBLE, DOUBLE, FLOAT, FLOAT, BYTE])
        elif self.server.version > PROTOCOL_1_8END:
            data = self.packet.readpkt(
                [DOUBLE, DOUBLE, DOUBLE, FLOAT, FLOAT, BYTE, VARINT])
        else:
            data = self.packet.readpkt([DOUBLE, DOUBLE, DOUBLE, REST])

        # not a bad idea to fill player position
        self.client.position = (data[0], data[1], data[2])
        return True

    def parse_play_use_bed(self):
        data = self.packet.readpkt([VARINT, POSITION])
        if data[0] == self.client.server_eid:
            self.wrapper.events.callevent(
                "player.usebed",
                {"player": self.wrapper.javaserver.players[
                    self.client.username], "position": data[1]})
            '''
            :decription: When server sends client to bed mode.

            :Event: Notification only.
            '''
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

    def parse_play_spawn_object(self):
        # objects are entities and are GC-ed by detroy entities packet
        if not self.wrapper.javaserver.entity_control:
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
        if dt[2] in self.wrapper.javaserver.entity_control.objecttypes:
            objectname = self.wrapper.javaserver.entity_control.objecttypes[
                dt[2]]
            newobject = {dt[0]: Entity(dt[0], entityuuid, dt[2], objectname,
                                       (dt[3], dt[4], dt[5],), (dt[6], dt[7]),
                                       True, self.client.username)}

            # in many places here, we could have used another self definition
            # like self.entities = self.wrapper.javaserver..., but we chose
            # not to to make sure (given the lagacy complexity of the code)
            # that we remember where all these classes and methods are
            # in the code and to keep a mental picture of the code layout.
            self.wrapper.javaserver.entity_control.entities.update(newobject)
        return True

    def parse_play_spawn_mob(self):
        if not self.wrapper.javaserver.entity_control:
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
        if dt[2] in self.wrapper.javaserver.entity_control.entitytypes:
            mobname = self.wrapper.javaserver.entity_control.entitytypes[
                dt[2]]["name"]
            newmob = {dt[0]: Entity(dt[0], entityuuid, dt[2], mobname,
                                    (dt[3], dt[4], dt[5],),
                                    (dt[6], dt[7], dt[8]),
                                    False, self.client.username)}

            self.wrapper.javaserver.entity_control.entities.update(newmob)
        return True

    def parse_play_entity_relative_move(self):
        if not self.wrapper.javaserver.entity_control:
            return True
        if self.server.version < PROTOCOL_1_8START:  # 1.7.10 - 1.7.2
            data = self.packet.readpkt([INT, BYTE, BYTE, BYTE])

        # FutureVersion > elif self.version > mcpacket.PROTOCOL_1_7_9:  1.8 ++
        else:
            data = self.packet.readpkt([VARINT, BYTE, BYTE, BYTE])
        # ("varint:eid|byte:dx|byte:dy|byte:dz")

        entupd = self.wrapper.javaserver.entity_control.getEntityByEID(
            data[0])
        if entupd:
            entupd.move_relative((data[1], data[2], data[3]))
        return True

    def parse_play_entity_teleport(self):
        if not self.wrapper.javaserver.entity_control:
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

        entupd = self.wrapper.javaserver.entity_control.getEntityByEID(
            data[0])
        if entupd:
            entupd.teleport((data[1], data[2], data[3]))
        return True

    def parse_play_attach_entity(self):
        data = []
        leash = True  # False to detach
        if self.server.version < PROTOCOL_1_8START:
            data = self.packet.readpkt([INT, INT, BOOL])
            leash = data[2]
        if PROTOCOL_1_8START <= self.server.version < PROTOCOL_1_9START:
            data = self.packet.readpkt([VARINT, VARINT, BOOL])
            leash = data[2]
        if self.server.version >= PROTOCOL_1_9START:
            data = self.packet.readpkt([VARINT, VARINT])
            if data[1] == -1:
                leash = False
        entityeid = data[0]  # rider, leash holder, etc
        vehormobeid = data[1]  # vehicle, leashed entity, etc
        player = self.proxy.getplayerby_eid(entityeid)

        if player is None:
            return True

        if entityeid == self.client.server_eid:
            if not leash:
                self.wrapper.events.callevent("player.unmount",
                                              {"player": player,
                                               "vehicle_id": vehormobeid,
                                               "leash": leash})
                '''
                :decription: When player attaches to entity.

                :Event: Notification only.
                '''
                self.log.debug("player unmount called for %s", player.username)
                self.client.riding = None
            else:
                self.wrapper.events.callevent("player.mount",
                                              {"player": player,
                                               "vehicle_id": vehormobeid,
                                               "leash": leash})
                '''
                :decription: When player detaches/unmounts entity.

                :Event: Notification only.
                '''
                self.client.riding = vehormobeid
                self.log.debug("player mount called for %s on eid %s",
                               player.username, vehormobeid)
                if not self.wrapper.javaserver.entity_control:
                    return
                entupd = self.wrapper.javaserver.entity_control.getEntityByEID(
                    vehormobeid)
                if entupd:
                    self.client.riding = entupd
                    entupd.rodeBy = self.client
        return True

    def parse_play_destroy_entities(self):
        # Get rid of dead entities so that python can GC them.
        # TODO - not certain this works correctly (errors -
        # eids not used and too broad exception)
        if not self.wrapper.javaserver.entity_control:
            return True

        # noinspection PyUnusedLocal
        eids = []  # todo what was this for??
        if self.server.version < PROTOCOL_1_8START:
            # make sure we get iterable integer
            entitycount = bytearray(self.packet.readpkt([BYTE])[0])[0]
            parser = [INT]
        else:
            entitycount = bytearray(self.packet.readpkt([VARINT]))[0]
            parser = [VARINT]

        for _ in range(entitycount):
            eid = self.packet.readpkt(parser)[0]
            # noinspection PyBroadException
            if eid in self.wrapper.javaserver.entity_control.entities:
                self.wrapper.javaserver.entity_control.entities.pop(eid, None)

        return True

    def parse_play_map_chunk_bulk(self):  # (packet no longer exists in 1.9)
        # if PROTOCOL_1_9START > self.version > PROTOCOL_1_8START:
        #     data = self.packet.readpkt([BOOL, VARINT])
        #     chunks = data[1]
        #     skylightbool = data[0]
        #     # ("bool:skylight|varint:chunks")
        #     for chunk in xxrange(chunks):
        #         meta = self.packet.readpkt([INT, INT, _USHORT])
        #         # ("int:x|int:z|ushort:primary")
        #         primary = meta[2]
        #         bitmask = bin(primary)[2:].zfill(16)
        #         chunkcolumn = bytearray()
        #         for bit in bitmask:
        #             if bit == "1":
        #                 # packetanisc
        #                 chunkcolumn += bytearray(self.packet.read_data(
        # 16 * 16 * 16 * 2))
        #                 if self.client.dimension == 0:
        #                     metalight = bytearray(self.packet.read_data(
        # 16 * 16 * 16))
        #                 if skylightbool:
        #                     skylight = bytearray(self.packet.read_data(
        # 16 * 16 * 16))
        #             else:
        #                 # Null Chunk
        #                 chunkcolumn += bytearray(16 * 16 * 16 * 2)
        return True

    def parse_play_change_game_state(self):
        data = self.packet.readpkt([UBYTE, FLOAT])
        # ("ubyte:reason|float:value")
        if data[0] == 3:
            self.client.gamemode = data[1]
        return True

    def parse_play_open_window(self):
        # This works together with SET_SLOT to maintain
        #  accurate inventory in wrapper
        if self.server.version < PROTOCOL_1_8START:
            parsing = [UBYTE, UBYTE, STRING, UBYTE]
        else:
            parsing = [UBYTE, STRING, JSON, UBYTE]
        data = self.packet.readpkt(parsing)
        self.client.currentwindowid = data[0]
        self.client.noninventoryslotcount = data[3]
        return True

    def parse_play_set_slot(self):
        # ("byte:wid|short:slot|slot:data")
        data = [-12, -12, None]

        # todo - not sure how we  are dealing with slot counts
        # inventoryslots = 35
        if self.server.version < PROTOCOL_1_8START:
            data = self.packet.readpkt([BYTE, SHORT, SLOT_NO_NBT])
            # inventoryslots = 35
        elif self.server.version < PROTOCOL_1_9START:
            data = self.packet.readpkt([BYTE, SHORT, SLOT])
            # inventoryslots = 35
        elif self.server.version > PROTOCOL_1_8END:
            data = self.packet.readpkt([BYTE, SHORT, SLOT])
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

    def parse_play_window_items(self):
        # I am interested to see when this is used and in what versions.
        #   It appears to be superfluous, as SET_SLOT seems to do the
        #   purported job nicely.
        data = self.packet.readpkt([UBYTE, SHORT])
        windowid = data[0]
        elementcount = data[1]
        # data = self.packet.read("byte:wid|short:count")
        # if data["wid"] == 0:
        #     for slot in range(1, data["count"]):
        #         data = self.packet.readpkt("slot:data")
        #         self.client.inventory[slot] = data["data"]
        elements = []

        # just parsing for now; not acting on, so OK to skip 1.7.9
        if self.server.version > PROTOCOL_1_7_9:
            for _ in xrange(elementcount):
                elements.append(self.packet.read_slot())

        # noinspection PyUnusedLocal
        jsondata = {  # todo nothin done with data
            "windowid": windowid,
            "elementcount": elementcount,
            "elements": elements
        }
        return True

    def parse_play_entity_properties(self):
        """ Not sure why I added this.  Based on the wiki, it looked like
        this might contain a player uuid buried in the lowdata (wiki -
        "Modifier Data") area that might need to be parsed and reset to
         the server local uuid.  Thus far, I have not seen it used.

        IF there is a uuid, it may need parsed.

        parser_three = [UUID, DOUBLE, BYTE]
        if self.version < PROTOCOL_1_8START:
            parser_one = [INT, INT]
            parser_two = [STRING, DOUBLE, SHORT]
            writer_one = self.packet.send_int
            writer_two = self.packet.send_short
        else:
            parser_one = [VARINT, INT]
            parser_two = [STRING, DOUBLE, VARINT]
            writer_one = self.packet.send_varint
            writer_two = self.packet.send_varint
        raw = b""  # use bytes

        # read first level and repack
        pass1 = self.packet.readpkt(parser_one)
        isplayer = self.proxy.getplayerby_eid(pass1[0])
        if not isplayer:
            return True
        raw += writer_one(pass1[0])
        print(pass1[0], pass1[1])
        raw += self.packet.send_int(pass1[1])

        # start level 2
        for _x in range(pass1[1]):
            pass2 = self.packet.readpkt(parser_two)
            print(pass2[0], pass2[1], pass2[2])
            raw += self.packet.send_string(pass2[0])
            raw += self.packet.send_double(pass2[1])
            raw += writer_two(pass2[2])
            print(pass2[2])
            for _y in range(pass2[2]):
                lowdata = self.packet.readpkt(parser_three)
                print(lowdata)
                packetuuid = lowdata[0]
                playerclient = self.wrapper.proxy.getclientbyofflineserveruuid(
                    packetuuid)
                if playerclient:
                    raw += self.packet.send_uuid(playerclient.uuid.hex)
                else:
                    raw += self.packet.send_uuid(lowdata[0])
                raw += self.packet.send_double(lowdata[1])
                raw += self.packet.send_byte(lowdata[2])
                print("Low data: ", lowdata)
        # self.packet.sendpkt(self.pktCB.ENTITY_PROPERTIES, [RAW], (raw,))
        return True
        """
        return True

    def parse_play_player_list_item(self):
        if self.server.version >= PROTOCOL_1_8START:
            head = self.packet.readpkt([VARINT, VARINT])
            # ("varint:action|varint:length")
            lenhead = head[1]
            action = head[0]
            z = 0
            while z < lenhead:
                serveruuid = self.packet.readpkt([UUID])[0]
                playerclient = self.wrapper.proxy.getclientbyofflineserveruuid(
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

    def parse_play_disconnect(self):
        # def __str__():
        #    return "PLAY_DISCONNECT"
        message = self.packet.readpkt([JSON])
        self.log.info("%s disconnected from Server", self.client.username)
        self.server.close_server(message)

    def parse_entity_metadata(self):
        """
        This packet is parsed, then re-constituted, the original rejected,
        and a new packet formed to the client. if the entity is a baby,
        we rename it.. All of this, just for fun! (and as a demo)  Otherwise,
        this is a pretty useless parse, unless we opt to pump this data
        into the entity API.
        """
        eid, metadata = self.packet.readpkt(self.pktCB.ENTITY_METADATA[PARSER])
        if self.client.version >= PROTOCOL_1_8START:
            # 12 means 'ageable'
            if 12 in metadata:
                # boolean isbaby
                if 6 in metadata[12]:
                    # it's a baby!
                    if metadata[12][1] is True:

                        # print the data for reference
                        # see http://wiki.vg/Entities#Entity_Metadata_Format
                        # self.log.debug("EID: %s - %s", eid, metadata)
                        # name the baby and make tag visible (no index/type
                        # checking; accessing base entity class)
                        metadata[2] = (3, "Entity_%s" % eid)
                        metadata[3] = (6, True)

        self.client.packet.sendpkt(
            self.pktCB.ENTITY_METADATA[PKT],
            self.pktCB.ENTITY_METADATA[PARSER],
            (eid, metadata))
        return False
