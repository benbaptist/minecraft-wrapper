# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from core.exceptions import UnsupportedMinecraftProtocol

from proxy.constants import *

"""
Ways to reference packets by names and not hard-coded numbers.

This attempts to follow the wiki as much as possible.

the ServerBound and ClientBound classes take an integer protocol argument
to determine the packet values.

Protocol constants are named as follows:
    first two digits are major version, third digit in minor version.
    example: PROTOCOL_1_8_9 means - version 1.8.9.
    Explanatory text (pre, start, etc) may be last.

set something False/unimplemented using 0xEE

"""


class Packets(object):
    def __init__(self, protocol):

        if PROTOCOL_1_8END < protocol < PROTOCOL_1_9REL1:
            raise UnsupportedMinecraftProtocol

        # Login, Status, and Ping packets
        # -------------------------------
        # set server to STATUS(1) or LOGIN(2) mode.
        self.HANDSHAKE = 0x00
        # Server sends server json list data in response packet
        self.REQUEST = 0x00
        # server responds with a PONG
        self.STATUS_PING = 0x01
        # contains the "name" of user.  Sent after handshake for LOGIN
        self.LOGIN_START = 0x00
        # client response to ENCR_REQUEST
        self.LOGIN_ENCR_RESPONSE = 0x01

        # Play packets
        # -------------------------------
        # 1.7 - 1.7.10 PLAY packets
        self.KEEP_ALIVE = [0x00, [INT]]
        self.CHAT_MESSAGE = 0x01
        self.USE_ENTITY = 0x02
        self.PLAYER = 0x03
        self.PLAYER_POSITION = 0x04
        self.PLAYER_LOOK = 0x05
        self.PLAYER_POSLOOK = 0x06
        self.PLAYER_DIGGING = 0x07
        self.PLAYER_BLOCK_PLACEMENT = 0x08
        self.HELD_ITEM_CHANGE = 0x09
        self.ANIMATION = 0x0a  # TODO NEW
        self.ENTITY_ACTION = 0x0b  # TODO NEW
        self.STEER_VEHICLE = 0x0c  # TODO NEW
        self.CLOSE_WINDOW = 0x0b  # TODO NEW
        self.CLICK_WINDOW = 0x0e
        self.CONFIRM_TRANSACTION = 0x0f  # TODO NEW
        self.CREATIVE_INVENTORY_ACTION = 0x10  # TODO NEW
        self.ENCHANT_ITEM = 0x11  # TODO NEW
        self.PLAYER_UPDATE_SIGN = 0x12
        self.PLAYER_ABILITIES = 0x13
        self.TAB_COMPLETE = 0x14  # TODO NEW
        self.CLIENT_SETTINGS = 0x15
        self.CLIENT_STATUS = 0x16
        self.PLUGIN_MESSAGE = 0x17

        # new packets unimplemented in 1.7
        self.SPECTATE = 0xee
        self.RESOURCE_PACK_STATUS = 0xee
        self.TELEPORT_CONFIRM = 0xee
        self.USE_ITEM = 0xee
        self.VEHICLE_MOVE = 0xee
        self.STEER_BOAT = 0xee

        # Parsing changes
        if protocol >= PROTOCOL_1_8START:
            self.KEEP_ALIVE[PARSER] = [VARINT]

        if PROTOCOL_1_9START > protocol >= PROTOCOL_1_8START:
            self.SPECTATE = 0x18
            self.RESOURCE_PACK_STATUS = 0x19

        # 1.9
        if protocol >= PROTOCOL_1_9REL1:
            self.TELEPORT_CONFIRM = 0x00
            self.TAB_COMPLETE = 0x01  # TODO NEW
            self.CHAT_MESSAGE = 0x02
            self.CLIENT_STATUS = 0x03
            self.CLIENT_SETTINGS = 0x04
            self.CONFIRM_TRANSACTION = 0x05  # TODO NEW
            self.ENCHANT_ITEM = 0x06  # TODO NEW
            self.CLICK_WINDOW = 0x07
            self.CLOSE_WINDOW = 0x08  # TODO NEW
            self.PLUGIN_MESSAGE = 0x09
            self.USE_ENTITY = 0x0a
            self.KEEP_ALIVE[PKT] = 0x0b
            self.PLAYER_POSITION = 0x0c
            self.PLAYER_POSLOOK = 0x0d
            self.PLAYER_LOOK = 0x0e
            self.PLAYER = 0x0f
            self.VEHICLE_MOVE = 0x10  # TODO NEW
            self.STEER_BOAT = 0x11  # TODO NEW
            self.PLAYER_ABILITIES = 0x12
            self.PLAYER_DIGGING = 0x13
            self.ENTITY_ACTION = 0x14  # TODO NEW
            self.STEER_VEHICLE = 0x15  # TODO NEW
            self.RESOURCE_PACK_STATUS = 0x16  # TODO NEW
            self.HELD_ITEM_CHANGE = 0x17
            self.CREATIVE_INVENTORY_ACTION = 0x18  # TODO NEW
            self.PLAYER_UPDATE_SIGN = 0x19
            self.ANIMATION = 0x1a  # TODO NEW
            self.SPECTATE = 0x1b
            self.PLAYER_BLOCK_PLACEMENT = 0x1c
            self.USE_ITEM = 0x1d
