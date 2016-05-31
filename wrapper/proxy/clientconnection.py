# -*- coding: utf-8 -*-

# py3 compliant syntax

import threading
import time
import json
import hashlib
import uuid
import shutil
import os
import random

import utils.encryption as encryption
import proxy.mcpacket as mcpacket

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

try:  # Manually define an xrange builtin that works identically on both (to take advantage of xrange's speed in 2)
    xxrange = xrange
except NameError:
    xxrange = range

UNIVERSAL_CONNECT = False  # will tell the clientconnection not to disconnect dissimilar clients
HIDDEN_OPS = ["SurestTexas00", "BenBaptist"]

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
        self._refresh_server_version()

        self.abort = False
        self.time_server_pinged = time.time()
        self.time_client_responded = time.time()
        self.keepalive_val = 0
        self.server = None  # Proxy ServerConnection() (not the javaserver)
        self.isServer = False
        self.isLocal = True
        self.server_temp = None

        # UUIDs - all should use MCUUID unless otherwise specified
        self.uuid = None  # this is intended to be the client UUID
        self.serverUuid = None  # Server UUID - which Could be the local offline UUID.
        self.mojangUuid = None  # Online UUID (should be same as client) - included for now to help refactoring
        self.address = None
        self.ip = None  # this will gather the client IP for use by player.py
        self.serveraddressplayeruses = None
        self.serverportplayeruses = None

        self.state = ClientState.HANDSHAKE

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
        self.servereid = None
        self.bedposition = None

        for i in xxrange(46):  # there are 46 items 0-45 in 1.9 (shield) versus 45 (0-44) in 1.8 and below.
            self.inventory[i] = None
        self.lastitem = None

    @property
    def version(self):
        return self.clientversion

    def send(self, packetid, xpr, payload):  # not supported. no docstring. For old code compatability purposes only.
        self.log.debug("deprecated client.send() called.  Use client.packet.sendpkt for best performance.")
        self.packet.send(packetid, xpr, payload)
        pass

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
            self.server_temp = ServerConnection(self, self.wrapper, ip, port)
            try:
                self.server_temp.connect()
                self.server.close(kill_client=False)
                self.server.client = None
                self.server = self.server_temp
            except OSError:
                self.server_temp.close(kill_client=False)
                self.server_temp = None
                if self.state == ClientState.PLAY:
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
            if UNIVERSAL_CONNECT:
                self.server.packet.sendpkt(0x00, [_VARINT, _STRING, _USHORT, _VARINT],
                                           (self.wrapper.javaserver.protocolVersion, "localhost",
                                            self.config["Proxy"]["server-port"], 2))
            else:
                self.server.packet.sendpkt(0x00, [_VARINT, _STRING, _USHORT, _VARINT],
                                           (self.clientversion, "localhost", self.config["Proxy"]["server-port"], 2))
        self.server.packet.sendpkt(0x00, [_STRING], [self.username])

        if self.clientversion > mcpacket.PROTOCOL_1_8START:  # anti-rain hack for cross server lobby return connections
            if self.config["Proxy"]["online-mode"]:
                self.packet.sendpkt(self.pktCB.CHANGE_GAME_STATE, [_UBYTE, _FLOAT], (1, 0))
                pass
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

    def disconnect(self, message):
        try:
            message = json.loads(message["string"])
        except TypeError:  # optionally use json
            pass
        except ValueError:
            pass

        if self.state == ClientState.PLAY:
            self.packet.sendpkt(self.pktCB.DISCONNECT, [_JSON], [message])
        else:
            self.packet.sendpkt(0x00, [_JSON], [{"text": message, "color": "red"}])

        time.sleep(1)
        self.close()

    def flush(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket.error:
                self.log.debug("clientconnection socket closed (bad file descriptor), closing flush..")
                self.abort = True
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
        # Get serverversion for mcpacket use
        try:
            self.serverversion = self.wrapper.javaserver.protocolVersion
        except AttributeError:
            # Default to 1.8 if no server is running
            # This can be modified to any version
            self.serverversion = 47

        # Determine packet types - currently 1.8 is the lowest version supported.
        if mcpacket.Server194.end() >= self.serverversion >= mcpacket.Server194.start():  # 1.9.4
            self.pktSB = mcpacket.Server194
            self.pktCB = mcpacket.Client194
        elif mcpacket.Server19.end() >= self.serverversion >= mcpacket.Server19.start():  # 1.9 - 1.9.3 Pre 3
            self.pktSB = mcpacket.Server19
            self.pktCB = mcpacket.Client19
        else:  # 1.8 default
            self.pktSB = mcpacket.Server18
            self.pktCB = mcpacket.Client18

    def parse(self, pkid):  # server - bound parse ("Client" class connection)
        if self.state == ClientState.PLAY:
            if pkid == self.pktSB.KEEP_ALIVE:
                if self.serverversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_INT])
                    # ("int:payload")
                else:  # self.version >= mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_VARINT])
                    # ("varint:payload")
                self.log.trace("(PROXY CLIENT) -> Received KEEP_ALIVE from client:\n%s", data)
                if data[0] == self.keepalive_val:
                    self.time_client_responded = time.time()

                # Arbitrary place for this.  It works since Keep alives will be received periodically
                # Needed to move out of the _keep_alive_tracker thread

                # I have no idea what the purpose of parsing these and resending them is (ask the ben bot?)
                if self.clientSettings and not self.clientSettingsSent:
                    if self.clientversion < mcpacket.PROTOCOL_1_8START:
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
                    elif mcpacket.PROTOCOL_1_7_9 < self.clientversion < mcpacket.PROTOCOL_1_9START:
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
                self.log.trace("(PROXY CLIENT) -> Parsed CHAT_MESSAGE packet with client state PLAY:\n%s", data)

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
                if self.clientversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _DOUBLE, _BOOL])
                    # ("double:x|double:y|double:yhead|double:z|bool:on_ground")
                elif self.clientversion >= mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _NULL, _DOUBLE, _BOOL])
                    # ("double:x|double:y|double:z|bool:on_ground")
                else:
                    data = [0, 0, 0, 0]
                self.position = (data[0], data[1], data[3])  # skip 1.7.10 and lower protocol yhead args
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSITION packet:\n%s", data)

            elif pkid == self.pktSB.PLAYER_POSLOOK:  # player position and look
                if self.clientversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _DOUBLE, _FLOAT, _FLOAT, _BOOL])
                else:
                    data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _FLOAT, _FLOAT, _BOOL])
                # ("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
                self.position = (data[0], data[1], data[4])
                self.head = (data[4], data[5])
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSLOOK packet:\n%s", data)

            elif pkid == self.pktSB.TELEPORT_CONFIRM:
                # don't interfere with this and self.pktSB.PLAYER_POSLOOK... doing so will glitch the client
                data = self.packet.readpkt([_VARINT])
                self.log.trace("(SERVER-BOUND) -> Client sent TELEPORT_CONFIRM packet:\n%s", data)

            elif pkid == self.pktSB.PLAYER_LOOK:  # Player Look
                data = self.packet.readpkt([_FLOAT, _FLOAT, _BOOL])
                # ("float:yaw|float:pitch|bool:on_ground")
                self.head = (data[0], data[1])
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_LOOK packet:\n%s", data)

            elif pkid == self.pktSB.PLAYER_DIGGING:  # Player Block Dig
                # if not self.isLocal: disable these for now and come back to it later - I think these are for lobbies.
                # such a construct should probably be done at the gamestate level.
                #     return True

                if self.clientversion < mcpacket.PROTOCOL_1_7:
                    data = None
                    position = data
                elif mcpacket.PROTOCOL_1_7 <= self.clientversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_BYTE, _INT, _UBYTE, _INT, _BYTE])
                    # "byte:status|int:x|ubyte:y|int:z|byte:face")
                    position = (data[1], data[2], data[3])
                    self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_DIGGING packet:\n%s", data)
                else:
                    data = self.packet.readpkt([_BYTE, _POSITION, _NULL, _NULL, _BYTE])
                    # "byte:status|position:position|byte:face")
                    position = data[1]
                    self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_DIGGING packet:\n%s", data)
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

                if self.clientversion < mcpacket.PROTOCOL_1_7:
                    data = None
                    position = data

                elif mcpacket.PROTOCOL_1_7 <= self.clientversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_INT, _UBYTE, _INT, _BYTE, _SLOT_NO_NBT, _REST])
                    # "int:x|ubyte:y|int:z|byte:face|slot:item")  _REST includes cursor positions x-y-z
                    position = (data[0], data[1], data[2])

                    # just FYI, notchian servers have been ignoring this field ("item")
                    # for a long time, using server inventory instead.
                    helditem = data[4]  # "item" - _SLOT

                elif mcpacket.PROTOCOL_1_8START <= self.clientversion < mcpacket.PROTOCOL_1_9REL1:
                    data = self.packet.readpkt([_POSITION, _NULL, _NULL, _BYTE, _SLOT, _REST])
                    # "position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                    # helditem = data["item"]  -available in packet, but server ignores it (we should too)!
                    # starting with 1.8, the server maintains inventory also.
                    position = data[0]

                else:  # self.clientversion >= mcpacket.PROTOCOL_1_9REL1:
                    data = self.packet.readpkt([_POSITION, _NULL, _NULL, _VARINT, _VARINT, _BYTE, _BYTE, _BYTE])
                    # "position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                    hand = data[4]  # used to be the spot occupied by "slot"
                    position = data[0]

                # Face and Position exist in all version protocols at this point
                clickposition = position
                face = data[3]

                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_BLOCK_PLACEMENT packet:\n%s", data)

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
                self.log.trace("(PROXY CLIENT) -> Parsed USE_ITEM packet:\n%s", data)
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
                self.log.trace("(PROXY CLIENT) -> Parsed HELD_ITEM_CHANGE packet:\n%s", slot)
                if 9 > slot[0] > -1:
                    self.slot = slot[0]
                else:
                    return False

            elif pkid == self.pktSB.PLAYER_UPDATE_SIGN:  # player update sign
                if self.clientversion < mcpacket.PROTOCOL_1_8START:
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
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_UPDATE_SIGN packet:\n%s", data)
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
                if self.clientversion <= mcpacket.PROTOCOL_1_7_9:
                    data = self.packet.readpkt([_STRING, _BYTE, _BYTE, _BOOL, _BYTE, _BOOL, _NULL, _NULL])
                    # "string:locale|byte:view_distance|byte:chat_flags|bool:chat_colors|
                    # byte:difficulty|bool:show_cape")
                elif mcpacket.PROTOCOL_1_7_9 < self.clientversion < mcpacket.PROTOCOL_1_9START:  # "1.8"
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
                self.log.trace("(PROXY CLIENT) -> Parsed CLIENT_SETTINGS packet:\n%s", settingsdict)

            elif pkid == self.pktSB.CLICK_WINDOW:  # click window
                if self.clientversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.readpkt([_BYTE, _SHORT, _BYTE, _SHORT, _BYTE, _SLOT_NO_NBT])
                    # ("byte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
                elif mcpacket.PROTOCOL_1_8START < self.clientversion < mcpacket.PROTOCOL_1_9START:
                    data = self.packet.readpkt([_UBYTE, _SHORT, _BYTE, _SHORT, _BYTE, _SLOT])
                    # ("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
                elif mcpacket.PROTOCOL_1_9START <= self.clientversion < mcpacket.PROTOCOL_MAX:
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

                self.log.trace("(PROXY CLIENT) -> Parsed CLICK_WINDOW packet:\n%s", datadict)

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
                self.log.trace("(PROXY CLIENT) -> Parsed SPECTATE packet:\n%s", data)
                for client in self.proxy.clients:
                    if data[0].hex == client.uuid.hex:
                        self.server.packet.sendpkt(self.pktSB.SPECTATE, [_UUID], [client.serverUuid])
                        return False
            else:
                return True  # no packet parsed in wrapper
            return True  # packet parsed, no rejects or changes
        elif self.state == ClientState.LOGIN:
            if pkid == 0x00:  # login start packet
                data = self.packet.readpkt([_STRING, _NULL])
                # ("string:username")
                self.username = data[0]
                if self.config["Proxy"]["online-mode"]:
                    if self.wrapper.javaserver.protocolVersion < 6:  # 1.7.x versions
                        self.packet.sendpkt(0x01, [_STRING, _BYTEARRAY_SHORT, _BYTEARRAY_SHORT],
                                            (self.serverID, self.publicKey, self.verifyToken))
                    else:
                        self.packet.sendpkt(0x01, [_STRING, _BYTEARRAY, _BYTEARRAY],
                                            (self.serverID, self.publicKey, self.verifyToken))
                else:
                    self.connect_to_server()
                    self.uuid = self.wrapper.getuuidfromname("OfflinePlayer:%s" % self.username)  # MCUUID object
                    self.serverUuid = self.wrapper.getuuidfromname("OfflinePlayer:%s" % self.username)  # MCUUID object
                    self.packet.sendpkt(0x02, [_STRING, _STRING], (self.uuid.string, self.username))
                    self.state = ClientState.PLAY
                    self.log.info("%s's client LOGON in (IP: %s)", self.username, self.addr[0])
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state LOGIN: \n%s", data)
                return False
            elif pkid == 0x01:
                if self.wrapper.javaserver.protocolVersion < 6:
                    data = self.packet.readpkt([_BYTEARRAY_SHORT, _BYTEARRAY_SHORT])
                    # ("bytearray_short:shared_secret|bytearray_short:verify_token")
                else:
                    data = self.packet.readpkt([_BYTEARRAY, _BYTEARRAY])
                    # "bytearray:shared_secret|bytearray:verify_token")
                self.log.trace("(PROXY CLIENT) -> Parsed 0x01 ENCRYPTION RESPONSE packet with client state LOGIN:\n%s",
                               data)

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
                    newusername = self.wrapper.getusernamebyuuid(self.uuid.string)
                    if newusername:
                        if newusername != self.username:
                            self.log.info("%s's client performed LOGON in with new name, falling back to %s",
                                          self.username, newusername)
                            self.username = newusername
                else:
                    # TODO: See if this can be accomplished via MCUUID
                    self.uuid = uuid.uuid3(uuid.NAMESPACE_OID, "OfflinePlayer:%s" % self.username)  # no space in name

                if self.config["Proxy"]["convert-player-files"]:  # Rename UUIDs accordingly
                    if self.config["Proxy"]["online-mode"]:
                        # Check player files, and rename them accordingly to offline-mode UUID
                        worldname = self.wrapper.javaserver.worldName
                        if not os.path.exists("%s/playerdata/%s.dat" % (worldname, self.serverUuid.string)):
                            if os.path.exists("%s/playerdata/%s.dat" % (worldname, self.uuid.string)):
                                self.log.info("Migrating %s's playerdata file to proxy mode", self.username)
                                shutil.move("%s/playerdata/%s.dat" % (worldname, self.uuid.string),
                                            "%s/playerdata/%s.dat" % (worldname, self.serverUuid.string))
                                with open("%s/.wrapper-proxy-playerdata-migrate" % worldname, "a") as f:
                                    f.write("%s %s\n" % (self.uuid.string, self.serverUuid.string))
                        # Change whitelist entries to offline mode versions
                        if os.path.exists("whitelist.json"):
                            with open("whitelist.json", "r") as f:
                                jsonwhitelistdata = json.loads(f.read())
                            if jsonwhitelistdata:
                                for player in jsonwhitelistdata:
                                    if not player["uuid"] == self.serverUuid.string and \
                                                    player["uuid"] == self.uuid.string:
                                        self.log.info("Migrating %s's whitelist entry to proxy mode", self.username)
                                        jsonwhitelistdata.append({"uuid": self.serverUuid.string,
                                                                  "name": self.username})
                                        # TODO I think the indent on this is wrong... looks like it will overwrite with
                                        # each record
                                        # either that, or it is making an insane number of re-writes (each time a record
                                        #  is processed)
                                        # since you can't append a json file like this, I assume the whole file should
                                        # be written at once,
                                        # after all the records are appended
                                        with open("whitelist.json", "w") as f:
                                            f.write(json.dumps(jsonwhitelistdata))
                                        self.wrapper.javaserver.console("whitelist reload")
                                        with open("%s/.wrapper-proxy-whitelist-migrate" % worldname, "a") as f:
                                            f.write("%s %s\n" % (self.uuid.string, self.serverUuid.string))

                self.serverUuid = self.wrapper.getuuidfromname("OfflinePlayer:%s" % self.username)
                self.ip = self.addr[0]
                playerwas = str(self.username)
                uuidwas = self.uuid.string  # TODO somewhere between HERE and ...
                self.log.debug("Value - playerwas: %s", playerwas)
                self.log.debug("Value - uuidwas: %s", uuidwas)
                if self.clientversion > 26:
                    self.packet.setCompression(256)

                # player ban code!  Uses vanilla json files - In wrapper proxy mode, supports
                #       temp-bans (the "expires" field of the ban record is used!)

                if self.proxy.isipbanned(self.addr[0]):  # TODO make sure ban code is not using player objects
                    self.disconnect("Your address is IP-banned from this server!.")
                    return False
                testforban = self.proxy.isuuidbanned(uuidwas)
                self.log.debug("Value - testforban: %s", testforban)
                if self.proxy.isuuidbanned(uuidwas):  # TODO ...HERE, the player stuff becomes "None" (was self.uuid)
                    banreason = self.wrapper.proxy.getuuidbanreason(uuidwas)  # TODO- which is why I archived the name
                    # and UUID strings
                    # maybe because I got these two lines reversed? disc and then log.info?
                    self.disconnect("Banned: %s" % banreason)
                    self.log.info("Banned player %s tried to connect:\n %s" % (playerwas, banreason))
                    return False

                if not self.wrapper.events.callevent("player.preLogin", {
                    "player": self.username,
                    "online_uuid": self.uuid.string,
                    "offline_uuid": self.serverUuid.string,
                    "ip": self.addr[0]
                }):
                    self.disconnect("Login denied by a Plugin.")
                    return False
                self.packet.sendpkt(0x02, [_STRING, _STRING], (self.uuid.string, self.username))
                self.time_client_responded = time.time()
                self.state = ClientState.PLAY

                # Put player object into server! (player login will be called later by mcserver.py)
                if self.username not in self.wrapper.javaserver.players:
                    self.wrapper.javaserver.players[self.username] = Player(self.username, self.wrapper)

                # TODO sadsadas
                # This will keep client connected regardless of server status (unless we explicitly disconnect it)
                t_keepalives = threading.Thread(target=self._keep_alive_tracker, kwargs={'playername': self.username})
                t_keepalives.daemon = True
                t_keepalives.start()

                self.connect_to_server()

                self.log.info("%s's client LOGON occurred: (UUID: %s | IP: %s)",
                              self.username, self.uuid.string, self.addr[0])
                return False
            else:
                # Unknown packet for login; return to Handshake:
                self.state = ClientState.HANDSHAKE
                return False

        elif self.state == ClientState.STATUS:
            if pkid == 0x01:
                data = self.packet.readpkt([_LONG])
                self.log.trace("(PROXY CLIENT) -> Received '0x01' Ping in STATUS mode")
                self.packet.sendpkt(0x01, [_LONG], [data[0]])
                self.state = ClientState.HANDSHAKE
                return False
            elif pkid == 0x00:
                self.log.trace("(PROXY CLIENT) -> Received '0x00' request (no payload) for list packet in STATUS mode")
                sample = []
                for i in self.wrapper.javaserver.players:
                    player = self.wrapper.javaserver.players[i]
                    if player.username not in HIDDEN_OPS:
                        sample.append({"name": player.username, "id": str(player.mojangUuid)})
                    if len(sample) > 5:
                        break
                if UNIVERSAL_CONNECT:
                    reported_version = self.clientversion
                    self.log.debug("(During status request, client reported it's version as: %s", self.clientversion)
                    reported_name = "%s (Compatibility mode)" % self.wrapper.javaserver.version
                else:
                    reported_version = self.wrapper.javaserver.protocolVersion
                    reported_name = self.wrapper.javaserver.version
                self.MOTD = {
                    "description": json.loads(processcolorcodes(self.wrapper.javaserver.motd.replace("\\", ""))),
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
                return False
            else:
                # Unknown packet type, return to Handshake:
                self.state = ClientState.HANDSHAKE
                return False

        elif self.state == ClientState.HANDSHAKE:
            if pkid == 0x00:
                data = self.packet.readpkt([_VARINT, _STRING, _USHORT, _VARINT])
                # ("varint:version|string:address|ushort:port|varint:state")
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state HANDSHAKE:\n%s", data)
                self.clientversion = data[0]
                self._refresh_server_version()
                self.serveraddressplayeruses = data[1]
                self.serverportplayeruses = data[2]

                if not self.wrapper.javaserver.state == 2:  # TODO - one day, allow connection despite this
                    self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
                    return False
                if self.wrapper.javaserver.protocolVersion == -1:  # TODO make sure wrapper.mcserver.protocolVersion
                    #  ... returns -1 to signal no server
                    self.disconnect("Proxy client was unable to connect to the server.")
                    return False
                if self.serverversion == self.clientversion and data[3] == ClientState.LOGIN:  # TODO login VERSION code
                    # login start...
                    self.state = ClientState.LOGIN
                    return True  # packet passes to server, which will also switch to Login
                if data[3] == ClientState.STATUS:
                    self.state = ClientState.STATUS
                    return False  # wrapper will handle responses, so we do not pass this to the server.
                if self.serverversion != self.clientversion:
                    if mcpacket.PROTOCOL_1_9START < self.clientversion < mcpacket.PROTOCOL_1_9REL1:
                        self.disconnect("You're running an unsupported or outdated snapshot (%s)!" % self.clientversion)
                        return False
                    if UNIVERSAL_CONNECT:
                        pass  # TODO place holder for future feature
                    else:
                        self.disconnect("You're not running the same Minecraft version as the server!")
                        return False
                self.disconnect("Invalid client state request for handshake: '%d'" % data["state"])
                return False
        else:
            self.log.error("(PROXY CLIENT) Unknown gamestate encountered: %s", self.state)
            return False

    def handle(self):
        t = threading.Thread(target=self.flush, args=())
        t.daemon = True
        t.start()
        try:
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
                if self.parse(pkid) and self.server:
                    if self.server.state == 3:  # 3 is also serverconnection.py's PLAY state
                        self.server.packet.sendRaw(original)
        except Exception as ex:
            self.log.exception("Error in the [PROXY] <- [CLIENT] handle (%s):", ex)

    def _keep_alive_tracker(self, playername):
        # send keep alives to client and send client settings to server.
        while not self.abort:
            if self.abort is True:
                self.log.debug("Closing Keep alive tracker thread for %s's client.", playername)
                self.close()
                break
            time.sleep(1)
            while self.state == ClientState.PLAY:
                if time.time() - self.time_server_pinged > 5:  # client expects < 20sec
                    self.keepalive_val = random.randrange(0, 99999)
                    if self.clientversion > mcpacket.PROTOCOL_1_8START:
                        self.packet.sendpkt(self.pktCB.KEEP_ALIVE, [_VARINT], [self.keepalive_val])
                    else:
                        # _OLD_ MC version
                        self.packet.sendpkt(0x00, [_INT], [self.keepalive_val])
                    self.time_server_pinged = time.time()
                # ckeck for active client keep alive status:
                if time.time() - self.time_client_responded > 25:  # server can allow up to 30 seconds for response
                    self.state = ClientState.HANDSHAKE
                    self.log.debug("Closing %s's client thread due to lack of keepalive response", playername)
                    self.close()


class ClientState:
    """
    This class represents proxy Client states
    """

    HANDSHAKE = 0  # this is the default mode of a server awaiting packets from a client out in the ether..
    # client will send a handshake (a 0x00 packet WITH payload) asking for STATUS or LOGIN mode
    STATUS = 1
    # Status mode will await either a ping (0x01) containing a unique long int and will respond with same integer.
    #     ... OR if it receives a 0x00 packet (with no payload), that signals server (client.py) to send
    #         the MOTD json response packet.  This aspect was badly handled in pervious wrapper versions,
    #         resulting in the dreaded "zero length packet" errors.
    #         The ping will follow the 0x00 request for json response.  The ping will set wrapper/server
    #         back to HANDSHAKE mode (to await next handshake).
    LOGIN = 2
    #
    PLAY = 3

    def __init__(self):
        pass
