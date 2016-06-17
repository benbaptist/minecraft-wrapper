# -*- coding: utf-8 -*-

# py3 compliant syntax

import threading
import time
import json
import hashlib
import uuid
# import shutil  # these are part of commented out code below for whitelist and name processing
# import os
import random

import utils.encryption as encryption
import proxy.mcpackets as mcpackets

from proxy.serverconnection import ServerConnection
from proxy.packet import Packet
from core.mcuuid import MCUUID
from utils.helpers import processcolorcodes
from api.player import Player

import socket  # not explicitly reference in this module, but this import is used by error handling

# wrapper.py will check for requests to run proxy mode
try:
    import requests
except ImportError:
    requests = False

# region Constants
# ------------------------------------------------

HIDDEN_OPS = ["SurestTexas00", "BenBaptist"]  # These names never appear in the ping list

HANDSHAKE = 0  # this is the default mode of a server awaiting packets from a client out in the ether..
# client will send a handshake (a 0x00 packet WITH payload) asking for STATUS or LOGIN mode
STATUS = 1
# Status mode will await either a ping (0x01) containing a unique long int and will respond with same integer.
#     ... OR if it receives a 0x00 packet (with no payload), that signals server (client.py) to send
#         the MOTD json response packet.
#         The ping will follow the 0x00 request for json response.  The ping will set wrapper/server
#         back to HANDSHAKE mode (to await next handshake).
LOGIN = 2
PLAY = 3
LOBBY = 4  # in lobby state, client is connected to clientconnection, but nothing is passed to the server.
#            the actual client will be in play mode.

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
_SLOT_NO_NBT = 18
_UUID = 16
_METADATA = 17
_REST = 90
_RAW = 90
_NULL = 100
# endregion


