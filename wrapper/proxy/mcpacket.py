# -*- coding: utf-8 -*-

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
    example: PROTOCOL_1_8_9 means - major version 1.8, minor version 9 (i.e., 1.8.9).
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
# Use Server19/Client19
PROTOCOL_1_9_4 = 110      # post- 1.9.3 "pre" releases (1.9.3 pre-2 -)

# Use Server19/Client19
PROTOCOL_1_9_3PRE3 = 109  # post- 1.9 "pre" releases (1.9.2 - 1.9.3 pre-1)
PROTOCOL_1_9_1PRE = 108   # post- 1.9 "pre" releases (1.9.1 pre-3 through 1.9.1)
PROTOCOL_1_9REL1 = 107    # start of stable 1.9 release

# Between 49-106, the protocol is incredibly unstable.  Packet numbers changed almost weekly. Recommend
#   you not have a client or server running in these protocol versions

# Up to this point (<48), 18 is appropriate, but
PROTOCOL_1_9START = 48    # start of 1.9 snapshots

# Use Server18/Client18
PROTOCOL_1_8START = 6     # 1.8 snapshots start- # 47 Protocol docs - http://wiki.vg/index.php?title=Protocol&oldid=7368
# below this, you take your chances!, but Client/Server18 may work.

# for reference:
PROTOCOL_1_7_9 = 5       # 1.7.6 - 1.7.10      http://wiki.vg/index.php?title=Protocol&oldid=6003
PROTOCOL_1_7 = 4          # 1.7.1-pre to 1.7.5  http://wiki.vg/index.php?title=Protocol&oldid=5486

"""Minecraft version 1.6.4 and older used a protocol versioning scheme separate from the current one.
 Accordingly, an old protocol version number may ambiguously refer to an one of those old versions and
 from the list above.  Do not run a 1.6.4 server with proxy mode."""


class ServerBound18:
    """ wrapper's "Client" process, which handles connections from client to wrapper.
    These packets are being sent to the server (i.e., wrapper's proxy) from the client.
    Proxy, in turn, can "send" these on, or drop them (return False)
    """
    def __init__(self):
        pass

    KEEP_ALIVE = 0x00  # Client's Response To Server Challenge
    CHAT_MESSAGE = 0x01
    USE_ENTITY = 0x02
    PLAYER = 0x03  # Onground
    PLAYER_POSITION = 0x04
    PLAYER_POSLOOK = 0x06
    PLAYER_LOOK = 0x05
    PLAYER_DIGGING = 0x07
    PLAYER_BLOCK_PLACEMENT = 0x08
    PLAYER_UPDATE_SIGN = 0x12
    HELD_ITEM_CHANGE = 0x09
    CLIENT_SETTINGS = 0x15
    CLICK_WINDOW = 0x0e
    SPECTATE = 0x18
    PLAYER_ABILITIES = 0x13  # corrected/added/verified wiki.vg/Protocol_History#16w07b see 15w31a serverbound
    USE_ITEM = 0xEE  # Does not exist in 1.8
    TELEPORT_CONFIRM = 0xEE  # Does not exist in 1.8


class ServerBound19:  # Updated To Protocol 94 15w51b
    """ wrapper's "Client" process, which handles connections from client to wrapper.
    These packets are being sent to the server (i.e., wrapper's proxy) from the client.
    Proxy, in turn, can "send" these on, or drop them (return False)
    """
    def __init__(self):
        pass

    KEEP_ALIVE = 0x0b  # Client's Response To Server Challenge
    CHAT_MESSAGE = 0x02
    USE_ENTITY = 0x0a
    PLAYER = 0x0f  # Onground
    PLAYER_POSITION = 0x0c
    PLAYER_POSLOOK = 0x0d
    PLAYER_LOOK = 0x0e
    PLAYER_DIGGING = 0x13
    PLAYER_BLOCK_PLACEMENT = 0x1c
    PLAYER_UPDATE_SIGN = 0x19
    HELD_ITEM_CHANGE = 0x17
    CLIENT_SETTINGS = 0x04
    CLICK_WINDOW = 0x07
    SPECTATE = 0x1b
    PLAYER_ABILITIES = 0x12  # corrected/added/verified wiki.vg/Protocol_History#16w07b see 15w43a serverbound
    USE_ITEM = 0x1d  # Only Used For Animation Purposes
    TELEPORT_CONFIRM = 0x00

