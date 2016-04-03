# -*- coding: utf-8 -*-

# Ways to reference packets by names and not hard-coded numbers
# It is up to wrapper to know what the actual connection versions are.
# Once it knows the version, it can do something like:
#  `from mcpkt import serverBound18 as ClPkt`
# the remainder of the wrapper/plugin code can simply reference
# `ClPkt.playerlook`

# set something False using 0xEE

class ServerBound18:
    """ wrapper's "Client" process, which handles connections from client to wrapper.
    These packets are being sent to the server (i.e., wrapper's proxy) from the client.
    Proxy, in turn, can "send" these on, or drop them (return False)
    """

    keepalive = 0x00  # client's response to server challenge
    chatmessage = 0x01
    useentity = 0x02
    player = 0x03  # onground
    playerposition = 0x04
    playerposlook = 0x06
    playerlook = 0x05
    playerdigging = 0x07
    playerblockplacement = 0x08
    helditemchange = 0x09
    playerupdatesign = 0x12
    clientsettings = 0x15
    spectate = 0x18
    clickwindow = 0x0e

    teleportconfirm = 0xEE  # Does not exist in 1.8
    useitem = 0xEE  # Does not exist in 1.8


class ServerBound19:  # updated to protocol 94 15w51b
    """ wrapper's "Client" process, which handles connections from client to wrapper.

    These packets are being sent to the server (i.e., wrapper's proxy) from the client.
    Proxy, in turn, can "send" these on, or drop them (return False)
    """

    teleportconfirm = 0x00
    keepalive = 0x0b  # client's response to server challenge
    chatmessage = 0x02
    useentity = 0x0a
    clientsettings = 0x04
    player = 0x0f  # onground
    clickwindow = 0x07
    playerposition = 0x0c
    playerposlook = 0x0d
    playerlook = 0x0e
    playerdigging = 0x13
    helditemchange = 0x17
    playerupdatesign = 0x19
    spectate = 0x1b
    playerblockplacement = 0x1c
    useitem = 0x1d  # only used for animation purposes


class ClientBound18:
    """ wrapper's "Server" process, which handles connections from server to wrapper.

    These packets are being sent to the client (i.e., wrapper's proxy) from the server.
    Proxy, in turn reads the info and passes it on the client (making any needed mods).
    """

    keepalive = 0x00  # server challenge to client
    joingame = 0x01
    chatmessage = 0x02
    timeupdate = 0x03
    spawnposition = 0x05
    respawn = 0x07
    playerposlook = 0x08
    usebed = 0x0a
    animation = 0x0b
    spawnplayer = 0x0c
    spawnobject = 0x0e
    spawnmob = 0x0f
    entityrelativemove = 0x15
    entityteleport = 0x18
    entityheadlook = 0x19
    entitystatus = 0x1a
    attachentity = 0x1b
    entitymetadata = 0x1c
    entityeffect = 0x1d
    removeentityeffect = 0x1e
    entityproperties = 0x20
    chunkdata = 0x21
    blockchange = 0x23
    mapchunkbulk = 0x26
    setslot = 0x2f
    playerlistitem = 0x38
    disconnect = 0x40
    changegamestate = 0x2b
    namedsoundeffect = 0x29  # 1.8 protocol just calls it "sound effect"
    playerabilities = 0x13
    openwindow = 0x2d
    setexperience = 0x1f
    resourcepacksend = 0x48


class ClientBound19:  # updated to protocol 107 1.9 minecraft
    """ wrapper's "Server" process, which handles connections from server to wrapper.

    These packets are being sent to the client (i.e., wrapper's proxy) from the server.
    Proxy, in turn reads the info and passes it on the client (making any needed mods).
    """

    keepalive = 0x1f  # server challenge to client
    spawnobject = 0x00
    spawnmob = 0x03
    spawnplayer = 0x05
    animation = 0x06
    blockchange = 0xEE  # -0x0b  disabled: wrapper code prior to build 109 does nothing
    chatmessage = 0x0f
    setslot = 0x16
    namedsoundeffect = 0x19
    disconnect = 0x1a
    entitystatus = 0x1b
    changegamestate = 0x1e
    chunkdata = 0x20
    joingame = 0x23
    entityrelativemove = 0x25
    playerlistitem = 0x2d
    playerposlook = 0x2e
    usebed = 0x2f
    removeentityeffect = 0x31
    respawn = 0x33
    entityheadlook = 0x34
    entitymetadata = 0x39
    attachentity = 0x3a
    spawnposition = 0x43
    timeupdate = 0x44
    entityteleport = 0x4a
    entityproperties = 0x4b
    entityeffect = 0x4c
    mapchunkbulk = 0xEE  # deprecated and not used in 1.9
    playerabilities = 0x2b
    openwindow = 0x13
    setexperience = 0x3d
    resourcepacksend = 0x32
