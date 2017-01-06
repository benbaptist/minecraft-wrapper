# -*- coding: utf-8 -*-

# Copyright (C) 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

from proxy import mcpackets
# noinspection PyPep8Naming
from utils import pkt_datatypes as D


# noinspection PyMethodMayBeStatic
class ParseCB:
    """
    ParseSB parses server bound packets that are coming from the client.
    """
    def __init__(self, server, packet):
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

