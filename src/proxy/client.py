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

import mcpacket

from server import Server
from packet import Packet
from config import Config
from helpers import args, argsAfter

try:
    import encryption
    import requests
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False

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
        self.uuid = None
        self.serverUUID = None
        self.server = None
        self.address = None
        self.handshake = False

        self.state = 0  # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing

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
            self.pktSB = mcpacket.ServerBound18  # receive/parse these
            self.pktCB = mcpacket.ClientBound18  # send these (if needed)

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
            if UNIVERSAL_CONNECT is True:
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
            self.log.error("Could not close client socket! (%s)" % e)
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

        if self.state == 3:
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
        if pkid == 0x00 and self.state != 3:  # 0x00 is a 1.9 gameplay packet of "spawn object"
            self.log.debug("Parsing client.............................. 0x00 and state not 3")
            if self.state == 0:   # Handshake
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
                            # mcpacket.PROTOCOLv1_9REL1 = 107  # start of stable 1.9 release (or most current snapshop that is documented by protocol)
                            # mcpacket.PROTOCOL_1_9START = 48  # start of 1.9 snapshots
                            self.disconnect("You're running unsupported or outdated snapshots (%s)!" % self.version)
                            return
                if not self.wrapper.server.state == 2:
                    self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
                    return
                if data["state"] in (1, 2):
                    self.state = data["state"]
                else:
                    self.disconnect("Invalid state '%d'" % data["state"])
                return False
            elif self.state == 1:
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
                self.state = 5
                return False
            elif self.state == 2:
                data = self.read("string:username")
                self.username = data["username"]

                if self.config["Proxy"]["online-mode"]:
                    self.state = 4
                    self.verifyToken = encryption.generate_challenge_token()
                    self.serverID = encryption.generate_server_id()
                    if self.wrapper.server.protocolVersion < 6:  # 1.7.x versions
                        self.send(0x01, "string|bytearray_short|bytearray_short", (self.serverID, self.publicKey, self.verifyToken))
                    else:
                        self.send(0x01, "string|bytearray|bytearray", (self.serverID, self.publicKey, self.verifyToken))
                else:
                    self.connect()
                    self.uuid = self.wrapper.UUIDFromName("OfflinePlayer:%s" % self.username)
                    self.serverUUID = self.wrapper.UUIDFromName("OfflinePlayer:%s" % self.username)
                    self.send(0x02, "string|string", (str(self.uuid), self.username))
                    self.state = 3
                    self.log.info("%s logged in (IP: %s)" % (self.username, self.addr[0]))
                return False

        if pkid == 0x01:
            self.log.debug("Parsing client.............................. 0x01")
            # Moved 'if state == 3' out and created the if pkid == self.pktSB.CHAT_MESSAGE
            if self.state == 4:  # Encryption Response Packet
                if self.wrapper.server.protocolVersion < 6:
                    data = self.read("bytearray_short:shared_secret|bytearray_short:verify_token")
                else:
                    data = self.read("bytearray:shared_secret|bytearray:verify_token")

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
                    r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s&serverId=%s" % (self.username, serverId))
                    if r.status_code == 200:
                        data = r.json()
                        # self.uuid = self.wrapper.formatUUID(data["id"])
                        self.uuid = uuid.UUID(data["id"])
                        if data["name"] != self.username:
                            self.disconnect("Client's username did not match Mojang's record")
                            return False
                        for prop in data["properties"]:
                            if prop["name"] == "textures":
                                self.skinBlob = prop["value"]
                                self.wrapper.proxy.skins[str(self.uuid)] = self.skinBlob
                        self.properties = data["properties"]
                    else:
                        self.disconnect("Server Session Error (HTTP Status Code %d)" % r.status_code)
                        return False
                    newUsername = self.wrapper.lookupUsernamebyUUID(str(self.uuid))
                    if newUsername:
                        if newUsername != self.username:
                            self.log.info("%s logged in with new name, falling back to %s" % (self.username, newUsername))
                            self.username = newUsername
                else:
                    self.uuid = uuid.uuid3(uuid.NAMESPACE_OID, "OfflinePlayer: %s" % self.username)
                
                if self.config["Proxy"]["convert-player-files"]: # Rename UUIDs accordingly
                    if self.config["Proxy"]["online-mode"]:
                        # Check player files, and rename them accordingly to offline-mode UUID
                        worldName = self.wrapper.server.worldName
                        if not os.path.exists("%s/playerdata/%s.dat" % (worldName, str(self.serverUUID))):
                            if os.path.exists("%s/playerdata/%s.dat" % (worldName, str(self.uuid))):
                                self.log.info("Migrating %s's playerdata file to proxy mode" % self.username)
                                shutil.move("%s/playerdata/%s.dat" % (worldName, str(self.uuid)), "%s/playerdata/%s.dat" % (worldName, self.serverUUID))
                                with open("%s/.wrapper-proxy-playerdata-migrate" % worldName, "a") as f:
                                    f.write("%s %s\n" % (str(self.uuid), str(self.serverUUID)))
                        # Change whitelist entries to offline mode versions
                        if os.path.exists("whitelist.json"):
                            with open("whitelist.json", "r") as f:
                                data = json.loads(f.read())
                            if data:
                                if not player["uuid"] == str(self.serverUUID) and player["uuid"] == str(self.uuid):
                                    self.log.info("Migrating %s's whitelist entry to proxy mode" % self.username)
                                    data.append({"uuid": str(self.serverUUID), "name": self.username})
                                    with open("whitelist.json", "w") as f:
                                        f.write(json.dumps(data))
                                    self.wrapper.server.console("whitelist reload")
                                    with open("%s/.wrapper-proxy-whitelist-migrate" % worldName, "a") as f:
                                        f.write("%s %s\n" % (str(self.uuid), str(self.serverUUID)))

                self.serverUUID = self.wrapper.UUIDFromName("OfflinePlayer:%s" % self.username)

                if self.version > 26:
                    self.packet.setCompression(256)

                # Ban code should go here
                if self.proxy.isAddressBanned(self.addr[0]): # IP ban
                    self.disconnect("You have been IP-banned from this server!.")
                    return False

                if not self.wrapper.callEvent("player.preLogin", {"player": self.username, "online_uuid": str(self.uuid), "offline_uuid": str(self.serverUUID), "ip": self.addr[0]}):
                    self.disconnect("Login denied.")
                    return False

                self.send(0x02, "string|string", (str(self.uuid), self.username))
                self.state = 3

                self.connect()

                self.log.info("%s logged in (UUID: %s | IP: %s)" % (self.username, str(self.uuid), self.addr[0]))
                # lookup in cache and update IP
                # self.wrapper.setUUID(self.uuid, self.username)
                return False
            elif self.state == 5: # ping packet during status request  (What is state 5?)
                keepAlive = self.read("long:keepAlive")["keepAlive"]
                self.send(0x01, "long", (keepAlive,))
                pass

        if pkid == self.pktSB.CHAT_MESSAGE and self.state == 3:
            self.log.debug("Parsing client.............................. chat_message and state 3")
            data = self.read("string:message")
            if data is None:
                return False
            try:
                chatmsg = data["message"]
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
                    if self.wrapper.callEvent("player.runCommand", {
                        "player": self.getPlayerObject(), 
                        "command": args(chatmsg.split(" "), 0)[1:].lower(), 
                        "args": argsAfter(chatmsg.split(" "), 1)
                    }):
                        self.message(chatmsg)
                        return False
                    return
                # print chatmsg
                self.message(chatmsg)
                return False
            except Exception as e:
                self.log.error("Formulating CHAT_MESSAGE failed (%s)" % e)
                self.log.error(traceback.format_exc())

            # if self.getPlayerObject().hasGroup("test"):
            #     pass

        if pkid == self.pktSB.PLAYER_POSITION: # player position
            self.log.debug("Parsing client.............................. player_position")
            data = self.read("double:x|double:y|double:z|bool:on_ground")
            self.position = (data["x"], data["y"], data["z"])
        
        if pkid == self.pktSB.PLAYER_POSLOOK: # player position and look
            self.log.debug("Parsing client.............................. player_poslook")
            data = self.read("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
            self.position = (data["x"], data["y"], data["z"])
            self.head = (data["yaw"], data["pitch"])
            if self.server.state != 3:
                return False

        if pkid == self.pktSB.PLAYER_LOOK: # Player Look
            self.log.debug("Parsing client.............................. player_look")
            data = self.read("float:yaw|float:pitch|bool:on_ground")
            yaw, pitch = data["yaw"], data["pitch"]
            self.head = (yaw, pitch)

        if pkid == self.pktSB.PLAYER_DIGGING: # Player Block Dig
            if not self.isLocal:
                return True
            if self.version < mcpacket.PROTOCOLv1_8START:
                data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face")
                position = (data["x"], data["y"], data["z"])
            else:
                data = self.read("byte:status|position:position|byte:face")
                position = data["position"]
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
            # "helditem: %s" % str(helditem))  # wanna see if this differs from the held item dispensed by 1.8 slot

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
                    # print("interaction : %s" % str(data))
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
            # print(data)
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
            self.log.debug("Parsing client.............................. client_settings")
            if self.version < mcpacket.PROTOCOL_1_9START:
                data = self.read("string:locale|byte:view_distance|byte:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts")
            else:
                data = self.read("string:locale|byte:view_distance|varint:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts|varint:main_hand")
            self.clientSettings = data
        
        if pkid == self.pktSB.CLICK_WINDOW: # click window
            data = self.read("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
            data['player'] = self.getPlayerObject()
            if not self.wrapper.callEvent("player.slotClick", data):
                return False
        
        if pkid == self.pktSB.SPECTATE: # Spectate - convert packet to local server UUID
            data = self.read("uuid:target_player")
            for client in self.proxy.clients:
                if data["target_player"].hex == client.uuid.hex:
                    # Convert SPECTATE packet...
                    self.server.send(self.pktSB.SPECTATE, "uuid", [client.serverUUID])
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
                    self.log.error("Packet EOF (%s)" % eof)
                    self.log.error(traceback.format_exc())
                    self.close()
                    break
                except Exception as e:
                    if Config.debug:
                        self.log.error("Failed to grab packet [CLIENT] (%s):" % e)
                        self.log.error(traceback.format_exc())
                    self.close()
                    break
                # DISABLED until github #5 is resolved
                # if time.time() - self.tPing > 1 and self.state == 3:
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
        except Exception as e:
            self.log.error("Error in the Client->Server method (%s):" % e)
            self.log.error(traceback.format_exc())