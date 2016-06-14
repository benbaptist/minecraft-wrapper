# -*- coding: utf-8 -*-

from core.exceptions import UnsupportedMinecraftProtocol

"""
Ways to reference packets by names and not hard-coded numbers.

This attempts to follow the wiki as much as possible.

It is up to wrapper to know what the actual connection versions are.
Once it knows the version, it can do something like:
    `from mcpkt import server18 as ClPkt` (remember wrappers "server" process parses client-bound packets).
the remainder of the wrapper/plugin code can simply reference
    `ClPkt.playerlook`

Protocol constants are named as follows:
    first two digits are major version, third digit in minor version.
    example: PROTOCOL_1_8_9 means - version 1.8.9.
    Explanatory text (pre, start, etc) may be last.

packet classes are named as follows:
    First word is the bound direction (as found in the protocol Wiki), followed by two digit major version.
    example: Server189 means - "Server" bound packets (en-route to server),
    major version 1.8, minor version 9 (i.e., 1.8.9). Explanatory text (pre, start, etc) are last and
    are discouraged... Keeping packet classes to an actual major release is the ideal (although some
    minor releases may be needed).

set something False/unimplemented using 0xEE

"""

# Version Constants
# use these constants to select which packet set to use.

PROTOCOL_MAX = 1000  # used for lastest protocol end version.
#
# Use Server194/Client194
PROTOCOL_1_9_4 = 110      # post- 1.9.3 "pre" releases (1.9.3 pre-2 -)
# Still in development at versions 201-203 (5/27/16)

# Use Server19/Client19
PROTOCOL_1_9_3PRE3 = 109  # post- 1.9 "pre" releases (1.9.2 - 1.9.3 pre-1)
# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=7817

PROTOCOL_1_9_1PRE = 108   # post- 1.9 "pre" releases (1.9.1 pre-3 through 1.9.1)
PROTOCOL_1_9REL1 = 107    # first stable 1.9 release
# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=7617

# Between 49-106, the protocol is incredibly unstable.  Packet numbers changed almost weekly. Recommend
#   you not have a client or server running in these protocol versions

# Up to this point (<48), 18 is appropriate, but
PROTOCOL_1_9START = 48    # start of 1.9 snapshots
# Use Server18/Client18
PROTOCOL_1_8END = 47      # 1.8.9
# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=7368
PROTOCOL_1_8START = 6     # 1.8 snapshots start- #

# for reference:
PROTOCOL_1_7_9 = 5       # 1.7.6 - 1.7.10
# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=6003


PROTOCOL_1_7 = 4          # 1.7.1-pre to 1.7.5
# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=5486

"""Minecraft version 1.6.4 and older used a protocol versioning scheme separate from the current one.
 Accordingly, an old protocol version number may ambiguously refer to an one of those old versions and
 from the list above.  Do not run a 1.6.4 server with proxy mode."""

# region Constants
# ------------------------------------------------

_STRING = 0
_JSON = 1
_UBYTE = 2
_BYTE = 3
_INT = 4
_SHORT = 5
_USHORT = 6
_LONG = 7
_DOUBLE = 8
_FLOAT = 9
_BOOL = 10
_VARINT = 11
_BYTEARRAY = 12
_BYTEARRAY_SHORT = 13
_POSITION = 14
_SLOT = 15
_UUID = 16
_METADATA = 17
_SLOT_NO_NBT = 18
_REST = 90
_RAW = 90
_NULL = 100
# endregion


