# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - SurestTexas00 and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from __future__ import print_function
from proxy.utils.constants import *

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
        # not supporting 1.9 and 1.12 snapshots due to high instability/changes
        if protocol in UNSUPPORTED:
            print("Protocol version not supported:", protocol)
            raise ValueError

        # Login, Status, and Ping packets
        # -------------------------------
        self.LEGACY_HANDSHAKE = [0xfe, [NULL, ]]
        # set server to STATUS(1) or LOGIN(2) mode.
        self.HANDSHAKE = [0x00, [NULL, ]]
        # Server sends server json list data in response packet
        self.REQUEST = [0x00, [NULL, ]]
        # server responds with a PONG
        self.STATUS_PING = [0x01, [NULL, ]]
        # contains the "name" of user.  Sent after handshake for LOGIN
        self.LOGIN_START = [0x00, [NULL, ]]
        # client response to ENCR_REQUEST
        self.LOGIN_ENCR_RESPONSE = [0x01, [NULL, ]]
        # Play packets
        # -------------------------------
        # 1.7 - 1.7.10 PLAY packets
        self.KEEP_ALIVE = [0x00, [INT]]
        self.CHAT_MESSAGE = [0x01, [STRING]]  # until 1.11, max string length is 100 or client gets kicked  # noqa
        self.USE_ENTITY = [0x02, [NULL, ]]
        self.PLAYER = [0x03, [NULL, ]]
        self.PLAYER_POSITION = [0x04, [NULL, ]]
        self.PLAYER_LOOK = [0x05, [NULL, ]]
        self.PLAYER_POSLOOK = [0x06, [DOUBLE, DOUBLE, DOUBLE, DOUBLE, FLOAT, FLOAT, BOOL]]  # noqa
        self.PLAYER_DIGGING = [0x07, [NULL, ]]
        self.PLAYER_BLOCK_PLACEMENT = [0x08, [NULL, ]]
        self.HELD_ITEM_CHANGE = [0x09, [NULL, ]]
        self.ANIMATION = [0x0a, [NULL, ]]
        self.ENTITY_ACTION = [0x0b, [NULL, ]]
        self.STEER_VEHICLE = [0x0c, [NULL, ]]
        self.CLOSE_WINDOW = [0x0b, [NULL, ]]
        self.CLICK_WINDOW = [0x0e, [BYTE, SHORT, BYTE, SHORT, BYTE, SLOT]]
        self.CONFIRM_TRANSACTION = [0x0f, [NULL, ]]
        self.CREATIVE_INVENTORY_ACTION = [0x10, [NULL, ]]
        self.ENCHANT_ITEM = [0x11, [NULL, ]]
        self.PLAYER_UPDATE_SIGN = [0x12, [NULL, ]]
        self.PLAYER_ABILITIES = [0x13, [NULL, ]]
        self.TAB_COMPLETE = [0x14, [NULL, ]]
        self.CLIENT_SETTINGS = [0x15, [NULL, ]]
        self.CLIENT_STATUS = [0x16, [BYTE, ]]
        self.PLUGIN_MESSAGE = [0x17, [NULL, ]]
        # new packets implemented after 1.7
        self.SPECTATE = [0xee, [NULL, ]]
        self.RESOURCE_PACK_STATUS = [0xee, [NULL, ]]
        self.TELEPORT_CONFIRM = [0xee, [NULL, ]]
        self.USE_ITEM = [0xee, [NULL, ]]
        self.VEHICLE_MOVE = [0xee, [NULL, ]]
        self.STEER_BOAT = [0xee, [NULL, ]]
        self.PREPARE_CRAFTING_GRID = [0xee, [NULL, ]]
        self.CRAFTING_BOOK_DATA = [0xee, [NULL, ]]
        self.ADVANCEMENT_TAB = [0xee, [NULL, ]]
        self.CRAFT_RECIPE_REQUEST = [0xee, [NULL, ]]

        # Parsing changes
        if protocol >= PROTOCOL_1_8START:
            self.KEEP_ALIVE[PARSER] = [VARINT]
            self.PLAYER_POSLOOK[PARSER] = [DOUBLE, DOUBLE, DOUBLE, FLOAT, FLOAT, BOOL]  # noqa
            self.CLIENT_STATUS[PARSER] = [VARINT]
            self.CLICK_WINDOW[PARSER] = [UBYTE, SHORT, BYTE, SHORT, BYTE, SLOT]

        if PROTOCOL_1_9START > protocol >= PROTOCOL_1_8START:
            self.SPECTATE[PKT] = 0x18
            self.RESOURCE_PACK_STATUS[PKT] = 0x19

        # 1.9 - 1.11
        if protocol >= PROTOCOL_1_9REL1:
            self.TELEPORT_CONFIRM[PKT] = 0x00
            self.TAB_COMPLETE[PKT] = 0x01 
            self.CHAT_MESSAGE[PKT] = 0x02  # message length increased to 256 at 1.11 (315)  # noqa
            self.CLIENT_STATUS[PKT] = 0x03
            self.CLIENT_SETTINGS[PKT] = 0x04
            self.CONFIRM_TRANSACTION[PKT] = 0x05 
            self.ENCHANT_ITEM[PKT] = 0x06 
            self.CLICK_WINDOW[PKT] = 0x07
            self.CLOSE_WINDOW[PKT] = 0x08 
            self.PLUGIN_MESSAGE[PKT] = 0x09
            self.USE_ENTITY[PKT] = 0x0a
            self.KEEP_ALIVE[PKT] = 0x0b
            self.PLAYER_POSITION[PKT] = 0x0c
            self.PLAYER_POSLOOK[PKT] = 0x0d
            self.PLAYER_LOOK[PKT] = 0x0e
            self.PLAYER[PKT] = 0x0f
            self.VEHICLE_MOVE[PKT] = 0x10 
            self.STEER_BOAT[PKT] = 0x11 
            self.PLAYER_ABILITIES[PKT] = 0x12
            self.PLAYER_DIGGING[PKT] = 0x13
            self.ENTITY_ACTION[PKT] = 0x14 
            self.STEER_VEHICLE[PKT] = 0x15 
            self.RESOURCE_PACK_STATUS[PKT] = 0x16 
            self.HELD_ITEM_CHANGE[PKT] = 0x17
            self.CREATIVE_INVENTORY_ACTION[PKT] = 0x18 
            self.PLAYER_UPDATE_SIGN[PKT] = 0x19
            self.ANIMATION[PKT] = 0x1a 
            self.SPECTATE[PKT] = 0x1b
            self.PLAYER_BLOCK_PLACEMENT[PKT] = 0x1c
            self.USE_ITEM[PKT] = 0x1d

            # parsing changes:
            self.CLICK_WINDOW[PARSER] = [UBYTE, SHORT, BYTE, SHORT, BYTE, SLOT]  # noqa

        if protocol > PROTOCOL_1_12START:
            # snapshots raise ValueError, so this is really >= PROTOCOL_1_12
            self.PREPARE_CRAFTING_GRID[PKT] = 0x01
            self.TAB_COMPLETE[PKT] = 0x02 
            self.CHAT_MESSAGE[PKT] = 0x03
            self.CLIENT_STATUS[PKT] = 0x04  # open inventory was removed as a status  # noqa
            self.CLIENT_SETTINGS[PKT] = 0x05
            self.CONFIRM_TRANSACTION[PKT] = 0x06 
            self.ENCHANT_ITEM[PKT] = 0x07 
            self.CLICK_WINDOW[PKT] = 0x08
            self.CLOSE_WINDOW[PKT] = 0x09 
            self.PLUGIN_MESSAGE[PKT] = 0x0a
            self.USE_ENTITY[PKT] = 0x0b
            self.KEEP_ALIVE[PKT] = 0x0c
            self.PLAYER[PKT] = 0x0d
            self.PLAYER_POSITION[PKT] = 0x0e
            self.PLAYER_POSLOOK[PKT] = 0x0f
            self.PLAYER_LOOK[PKT] = 0x10
            self.VEHICLE_MOVE[PKT] = 0x11 
            self.STEER_BOAT[PKT] = 0x12 
            self.PLAYER_ABILITIES[PKT] = 0x13
            self.PLAYER_DIGGING[PKT] = 0x14  # TODO - 1.9 changed status codes some  # noqa
            self.ENTITY_ACTION[PKT] = 0x15 
            self.STEER_VEHICLE[PKT] = 0x16 
            self.CRAFTING_BOOK_DATA[PKT] = 0x17 
            self.RESOURCE_PACK_STATUS[PKT] = 0x18 
            self.ADVANCEMENT_TAB[PKT] = 0x19  # ADDED 1.12
            self.HELD_ITEM_CHANGE[PKT] = 0x1a
            self.CREATIVE_INVENTORY_ACTION[PKT] = 0x1b 
            self.PLAYER_UPDATE_SIGN[PKT] = 0x1c
            self.ANIMATION[PKT] = 0x1d 
            self.SPECTATE[PKT] = 0x1e
            self.PLAYER_BLOCK_PLACEMENT[PKT] = 0x1f
            self.USE_ITEM[PKT] = 0x20

        if protocol > PROTOCOL_1_12_1START:
            self.PREPARE_CRAFTING_GRID[PKT] = 0xee  # replaced by CRAFT_RECIPE_REQUEST  # noqa
            self.TAB_COMPLETE[PKT] = 0x01
            self.CHAT_MESSAGE[PKT] = 0x02
            self.CLIENT_STATUS[PKT] = 0x03  # open inventory was removed as a status  # noqa
            self.CLIENT_SETTINGS[PKT] = 0x04
            self.CONFIRM_TRANSACTION[PKT] = 0x05 
            self.ENCHANT_ITEM[PKT] = 0x06 
            self.CLICK_WINDOW[PKT] = 0x07
            self.CLOSE_WINDOW[PKT] = 0x08 
            self.PLUGIN_MESSAGE[PKT] = 0x09
            self.USE_ENTITY[PKT] = 0x0a
            self.KEEP_ALIVE = [0x0b, [LONG]]
            self.PLAYER[PKT] = 0x0c
            self.PLAYER_POSITION[PKT] = 0x0d
            self.PLAYER_POSLOOK[PKT] = 0x0e
            self.PLAYER_LOOK[PKT] = 0x0f
            self.VEHICLE_MOVE[PKT] = 0x10 
            self.STEER_BOAT[PKT] = 0x11 
            self.CRAFT_RECIPE_REQUEST[PKT] = 0x12
