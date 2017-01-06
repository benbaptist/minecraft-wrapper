# -*- coding: utf-8 -*-

# Copyright (C) 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

import json

from core.entities import Entity
from proxy import mcpackets
# noinspection PyPep8Naming
from utils import pkt_datatypes as D


# noinspection PyMethodMayBeStatic
class ParseCB:
    """
    ParseSB parses client bound packets that are coming from the server.
    """
    def __init__(self, server, packet):
        self.server = server
        self.client = server.client
        self.wrapper = server.client.wrapper
        self.proxy = server.client.proxy
        self.log = server.client.wrapper.log
        self.packet = packet

    def parse_play_combat_event(self):
        print("\nSTART COMB_PARSE\n")
        data = self.packet.readpkt([D.VARINT, ])
        print("\nread COMB_PARSE\n")
        if data[0] == 2:
            print("\nread COMB_PARSE2\n")
            player_i_d = self.packet.readpkt([D.VARINT, ])
            print("\nread COMB_PARSE3\n")
            e_i_d = self.packet.readpkt([D.INT, ])
            print("\nread COMB_PARSE4\n")
            strg = self.packet.readpkt([D.STRING, ])

            print("\nplayerEID=%s\nEID=%s\n" % (player_i_d, e_i_d))
            print("\nTEXT=\n%s\n" % strg)

            return True
        return True

    def parse_play_chat_message(self):
        if self.server.version < mcpackets.PROTOCOL_1_8START:
            parsing = [D.STRING, D.NULL]
        else:
            parsing = [D.JSON, D.BYTE]

        data, position = self.packet.readpkt(parsing)

        # position (1.8+ only)
        # 0: chat (chat box), 1: system message (chat box), 2: above hotbar

        payload = self.wrapper.events.callevent("player.chatbox", {"player": self.client.getplayerobject(),
                                                                   "json": data})
        '''
        :decription: Chat message sent from server to the client.

        :Event: Can be hidden by returning False.  New `data` can be returned to change what is sent to client.
        '''

        if payload is False:  # reject the packet .. no chat gets sent to the client
            return False

        elif type(payload) == dict:  # if payload returns a dictionary, convert it to string and resend
            chatmsg = json.dumps(payload)
            self.client.packet.sendpkt(self.client.pktCB.CHAT_MESSAGE, parsing, (chatmsg, position))
            return False  # reject the orginal packet (it will not reach the client)
        elif type(payload) == str:  # if payload (plugin dev) returns a string-only object...
            self.client.packet.sendpkt(self.client.pktCB.CHAT_MESSAGE, parsing, (payload, position))
            return False
        else:  # no payload, nor was the packet rejected.. packet passes to the client (and his chat)
            return True

    def parse_play_join_game(self):
        if self.server.version < mcpackets.PROTOCOL_1_9_1PRE:
            data = self.packet.readpkt([D.INT, D.UBYTE, D.BYTE, D.UBYTE, D.UBYTE, D.STRING])
            #    "int:eid|ubyte:gm|byte:dim|ubyte:diff|ubyte:max_players|string:level_type")
        else:
            data = self.packet.readpkt([D.INT, D.UBYTE, D.INT, D.UBYTE, D.UBYTE, D.STRING])
            #    "int:eid|ubyte:gm|int:dim|ubyte:diff|ubyte:max_players|string:level_type")

        self.server.eid = data[0]  # This is the EID of the player on the point-of-use server
        # not always the EID that the client is aware of.

        self.client.gamemode = data[1]
        self.client.dimension = data[2]
        # self.client.eid = data[0]

        return True

    def parse_play_time_update(self):
        data = self.packet.readpkt([D.LONG, D.LONG])
        # "long:worldage|long:timeofday")
        self.wrapper.javaserver.timeofday = data[1]
        return True

    def parse_play_spawn_position(self):
        data = self.packet.readpkt([D.POSITION])
        #  javaserver.spawnPoint doesn't exist.. this is player spawnpoint anyway... ?
        # self.wrapper.javaserver.spawnPoint = data[0]
        self.client.position = data[0]
        self.wrapper.events.callevent("player.spawned", {"player": self.client.getplayerobject()})
        return True

    def parse_play_respawn(self):
        data = self.packet.readpkt([D.INT, D.UBYTE, D.UBYTE, D.STRING])
        # "int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
        self.client.gamemode = data[2]
        self.client.dimension = data[0]
        return True

    def parse_play_player_poslook(self):
        # CAVEAT - The client and server bound packet formats are different!
        if self.server.version < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.DOUBLE, D.FLOAT, D.FLOAT, D.BOOL])
        elif mcpackets.PROTOCOL_1_7_9 < self.server.version < mcpackets.PROTOCOL_1_9START:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.DOUBLE, D.FLOAT, D.FLOAT, D.BYTE])
        elif self.server.version > mcpackets.PROTOCOL_1_8END:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.DOUBLE, D.FLOAT, D.FLOAT, D.BYTE, D.VARINT])
        else:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.DOUBLE, D.REST])
        self.client.position = (data[0], data[1], data[2])  # not a bad idea to fill player position
        return True

    def parse_play_use_bed(self):
        data = self.packet.readpkt([D.VARINT, D.POSITION])
        if data[0] == self.server.eid:
            self.wrapper.events.callevent("player.usebed",
                                          {"player": self.wrapper.javaserver.players[self.client.username],
                                           "position": data[1]})
        return True

    def parse_play_spawn_player(self):  # embedded UUID -must parse.
        # This packet  is used to spawn other players into a player client's world.
        # is this packet does not arrive, the other player(s) will not be visible to the client
        if self.server.version < mcpackets.PROTOCOL_1_8START:
            dt = self.packet.readpkt([D.VARINT, D.STRING, D.REST])
        else:
            dt = self.packet.readpkt([D.VARINT, D.UUID, D.REST])
        # 1.7.6 "varint:eid|string:uuid|rest:metadt")
        # 1.8 "varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|short:item|rest:metadt")
        # 1.9 "varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|rest:metadt")

        # We dont need to read the whole thing.
        clientserverid = self.proxy.getclientbyofflineserveruuid(dt[1])
        if clientserverid.uuid:
            if self.server.version < mcpackets.PROTOCOL_1_8START:
                self.client.packet.sendpkt(
                    self.client.pktCB.SPAWN_PLAYER, [D.VARINT, D.STRING, D.RAW], (dt[0],
                                                                                  str(clientserverid.uuid), dt[2]))
            else:
                self.client.packet.sendpkt(
                    self.client.pktCB.SPAWN_PLAYER, [D.VARINT, D.UUID, D.RAW], (dt[0], clientserverid.uuid, dt[2]))
            return False
        return True

    def parse_play_spawn_object(self):
        if not self.wrapper.javaserver.entity_control:
            return True  # return now if no object tracking
        if self.server.version < mcpackets.PROTOCOL_1_9START:
            dt = self.packet.readpkt([D.VARINT, D.NULL, D.BYTE, D.INT, D.INT, D.INT, D.BYTE, D.BYTE])
            dt[3], dt[4], dt[5] = dt[3] / 32, dt[4] / 32, dt[5] / 32
            # "varint:eid|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw")
        else:
            dt = self.packet.readpkt([D.VARINT, D.UUID, D.BYTE, D.DOUBLE, D.DOUBLE, D.DOUBLE, D.BYTE, D.BYTE])
            # "varint:eid|uuid:objectUUID|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|int:info|
            # short:velocityX|short:velocityY|short:velocityZ")
        entityuuid = dt[1]

        # we have to check these first, lest the object type be new and cause an exception.
        if dt[2] in self.wrapper.javaserver.entity_control.objecttypes:
            objectname = self.wrapper.javaserver.entity_control.objecttypes[dt[2]]
            newobject = {dt[0]: Entity(dt[0], entityuuid, dt[2], objectname,
                                       (dt[3], dt[4], dt[5],), (dt[6], dt[7]), True, self.client.username)}

            self.wrapper.javaserver.entity_control.entities.update(newobject)
        return True
