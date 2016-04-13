# -*- coding: utf-8 -*-

import socket
import threading
import time
import traceback
import json
import random
import hashlib
import uuid
import shutil
import os

import utils.encryption as encryption
import mcpacket

from utils.helpers import args, argsAfter
from server import Server
from packet import Packet
from core.config import Config
from core.mcuuid import MCUUID
import requests  # wrapper.py will check for requests to run proxy mode

UNIVERSAL_CONNECT = False # tells the client "same version as you" or does not disconnect dissimilar clients
HIDDEN_OPS = ["SurestTexas00", "BenBaptist"]

class Client:
    def __init__(self, socket, addr, wrapper, publicKey, privateKey, proxy):
        self.socket = socket
        self.wrapper = wrapper
        self.config = wrapper.config
        self.socket = socket
        self.publicKey = publicKey
        self.privateKey = privateKey
        self.proxy = proxy
        self.addr = addr

        try:
            self.serverversion = self.wrapper.server.protocolVersion
        except AttributeError:
            # Default to 1.8 if no server is running
            # This can be modified to any version
            self.serverversion = 47

        self.abort = False
        self.log = wrapper.log
        self.tPing = time.time()
        self.server = None
        self.isServer = False
        self.isLocal = True
        self.uuid = None # Expect this to be an MCUUID
        self.serverUUID = None # Expect this to be an MCUUID
        self.server = None
        self.address = None
        self.ip = None
        self.handshake = False

        self.state = State.INIT

        self.packet = Packet(self.socket, self)
        self.send = self.packet.send
        self.read = self.packet.read
        self.sendRaw = self.packet.sendRaw

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

        for i in xrange(45):
            self.inventory[i] = None

        # Determine packet types - currently 1.8 is the lowest version supported.
        if self.serverversion >= mcpacket.PROTOCOLv1_9REL1:
            self.pktSB = mcpacket.ServerBound19
            self.pktCB = mcpacket.ClientBound19
        else:
            self.pktSB = mcpacket.ServerBound18
            self.pktCB = mcpacket.ClientBound18

    def connect(self, ip=None, port=None):
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
            except Exception as e:
                self.server_temp.close(kill_client=False)
                self.server_temp = None
                self.send(self.pktCB.CHAT_MESSAGE, "string|byte", ("""{"text": "Could not connect to that server!", "color": "red", "bold": "true"}""", 0))
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
            self.server.send(0x00, "varint|string|ushort|varint", (self.version, payload, self.config["Proxy"]["server-port"], 2))
        else:
            if UNIVERSAL_CONNECT:
                self.server.send(0x00, "varint|string|ushort|varint", (self.wrapper.server.protocolVersion, "localhost", self.config["Proxy"]["server-port"], 2))
            else:
                self.server.send(0x00, "varint|string|ushort|varint", (self.version, "localhost", self.config["Proxy"]["server-port"], 2))
        self.server.send(0x00, "string", (self.username,))

        if self.version > mcpacket.PROTOCOLv1_8START:  # Ben's anti-rain hack for cross server, lobby return, connections
            if self.config["Proxy"]["online-mode"]:
                self.send(self.pktCB.CHANGE_GAME_STATE, "ubyte|float", (1, 0))
                pass
        self.server.state = 2

    def close(self):
        self.abort = True
        try:
            self.socket.close()
        except Exception as e:
            self.log.exception("Could not close client socket! (%s)", e)
        if self.server:
            self.server.abort = True
            self.server.close()
        for i, client in enumerate(self.wrapper.proxy.clients):
            if client.username == self.username:
                del self.wrapper.proxy.clients[i]
        

    def disconnect(self, message):
        try:
            message = json.loads(message["string"])
        except Exception as e:
            pass

        if self.state == State.ACTIVE:
            self.send(self.pktCB.DISCONNECT, "json", (message,))
        else:
            self.send(0x00, "json", ({"text": message, "color": "red"},))

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

    def editsign(self, position, line1, line2, line3, line4):
        self.server.send(self.pktSB.PLAYER_UPDATE_SIGN, "position|string|string|string|string", (position, line1, line2, line3, line4))

    def message(self, string):
        self.server.send(self.pktSB.CHAT_MESSAGE, "string", (string,))

    def parse(self, pkid):  # server - bound parse ("Client" class connection)
        if pkid == 0x00 and self.state != State.ACTIVE:  # 0x00 is a 1.9 gameplay packet of "spawn object"
            if self.state == State.INIT:   # Handshake
                data = self.read("varint:version|string:address|ushort:port|varint:state")
                self.version = data["version"]
                self.packet.version = self.version
                if not self.wrapper.server.protocolVersion == self.version and data["state"] == 2:
                    if self.wrapper.server.protocolVersion == -1:
                        self.disconnect("Proxy client was unable to connect to the server.")
                        return
                    else:
                        if not UNIVERSAL_CONNECT:
                            self.disconnect("You're not running the same Minecraft version as the server!")
                            return
                        if mcpacket.PROTOCOL_1_9START < self.version < mcpacket.PROTOCOLv1_9REL1:
                            self.disconnect("You're running unsupported or outdated snapshots (%s)!" % self.version)
                            return
                if not self.wrapper.server.state == 2:
                    self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
                    return
                if data["state"] in (State.MOTD, State.LOGIN):
                    self.state = data["state"]
                else:
                    self.disconnect("Invalid state '%d'" % data["state"])
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state 0 (HANDSHAKE):\n%s", data)
                return False
            elif self.state == State.MOTD:
                sample = []
                for i in self.wrapper.server.players:
                    player = self.wrapper.server.players[i]
                    if player.username not in HIDDEN_OPS:
                        sample.append({"name": player.username, "id": str(player.uuid)})
                    if len(sample) > 5:
                        break
                if UNIVERSAL_CONNECT:
                    reported_version = self.version
                    reported_name = "%s (Compatibility mode)" % self.wrapper.server.version
                else:
                    reported_version = self.wrapper.server.protocolVersion
                    reported_name = self.wrapper.server.version
                MOTD = {
                    "description": json.loads(self.wrapper.server.processColorCodes(self.wrapper.server.motd.replace("\\", ""))),
                    "players": {
                        "max": self.wrapper.server.maxPlayers, 
                        "online": len(self.wrapper.server.players), 
                        "sample": sample
                    },
                    "version": {
                        "name": reported_name, 
                        "protocol": reported_version
                    }
                }
                if self.wrapper.server.serverIcon:
                    MOTD["favicon"] = self.wrapper.server.serverIcon
                self.send(0x00, "string", (json.dumps(MOTD),))
                self.state = State.PING
                return False
            elif self.state == State.LOGIN:
                data = self.read("string:username")
                self.username = data["username"]

                if self.config["Proxy"]["online-mode"]:
                    self.state = State.AUTHORIZING
                    self.verifyToken = encryption.generate_challenge_token()
                    self.serverID = encryption.generate_server_id()
                    if self.wrapper.server.protocolVersion < 6:  # 1.7.x versions
                        self.send(0x01, "string|bytearray_short|bytearray_short", (self.serverID, self.publicKey, self.verifyToken))
                    else:
                        self.send(0x01, "string|bytearray|bytearray", (self.serverID, self.publicKey, self.verifyToken))
                else:
                    self.connect()
                    self.uuid = self.wrapper.UUIDFromName("OfflinePlayer:%s" % self.username) # MCUUID object
                    self.serverUUID = self.wrapper.UUIDFromName("OfflinePlayer:%s" % self.username) # MCUUID object
                    self.send(0x02, "string|string", (self.uuid.string, self.username))
                    self.state = State.ACTIVE
                    self.log.info("%s logged in (IP: %s)", self.username, self.addr[0])
                self.log.trace("(PROXY CLIENT) -> Parsed 0x00 packet with client state 2:\n%s", data)
                return False

        if pkid == 0x01:
            # Moved 'if state == 3' out and created the if pkid == self.pktSB.CHAT_MESSAGE
            if self.state == State.AUTHORIZING:  # Encryption Response Packet
                if self.wrapper.server.protocolVersion < 6:
                    data = self.read("bytearray_short:shared_secret|bytearray_short:verify_token")
                else:
                    data = self.read("bytearray:shared_secret|bytearray:verify_token")
                self.log.trace("(PROXY CLIENT) -> Parsed 0x01 packet with client state 4 (ENCRYPTION RESPONSE):\n%s", data)

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
                    newUsername = self.wrapper.lookupUsernamebyUUID(self.uuid.string)
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
                        if not os.path.exists("%s/playerdata/%s.dat" % (worldName, self.serverUUID.string)):
                            if os.path.exists("%s/playerdata/%s.dat" % (worldName, self.uuid.string)):
                                self.log.info("Migrating %s's playerdata file to proxy mode", self.username)
                                shutil.move("%s/playerdata/%s.dat" % (worldName, self.uuid.string),
                                            "%s/playerdata/%s.dat" % (worldName, self.serverUUID.string))
                                with open("%s/.wrapper-proxy-playerdata-migrate" % worldName, "a") as f:
                                    f.write("%s %s\n" % (self.uuid.string, self.serverUUID.string))
                        # Change whitelist entries to offline mode versions
                        if os.path.exists("whitelist.json"):
                            with open("whitelist.json", "r") as f:
                                data = json.loads(f.read())
                            if data:
                                for player in data:
                                    if not player["uuid"] == self.serverUUID.string and player["uuid"] == self.uuid.string:
                                        self.log.info("Migrating %s's whitelist entry to proxy mode", self.username)
                                        data.append({"uuid": self.serverUUID.string, "name": self.username})
                                        with open("whitelist.json", "w") as f:
                                            f.write(json.dumps(data))
                                        self.wrapper.server.console("whitelist reload")
                                        with open("%s/.wrapper-proxy-whitelist-migrate" % worldName, "a") as f:
                                            f.write("%s %s\n" % (self.uuid.string, self.serverUUID.string))

                self.serverUUID = self.wrapper.UUIDFromName("OfflinePlayer:%s" % self.username)
                self.ip = self.addr[0]

                if self.version > 26:
                    self.packet.setCompression(256)

                # player ban code needs to go here - we should use the vanilla 'banned-players.json' since
                #    that will allow the vanilla client to handle the indentical bans should the server be switched
                #    to online mode.

                # banned-players.json format (2 space indents):
                """
                    [
                      {
                        "uuid": "23881df5-76ab-32ee-83c4-85086ceea301",
                        "name": "SapperLeader2",
                        "created": "2016-04-12 18:54:51 -0400",
                        "source": "Server",
                        "expires": "forever",
                        "reason": "Banned by an operator."
                      }
                    ]
                """
                 # banned-ips.json format (2 space indents):
                """
                    [
                      {
                        "ip": "199.199.199.199",
                        "created": "2016-04-12 19:10:38 -0400",
                        "source": "Server",
                        "expires": "forever",
                        "reason": "Banned by an operator."
                      }
                    ]
                """
                if self.proxy.isAddressBanned(self.addr[0]): #  IP ban- This should also be migrated to the vanilla file
                    self.disconnect("You have been IP-banned from this server!.")
                    return False

                if not self.wrapper.callEvent("player.preLogin", {
                    "player": self.username, 
                    "online_uuid": self.uuid.string, 
                    "offline_uuid": self.serverUUID.string, 
                    "ip": self.addr[0]
                }):
                    self.disconnect("Login denied.")
                    return False

                self.send(0x02, "string|string", (self.uuid.string, self.username))
                self.state = State.ACTIVE

                self.connect()

                self.log.info("%s logged in (UUID: %s | IP: %s)", self.username, self.uuid.string, self.addr[0])
                return False
            elif self.state == State.PING: # ping packet during status request
                keepAlive = self.read("long:keepAlive")["keepAlive"]
                self.send(0x01, "long", (keepAlive,))
                self.log.trace("(PROXY CLIENT) -> Parsed 0x01 packet with client state 5 (PING)")
                pass

        if pkid == self.pktSB.CHAT_MESSAGE and self.state == State.ACTIVE:
            data = self.read("string:message")
            self.log.trace("(PROXY CLIENT) -> Parsed CHAT_MESSAGE packet with client state 3:\n%s", data)
            if data is None:
                return False
            try:
                chatmsg = data["message"]
                print "Client.py - chatmsg: %s" % chatmsg
                if not self.isLocal and chatmsg == "/lobby":
                    self.server.close(reason="Lobbification", kill_client=False)
                    self.address = None
                    self.connect()
                    self.isLocal = True
                    return False
                if not self.isLocal:
                    return True
                payload = self.wrapper.callEvent("player.rawMessage", {"player": self.getPlayerObject(), "message": data["message"]})
                if not payload:
                    return False
                if type(payload) == str:
                    chatmsg = payload
                if chatmsg[0] == "/":
                    print "Command.py - args: %s" % argsAfter(chatmsg.split(" "), 1)
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
            data = self.read("double:x|double:y|double:z|bool:on_ground")
            self.position = (data["x"], data["y"], data["z"])
            self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSITION packet:\n%s", data)
        
        if pkid == self.pktSB.PLAYER_POSLOOK: # player position and look
            data = self.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
            self.position = (data["x"], data["y"], data["z"])
            self.head = (data["yaw"], data["pitch"])
            self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_POSLOOK packet:\n%s", data)
            if self.server.state != 3:
                return False

        if pkid == self.pktSB.PLAYER_LOOK: # Player Look
            data = self.read("float:yaw|float:pitch|bool:on_ground")
            yaw, pitch = data["yaw"], data["pitch"]
            self.head = (yaw, pitch)
            self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_LOOK packet:\n%s", data)

        if pkid == self.pktSB.PLAYER_DIGGING: # Player Block Dig
            if not self.isLocal:
                return True
            if self.version < mcpacket.PROTOCOLv1_8START:
                data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face")
                position = (data["x"], data["y"], data["z"])
                self.log.trace("(PROXY CLIENT) -> Parsed PLAYER_DIGGING packet:\n%s", data)
            else:
                data = self.read("byte:status|position:position|byte:face")
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
            if self.server.state != 3:
                return False

        if pkid == self.pktSB.PLAYER_BLOCK_PLACEMENT: # Player Block Placement
            player = self.getPlayerObject()
            curposx = False  # pre- 1.8
            curposy = False
            curposz = False
            hand = 0  # main hand

            # see which one works best
            # helditem = self.client.inventory[self.client.slot]
            # helditem = player.getClient().inventory[self.slot]
            helditem = player.getHeldItem()
            # helditem = self.wrapper.getClient()inventory[self.slot]
            # "helditem: %s" % helditem)  # wanna see if this differs from the held item dispensed by 1.8 slot

            if not self.isLocal:
                return True
            if self.version < mcpacket.PROTOCOLv1_8START:
                data = self.read("int:x|ubyte:y|int:z|byte:face|slot:item")
                position = (data["x"], data["y"], data["z"])
                # just FYI, notchian servers have been ignoring this field
                # for a long time, using server inventory instead.
                helditem = data["item"]
            else:
                if self.version >= mcpacket.PROTOCOLv1_9REL1:
                    data = self.read("position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                    hand = data["hand"]
                else:
                    data = self.read("position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                    helditem = data["item"]
                curposx = data["CurPosX"]
                curposy = data["CurPosY"]
                curposz = data["CurPosZ"]
            # Face and Position exist in all version protocols at this point
            position = data["Location"]
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
            if helditem == None:
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
            data = self.read("rest:pack")
            self.log.trace("(PROXY CLIENT) -> Parsed USE_ITEM packet:\n%s", data)
            player = self.getPlayerObject()
            position = self.lastplacecoords
            helditem = player.getHeldItem()
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
            slot = self.read("short:short")["short"]
            self.log.trace("(PROXY CLIENT) -> Parsed HELD_ITEM_CHANGE packet:\n%s", slot)
            if self.slot > -1 and self.slot < 9:
                self.slot = slot
            else:
                return False

        if pkid == self.pktSB.PLAYER_UPDATE_SIGN: # player update sign
            if not self.isLocal:
                return True  # ignore signs from child wrapper/server instance
            if self.version < mcpacket.PROTOCOLv1_8START:
                return True  # player.createsign not implemented for older minecraft versions
            data = self.read("position:position|string:line1|string:line2|string:line3|string:line4")
            position = data["position"]
            l1 = data["line1"]
            l2 = data["line2"]
            l3 = data["line3"]
            l4 = data["line4"]
            payload = self.wrapper.callEvent("player.createsign", {"player": self.getPlayerObject(), "position": position, "line1": l1, "line2": l2, "line3": l3, "line4": l4})
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
            self.editsign(position, l1, l2, l3, l4)
            return False
        
        if pkid == self.pktSB.CLIENT_SETTINGS: # read Client Settings
            if self.version < mcpacket.PROTOCOL_1_9START:
                data = self.read("string:locale|byte:view_distance|byte:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts")
            else:
                data = self.read("string:locale|byte:view_distance|varint:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts|varint:main_hand")
            self.clientSettings = data
            self.log.trace("(PROXY CLIENT) -> Parsed CLIENT_SETTINGS packet:\n%s", data)
        
        if pkid == self.pktSB.CLICK_WINDOW: # click window
            data = self.read("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
            data['player'] = self.getPlayerObject()
            self.log.trace("(PROXY CLIENT) -> Parsed CLICK_WINDOW packet:\n%s", data)
            if not self.wrapper.callEvent("player.slotClick", data):
                return False
        
        if pkid == self.pktSB.SPECTATE: # Spectate - convert packet to local server UUID
            data = self.read("uuid:target_player")
            self.log.trace("(PROXY CLIENT) -> Parsed SPECTATE packet:\n%s", data)
            for client in self.proxy.clients:
                if data["target_player"].hex == client.uuid.hex:
                    self.server.send(self.pktSB.SPECTATE, "uuid", [client.serverUUID]) # Convert SPECTATE packet...
                    return False

        return True # Default case

    def handle(self):
        t = threading.Thread(target=self.flush, args=())
        t.daemon = True
        t.start()
        try:
            while not self.abort:
                try:
                    pkid, original = self.packet.grabPacket()
                    self.original = original
                except EOFError as eof:
                    # This error is often erroneous since socket data recv length is 0 when transmit ends
                    self.log.exception("Client Packet EOF (%s)", eof)
                    self.close()
                    break
                except Exception as e:
                    # Bad file descriptor often occurs, cause is currently unknown, but seemingly harmless
                    self.log.exception("Failed to grab packet [CLIENT] (%s):", e)
                    self.close()
                    break
                # DISABLED until github #5 is resolved
                # if time.time() - self.tPing > 1 and self.state == State.ACTIVE:
                #     if self.version > 32:
                #         self.send(self.pktCB.KEEP_ALIVE, "varint",
                #                   (random.randrange(0, 99999),))
                #         if self.clientSettings and not self.clientSettingsSent:
                #             # print "Sending self.clientSettings..."
                #             # print self.clientSettings
                #             if self.version < mcpacket.PROTOCOL_1_9START:
                #                 self.server.send(self.pktSB.CLIENT_SETTINGS, "string|byte|byte|bool|ubyte", (
                #                     self.clientSettings["locale"],
                #                     self.clientSettings["view_distance"],
                #                     self.clientSettings["chat_mode"],
                #                     self.clientSettings["chat_colors"],
                #                     self.clientSettings["displayed_skin_parts"]
                #                 ))
                #                 self.clientSettingsSent = True
                #             else:
                #                 self.server.send(self.pktSB.CLIENT_SETTINGS, "string|byte|varint|bool|ubyte|varint", (
                #                     self.clientSettings["locale"],
                #                     self.clientSettings["view_distance"],
                #                     self.clientSettings["chat_mode"],
                #                     self.clientSettings["chat_colors"],
                #                     self.clientSettings[
                #                         "displayed_skin_parts"],
                #                     self.clientSettings["main_hand"]
                #                 ))
                #                 self.clientSettingsSent = True
                #     else:
                #         # _OLD_ MC version
                #         self.send(0x00, "int", (random.randrange(0, 99999),))
                #     self.tPing = time.time()
                if self.parse(pkid) and self.server:
                    if self.server.state == 3:
                        self.server.sendRaw(original)
        except Exception as ex:
            self.log.exception("Error in the [Client] -> [Server] handle (%s):", ex)

class State:
    """
    This class represents proxy Client states
    """

    # TODO: Provide details on each state
    INIT = 0
    MOTD = 1
    LOGIN = 2
    ACTIVE = 3
    AUTHORIZING = 4
    PING = 5
