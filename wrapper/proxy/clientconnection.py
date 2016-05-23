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


class Client:
    def __init__(self, sock, addr, wrapper, publickey, privatekey, proxy):
        """
        Client receives "SERVER BOUND" packets from client.  These are what get parsed (SERVER BOUND format).
        'server.packet.send' - sends a packet to the server (use SERVER BOUND packet format)
        'self.packet.send' - sends a packet back to the client (use CLIENT BOUND packet format)

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
        self.windowCounter = 2
        self.properties = {}
        self.clientSettings = False
        self.clientSettingsSent = False
        self.skinBlob = {}

        for i in xxrange(45):
            self.inventory[i] = None

    @property
    def version(self):
        return self.clientversion

    def send(self, packetid, xpr, payload):  # not supported... no docstring. For backwards compatability purposes only.
        self.log.debug("deprecated client.send() called (by a plugin)")
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
                    self.packet.send(
                        self.pktCB.CHAT_MESSAGE,
                        "string",
                        ("""{"text": "Could not connect to that server!", "color": "red", "bold": "true"}""",
                         0))
                else:
                    self.packet.send(
                        0x00, "string",
                        ("""{"text": "Could not connect to that server!", "color": "red", "bold": "true"}""",
                         ))
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
            self.server.packet.send(0x00, "varint|string|ushort|varint", (self.clientversion, payload,
                                                                          self.config["Proxy"]["server-port"], 2))
        else:
            if UNIVERSAL_CONNECT:
                self.server.packet.send(0x00, "varint|string|ushort|varint",
                                        (self.wrapper.javaserver.protocolVersion, "localhost",
                                         self.config["Proxy"]["server-port"], 2))
            else:
                self.server.packet.send(0x00, "varint|string|ushort|varint",
                                        (self.clientversion, "localhost", self.config["Proxy"]["server-port"], 2))
        self.server.packet.send(0x00, "string", (self.username,))

        if self.clientversion > mcpacket.PROTOCOL_1_8START:  # anti-rain hack for cross server lobby return connections
            if self.config["Proxy"]["online-mode"]:
                self.packet.send(self.pktCB.CHANGE_GAME_STATE, "ubyte|float", (1, 0))
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
        except:  # optionally use json
            pass

        if self.state == ClientState.PLAY:
            self.packet.send(self.pktCB.DISCONNECT, "json", (message,))
        else:
            self.packet.send(0x00, "json", ({"text": message, "color": "red"},))

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

    def editSign(self, position, line1, line2, line3, line4):
        self.server.packet.send(self.pktSB.PLAYER_UPDATE_SIGN, "position|string|string|string|string",
                                (position, line1, line2, line3, line4))

    def message(self, string):
        self.server.packet.send(self.pktSB.CHAT_MESSAGE, "string", (string,))

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
                    data = self.packet.read("int:payload")
                else:  # self.version >= mcpacket.PROTOCOL_1_8START:
                    data = self.packet.read("varint:payload")
                self.log.trace("(PROXY CLIENT) -> Received KEEP_ALIVE from client:\n%s", data)
                if data["payload"] == self.keepalive_val:
                    self.time_client_responded = time.time()
                # Arbitrary place for this.  It works since Keep alives will be received periodically
                # Needed to move out of the _keep_alive_tracker thread
                if self.clientSettings and not self.clientSettingsSent:
                    if self.clientversion < mcpacket.PROTOCOL_1_9START:
                        self.server.packet.send(self.pktSB.CLIENT_SETTINGS, "string|byte|byte|bool|ubyte", (
                            self.clientSettings["locale"],
                            self.clientSettings["view_distance"],
                            self.clientSettings["chat_mode"],
                            self.clientSettings["chat_colors"],
                            self.clientSettings["displayed_skin_parts"]
                        ))
                    else:
                        self.server.packet.send(self.pktSB.CLIENT_SETTINGS, "string|byte|varint|bool|ubyte|varint", (
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
                data = self.packet.read("string:message")
                self.log.trace("(PROXY CLIENT) -> Parsed CHAT_MESSAGE packet with client state PLAY:\n%s", data)
                if data is None:
                    return False
                try:  # TODO - OMG A huge try-except!
                    chatmsg = data["message"]
                    if not self.isLocal and chatmsg == "/lobby":
                        self.server.close(reason="Lobbification", kill_client=False)
                        self.address = None
                        self.connect_to_server()
                        self.isLocal = True
                        return False
                    if not self.isLocal:
                        return True
                    payload = self.wrapper.events.callevent("player.rawMessage", {
                        "player": self.getPlayerObject(),
                        "message": data["message"]
                    })
                    if not payload:
                        return False
                    if type(payload) == str:
                        chatmsg = payload
                    if chatmsg[0] == "/":
                        if self.wrapper.events.callevent("player.runCommand", {
                            "player": self.getPlayerObject(),
                            "command": chatmsg.split(" ")[0][1:].lower(),
                            "args": chatmsg.split(" ")[1:]
                        }):
                            self.message(chatmsg)
                            return False
                        return
                    self.message(chatmsg)
                    return False
                except Exception as e:
                    self.log.exception("Formulating CHAT_MESSAGE failed (%s)", e)
                return True

            elif pkid == self.pktSB.PLAYER_POSITION:  # player position
                data = self.packet.read("double:x|double:y|double:z|bool:on_ground")
                self.position = (data["x"], data["y"], data["z"])
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSITION packet:\n%s", data)
                return True

            elif pkid == self.pktSB.PLAYER_POSLOOK:  # player position and look
                data = self.packet.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
                self.position = (data["x"], data["y"], data["z"])
                self.head = (data["yaw"], data["pitch"])
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSLOOK packet:\n%s", data)
                return True

            elif pkid == self.pktSB.PLAYER_LOOK:  # Player Look
                data = self.packet.read("float:yaw|float:pitch|bool:on_ground")
                yaw, pitch = data["yaw"], data["pitch"]
                self.head = (yaw, pitch)
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_LOOK packet:\n%s", data)
                return True

            elif pkid == self.pktSB.PLAYER_DIGGING:  # Player Block Dig
                if not self.isLocal:
                    return True
                if self.clientversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.read("byte:status|int:x|ubyte:y|int:z|byte:face")
                    position = (data["x"], data["y"], data["z"])
                    self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_DIGGING packet:\n%s", data)
                else:
                    data = self.packet.read("byte:status|position:position|byte:face")
                    position = data["position"]
                    self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_DIGGING packet:\n%s", data)
                if data is None:
                    return False
                # finished digging
                if data["status"] == 2:
                    if not self.wrapper.events.callevent("player.dig", {
                        "player": self.getPlayerObject(),
                        "position": position,
                        "action": "end_break",
                        "face": data["face"]
                    }):
                        return False  # stop packet if  player.dig returns False
                # started digging
                if data["status"] == 0:
                    if self.gamemode != 1:
                        if not self.wrapper.events.callevent("player.dig", {
                            "player": self.getPlayerObject(),
                            "position": position,
                            "action": "begin_break",
                            "face": data["face"]
                        }):
                            return False
                    else:
                        if not self.wrapper.events.callevent("player.dig", {
                            "player": self.getPlayerObject(),
                            "position": position,
                            "action": "end_break",
                            "face": data["face"]
                        }):
                            return False
                if data["status"] == 5 and data["face"] == 255:
                    if self.position != (0, 0, 0):
                        playerpos = self.position
                        if not self.wrapper.events.callevent("player.interact", {
                            "player": self.getPlayerObject(),
                            "position": playerpos,
                            "action": "finish_using"
                        }):
                            return False
                return True

            elif pkid == self.pktSB.PLAYER_BLOCK_PLACEMENT:  # Player Block Placement
                player = self.getPlayerObject()
                # curposx = False  # pre- 1.8 - not used by wrapper
                # curposy = False
                # curposz = False
                hand = 0  # main hand

                helditem = player.getHeldItem()
                if not self.isLocal:
                    return True
                if self.clientversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.read("int:x|ubyte:y|int:z|byte:face|slot:item")
                    position = (data["x"], data["y"], data["z"])
                    # just FYI, notchian servers have been ignoring this field
                    # for a long time, using server inventory instead.
                    helditem = data["item"]
                else:
                    if self.clientversion >= mcpacket.PROTOCOL_1_9REL1:
                        data = self.packet.read(
                            "position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                        hand = data["hand"]
                    else:
                        data = self.packet.read(
                            "position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                        helditem = data["item"]
                    position = data["Location"]
                    # curposx = data["CurPosX"]
                    # curposy = data["CurPosY"]
                    # curposz = data["CurPosZ"]
                # Face and Position exist in all version protocols at this point
                clickposition = data["Location"]
                face = data["face"]
                # all variables populated for all versions for:
                # position, face, helditem, hand, and all three cursor positions
                # (x, y, z)

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
                        "action": "useitem"
                    }):
                        return False

                self.lastplacecoords = position
                if not self.wrapper.events.callevent("player.place", {"player": player,
                                                                      "position": position,
                                                                      "clickposition": clickposition,
                                                                      "hand": hand,
                                                                      "item": helditem}):
                    return False

                if self.server.state != ClientState.PLAY:  # PLAY is some in both
                    return False
                return True

            elif pkid == self.pktSB.USE_ITEM:
                if self.isLocal is not True:
                    return True
                data = self.packet.read("rest:pack")
                self.log.trace("(PROXY CLIENT) -> Parsed USE_ITEM packet:\n%s", data)
                player = self.getPlayerObject()
                position = self.lastplacecoords
                # helditem = player.getHeldItem()
                # if helditem is not None:
                if "pack" in data:
                    if data["pack"] == '\x00':
                        # if helditem["pkid"] in (326, 326, 327):  # or just limit
                        # certain items use??
                        if not self.wrapper.events.callevent("player.interact", {
                            "player": player,
                            "position": position,
                            "action": "useitem"
                        }):
                            return False
                return True

            elif pkid == self.pktSB.HELD_ITEM_CHANGE:  # Held Item Change
                slot = self.packet.read("short:short")["short"]
                self.log.trace("(PROXY CLIENT) -> Parsed HELD_ITEM_CHANGE packet:\n%s", slot)
                if 9 > self.slot > -1:
                    self.slot = slot
                else:
                    return False
                return True

            elif pkid == self.pktSB.PLAYER_UPDATE_SIGN:  # player update sign
                if not self.isLocal:
                    return True  # ignore signs from child wrapper/server instance
                if self.clientversion < mcpacket.PROTOCOL_1_8START:
                    return True  # player.createsign not implemented for older minecraft versions
                data = self.packet.read("position:position|string:line1|string:line2|string:line3|string:line4")
                position = data["position"]
                l1 = data["line1"]
                l2 = data["line2"]
                l3 = data["line3"]
                l4 = data["line4"]
                payload = self.wrapper.events.callevent("player.createsign", {
                    "player": self.getPlayerObject(),
                    "position": position,
                    "line1": l1,
                    "line2": l2,
                    "line3": l3,
                    "line4": l4
                })
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_UPDATE_SIGN packet:\n%s", data)
                if not payload:
                    return False
                if type(payload) == dict:
                    if "line1" in payload:
                        l1 = payload["line1"]
                    if "line2" in payload:
                        l2 = payload["line2"]
                    if "line3" in payload:
                        l3 = payload["line3"]
                    if "line4" in payload:
                        l4 = payload["line4"]
                self.editSign(position, l1, l2, l3, l4)
                return False

            elif pkid == self.pktSB.CLIENT_SETTINGS:  # read Client Settings
                if self.clientversion < mcpacket.PROTOCOL_1_9START:
                    data = self.packet.read("string:locale|byte:view_distance|byte:chat_mode|bool:chat_colors|"
                                            "ubyte:displayed_skin_parts")
                else:
                    data = self.packet.read("string:locale|byte:view_distance|varint:chat_mode|bool:chat_colors|"
                                            "ubyte:displayed_skin_parts|varint:main_hand")
                self.clientSettings = data
                self.log.trace("(PROXY CLIENT) -> Parsed CLIENT_SETTINGS packet:\n%s", data)

            elif pkid == self.pktSB.CLICK_WINDOW:  # click window
                data = self.packet.read("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
                data['player'] = self.getPlayerObject()
                self.log.trace("(PROXY CLIENT) -> Parsed CLICK_WINDOW packet:\n%s", data)
                if not self.wrapper.events.callevent("player.slotClick", data):
                    return False
                return True

            elif pkid == self.pktSB.SPECTATE:  # Spectate - convert packet to local server UUID
                data = self.packet.read("uuid:target_player")
                self.log.trace("(PROXY CLIENT) -> Parsed SPECTATE packet:\n%s", data)
                for client in self.proxy.clients:
                    if data["target_player"].hex == client.uuid.hex:
                        self.server.packet.send(self.pktSB.SPECTATE, "uuid", ([client.serverUuid],))
                        return False
            else:
                # no packet parsed - just pass to server...
                return True

        elif self.state == ClientState.LOGIN:
            if pkid == 0x00:  # login start packet
                data = self.packet.read("string:username")
                self.username = data["username"]
                if self.config["Proxy"]["online-mode"]:
                    if self.wrapper.javaserver.protocolVersion < 6:  # 1.7.x versions
                        self.packet.send(0x01, "string|bytearray_short|bytearray_short", (self.serverID, self.publicKey,
                                                                                          self.verifyToken))
                    else:
                        self.packet.send(0x01, "string|bytearray|bytearray", (self.serverID, self.publicKey,
                                                                              self.verifyToken))
                else:
                    self.connect_to_server()
                    self.uuid = self.wrapper.getuuidfromname("OfflinePlayer:%s" % self.username)  # MCUUID object
                    self.serverUuid = self.wrapper.getuuidfromname("OfflinePlayer:%s" % self.username)  # MCUUID object
                    self.packet.send(0x02, "string|string", (self.uuid.string, self.username))
                    self.state = ClientState.PLAY
                    self.log.info("%s's client LOGON in (IP: %s)", self.username, self.addr[0])
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state LOGIN: \n%s", data)
                return False
            elif pkid == 0x01:
                if self.wrapper.javaserver.protocolVersion < 6:
                    data = self.packet.read("bytearray_short:shared_secret|bytearray_short:verify_token")
                else:
                    data = self.packet.read("bytearray:shared_secret|bytearray:verify_token")
                self.log.trace("(PROXY CLIENT) -> Parsed 0x01 ENCRYPTION RESPONSE packet with client state LOGIN:\n%s",
                               data)

                sharedsecret = encryption.decrypt_shared_secret(data["shared_secret"], self.privateKey)
                verifytoken = encryption.decrypt_shared_secret(data["verify_token"], self.privateKey)
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
                        data = r.json()
                        self.uuid = MCUUID(data["id"])

                        if data["name"] != self.username:
                            self.disconnect("Client's username did not match Mojang's record")
                            return False
                        for prop in data["properties"]:
                            if prop["name"] == "textures":
                                self.skinBlob = prop["value"]
                                self.wrapper.proxy.skins[self.uuid.string] = self.skinBlob
                        self.properties = data["properties"]
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
                                data = json.loads(f.read())
                            if data:
                                for player in data:
                                    if not player["uuid"] == self.serverUuid.string and \
                                                    player["uuid"] == self.uuid.string:
                                        self.log.info("Migrating %s's whitelist entry to proxy mode", self.username)
                                        data.append({"uuid": self.serverUuid.string, "name": self.username})
                                        # TODO I think the indent on this is wrong... looks like it will overwrite with
                                        # each record
                                        # either that, or it is making an insane number of re-writes (each time a record
                                        #  is processed)
                                        # since you can't append a json file like this, I assume the whole file should
                                        # be written at once,
                                        # after all the records are appended
                                        with open("whitelist.json", "w") as f:
                                            f.write(json.dumps(data))
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

                if self.proxy.isIPBanned(self.addr[0]):  # TODO make sure ban code is not using player objects
                    self.disconnect("Your address is IP-banned from this server!.")
                    return False
                testforban = self.proxy.isUUIDBanned(uuidwas)
                self.log.debug("Value - testforban: %s", testforban)
                if self.proxy.isUUIDBanned(uuidwas):  # TODO ...HERE, the player stuff becomes "None" (was self.uuid)
                    banreason = self.wrapper.proxy.getUUIDBanReason(uuidwas)  # TODO- which is why I archived the name
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
                self.packet.send(0x02, "string|string", (self.uuid.string, self.username))
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
                data = self.packet.read("long:payload")
                self.log.trace("(PROXY CLIENT) -> Received '0x01' Ping in STATUS mode")
                self.packet.send(0x01, "long", (data["payload"],))
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
                self.packet.send(0x00, "string", (json.dumps(self.MOTD),))
                return False
            else:
                # Unknown packet type, return to Handshake:
                self.state = ClientState.HANDSHAKE
                return False

        elif self.state == ClientState.HANDSHAKE:
            if pkid == 0x00:
                data = self.packet.read("varint:version|string:address|ushort:port|varint:state")
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state HANDSHAKE:\n%s", data)
                self.clientversion = data["version"]
                self._refresh_server_version()
                if not self.wrapper.javaserver.state == 2:  # TODO - one day, allow connection despite this
                    self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
                    return False
                if self.wrapper.javaserver.protocolVersion == -1:  # TODO make sure wrapper.mcserver.protocolVersion
                    #  ... returns -1 to signal no server
                    self.disconnect("Proxy client was unable to connect to the server.")
                    return False
                if self.serverversion == self.clientversion and data["state"] == ClientState.LOGIN:
                    # login start...
                    self.state = ClientState.LOGIN
                    return True  # packet passes to server, which will also switch to Login
                if data["state"] == ClientState.STATUS:
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
                    if self.server.state == 3:
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
                        self.packet.send(self.pktCB.KEEP_ALIVE, "varint", (self.keepalive_val,))
                    else:
                        # _OLD_ MC version
                        self.packet.send(0x00, "int", (self.keepalive_val,))
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
