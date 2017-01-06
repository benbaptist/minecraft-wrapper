# -*- coding: utf-8 -*-

# Copyright (C) 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

import json

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