class ClientBound18:
    """ wrapper's "Server" process, which handles connections from server to wrapper.
    These packets are being sent to the client (i.e., wrapper's proxy) from the server.
    Proxy, in turn reads the info and passes it on the client (making any needed mods).
    """
    def __init__(self):
        pass

    KEEP_ALIVE = 0x00  # Server Challenge To Client
    CHAT_MESSAGE = 0x02
    PLAYER_POSLOOK = 0x08
    PLAYER_LIST_ITEM = 0x38
    PLAYER_ABILITIES = 0x39  # corrected/added/verified wiki.vg/Protocol_History#16w07b see 15w43a clientbound
    JOIN_GAME = 0x01
    DISCONNECT = 0x40
    RESPAWN = 0x07
    SPAWN_POSITION = 0x05
    SPAWN_PLAYER = 0x0c
    SPAWN_OBJECT = 0x0e
    SPAWN_MOB = 0x0f
    ATTACH_ENTITY = 0x1b
    ENTITY_RELATIVE_MOVE = 0x15
    ENTITY_TELEPORT = 0x18
    ENTITY_HEAD_LOOK = 0x19
    ENTITY_STATUS = 0x1a
    ENTITY_METADATA = 0x1c
    ENTITY_EFFECT = 0x1d
    ENTITY_PROPERTIES = 0x20
    REMOVE_ENTITY_EFFECT = 0x1e
    SET_EXPERIENCE = 0x1f
    CHANGE_GAME_STATE = 0x2b
    NAMED_SOUND_EFFECT = 0x29  # 1.8 protocol just calls it "sound effect"
    RESOURCE_PACK_SEND = 0x48
    CHUNK_DATA = 0x21
    BLOCK_CHANGE = 0x23
    MAP_CHUNK_BULK = 0x26
    SET_SLOT = 0x2f
    OPEN_WINDOW = 0x2d
    USE_BED = 0x0a
    TIME_UPDATE = 0x03
    ANIMATION = 0x0b


class ClientBound19:  # Updated To Protocol 107 1.9 Minecraft
    """ wrapper's "Server" process, which handles connections from server to wrapper.
    These packets are being sent to the client (i.e., wrapper's proxy) from the server.
    Proxy, in turn reads the info and passes it on the client (making any needed mods).
    """
    def __init__(self):
        pass

    KEEP_ALIVE = 0x1f  # Server Challenge To Client
    CHAT_MESSAGE = 0x0f
    PLAYER_POSLOOK = 0x2e
    PLAYER_LIST_ITEM = 0x2d
    PLAYER_ABILITIES = 0x2b  # corrected/added/verified wiki.vg/Protocol_History#16w07b see 15w43a clientbound
    JOIN_GAME = 0x23
    DISCONNECT = 0x1a
    RESPAWN = 0x33
    SPAWN_POSITION = 0x43
    SPAWN_PLAYER = 0x05
    SPAWN_OBJECT = 0x00
    SPAWN_MOB = 0x03
    ATTACH_ENTITY = 0x3a
    ENTITY_RELATIVE_MOVE = 0x25
    ENTITY_TELEPORT = 0x4a
    ENTITY_HEAD_LOOK = 0x34
    ENTITY_STATUS = 0x1b
    ENTITY_METADATA = 0x39
    ENTITY_EFFECT = 0x4c
    ENTITY_PROPERTIES = 0x4b
    REMOVE_ENTITY_EFFECT = 0x31
    SET_EXPERIENCE = 0x3d
    CHANGE_GAME_STATE = 0x1e
    NAMED_SOUND_EFFECT = 0x19
    RESOURCE_PACK_SEND = 0x32
    CHUNK_DATA = 0x20
    BLOCK_CHANGE = 0xEE  # -0x0b  disabled: wrapper code prior to build 109 does nothing
    MAP_CHUNK_BULK = 0xEE  # Deprecated And Not Used In 1.9
    SET_SLOT = 0x16
    OPEN_WINDOW = 0x13
    USE_BED = 0x2f
    TIME_UPDATE = 0x44
    ANIMATION = 0x06