class ClientBound:
    def __init__(self, protocol):

        if PROTOCOL_1_8END < protocol < PROTOCOL_1_9REL1:
            raise UnsupportedMinecraftProtocol

        self.LOGIN_DISCONNECT = 0x00
        self.LOGIN_ENCR_REQUEST = 0x01
        self.LOGIN_SUCCESS = 0x02
        self.LOGIN_SET_COMPRESSION = 0X03

        self.PING_JSON_RESPONSE = 0x00  # the json data represented as a string
        self.PING_PONG = 0x01  # PONG sent in response to Client PING

        # Base set 1.7 - 1.8.9
        self.ANIMATION = 0x0b
        self.ATTACH_ENTITY = 0x1b
        self.BLOCK_CHANGE = 0x23
        self.CHANGE_GAME_STATE = 0x2b
        self.CHAT_MESSAGE = 0x02
        self.CHUNK_DATA = 0x21
        self.DESTROY_ENTITIES = 0x13
        self.DISCONNECT = 0x40
        self.ENTITY = 0x14
        self.ENTITY_EFFECT = 0x1d
        self.ENTITY_HEAD_LOOK = 0x19
        self.ENTITY_METADATA = 0x1c
        self.ENTITY_PROPERTIES = 0x20
        self.ENTITY_RELATIVE_MOVE = 0x15
        self.ENTITY_STATUS = 0x1a
        self.ENTITY_TELEPORT = 0x18
        self.JOIN_GAME = 0x01
        self.KEEP_ALIVE = 0x00
        self.MAP_CHUNK_BULK = 0x26
        self.NAMED_SOUND_EFFECT = 0x29
        self.OPEN_WINDOW = 0x2d
        self.PARTICLE = 0x2a
        self.PLAYER_ABILITIES = 0x39
        self.PLAYER_LIST_ITEM = 0x38
        self.PLAYER_POSLOOK = 0x08
        self.REMOVE_ENTITY_EFFECT = 0x1e
        self.RESOURCE_PACK_SEND = 0x48
        self.RESPAWN = 0x07
        self.SET_EXPERIENCE = 0x1f
        self.SET_SLOT = 0x2f
        self.SPAWN_MOB = 0x0f
        self.SPAWN_OBJECT = 0x0e
        self.SPAWN_PLAYER = 0x0c
        self.SPAWN_POSITION = 0x05
        self.TIME_UPDATE = 0x03
        self.USE_BED = 0x0a
        self.WINDOW_ITEMS = 0x30
        self.UPDATE_BLOCK_ENTITY = 0xEE  # Added protocol 110

        # 1.9 changes
        if protocol >= PROTOCOL_1_9REL1:
            self.ANIMATION = 0x06
            self.ATTACH_ENTITY = 0x3a
            self.BLOCK_CHANGE = 0x0b
            self.CHANGE_GAME_STATE = 0x1e
            self.CHAT_MESSAGE = 0x0f
            self.CHUNK_DATA = 0x20
            self.DESTROY_ENTITIES = 0x30
            self.DISCONNECT = 0x1a
            self.ENTITY = 0x28
            self.ENTITY_EFFECT = 0x4c
            self.ENTITY_HEAD_LOOK = 0x34
            self.ENTITY_METADATA = 0x39
            self.ENTITY_PROPERTIES = 0x4b
            self.ENTITY_RELATIVE_MOVE = 0x25
            self.ENTITY_STATUS = 0x1b
            self.ENTITY_TELEPORT = 0x4a
            self.JOIN_GAME = 0x23
            self.KEEP_ALIVE = 0x1f
            self.MAP_CHUNK_BULK = 0xEE
            self.NAMED_SOUND_EFFECT = 0x19
            self.OPEN_WINDOW = 0x13
            self.PARTICLE = 0x22
            self.PLAYER_ABILITIES = 0x2b
            self.PLAYER_LIST_ITEM = 0x2d
            self.PLAYER_POSLOOK = 0x2e
            self.REMOVE_ENTITY_EFFECT = 0x31
            self.RESOURCE_PACK_SEND = 0x32
            self.RESPAWN = 0x33
            self.SET_EXPERIENCE = 0x3d
            self.SET_SLOT = 0x16
            self.SPAWN_MOB = 0x03
            self.SPAWN_OBJECT = 0x00
            self.SPAWN_PLAYER = 0x05
            self.SPAWN_POSITION = 0x43
            self.TIME_UPDATE = 0x44
            self.USE_BED = 0x2f
            self.WINDOW_ITEMS = 0x14

        # 1.9.4 changes
        if protocol > PROTOCOL_1_9_4:
            self.ENTITY_EFFECT = 0x4b
            self.ENTITY_PROPERTIES = 0x4a
            self.ENTITY_TELEPORT = 0x49
            self.UPDATE_BLOCK_ENTITY = 0x09


class ServerBound:
    def __init__(self, protocol):

        if PROTOCOL_1_8END < protocol < PROTOCOL_1_9REL1:
            raise UnsupportedMinecraftProtocol

        self.HANDSHAKE = 0x00  # set server to STATUS(1) or LOGIN(2) mode.

        self.REQUEST = 0x00  # ... functions like a "go!" when one starts a race.  Server sends data in response packet

        self.STATUS_PING = 0x01  # server responds with a PONG

        self.LOGIN_START = 0x00  # contains the "name" of user.  Sent after handshake for LOGIN
        self.LOGIN_ENCR_RESPONSE = 0x01  # client response to ENCR_REQUEST

        # 1.7 - 1.7.10 PLAY packets
        self.CHAT_MESSAGE = 0x01
        self.CLICK_WINDOW = 0x0e
        self.CLIENT_SETTINGS = 0x15
        self.HELD_ITEM_CHANGE = 0x09
        self.KEEP_ALIVE = 0x00
        self.PLAYER = 0x03
        self.PLAYER_ABILITIES = 0x13
        self.PLAYER_BLOCK_PLACEMENT = 0x08
        self.PLAYER_DIGGING = 0x07
        self.PLAYER_LOOK = 0x05
        self.PLAYER_POSITION = 0x04
        self.PLAYER_POSLOOK = 0x06
        self.PLAYER_UPDATE_SIGN = 0x12
        self.SPECTATE = 0xEE
        self.TELEPORT_CONFIRM = 0xEE
        self.USE_ENTITY = 0x02
        self.USE_ITEM = 0xEE

        # 1.8 - 1.8.9
        if PROTOCOL_1_9START > protocol >= PROTOCOL_1_8START:
            self.SPECTATE = 0x18

        # 1.9
        if protocol >= PROTOCOL_1_9REL1:
            self.CHAT_MESSAGE = 0x02
            self.CLICK_WINDOW = 0x07
            self.CLIENT_SETTINGS = 0x04
            self.HELD_ITEM_CHANGE = 0x17
            self.KEEP_ALIVE = 0x0b
            self.PLAYER = 0x0f
            self.PLAYER_ABILITIES = 0x12
            self.PLAYER_BLOCK_PLACEMENT = 0x1c
            self.PLAYER_DIGGING = 0x13
            self.PLAYER_LOOK = 0x0e
            self.PLAYER_POSITION = 0x0c
            self.PLAYER_POSLOOK = 0x0d
            self.PLAYER_UPDATE_SIGN = 0x19
            self.SPECTATE = 0x1b
            self.TELEPORT_CONFIRM = 0x00
            self.USE_ENTITY = 0x0a
            self.USE_ITEM = 0x1d
