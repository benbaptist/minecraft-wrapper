# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
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

        # new packets implemented after 1.7
        self.SPECTATE = 0xee  # 1.8
        self.RESOURCE_PACK_STATUS = 0xee  # 1.8

        self.TELEPORT_CONFIRM = 0xee  # 1.9
        self.USE_ITEM = 0xee  # 1.9
        self.VEHICLE_MOVE = 0xee  # 1.9
        self.STEER_BOAT = 0xee  # 1.9

        self.PREPARE_CRAFTING_GRID = 0xee  # 1.12
        self.CRAFTING_BOOK_DATA = 0xee  # 1.12
        self.ADVANCEMENT_TAB = 0xee  # 1.12

        self.CRAFT_RECIPE_REQUEST = 0xee  # 1.12.1

        # Parsing changes
        if protocol >= PROTOCOL_1_8START:
            self.KEEP_ALIVE[PARSER] = [VARINT]

        if PROTOCOL_1_9START > protocol >= PROTOCOL_1_8START:
            self.SPECTATE = 0x18
            self.RESOURCE_PACK_STATUS = 0x19

        # 1.9 - 1.11
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

        if protocol > PROTOCOL_1_12START:
            # snapshots raise ValueError, so this is really >= PROTOCOL_1_12
            self.PREPARE_CRAFTING_GRID = 0x01  # TODO NEW 1.12
            self.TAB_COMPLETE = 0x02  # TODO NEW
            self.CHAT_MESSAGE = 0x03
            self.CLIENT_STATUS = 0x04  # open inventory was removed as a status
            self.CLIENT_SETTINGS = 0x05
            self.CONFIRM_TRANSACTION = 0x06  # TODO NEW
            self.ENCHANT_ITEM = 0x07  # TODO NEW
            self.CLICK_WINDOW = 0x08
            self.CLOSE_WINDOW = 0x09  # TODO NEW
            self.PLUGIN_MESSAGE = 0x0a
            self.USE_ENTITY = 0x0b
            self.KEEP_ALIVE[PKT] = 0x0c
            self.PLAYER = 0x0d
            self.PLAYER_POSITION = 0x0e
            self.PLAYER_POSLOOK = 0x0f
            self.PLAYER_LOOK = 0x10
            self.VEHICLE_MOVE = 0x11  # TODO NEW
            self.STEER_BOAT = 0x12  # TODO NEW
            self.PLAYER_ABILITIES = 0x13
            self.PLAYER_DIGGING = 0x14  # TODO - 1.9 changed status codes some
            self.ENTITY_ACTION = 0x15  # TODO NEW
            self.STEER_VEHICLE = 0x16  # TODO NEW
            self.CRAFTING_BOOK_DATA = 0x17  # TODO NEW
            self.RESOURCE_PACK_STATUS = 0x18  # TODO NEW
            self.ADVANCEMENT_TAB = 0x19  # ADDED 1.12
            self.HELD_ITEM_CHANGE = 0x1a
            self.CREATIVE_INVENTORY_ACTION = 0x1b  # TODO NEW
            self.PLAYER_UPDATE_SIGN = 0x1c
            self.ANIMATION = 0x1d  # TODO NEW
            self.SPECTATE = 0x1e
            self.PLAYER_BLOCK_PLACEMENT = 0x1f
            self.USE_ITEM = 0x20

        if protocol > PROTOCOL_1_12_1START:
            self.PREPARE_CRAFTING_GRID = 0xee  # replaced by CRAFT_RECIPE_REQUEST
            self.TAB_COMPLETE = 0x01
            self.CHAT_MESSAGE = 0x02
            self.CLIENT_STATUS = 0x03  # open inventory was removed as a status
            self.CLIENT_SETTINGS = 0x04
            self.CONFIRM_TRANSACTION = 0x05  # TODO NEW
            self.ENCHANT_ITEM = 0x06  # TODO NEW
            self.CLICK_WINDOW = 0x07
            self.CLOSE_WINDOW = 0x08  # TODO NEW
            self.PLUGIN_MESSAGE = 0x09
            self.USE_ENTITY = 0x0a
            self.KEEP_ALIVE[PKT] = 0x0b
            self.PLAYER = 0x0c
            self.PLAYER_POSITION = 0x0d
            self.PLAYER_POSLOOK = 0x0e
            self.PLAYER_LOOK = 0x0f
            self.VEHICLE_MOVE = 0x10  # TODO NEW
            self.STEER_BOAT = 0x11  # TODO NEW
            self.CRAFT_RECIPE_REQUEST = 0x12

            # Parsing changes
            self.KEEP_ALIVE[PARSER] = [LONG]

            # New Notes:
            # - Client status has new notes relevant to respawns
            # - Block placement has more precise info about placement
