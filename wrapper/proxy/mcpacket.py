# -*- coding: utf-8 -*-

# p2 and py3 compliant (no PyCharm IDE-flagged warnings or errors)

"""
Ways to reference packets by names and not hard-coded numbers
It is up to wrapper to know what the actual connection versions are.
Once it knows the version, it can do something like:
    `from mcpkt import serverBound18 as ClPkt`
the remainder of the wrapper/plugin code can simply reference
    `ClPkt.playerlook`

set something False using 0xEE
"""

# Version Coding
PROTOCOL_1_9_1_PRE = 108  # post- 1.9 "pre releases (1.9.1 pre-3 and later
PROTOCOL_1_9REL1 = 107    # start of stable 1.9 release (or most current snapshop that is documented by protocol)
PROTOCOL_1_9START = 48    # start of 1.9 snapshots
PROTOCOL_1_8START = 6     # 1.8 snapshots started here

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
