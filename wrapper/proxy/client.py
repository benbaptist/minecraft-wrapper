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

from proxy.server import Server
from proxy.packet import Packet
from core.mcuuid import MCUUID

# wrapper.py will check for requests to run proxy mode
try:
    import requests
except ImportError:
    requests = False


UNIVERSAL_CONNECT = False # tells the client "same version as you" or does not disconnect dissimilar clients
HIDDEN_OPS = ["SurestTexas00", "BenBaptist"]

class Client:
    def __init__(self, sock, addr, wrapper, publicKey, privateKey, proxy):
        """
        Client receives "SERVER BOUND" packets from client.  These are what get parsed (SERVER BOUND format).
        'server.packet.send' - sends a packet to the server (use SERVER BOUND packet format)
        'self.packet.send' - sends a packet back to the client (use CLIENT BOUND packet format)

        Args: (self explanatory, hopefully)
            sock:
            addr:
            wrapper:
            publicKey:
            privateKey:
            proxy:

        """
        self.socket = sock
        self.addr = addr
        self.wrapper = wrapper
        self.publicKey = publicKey
        self.privateKey = privateKey
        self.proxy = proxy

        self.log = wrapper.log
        self.config = wrapper.config
        self.packet = Packet(self.socket, self)

        self._refresh_server_version()
        self.verifyToken = encryption.generate_challenge_token()
        self.serverID = encryption.generate_server_id()
        self.MOTD = {}

        self.clientversion = self.serverversion  # client will reset this later, if need be..
        self.abort = False
        self.time_server_pinged = time.time()
        self.time_client_responded = time.time()
        self.keepalive_val = 0
        self.server = None  # Server()
        self.isServer = False
        self.isLocal = True
        self.server_temp = None

        # UUIDs - all should use MCUUID unless otherwise specified
        self.uuid = None # this is intended to be the client UUID
        self.serverUuid = None # Server UUID - which Could be the local offline UUID.
        self.mojangUuid = None # Online UUID (should be same as client) - included for now to help refactoring
        self.server = None
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
        self.lastplacecoords = (0, 0, 0) # last placement (for use in cases of bucket use)
        self.windowCounter = 2
        self.properties = {}
        self.clientSettings = None
        self.clientSettingsSent = False
        self.skinBlob = {}

        for i in range(45):
            self.inventory[i] = None

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
            self.server_temp = Server(self, self.wrapper, ip, port)
            try:
                self.server_temp.connect()
                self.server.close(kill_client=False)
                self.server.client = None
                self.server = self.server_temp
            except OSError:
                self.server_temp.close(kill_client=False)
                self.server_temp = None
                self.packet.send(self.pktCB.CHAT_MESSAGE, "string|byte", ("""{"text": "Could not connect to that server!", "color": "red", "bold": "true"}""", 0))
                self.address = None
                return
        else:
            self.server = Server(self, self.wrapper, ip, port)
            try:
                self.server.connect()
            except Exception as e:
                self.disconnect("Proxy client could not connect to the server (%s)" % e)
        t = threading.Thread(target=self.server.handle, args=())
        t.daemon = True
        t.start()

        if self.config["Proxy"]["spigot-mode"]:
            payload = "localhost\x00%s\x00%s" % (self.addr[0], self.uuid.hex)
            self.server.packet.send(0x00, "varint|string|ushort|varint", (self.clientversion, payload, self.config["Proxy"]["server-port"], 2))
        else:
            if UNIVERSAL_CONNECT:
                self.server.packet.send(0x00, "varint|string|ushort|varint", (self.wrapper.server.protocolVersion, "localhost", self.config["Proxy"]["server-port"], 2))
            else:
                self.server.packet.send(0x00, "varint|string|ushort|varint", (self.clientversion, "localhost", self.config["Proxy"]["server-port"], 2))
        self.server.packet.send(0x00, "string", (self.username,))

        if self.clientversion > mcpacket.PROTOCOL_1_8START:  # Ben's anti-rain hack for cross server, lobby return, connections
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
        except ValueError: # optionally use json
            pass

        if self.state == ClientState.PLAY:
            self.packet.send(self.pktCB.DISCONNECT, "json", (message,))
        else:
            self.packet.send(0x00, "json", ({"text": message, "color": "red"},))

        time.sleep(1)
        self.close()

    def flush(self):
        while not self.abort:
            self.packet.flush()
            time.sleep(0.03)

    def getPlayerObject(self):
        if self.username in self.wrapper.server.players:
            return self.wrapper.server.players[self.username]
        return False

    def editSign(self, position, line1, line2, line3, line4):
        self.server.send(self.pktSB.PLAYER_UPDATE_SIGN, "position|string|string|string|string", (position, line1, line2, line3, line4))

    def message(self, string):
        self.server.send(self.pktSB.CHAT_MESSAGE, "string", (string,))

    def _refresh_server_version(self):
        # Get serverversion for mcpacket use
        try:
            self.serverversion = self.wrapper.server.protocolVersion
        except AttributeError:
            # Default to 1.8 if no server is running
            # This can be modified to any version
            self.serverversion = 47

        # Determine packet types - currently 1.8 is the lowest version supported.
        if self.serverversion >= mcpacket.PROTOCOL_1_9REL1:
            self.pktSB = mcpacket.ServerBound19
            self.pktCB = mcpacket.ClientBound19
        else:
            self.pktSB = mcpacket.ServerBound18
            self.pktCB = mcpacket.ClientBound18

    def parse(self, pkid):  # server - bound parse ("Client" class connection)
        if self.state == ClientState.PLAY:
            # TODO - elif these packet parsers
            if pkid == self.pktCB.KEEP_ALIVE:
                if self.serverversion < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.read("int:payload")
                else:  # self.version >= mcpacket.PROTOCOL_1_8START:
                    data = self.packet.read("varint:payload")
                self.log.trace("(PROXY CLIENT) -> Received KEEP_ALIVE from client:\n%s", data)
                if data["payload"] == self.keepalive_val:
                    self.time_client_responded = time.time()
                return False
            if pkid == self.pktSB.CHAT_MESSAGE:
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
                    payload = self.wrapper.callEvent("player.rawMessage", {
                        "player": self.getPlayerObject(),
                        "message": data["message"]
                    })
                    if not payload:
                        return False
                    if type(payload) == str:
                        chatmsg = payload
                    if chatmsg[0] == "/":
                        if self.wrapper.callEvent("player.runCommand", {
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

                # if self.getPlayerObject().hasGroup("test"):
                #     pass

            if pkid == self.pktSB.PLAYER_POSITION: # player position
                data = self.packet.read("double:x|double:y|double:z|bool:on_ground")
                self.position = (data["x"], data["y"], data["z"])
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSITION packet:\n%s", data)

            if pkid == self.pktSB.PLAYER_POSLOOK: # player position and look
                data = self.packet.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
                self.position = (data["x"], data["y"], data["z"])
                self.head = (data["yaw"], data["pitch"])
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSLOOK packet:\n%s", data)

            if pkid == self.pktSB.PLAYER_LOOK: # Player Look
                data = self.packet.read("float:yaw|float:pitch|bool:on_ground")
                yaw, pitch = data["yaw"], data["pitch"]
                self.head = (yaw, pitch)
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_LOOK packet:\n%s", data)

            if pkid == self.pktSB.PLAYER_DIGGING: # Player Block Dig
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
                    if not self.wrapper.callEvent("player.dig", {
                        "player": self.getPlayerObject(),
                        "position": position,
                        "action": "end_break",
                        "face": data["face"]
                    }):
                        return False  # stop packet if  player.dig returns False
                # started digging
                if data["status"] == 0:
                    if self.gamemode != 1:
                        if not self.wrapper.callEvent("player.dig", {
                            "player": self.getPlayerObject(),
                            "position": position,
                            "action": "begin_break",
                            "face": data["face"]
                        }):
                            return False
                    else:
                        if not self.wrapper.callEvent("player.dig", {
                            "player": self.getPlayerObject(),
                            "position": position,
                            "action": "end_break",
                            "face": data["face"]
                        }):
                            return False
                if data["status"] == 5 and data["face"] == 255:
                    if self.position != (0, 0, 0):
                        playerpos = self.position
                        if not self.wrapper.callEvent("player.interact", {
                            "player": self.getPlayerObject(),
                            "position": playerpos,
                            "action": "finish_using"
                        }):
                            return False

            if pkid == self.pktSB.PLAYER_BLOCK_PLACEMENT: # Player Block Placement
                player = self.getPlayerObject()
                #curposx = False  # pre- 1.8 - not used by wrapper
                #curposy = False
                #curposz = False
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
                        data = self.packet.read("position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                        hand = data["hand"]
                    else:
                        data = self.packet.read("position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                        helditem = data["item"]
                    position = data["Location"]
                    #curposx = data["CurPosX"]
                    #curposy = data["CurPosY"]
                    #curposz = data["CurPosZ"]
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
                    if not self.wrapper.callEvent("player.interact", {
                        "player": player,
                        "position": position,
                        "action": "useitem"
                    }):
                        return False

                self.lastplacecoords = position
                if not self.wrapper.callEvent("player.place", {
                    "player": player,
                    "position": position,
                    "clickposition": clickposition,
                    "hand": hand,
                    "item": helditem
                }):
                    return False
                if self.server.state != 3:
                    return False

            if pkid == self.pktSB.USE_ITEM:
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
                        if not self.wrapper.callEvent("player.interact", {
                            "player": player,
                            "position": position,
                            "action": "useitem"
                        }):
                            return False

            if pkid == self.pktSB.HELD_ITEM_CHANGE: # Held Item Change
                slot = self.packet.read("short:short")["short"]
                self.log.trace("(PROXY CLIENT) -> Parsed HELD_ITEM_CHANGE packet:\n%s", slot)
                if 9 > self.slot > -1:
                    self.slot = slot
                else:
                    return False

            if pkid == self.pktSB.PLAYER_UPDATE_SIGN: # player update sign
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
                payload = self.wrapper.callEvent("player.createsign", {
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

            if pkid == self.pktSB.CLIENT_SETTINGS: # read Client Settings
                if self.clientversion < mcpacket.PROTOCOL_1_9START:
                    data = self.packet.read("string:locale|byte:view_distance|byte:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts")
                else:
                    data = self.packet.read("string:locale|byte:view_distance|varint:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts|varint:main_hand")
                self.clientSettings = data
                self.log.trace("(PROXY CLIENT) -> Parsed CLIENT_SETTINGS packet:\n%s", data)

            if pkid == self.pktSB.CLICK_WINDOW: # click window
                data = self.packet.read("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
                data['player'] = self.getPlayerObject()
                self.log.trace("(PROXY CLIENT) -> Parsed CLICK_WINDOW packet:\n%s", data)
                if not self.wrapper.callEvent("player.slotClick", data):
                    return False

            if pkid == self.pktSB.SPECTATE: # Spectate - convert packet to local server UUID
                data = self.packet.read("uuid:target_player")
                self.log.trace("(PROXY CLIENT) -> Parsed SPECTATE packet:\n%s", data)
                for client in self.proxy.clients:
                    if data["target_player"].hex == client.uuid.hex:
                        self.server.send(self.pktSB.SPECTATE, "uuid", [client.serverUuid]) # Convert SPECTATE packet...
                        return False
            # no packet parsed - just pass to server...
            return True

        elif self.state == ClientState.LOGIN:
            if pkid == 0x00:  # login start packet
                data = self.packet.read("string:username")
                self.username = data["username"]
                if self.config["Proxy"]["online-mode"]:
                    if self.wrapper.server.protocolVersion < 6:  # 1.7.x versions
                        self.packet.send(0x01, "string|bytearray_short|bytearray_short", (self.serverID, self.publicKey,
                                                                                          self.verifyToken))
                    else:
                        self.packet.send(0x01, "string|bytearray|bytearray", (self.serverID, self.publicKey,
                                                                              self.verifyToken))
                else:
                    self.connect_to_server()
                    self.uuid = self.wrapper.getUUIDFromName("OfflinePlayer:%s" % self.username) # MCUUID object
                    self.serverUuid = self.wrapper.getUUIDFromName("OfflinePlayer:%s" % self.username) # MCUUID object
                    self.packet.send(0x02, "string|string", (self.uuid.string, self.username))
                    self.state = ClientState.PLAY
                    self.log.info("%s logged in (IP: %s)", self.username, self.addr[0])
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state LOGIN: \n%s", data)
                return False
            if pkid == 0x01:
                if self.wrapper.server.protocolVersion < 6:
                    data = self.packet.read("bytearray_short:shared_secret|bytearray_short:verify_token")
                else:
                    data = self.packet.read("bytearray:shared_secret|bytearray:verify_token")
                self.log.trace("(PROXY CLIENT) -> Parsed 0x01 ENCRYPTION RESPONSE packet with client state LOGIN:\n%s",
                               data)

                sharedSecret = encryption.decrypt_shared_secret(data["shared_secret"], self.privateKey)
                verifyToken = encryption.decrypt_shared_secret(data["verify_token"], self.privateKey)
                h = hashlib.sha1()
                h.update(self.serverID)
                h.update(sharedSecret)
                h.update(self.publicKey)
                serverId = self.packet.hexdigest(h)

                self.packet.sendCipher = encryption.AES128CFB8(sharedSecret)
                self.packet.recvCipher = encryption.AES128CFB8(sharedSecret)

                if not verifyToken == self.verifyToken:
                    self.disconnect("Verify tokens are not the same")
                    return False
                if self.config["Proxy"]["online-mode"]:
                    r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s"
                                     "&serverId=%s" % (self.username, serverId))
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
                        self.disconnect("Server Session Error (HTTP Status Code %d)" % r.status_code)
                        return False
                    newUsername = self.wrapper.getUsernamebyUUID(self.uuid.string)
                    if newUsername:
                        if newUsername != self.username:
                            self.log.info("%s logged in with new name, falling back to %s", self.username, newUsername)
                            self.username = newUsername
                else:
                    # TODO: See if this can be accomplished via MCUUID
                    self.uuid = uuid.uuid3(uuid.NAMESPACE_OID, "OfflinePlayer:%s" % self.username)  # no space in name

                if self.config["Proxy"]["convert-player-files"]: # Rename UUIDs accordingly
                    if self.config["Proxy"]["online-mode"]:
                        # Check player files, and rename them accordingly to offline-mode UUID
                        worldName = self.wrapper.server.worldName
                        if not os.path.exists("%s/playerdata/%s.dat" % (worldName, self.serverUuid.string)):
                            if os.path.exists("%s/playerdata/%s.dat" % (worldName, self.uuid.string)):
                                self.log.info("Migrating %s's playerdata file to proxy mode", self.username)
                                shutil.move("%s/playerdata/%s.dat" % (worldName, self.uuid.string),
                                            "%s/playerdata/%s.dat" % (worldName, self.serverUuid.string))
                                with open("%s/.wrapper-proxy-playerdata-migrate" % worldName, "a") as f:
                                    f.write("%s %s\n" % (self.uuid.string, self.serverUuid.string))
                        # Change whitelist entries to offline mode versions
                        if os.path.exists("whitelist.json"):
                            with open("whitelist.json", "r") as f:
                                data = json.loads(f.read())
                            if data:
                                for player in data:
                                    if not player["uuid"] == self.serverUuid.string and player["uuid"] == self.uuid.string:
                                        self.log.info("Migrating %s's whitelist entry to proxy mode", self.username)
                                        data.append({"uuid": self.serverUuid.string, "name": self.username})
                                        # TODO I think the indent on this is wrong... looks like it will overwrite with each record
                                        # either that, or it is making an insane number of re-writes (each time a record is processed)
                                        # since you can't append a json file like this, I assume the whole file should be written at once,
                                        # after all the records are appended
                                        with open("whitelist.json", "w") as f:
                                            f.write(json.dumps(data))
                                        self.wrapper.server.console("whitelist reload")
                                        with open("%s/.wrapper-proxy-whitelist-migrate" % worldName, "a") as f:
                                            f.write("%s %s\n" % (self.uuid.string, self.serverUuid.string))

                self.serverUuid = self.wrapper.getUUIDFromName("OfflinePlayer:%s" % self.username)
                self.ip = self.addr[0]
                playerwas = str(self.username)
                uuidwas = self.uuid.string  # TODO somewhere between HERE and ...
                self.log.debug("Value - playerwas: %s", playerwas)
                self.log.debug("Value - uuidwas: %s", uuidwas)
                if self.clientversion > 26:
                    self.packet.setCompression(256)

                # player ban code!  Uses vanilla json files - In wrapper proxy mode, supports
                #       temp-bans (the "expires" field of the ban record is used!)

                if self.proxy.isIPBanned(self.addr[0]):
                    self.disconnect("Your address is IP-banned from this server!.")
                    return False
                testforban = self.proxy.isUUIDBanned(uuidwas)
                self.log.debug("Value - testforban: %s", testforban)
                if self.proxy.isUUIDBanned(uuidwas):  # TODO ...HERE, the player stuff becomes "None" (was self.uuid)
                    banreason = self.wrapper.proxy.getUUIDBanReason(uuidwas)  # TODO- which is why I archived the name and UUID strings
                    self.disconnect("Banned: %s" % banreason)  # maybe because I got these two lines reversed? disc and then log.info?
                    self.log.info("Banned player %s tried to connect:\n %s" % (playerwas, banreason))
                    return False

                if not self.wrapper.callEvent("player.preLogin", {
                    "player": self.username,
                    "online_uuid": self.uuid.string,
                    "offline_uuid": self.serverUuid.string,
                    "ip": self.addr[0]
                }):
                    self.disconnect("Login denied.")
                    return False
                self.packet.send(0x02, "string|string", (self.uuid.string, self.username))
                self.time_client_responded = time.time()
                self.state = ClientState.PLAY

                # This will keep client connected regardless of server status (unless we explicitly disconnect it)
                t_keepalives = threading.Thread(target=self._keep_alive_tracker, args=())
                t_keepalives.daemon = True
                t_keepalives.start()

                #self.connect_to_server()

                self.log.info("%s logged in (UUID: %s | IP: %s)", self.username, self.uuid.string, self.addr[0])
                return False

        elif self.state == ClientState.STATUS:
            if pkid == 0x01:
                data = self.packet.read("long:payload")
                self.log.trace("(PROXY CLIENT) -> Received '0x01' Ping in STATUS mode")
                self.packet.send(0x01, "long", (data["payload"],))
                self.state = ClientState.HANDSHAKE
                return False
            if pkid == 0x00:
                self.log.trace("(PROXY CLIENT) -> Received '0x00' request (no payload) for list packet in STATUS mode")
                sample = []
                for i in self.wrapper.server.players:
                    player = self.wrapper.server.players[i]
                    if player.username not in HIDDEN_OPS:
                        sample.append({"name": player.username, "id": str(player.mojangUuid)})
                    if len(sample) > 5:
                        break
                if UNIVERSAL_CONNECT:
                    reported_version = self.clientversion
                    self.log.debug("(During status request, client reported it's version as: %s", self.clientversion)
                    reported_name = "%s (Compatibility mode)" % self.wrapper.server.version
                else:
                    reported_version = self.wrapper.server.protocolVersion
                    reported_name = self.wrapper.server.version
                self.MOTD = {
                    "description": json.loads(self.wrapper.server.processColorCodes(self.wrapper.server.motd.replace("\\", ""))),
                    "players": {
                        "max": int(self.wrapper.server.maxPlayers),
                        "online": len(self.wrapper.server.players),
                        "sample": sample
                    },
                    "version": {
                        "name": reported_name,
                        "protocol": reported_version
                    }
                }
                if self.wrapper.server.serverIcon:  # add Favicon, if it exists
                    self.MOTD["favicon"] = self.wrapper.server.serverIcon
                self.packet.send(0x00, "string", (json.dumps(self.MOTD),))
                return False
            # Unknown packet type, return to Handshake:
            self.state = ClientState.HANDSHAKE
            return False

        elif self.state == ClientState.HANDSHAKE:
            if pkid == 0x00:
                data = self.packet.read("varint:version|string:address|ushort:port|varint:state")
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state HANDSHAKE:\n%s", data)
                self.clientversion = data["version"]
                self._refresh_server_version()
                if not self.wrapper.server.state == 2:  # TODO - one day, allow connection despite this
                    self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
                    return False
                if self.wrapper.server.protocolVersion == -1:  # TODO make sure wrapper.mcserver.protocolVersion returns -1 to signal no server
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

    def handle(self):
        t = threading.Thread(target=self.flush, args=())
        t.daemon = True
        t.start()
        try:
            while not self.abort:
                try:
                    pkid, original = self.packet.grabPacket()
                except EOFError:
                    # This is not an error.. It means the client disconnected and is not sending packet stream anymore
                    self.log.debug("Client Packet steam ended (EOF)")
                    self.close()
                    break
                except Exception as e:
                    # Bad file descriptor often occurs, cause is currently unknown, but seemingly harmless
                    self.log.exception("Failed to grab packet [CLIENT] (%s):", e)
                    self.close()
                    break

                # send packet if server available and parsing passed.
                if self.parse(pkid) and self.server:
                    if self.server.state == 3:
                        self.server.sendRaw(original)
        except Exception as ex:
            self.log.exception("Error in the [Client] -> [Server] handle (%s):", ex)

    def _keep_alive_tracker(self):
        # send keep alives to client and send client settings to server.
        while not self.abort:
            time.sleep(1)
            while self.state == ClientState.PLAY:
                if time.time() - self.time_server_pinged > 10:  # client expects < 20sec
                    self.keepalive_val = random.randrange(0, 99999)
                    if self.clientversion > 32:
                        self.packet.send(self.pktCB.KEEP_ALIVE, "varint",
                                   (self.keepalive_val,))
                        if self.clientSettings and not self.clientSettingsSent:
                            if self.clientversion < mcpacket.PROTOCOL_1_9START:
                                self.server.send(self.pktSB.CLIENT_SETTINGS, "string|byte|byte|bool|ubyte", (
                                    self.clientSettings["locale"],
                                    self.clientSettings["view_distance"],
                                    self.clientSettings["chat_mode"],
                                    self.clientSettings["chat_colors"],
                                    self.clientSettings["displayed_skin_parts"]
                                ))
                                self.clientSettingsSent = True
                            else:
                                self.server.send(self.pktSB.CLIENT_SETTINGS, "string|byte|varint|bool|ubyte|varint", (
                                    self.clientSettings["locale"],
                                    self.clientSettings["view_distance"],
                                    self.clientSettings["chat_mode"],
                                    self.clientSettings["chat_colors"],
                                    self.clientSettings["displayed_skin_parts"],
                                    self.clientSettings["main_hand"]
                                ))
                                self.clientSettingsSent = True
                    else:
                        # _OLD_ MC version
                        self.packet.send(0x00, "int", (self.keepalive_val,))
                    self.time_server_pinged = time.time()
                # ckeck for active client keep alive status:
                if time.time() - self.time_client_responded > 20:  # server can allow up to 30 seconds for response
                    self.state = ClientState.HANDSHAKE
                    self.log.debug("Closing %s's client due to lack of keepalive response", "unknown")
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