class Client:
    def __init__(self, sock, addr, wrapper, publickey, privatekey, proxy):
        """
        Client receives "SERVER BOUND" packets from client.  These are what get parsed (SERVER BOUND format).
        'server.packet.sendpkt' - sends a packet to the server (use SERVER BOUND packet format)
        'self.packet.sendpkt' - sends a packet back to the client (use CLIENT BOUND packet format)

        Args: (self explanatory, hopefully)
            sock:
            addr:
            wrapper:
            publickey:
            privatekey:
            proxy:

        """
        self.socket = sock
        self.addr = addr
        self.wrapper = wrapper
        self.publicKey = publickey
        self.privateKey = privatekey
        self.proxy = proxy

        self.log = wrapper.log
        self.config = wrapper.config
        self.packet = Packet(self.socket, self)

        self.verifyToken = encryption.generate_challenge_token()
        self.serverID = encryption.generate_server_id()
        self.MOTD = {}

        self.serverversion = self.wrapper.javaserver.protocolVersion
        self.clientversion = self.serverversion  # client will reset this later, if need be..

        self.pktSB = mcpackets.ServerBound(self.clientversion)
        self.pktCB = mcpackets.ClientBound(self.clientversion)

        self.abort = False
        self.time_server_pinged = 0
        self.time_client_responded = 0
        self.keepalive_val = 0
        self.server = None  # Proxy ServerConnection() (not the javaserver)
        self.isServer = False
        self.isLocal = True
        self.server_temp = None

        # UUIDs - all should use MCUUID unless otherwise specified
        self.uuid = None  # this is the client UUID authenticated by connection to session server.
        self.serveruuid = None  # Server UUID - which Could be the local offline UUID.

        # information gathered during login or socket connection processes
        self.address = None
        self.ip = None  # this will gather the client IP for use by player.py
        self.serveraddressplayeruses = None
        self.serverportplayeruses = None
        self.lobbified = False

        self.state = HANDSHAKE

        # Items gathered for player info for player api
        self.username = ""
        self.gamemode = 0
        self.dimension = 0
        self.position = (0, 0, 0)  # X, Y, Z
        self.head = (0, 0)  # Yaw, Pitch
        self.inventory = {}
        self.slot = 0
        self.riding = None
        self.lastplacecoords = (0, 0, 0)  # last placement (for use in cases of bucket use)
        self.properties = {}
        self.clientSettings = False
        self.clientSettingsSent = False
        self.skinBlob = {}
        self.windowCounter = 2  # restored this
        self.servereid = None
        self.bedposition = None
        self.lastitem = None

    @property
    def version(self):
        return self.clientversion

    def send(self, packetid, xpr, payload):  # not supported. no docstring. For old code compatability purposes only.
        self.log.debug("deprecated client.send() called.  Use client.packet.sendpkt for best performance.")
        self.packet.send(packetid, xpr, payload)
        pass

    def inittheplayer(self):
        # so few items and so infrequently run that fussing with xrange/range PY3 difference is not needed.
        for i in range(46):  # there are 46 items 0-45 in 1.9 (shield) versus 45 (0-44) in 1.8 and below.
            self.inventory[i] = None
        self.time_server_pinged = time.time()
        self.time_client_responded = time.time()
        self._refresh_server_version()

    def connect_to_server(self, ip=None, port=None):
        """
        Args:
            ip: server IP
            port: server port

        this is the connection to the server.
        """

        self.clientSettingsSent = False
        if self.server is not None:
            self.address = (ip, port)
        if ip is not None:
            # Connect() feature . . .
            self.server_temp = ServerConnection(self, self.wrapper, ip, port)
            try:
                self.server_temp.connect()
                self.server.close(kill_client=False)
                self.server.client = None
                self.server = self.server_temp
            except OSError:
                self.server_temp.close(kill_client=False)
                self.server_temp = None
                if self.state == PLAY:
                    self.packet.sendpkt(
                        self.pktCB.CHAT_MESSAGE,
                        [_STRING],
                        ["""{"text": "Could not connect to that server!", "color": "red", "bold": "true"}"""])
                else:
                    self.packet.sendpkt(
                        0x00, [_STRING],
                        ["""{"text": "Could not connect to that server!", "color": "red", "bold": "true"}"""])
                self.address = None
                return
        else:
            self.server = ServerConnection(self, self.wrapper, ip, port)
            try:
                self.server.connect()
            except Exception as e:
                self.disconnect("Proxy client could not connect to the server (%s)" % e)
        t = threading.Thread(target=self.server.handle, args=())
        t.daemon = True
        t.start()

        if self.config["Proxy"]["spigot-mode"]:
            payload = "localhost\x00%s\x00%s" % (self.addr[0], self.uuid.hex)
            self.server.packet.sendpkt(0x00, [_VARINT, _STRING, _USHORT, _VARINT],
                                       (self.clientversion, payload, self.config["Proxy"]["server-port"], 2))
        else:
            self.server.packet.sendpkt(0x00, [_VARINT, _STRING, _USHORT, _VARINT],
                                       (self.clientversion, "localhost", self.config["Proxy"]["server-port"], 2))
        self.server.packet.sendpkt(0x00, [_STRING], [self.username])

        # Turn this off for now.  This seems like it would also stop legit rain too.  I think the proper way to
        #   do this is to keep track of the rain state of the server and send that instead.
        # if self.clientversion > mcpackets.PROTOCOL_1_8START:  # anti-rain hack for lobby return connections
        #    if self.config["Proxy"]["online-mode"]:
        #        self.packet.sendpkt(self.pktCB.CHANGE_GAME_STATE, [_UBYTE, _FLOAT], (1, 0))
        #        pass

        self.server.state = 2

    def close(self):
        self.abort = True
        try:
            self.socket.close()
        except OSError:
            self.log.debug("Client socket for %s already closed!", self.username)
        if self.server:
            self.server.abort = True
            self.server.close()
        for i, client in enumerate(self.wrapper.proxy.clients):
            if client.username == self.username:
                del self.wrapper.proxy.clients[i]

    def disconnect(self, message, color="white", bold=False, fromserver=False):
        """
        text only message
        """
        if not fromserver:
            jsonmessage = {"text": message,
                           "color": color,
                           "bold": bold
                           }
        else:
            jsonmessage = message  # server packets are read as json

        if self.state == PLAY:
            self.packet.sendpkt(self.pktCB.DISCONNECT, [_JSON], [jsonmessage])
        else:
            self.packet.sendpkt(0x00, [_JSON], [message])
        time.sleep(1)
        self.close()

    def flush(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket.error:
                self.log.debug("clientconnection socket closed (bad file descriptor), closing flush..")
                self.abort = True
                self.close()
                break
            time.sleep(0.03)

    def getPlayerObject(self):
        if self.username in self.wrapper.javaserver.players:
            return self.wrapper.javaserver.players[self.username]
        self.log.error("In playerlist:\n%s\nI could not locate player: %s\n"
                       "This resulted in setting the player object to FALSE!",
                       self.wrapper.javaserver.players, self.username)
        return False

    def editSign(self, position, line1, line2, line3, line4, pre18=False):
        if pre18:
            x = position[0]
            y = position[1]
            z = position[2]
            self.server.packet.sendpkt(self.pktSB.PLAYER_UPDATE_SIGN,
                                       [_INT, _SHORT, _INT, _STRING, _STRING, _STRING, _STRING],
                                       (x, y, z, line1, line2, line3, line4))
        else:
            self.server.packet.sendpkt(self.pktSB.PLAYER_UPDATE_SIGN, [_POSITION, _STRING, _STRING, _STRING, _STRING],
                                       (position, line1, line2, line3, line4))

    def message(self, string):
        self.server.packet.sendpkt(self.pktSB.CHAT_MESSAGE, [_STRING], [string])

    def _refresh_server_version(self):
        # Get serverversion for mcpackets use
        try:
            self.serverversion = self.wrapper.javaserver.protocolVersion
        except AttributeError:
            self.serverversion = -1

    def _getclientpacketset(self):
        # Determine packet types  - in this context, pktSB/pktCB is what is being received/sent from/to the client.
        #   that is why we refresh to the clientversion.
        # packets sent to the server connection from here are hard coded login items only
        self._refresh_server_version()

        self.pktSB = mcpackets.ServerBound(self.clientversion)
        self.pktCB = mcpackets.ClientBound(self.clientversion)

    def parse(self, pkid):  # server - bound parse ("Client" class connection)
        if self.state == PLAY:
            if pkid == self.pktSB.KEEP_ALIVE:
                if self.serverversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_INT])
                    # ("int:payload")
                else:  # self.version >= mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_VARINT])
                    # ("varint:payload")
                # self.log.trace("(PROXY CLIENT) -> Received KEEP_ALIVE from client:\n%s", data)
                if data[0] == self.keepalive_val:
                    self.time_client_responded = time.time()

                # Arbitrary place for this.  It works since Keep alives will be received periodically
                # Needed to move out of the _keep_alive_tracker thread

                # I have no idea what the purpose of parsing these and resending them is (ask the ben bot?)
                if self.clientSettings and not self.clientSettingsSent:
                    if self.clientversion < mcpackets.PROTOCOL_1_8START:
                        self.server.packet.sendpkt(self.pktSB.CLIENT_SETTINGS,
                                                   [_STRING, _BYTE, _BYTE, _BOOL, _BYTE, _BOOL],
                                                   (
                                                    self.clientSettings["locale"],
                                                    self.clientSettings["view_distance"],
                                                    self.clientSettings["chatflags"],
                                                    self.clientSettings["chat_colors"],
                                                    self.clientSettings["difficulty"],
                                                    self.clientSettings["show_cape"]
                                                    ))
                    elif mcpackets.PROTOCOL_1_7_9 < self.clientversion < mcpackets.PROTOCOL_1_9START:
                        self.server.packet.sendpkt(self.pktSB.CLIENT_SETTINGS,
                                                   [_STRING, _BYTE, _BYTE, _BOOL, _UBYTE],
                                                   (
                                                    self.clientSettings["locale"],
                                                    self.clientSettings["view_distance"],
                                                    self.clientSettings["chat_mode"],
                                                    self.clientSettings["chat_colors"],
                                                    self.clientSettings["displayed_skin_parts"]
                                                    ))
                    else:
                        self.server.packet.sendpkt(self.pktSB.CLIENT_SETTINGS,
                                                   [_STRING, _BYTE, _VARINT, _BOOL, _UBYTE, _VARINT],
                                                   (
                                                    self.clientSettings["locale"],
                                                    self.clientSettings["view_distance"],
                                                    self.clientSettings["chat_mode"],
                                                    self.clientSettings["chat_colors"],
                                                    self.clientSettings["displayed_skin_parts"],
                                                    self.clientSettings["main_hand"]
                                                    ))
                    self.clientSettingsSent = True
                return False

            elif pkid == self.pktSB.CHAT_MESSAGE:
                data = self.packet.readpkt([_STRING])
                # self.log.trace("(PROXY CLIENT) -> Parsed CHAT_MESSAGE packet with client state PLAY:\n%s", data)

                if data is None:
                    return False

                # Get the packet chat message contents
                chatmsg = data[0]

                # This was probably what that huge try-except was for.....  # TODO this should prob go away anyway
                # if not self.isLocal and chatmsg == "/lobby":  TODO playerConnect() broken anyway, so no lobbies
                #    self.server.close(reason="Lobbification", kill_client=False)
                #    self.address = None
                #    self.connect_to_server()
                #    self.isLocal = True
                #    return False

                payload = self.wrapper.events.callevent("player.rawMessage", {
                    "player": self.getPlayerObject(),
                    "message": chatmsg
                })

                # This part allows the player plugin event "player.rawMessage" to...
                if not payload:
                    return False  # ..reject the packet (by returning False)

                if type(payload) == str:  # or, if it can return a substitute payload
                    chatmsg = payload

                # determine if this is a command. act appropriately
                if chatmsg[0] == "/":  # it IS a command of some kind
                    if self.wrapper.events.callevent("player.runCommand", {
                            "player": self.getPlayerObject(),
                            "command": chatmsg.split(" ")[0][1:].lower(),
                            "args": chatmsg.split(" ")[1:]}):
                        return False  # wrapper processed this command.. it goes no further

                # NOW we can send it (possibly modded)  on to server...
                self.message(chatmsg)
                return False  # and cancel this original packet

            elif pkid == self.pktSB.PLAYER_POSITION:  # player position
                if self.clientversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _DOUBLE, _BOOL])
                    # ("double:x|double:y|double:yhead|double:z|bool:on_ground")
                elif self.clientversion >= mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _NULL, _DOUBLE, _BOOL])
                    # ("double:x|double:y|double:z|bool:on_ground")
                else:
                    data = [0, 0, 0, 0]
                self.position = (data[0], data[1], data[3])  # skip 1.7.10 and lower protocol yhead args
                # self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSITION packet:\n%s", data)

            elif pkid == self.pktSB.PLAYER_POSLOOK:  # player position and look
                if self.clientversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _DOUBLE, _FLOAT, _FLOAT, _BOOL])
                else:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _FLOAT, _FLOAT, _BOOL])
                # ("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
                self.position = (data[0], data[1], data[4])
                self.head = (data[4], data[5])
                # self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSLOOK packet:\n%s", data)

            elif pkid == self.pktSB.TELEPORT_CONFIRM:
                # don't interfere with this and self.pktSB.PLAYER_POSLOOK... doing so will glitch the client
                # data = self.packet.readpkt([_VARINT])
                # self.log.trace("(SERVER-BOUND) -> Client sent TELEPORT_CONFIRM packet:\n%s", data)
                return True

            elif pkid == self.pktSB.PLAYER_LOOK:  # Player Look
                data = self.packet.readpkt([_FLOAT, _FLOAT, _BOOL])
                # ("float:yaw|float:pitch|bool:on_ground")
                self.head = (data[0], data[1])
                # self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_LOOK packet:\n%s", data)

            elif pkid == self.pktSB.PLAYER_DIGGING:  # Player Block Dig
                # if not self.isLocal: disable these for now and come back to it later - I think these are for lobbies.
                # such a construct should probably be done at the gamestate level.
                #     return True

                if self.clientversion < mcpackets.PROTOCOL_1_7:
                    data = None
                    position = data
                elif mcpackets.PROTOCOL_1_7 <= self.clientversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_BYTE, _INT, _UBYTE, _INT, _BYTE])
                    # "byte:status|int:x|ubyte:y|int:z|byte:face")
                    position = (data[1], data[2], data[3])
                    # self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_DIGGING packet:\n%s", data)
                else:
                    data = self.packet.readpkt([_BYTE, _POSITION, _NULL, _NULL, _BYTE])
                    # "byte:status|position:position|byte:face")
                    position = data[1]
                    # self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_DIGGING packet:\n%s", data)
                if data is None:
                    return True

                # finished digging
                if data[0] == 2:
                    if not self.wrapper.events.callevent("player.dig", {
                        "player": self.getPlayerObject(),
                        "position": position,
                        "action": "end_break",
                        "face": data[4]
                    }):
                        return False  # stop packet if  player.dig returns False

                # started digging
                if data[0] == 0:
                    if self.gamemode != 1:
                        if not self.wrapper.events.callevent("player.dig", {
                            "player": self.getPlayerObject(),
                            "position": position,
                            "action": "begin_break",
                            "face": data[4]
                        }):
                            return False
                    else:
                        if not self.wrapper.events.callevent("player.dig", {
                            "player": self.getPlayerObject(),
                            "position": position,
                            "action": "end_break",
                            "face": data[4]
                        }):
                            return False
                if data[0] == 5 and data[4] == 255:
                    if self.position != (0, 0, 0):
                        playerpos = self.position
                        if not self.wrapper.events.callevent("player.interact", {
                            "player": self.getPlayerObject(),
                            "position": playerpos,
                            "action": "finish_using"
                        }):
                            return False

            elif pkid == self.pktSB.PLAYER_BLOCK_PLACEMENT:  # Player Block Placement
                player = self.getPlayerObject()
                hand = 0  # main hand
                helditem = player.getHeldItem()

                if self.clientversion < mcpackets.PROTOCOL_1_7:
                    data = None
                    position = data

                elif mcpackets.PROTOCOL_1_7 <= self.clientversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_INT, _UBYTE, _INT, _BYTE, _SLOT_NO_NBT, _REST])
                    # "int:x|ubyte:y|int:z|byte:face|slot:item")  _REST includes cursor positions x-y-z
                    position = (data[0], data[1], data[2])

                    # just FYI, notchian servers have been ignoring this field ("item")
                    # for a long time, using server inventory instead.
                    helditem = data[4]  # "item" - _SLOT

                elif mcpackets.PROTOCOL_1_8START <= self.clientversion < mcpackets.PROTOCOL_1_9REL1:
                    data = self.packet.readpkt([_POSITION, _NULL, _NULL, _BYTE, _SLOT, _REST])
                    # "position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                    # helditem = data["item"]  -available in packet, but server ignores it (we should too)!
                    # starting with 1.8, the server maintains inventory also.
                    position = data[0]

                else:  # self.clientversion >= mcpackets.PROTOCOL_1_9REL1:
                    data = self.packet.readpkt([_POSITION, _NULL, _NULL, _VARINT, _VARINT, _BYTE, _BYTE, _BYTE])
                    # "position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                    hand = data[4]  # used to be the spot occupied by "slot"
                    position = data[0]

                # Face and Position exist in all version protocols at this point
                clickposition = position
                face = data[3]

                # self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_BLOCK_PLACEMENT packet:\n%s", data)

                if face == 0:  # Compensate for block placement coordinates
                    position = (position[0], position[1] - 1, position[2])
                elif face == 1:
                    position = (position[0], position[1] + 1, position[2])
                elif face == 2:
                    position = (position[0], position[1], position[2] - 1)
                elif face == 3:
                    position = (position[0], position[1], position[2] + 1)
                elif face == 4:
                    position = (position[0] - 1, position[1], position[2])
                elif face == 5:
                    position = (position[0] + 1, position[1], position[2])

                if helditem is None:
                    # if no item, treat as interaction (according to wrappers
                    # inventory :(, return False  )
                    if not self.wrapper.events.callevent("player.interact", {
                        "player": player,
                        "position": position,
                        "action": "useitem",
                        "origin": "pktSB.PLAYER_BLOCK_PLACEMENT"
                    }):
                        return False

                # block placement event
                self.lastplacecoords = position
                if not self.wrapper.events.callevent("player.place", {"player": player,
                                                                      "position": position,  # where new block goes
                                                                      "clickposition": clickposition,  # block clicked
                                                                      "hand": hand,
                                                                      "item": helditem}):
                    return False

            elif pkid == self.pktSB.USE_ITEM:  # no 1.8 or prior packet
                data = self.packet.readpkt([_REST])
                # "rest:pack")
                # self.log.trace("(PROXY CLIENT) -> Parsed USE_ITEM packet:\n%s", data)
                player = self.getPlayerObject()
                position = self.lastplacecoords
                if "pack" in data:
                    if data[0] == '\x00':
                        if not self.wrapper.events.callevent("player.interact", {
                            "player": player,
                            "position": position,
                            "action": "useitem",
                            "origin": "pktSB.USE_ITEM"
                        }):
                            return False

            elif pkid == self.pktSB.HELD_ITEM_CHANGE:
                slot = self.packet.readpkt([_SHORT])
                # "short:short")  # ["short"]
                # self.log.trace("(PROXY CLIENT) -> Parsed HELD_ITEM_CHANGE packet:\n%s", slot)
                if 9 > slot[0] > -1:
                    self.slot = slot[0]
                else:
                    return False

            elif pkid == self.pktSB.PLAYER_UPDATE_SIGN:  # player update sign
                if self.clientversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_INT, _SHORT, _INT, _STRING, _STRING, _STRING, _STRING])
                    # "int:x|short:y|int:z|string:line1|string:line2|string:line3|string:line4")
                    position = (data[0], data[1], data[2])
                    pre_18 = True
                else:
                    data = self.packet.readpkt([_POSITION, _NULL, _NULL, _STRING, _STRING, _STRING, _STRING])
                    # "position:position|string:line1|string:line2|string:line3|string:line4")
                    position = data[0]
                    pre_18 = False

                l1 = data[3]
                l2 = data[4]
                l3 = data[5]
                l4 = data[6]
                payload = self.wrapper.events.callevent("player.createsign", {
                    "player": self.getPlayerObject(),
                    "position": position,
                    "line1": l1,
                    "line2": l2,
                    "line3": l3,
                    "line4": l4
                })
                # self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_UPDATE_SIGN packet:\n%s", data)
                if not payload:  # plugin can reject sign entirely
                    return False

                if type(payload) == dict:  # send back edits
                    if "line1" in payload:
                        l1 = payload["line1"]
                    if "line2" in payload:
                        l2 = payload["line2"]
                    if "line3" in payload:
                        l3 = payload["line3"]
                    if "line4" in payload:
                        l4 = payload["line4"]

                self.editSign(position, l1, l2, l3, l4, pre_18)
                return False

            elif pkid == self.pktSB.CLIENT_SETTINGS:  # read Client Settings
                if self.clientversion <= mcpackets.PROTOCOL_1_7_9:
                    data = self.packet.readpkt([_STRING, _BYTE, _BYTE, _BOOL, _BYTE, _BOOL, _NULL, _NULL])
                    # "string:locale|byte:view_distance|byte:chat_flags|bool:chat_colors|
                    # byte:difficulty|bool:show_cape")
                elif mcpackets.PROTOCOL_1_7_9 < self.clientversion < mcpackets.PROTOCOL_1_9START:  # "1.8"
                    data = self.packet.readpkt([_STRING, _BYTE, _BYTE, _BOOL, _NULL, _NULL, _UBYTE, _NULL])
                    # "string:locale|byte:view_distance|byte:chat_mode|bool:chat_colors|
                    # ubyte:displayed_skin_parts")
                else:
                    data = self.packet.readpkt([_STRING, _BYTE, _VARINT, _BOOL, _NULL, _NULL, _UBYTE, _VARINT])
                    # "string:locale|byte:view_distance|varint:chat_mode|bool:chat_colors|
                    # ubyte:displayed_skin_parts|
                    # varint:main_hand")
                settingsdict = {"locale": data[0],
                                "view_distance": data[1],
                                "chatmode": data[2],
                                "chatflags": data[2],
                                "chat_colors": data[3],
                                "difficulty": data[4],
                                "show_cape": data[5],
                                "displayed_skin_parts": data[6],
                                "main_hand": data[7]
                                }
                self.clientSettings = settingsdict
                self.clientSettingsSent = True  # the packet is not stopped, sooo...
                # self.log.trace("(PROXY CLIENT) -> Parsed CLIENT_SETTINGS packet:\n%s", settingsdict)

            elif pkid == self.pktSB.CLICK_WINDOW:  # click window
                if self.clientversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_BYTE, _SHORT, _BYTE, _SHORT, _BYTE, _SLOT_NO_NBT])
                    # ("byte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
                elif mcpackets.PROTOCOL_1_8START < self.clientversion < mcpackets.PROTOCOL_1_9START:
                    data = self.packet.readpkt([_UBYTE, _SHORT, _BYTE, _SHORT, _BYTE, _SLOT])
                    # ("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
                elif mcpackets.PROTOCOL_1_9START <= self.clientversion < mcpackets.PROTOCOL_MAX:
                    data = self.packet.readpkt([_UBYTE, _SHORT, _BYTE, _SHORT, _VARINT, _SLOT])
                    # ("ubyte:wid|short:slot|byte:button|short:action|varint:mode|slot:clicked")
                else:
                    data = [False, 0, 0, 0, 0, 0, 0]

                datadict = {
                            "player": self.getPlayerObject(),
                            "wid": data[0],  # window id ... always 0 for inventory
                            "slot": data[1],  # slot number
                            "button": data[2],  # mouse / key button
                            "action": data[3],  # unique action id - incrementing counter
                            "mode": data[4],
                            "clicked": data[5]  # item data
                            }

                if not self.wrapper.events.callevent("player.slotClick", datadict):
                    return False

                # self.log.trace("(PROXY CLIENT) -> Parsed CLICK_WINDOW packet:\n%s", datadict)

                # for inventory control, the most straightforward way to update wrapper's inventory is
                # to use the data from each click.  The server will make other updates and corrections
                # via SET_SLOT

                # yes, this probably breaks for double clicks that send the item to who-can-guess what slot
                # we can fix that in a future update... this gets us 98% fixed (versus 50% before)
                # another source of breakage is if lagging causes server to deny the changes.  Our code
                # is not checking if the server accepted these changes with a CONFIRM_TRANSACTION.

                if data[0] == 0 and data[2] in (0, 1):  # window 0 (inventory) and right or left click
                    if self.lastitem is None and data[5] is None:  # player first clicks on an empty slot - mark empty.
                        self.inventory[data[1]] = None

                    if self.lastitem is None:  # player first clicks on a slot where there IS some data..
                        # having clicked on it puts the slot into NONE status (since it can now be moved)
                        self.inventory[data[1]] = None  # we set the current slot to empty/none
                        self.lastitem = data[5]  # ..and we cache the new slot data to see where it goes
                        return True

                    # up to this point, there was not previous item
                    if self.lastitem is not None and data[5] is None:  # now we have a previous item to process
                        self.inventory[data[1]] = self.lastitem  # that previous item now goes into the new slot.
                        self.lastitem = None  # since the slot was empty, there is no newer item to cache.
                        return True

                    if self.lastitem is not None and data[5] is not None:
                        # our last item now occupies the space clicked and the new item becomes the cached item.
                        self.inventory[data[1]] = self.lastitem  # set the cached item into the clicked slot.
                        self.lastitem = data[5]  # put the item that was in the clicked slot into the cache now.
                        return True

            elif pkid == self.pktSB.SPECTATE:  # Spectate - convert packet to local server UUID
                # !? WHAT!?
                # ___________
                # "Teleports the player to the given entity. The player must be in spectator mode.
                # The Notchian client only uses this to teleport to players, but it appears to accept
                #  any type of entity. The entity does not need to be in the same dimension as the
                # player; if necessary, the player will be respawned in the right world."
                """ Inter-dimensional player-to-player TP ! """  # TODO !

                data = self.packet.readpkt([_UUID, _NULL])  # solves the uncertainty of dealing with what gets returned.
                # ("uuid:target_player")
                # self.log.trace("(PROXY CLIENT) -> Parsed SPECTATE packet:\n%s", data)
                for client in self.proxy.clients:
                    if data[0].hex == client.uuid.hex:
                        self.server.packet.sendpkt(self.pktSB.SPECTATE, [_UUID], [client.serverUuid])
                        print("sent new Spectate packet")
                        return False
            else:
                return True  # no packet parsed in wrapper
            return True  # packet parsed, no rejects or changes
        elif self.state == LOGIN:
            if pkid == 0x00:  # login start packet
                data = self.packet.readpkt([_STRING, _NULL])
                # "username"
                self.username = data[0]

                # just to be clear... this only refers to "proxy"s online mode, not the server.
                if self.config["Proxy"]["online-mode"]:
                    if self.serverversion < 6:  # 1.7.x versions
                        # send to client 1.7
                        self.packet.sendpkt(0x01, [_STRING, _BYTEARRAY_SHORT, _BYTEARRAY_SHORT],
                                            (self.serverID, self.publicKey, self.verifyToken))
                    else:
                        # send to client 1.8 +
                        self.packet.sendpkt(0x01, [_STRING, _BYTEARRAY, _BYTEARRAY],
                                            (self.serverID, self.publicKey, self.verifyToken))
                    self.serveruuid = self.wrapper.getuuidfromname(self.username)  # MCUUID object

                # probably not a good idea to be below here ;)
                else:
                    self.connect_to_server()
                    self.uuid = self.wrapper.getuuidfromname(self.username)  # MCUUID object
                    self.serveruuid = self.wrapper.getuuidfromname(self.username)  # MCUUID object
                    self.packet.sendpkt(0x02, [_STRING, _STRING], (self.uuid.string, self.username))
                    self.state = PLAY
                    self.log.info("%s's client (insecure) LOGON from (IP: %s)", self.username, self.addr[0])
                # self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state LOGIN: \n%s", data)
                return False

            elif pkid == 0x01:
                if self.serverversion < 6:
                    data = self.packet.readpkt([_BYTEARRAY_SHORT, _BYTEARRAY_SHORT])
                    # "shared_secret|verify_token"
                else:
                    data = self.packet.readpkt([_BYTEARRAY, _BYTEARRAY])
                    # "bytearray:shared_secret|bytearray:verify_token")
                # self.log.trace("(PROXY CLIENT) -> Parsed 0x01 ENCRYP RESP packet with client state LOGIN:\n%s", data)

                sharedsecret = encryption.decrypt_shared_secret(data[0], self.privateKey)
                verifytoken = encryption.decrypt_shared_secret(data[1], self.privateKey)
                h = hashlib.sha1()
                h.update(self.serverID)
                h.update(sharedsecret)
                h.update(self.publicKey)
                serverid = self.packet.hexdigest(h)

                self.packet.sendCipher = encryption.AES128CFB8(sharedsecret)
                self.packet.recvCipher = encryption.AES128CFB8(sharedsecret)

                if not verifytoken == self.verifyToken:
                    self.disconnect("Verify tokens are not the same")
                    return False

                # begin Client login process
                if self.config["Proxy"]["online-mode"]:
                    r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s"
                                     "&serverId=%s" % (self.username, serverid))
                    if r.status_code == 200:
                        requestdata = r.json()
                        self.uuid = MCUUID(requestdata["id"])

                        if requestdata["name"] != self.username:
                            self.disconnect("Client's username did not match Mojang's record")
                            return False

                        for prop in requestdata["properties"]:
                            if prop["name"] == "textures":
                                self.skinBlob = prop["value"]
                                self.wrapper.proxy.skins[self.uuid.string] = self.skinBlob
                        self.properties = requestdata["properties"]
                    else:
                        self.disconnect("Proxy Client Session Error (HTTP Status Code %d)" % r.status_code)
                        return False
                    currentname = self.wrapper.getusernamebyuuid(self.uuid.string)
                    if currentname:
                        if currentname != self.username:
                            self.log.info("%s's client performed LOGON in with new name, falling back to %s",
                                          self.username, currentname)
                            self.username = currentname
                    self.serveruuid = self.wrapper.getuuidfromname(self.username)
                else:
                    # TODO: See if this can be accomplished via MCUUID
                    self.uuid = uuid.uuid3(uuid.NAMESPACE_OID, "OfflinePlayer:%s" % self.username)  # no space in name
                    self.log.debug("Client login with no proxymode - 'self.uuid = uuid.uuid3...'")

                #  This needs re-worked.
                # if self.config["Proxy"]["convert-player-files"]:  # Rename UUIDs accordingly
                #     if self.config["Proxy"]["online-mode"]:
                #         # Check player files, and rename them accordingly to offline-mode UUID
                #         worldname = self.wrapper.javaserver.worldname
                #         if not os.path.exists("%s/playerdata/%s.dat" % (worldname, self.serveruuid.string)):
                #             if os.path.exists("%s/playerdata/%s.dat" % (worldname, self.uuid.string)):
                #                 self.log.info("Migrating %s's playerdata file to proxy mode", self.username)
                #                 shutil.move("%s/playerdata/%s.dat" % (worldname, self.uuid.string),
                #                             "%s/playerdata/%s.dat" % (worldname, self.serveruuid.string))
                #                 with open("%s/.wrapper-proxy-playerdata-migrate" % worldname, "a") as f:
                #                     f.write("%s %s\n" % (self.uuid.string, self.serveruuid.string))
                #         # Change whitelist entries to offline mode versions
                #         if os.path.exists("whitelist.json"):
                #             with open("whitelist.json", "r") as f:
                #                 jsonwhitelistdata = json.loads(f.read())
                #             if jsonwhitelistdata:
                #                 for player in jsonwhitelistdata:
                #                     if not player["uuid"] == self.serveruuid.string and \
                #                                     player["uuid"] == self.uuid.string:
                #                         self.log.info("Migrating %s's whitelist entry to proxy mode", self.username)
                #                         jsonwhitelistdata.append({"uuid": self.serveruuid.string,
                #                                                   "name": self.username})
                #                         with open("whitelist.json", "w") as f:
                #                             f.write(json.dumps(jsonwhitelistdata))
                #                         self.wrapper.javaserver.console("whitelist reload")
                #                         with open("%s/.wrapper-proxy-whitelist-migrate" % worldname, "a") as f:
                #                             f.write("%s %s\n" % (self.uuid.string, self.serveruuid.string))

                self.ip = self.addr[0]

                # no idea what is special about version 26
                if self.clientversion > 26:
                    self.packet.setCompression(256)

                # player ban code.  Uses vanilla json files - In wrapper proxy mode, supports
                #       temp-bans (the "expires" field of the ban record is used!)
                #       Actaully, the vanilla server does too... there is just no command to fill it in.
                if self.proxy.isipbanned(self.ip):
                    self.log.info("Player %s tried to connect from banned ip: %s", self.username, self.ip)
                    self.state = HANDSHAKE
                    self.disconnect("Your address is IP-banned from this server!.")
                    return False
                if self.proxy.isuuidbanned(self.uuid.__str__()):
                    banreason = self.proxy.getuuidbanreason(self.uuid.__str__())  # was self.wrapper.proxy... ?
                    self.log.info("Banned player %s tried to connect:\n %s" % (self.username, banreason))
                    self.state = HANDSHAKE
                    self.disconnect("Banned: %s" % banreason)
                    return False

                self.inittheplayer()  # set up inventory and stuff
                self.log.info("%s's client LOGON occurred: (UUID: %s | IP: %s)",
                              self.username, self.uuid.string, self.addr[0])

                # Run the pre-login event
                if not self.wrapper.events.callevent("player.preLogin",
                                                     {
                                                      "player": self.username,
                                                      "online_uuid": self.uuid.string,
                                                      "offline_uuid": self.serveruuid.string,
                                                      "ip": self.addr[0]
                                                     }):
                    self.state = HANDSHAKE
                    self.disconnect("Login denied by a Plugin.")
                    return False

                # Put player object and client into server. (player login will be called later by mcserver.py)
                self.proxy.clients.append(self)

                if self.username not in self.wrapper.javaserver.players:
                    self.wrapper.javaserver.players[self.username] = Player(self.username, self.wrapper)

                # send login success to client
                self.packet.sendpkt(0x02, [_STRING, _STRING], (self.uuid.string, self.username))
                self.time_client_responded = time.time()
                self.state = PLAY

                t_keepalives = threading.Thread(target=self._keep_alive_tracker, kwargs={'playername': self.username})
                t_keepalives.daemon = True
                t_keepalives.start()

                self.connect_to_server()

                return False
            else:
                # Unknown packet for login; return to Handshake:
                self.state = HANDSHAKE
                return False

        elif self.state == STATUS:
            if pkid == 0x01:
                data = self.packet.readpkt([_LONG])
                # self.log.trace("(PROXY CLIENT) -> Received '0x01' Ping in STATUS mode")
                self.packet.sendpkt(0x01, [_LONG], [data[0]])
                self.state = HANDSHAKE
                return False
            elif pkid == 0x00:
                # self.log.trace("(PROXY CLIENT) -> Received '0x00' request (no payload) for list pckt in STATUS mode")
                sample = []
                for player in self.wrapper.javaserver.players:
                    playerobj = self.wrapper.javaserver.players[player]
                    if playerobj.username not in HIDDEN_OPS:
                        sample.append({"name": playerobj.username, "id": str(playerobj.mojangUuid)})
                    if len(sample) > 5:
                        break
                reported_version = self.serverversion
                reported_name = self.wrapper.javaserver.version

                if self.clientversion < mcpackets.PROTOCOL_1_8START:
                    motdtext = self.wrapper.javaserver.motd
                else:
                    motdtext = json.loads(processcolorcodes(self.wrapper.javaserver.motd.replace("\\", "")))
                self.MOTD = {
                    "description": motdtext,
                    "players": {
                        "max": int(self.wrapper.javaserver.maxPlayers),
                        "online": len(self.wrapper.javaserver.players),
                        "sample": sample
                    },
                    "version": {
                        "name": reported_name,
                        "protocol": reported_version
                    }
                }
                if self.wrapper.javaserver.serverIcon:  # add Favicon, if it exists
                    self.MOTD["favicon"] = self.wrapper.javaserver.serverIcon
                self.packet.sendpkt(0x00, [_STRING], [json.dumps(self.MOTD)])
                # after this, proxy waits for the expected PING to go back to Handshake mode
                return False
            else:
                # Unknown packet type, return to Handshake:
                self.state = HANDSHAKE
                self.abort = True
                return False

        elif self.state == HANDSHAKE:
            if pkid == 0x00:
                data = self.packet.readpkt([_VARINT, _STRING, _USHORT, _VARINT])  # "version|address|port|state"
                # self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state HANDSHAKE:\n%s", data)
                self.clientversion = data[0]
                self.serveraddressplayeruses = data[1]
                self.serverportplayeruses = data[2]
                requestedstate = data[3]

                if requestedstate == STATUS:
                    self.state = STATUS
                    return False  # wrapper will handle responses, so we do not pass this to the server.

                if requestedstate == LOGIN:
                    self._getclientpacketset()
                    # packetset needs defined before you can correctly administer a disconnect()

                    # TODO - coming soon: allow client connections despite lack of server connection
                    if self.serverversion == -1:
                        #  ... returns -1 to signal no server
                        self.disconnect("Proxy client was unable to connect to the server.")
                        return False
                    if not self.wrapper.javaserver.state == 2:
                        self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
                        return False
                    if mcpackets.PROTOCOL_1_9START < self.clientversion < mcpackets.PROTOCOL_1_9REL1:
                        self.disconnect("You're running an unsupported snapshot (protocol: %s)!" % self.clientversion)
                        return False

                    if self.serverversion == self.clientversion and requestedstate == LOGIN:
                        # login start...
                        self.state = LOGIN
                        self.lobbified = False
                        return True  # packet passes to server, which will also switch to Login

                    if self.clientversion == 94:  # secret lobby login 15w51b

                        # lobbified state does not interact with server
                        self.lobbified = True
                        self.state = LOGIN
                        return False

                    if self.serverversion != self.clientversion:
                        self.disconnect("You're not running the same Minecraft version as the server!")
                        return False

                    self.disconnect("Your game is mis-behaving!! Looks like you have the same version as the server,"
                                    " but are not trying to login!?")
                    return False

                self.disconnect("Invalid client state request for handshake: '%d'" % data["state"])
                return False

        # This is a work in progress; not used presently
        elif self.state == LOBBY:
            if pkid == self.pktSB.KEEP_ALIVE:
                if self.serverversion < mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_INT])
                else:  # self.version >= mcpackets.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_VARINT])
                # self.log.trace("(PROXY CLIENT) -> Received LOBBY KEEP_ALIVE from client:\n%s", data)
                if data[0] == self.keepalive_val:
                    self.time_client_responded = time.time()
                return False
            elif pkid == self.pktSB.CLICK_WINDOW:  # click window
                self.packet.sendpkt(0x33, [_INT, _UBYTE, _UBYTE, _STRING], [1, 3, 0, 'default'])
                self.packet.sendpkt(0x33, [_INT, _UBYTE, _UBYTE, _STRING], [0, 3, 0, 'default'])
                self.state = PLAY
                self.connect_to_server()

            else:
                return False  # No server available

        else:
            self.log.error("(PROXY CLIENT) Unknown gamestate encountered: %s", self.state)
            return False

    def handle(self):
        t = threading.Thread(target=self.flush, args=())
        t.daemon = True
        t.start()

        while not self.abort:
            if self.abort:
                self.close()
                break

            try:
                pkid, original = self.packet.grabPacket()
            except EOFError:
                # This is not an error.. It means the client disconnected and is not sending packet stream anymore
                self.log.debug("Client Packet stream ended (EOF)")
                self.abort = True
                self.close()
                break
            except socket.error:  # Bad file descriptor occurs anytime a socket is closed.
                self.log.debug("Failed to grab packet [CLIENT] socket closed; bad file descriptor")
                self.abort = True
                self.close()
                break
            except Exception as e:
                # anything that gets here is a bona-fide error we need to become aware of
                self.log.error("Failed to grab packet [CLIENT] (%s):", e)
                self.abort = True
                self.close()
                break

            # send packet if server available and parsing passed.
            # already tested - Python will not attempt eval of self.server.state if self.server is False
            if self.parse(pkid) and self.server and self.server.state == 3:
                self.server.packet.sendRaw(original)

    def _keep_alive_tracker(self, playername):
        # send keep alives to client and send client settings to server.
        while not self.abort:
            if self.abort is True:
                self.log.debug("Closing Keep alive tracker thread for %s's client.", playername)
                self.close()
                break
            time.sleep(1)
            while self.state in (PLAY, LOBBY) and not self.abort:

                # client expects < 20sec
                if time.time() - self.time_server_pinged > 5:
                    self.keepalive_val = random.randrange(0, 99999)
                    if self.clientversion > mcpackets.PROTOCOL_1_8START:
                        self.packet.sendpkt(self.pktCB.KEEP_ALIVE, [_VARINT], [self.keepalive_val])
                    else:
                        # pre- 1.8
                        self.packet.sendpkt(0x00, [_INT], [self.keepalive_val])
                    self.time_server_pinged = time.time()

                # ckeck for active client keep alive status:
                # server can allow up to 30 seconds for response
                if time.time() - self.time_client_responded > 25 and not self.abort:
                    self.state = HANDSHAKE
                    self.disconnect("Client closed due to lack of keepalive response")
                    self.log.debug("Closing %s's client thread due to lack of keepalive response", playername)
                    self.close()
        self.state = HANDSHAKE
        self.log.debug("Received abort signal - Closing %s's client thread", playername)
        self.close()
