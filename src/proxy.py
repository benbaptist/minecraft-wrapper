# -*- coding: utf-8 -*-

from config import Config
from api.entity import Entity
from mcpkt import ServerBound18 as defPacketsSB
from mcpkt import ClientBound18 as defPacketsCB
from mcpkt import ServerBound19 as PacketsSB19
from mcpkt import ClientBound19 as PacketsCB19
from helpers import args, argsAfter
import socket
import threading
import struct
import StringIO
import time
import traceback
import json
import random
import hashlib
import os
import zlib
import uuid
import storage
import shutil

try:
    import encryption
    import requests
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False

# I'll probably split this file into more parts later on, like such:
# proxy folder: __init__.py (Proxy), client.py (Client), server.py (Server), network.py (Packet), bot.py (will contain Bot, for bot code)
# this could definitely use some code-cleaning.

# version coding
PROTOCOL_1_9_1_PRE = 108  # post- 1.9 "pre releases (1.9.1 pre-3 and later
# start of stable 1.9 release (or most current snapshop that is documented
# by protocol)
PROTOCOLv1_9REL1 = 107
PROTOCOL_1_9START = 48  # start of 1.9 snapshots
PROTOCOLv1_8START = 6
# tells the client "same version as you" or does not disconnect dissimilar
# clients
UNIVERSAL_CONNECT = False
HIDDEN_OPS = ["SurestTexas00", "BenBaptist"]

class Proxy:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.server = wrapper.server
        self.log = wrapper.log
        self.socket = False
        self.isServer = False
        self.clients = []
        self.skins = {}
        self.skinTextures = {}
        self.uuidTranslate = {}
        self.storage = storage.Storage("proxy-data")

        self.privateKey = encryption.generate_key_pair()
        self.publicKey = encryption.encode_public_key(self.privateKey)

    def host(self):
        # get the protocol version from the server
        while not self.wrapper.server.state == 2:
            time.sleep(.2)
        try:
            self.pollServer()
        except Exception, e:
            self.log.error(
                "Proxy could not poll the Minecraft server - are you 100% sure that the ports are configured properly? Reason:")
            self.log.getTraceback()

        while not self.socket:
            try:
                self.socket = socket.socket()
                self.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind((self.wrapper.config["Proxy"][
                                 "proxy-bind"], self.wrapper.config["Proxy"]["proxy-port"]))
                self.socket.listen(5)
            except Exception, e:
                self.log.error(
                    "Proxy mode could not bind - retrying in five seconds")
                self.log.debug(traceback.format_exc())
                self.socket = False
            time.sleep(5)
        while not self.wrapper.halt:
            try:
                sock, addr = self.socket.accept()
                client = Client(sock, addr, self.wrapper,
                                self.publicKey, self.privateKey, self)

                t = threading.Thread(target=client.handle, args=())
                t.daemon = True
                t.start()

                self.clients.append(client)

                # Remove stale clients
                for i, client in enumerate(self.wrapper.proxy.clients):
                    if client.abort:
                        del self.wrapper.proxy.clients[i]
            except Exception, e:  # Not quite sure what's going on
                print traceback.print_exc()
                client.disconnect(e)

    def pollServer(self):
        try:
            sock = socket.socket()
            sock.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
            packet = Packet(sock, self)

            packet.send(0x00, "varint|string|ushort|varint", (5, "localhost", self.wrapper.config["Proxy"]["server-port"], 1))
            packet.send(0x00, "", ())
            packet.flush()

            while True:
                id, original = packet.grabPacket()
                if id == 0x00:
                    data = json.loads(packet.read("string:response")["response"])
                    self.wrapper.server.protocolVersion = data["version"]["protocol"]
                    self.wrapper.server.version = data["version"]["name"]
                    break
        except Exception, e:
            self.log.warn("Polling the server failed (%s)" % e)
        finally:
            if sock: sock.close()

    def getClientByServerUUID(self, id):
        for client in self.clients:
            if str(client.serverUUID) == str(id):
                self.uuidTranslate[str(id)] = str(client.uuid)
                return client
        # if str(id) in self.uuidTranslate:
        # 	return uuid.UUID(hex=self.uuidTranslate[str(id)])
        return False  # no client

    def banUUID(self, uuid, reason="Banned by an operator", source="Server"):
        """This is all wrong - needs to ban uuid, not username """
        if not self.storage.key("banned-uuid"):
            self.storage.key("banned-uuid", {})
        self.storage.key("banned-uuid")[str(uuid)] = {
            "reason": reason,
            "source": source,
            "created": time.time(), 
            "name": self.lookupUUID(uuid)["name"]
        }  # wrong

    def banIP(self, ipaddress, reason="Banned by an operator", source="Server"):
        if not self.storage.key("banned-ip"):
            self.storage.key("banned-ip", {})
        self.storage.key(
            "banned-ip")[str(ipaddress)] = {"reason": reason, "source": source, "created": time.time()}
        for i in self.wrapper.server.players:
            player = self.wrapper.server.players[i]
            if str(player.client.addr[0]) == str(ipaddress):
                self.wrapper.server.console(
                    "kick %s Your IP is Banned!" % str(player.username))

    def pardonIP(self, ipaddress):
        if self.storage.key("banned-ip"):
            if str(ipaddress) in self.storage.key("banned-ip"):
                try:
                    del self.storage.key("banned-ip")[str(ipaddress)]
                    return True
                except Exception, e:
                    self.log.warn("Failed to pardon %s (%s)" % (ipdaddress, e))
                    return False
        self.log.warn("Could not find %s to pardon them" % ipaddress)
        return False

    def isUUIDBanned(self, uuid):  # Check if the UUID of the user is banned
        if not self.storage.key("banned-uuid"):
            self.storage.key("banned-uuid", {})
        if uuid in self.storage.key("banned-uuid"):
            return True
        else:
            return False

    def isAddressBanned(self, address):  # Check if the IP address is banned
        if not self.storage.key("banned-ip"):
            self.storage.key("banned-ip", {})
        if address in self.storage.key("banned-ip"):
            return True
        else:
            return False

    def getSkinTexture(self, uuid):
        if uuid not in self.skins:
            return False
        if uuid in self.skinTextures:
            return self.skinTextures[uuid]
        skinBlob = json.loads(self.skins[uuid].decode("base64"))
        # Player has no skin, so set to Alex [fix from #160]
        if "SKIN" not in skinBlob["textures"]:
            skinBlob["textures"]["SKIN"] = {
                "url": "http://hydra-media.cursecdn.com/minecraft.gamepedia.com/f/f2/Alex_skin.png"}
        r = requests.get(skinBlob["textures"]["SKIN"]["url"])
        if r.status_code == 200:
            self.skinTextures[uuid] = r.content.encode("base64")
            return self.skinTextures[uuid]
        else:
            self.log.warn("Could not fetch skin texture! (status code %d)" % r.status_code)
            return False


class Client:  # handle server-bound packets (client/game connection)

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
            # default to 1.8 if no server is running - can be changed to
            # whatever lowest life
            self.serverversion = 47
            # form we want to support!

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

        self.username = None
        self.gamemode = 0
        self.dimension = 0
        self.position = (0, 0, 0)  # X, Y, Z
        self.head = (0, 0)  # Yaw, Pitch
        self.inventory = {}
        self.slot = 0
        self.riding = None
        # last placement (for use in cases of bucket use)
        self.lastplacecoords = (0, 0, 0)
        self.windowCounter = 2
        self.properties = {}
        self.clientSettings = None
        self.clientSettingsSent = False
        for i in range(45):
            self.inventory[i] = None

        # Determine packet types - currently 1.8 is the lowest life form
        # supported.
        self.pktSB = defPacketsSB  # receive/parse these
        self.pktCB = defPacketsCB  # send these (if needed)

        if self.serverversion >= PROTOCOLv1_9REL1:
            self.pktSB = PacketsSB19
            self.pktCB = PacketsCB19

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
            except Exception, e:
                self.server_temp.close(kill_client=False)
                self.server_temp = None
                self.send(self.pktCB.chatmessage, "string|byte", (
                    """{"text": "Could not connect to that server!", "color": "red", "bold": "true"}""", 0))
                self.address = None
                return
        else:
            self.server = Server(self, self.wrapper, ip, port)
            try:
                self.server.connect()
            except Exception, e:
                self.disconnect("Proxy not connected to the server (%s)" % e)
        t = threading.Thread(target=self.server.handle, args=())
        t.daemon = True
        t.start()

        if self.config["Proxy"]["spigot-mode"]:
            payload = "localhost\x00%s\x00%s" % (self.addr[0], self.uuid.hex)
            self.server.send(0x00, "varint|string|ushort|varint",
                             (self.version, payload, self.config["Proxy"]["server-port"], 2))
        else:
            if UNIVERSAL_CONNECT is True:
                self.server.send(0x00, "varint|string|ushort|varint", (
                    self.wrapper.server.protocolVersion, "localhost", self.config["Proxy"]["server-port"], 2))
            else:
                self.server.send(0x00, "varint|string|ushort|varint", (self.version,
                                                                       "localhost", self.config["Proxy"]["server-port"], 2))
        self.server.send(0x00, "string", (self.username,))

        if self.version > PROTOCOLv1_8START:  # Ben's anti-rain hack for cross server, lobby return, connections
            if self.config["Proxy"]["online-mode"]:
                self.send(self.pktCB.changegamestate, "ubyte|float", (1, 0))
                pass
        self.server.state = 2

    def close(self):
        self.abort = True
        try:
            self.socket.close()
        except Exception, e:
            pass
        if self.server:
            self.server.abort = True
            self.server.close()
        for i, client in enumerate(self.wrapper.proxy.clients):
            if client.username == self.username:
                del self.wrapper.proxy.clients[i]

    def disconnect(self, message):
        try:
            message = json.loads(message["string"])
        except Exception, e:
            pass
        else:
            if self.state == 3:
                self.send(self.pktCB.disconnect, "json", (message,))
            else:
                self.send(0x00, "json", ({"text": message, "color": "red"},))
        finally:
            time.sleep(1)
            self.close()

    def flush(self):
        while not self.abort:
            self.packet.flush()
            time.sleep(0.03)
    # UUID operations

    def UUIDIntToHex(self, uuid):
        uuid = uuid.encode("hex")
        uuid = "%s-%s-%s-%s-%s" % (uuid[:8], uuid[8:12],
                                   uuid[12:16], uuid[16:20], uuid[20:])
        return uuid

    def UUIDHexToInt(self, uuid):
        uuid = uuid.replace("-", "").decode("hex")
        return uuid

    def getPlayerObject(self):
        if self.username in self.wrapper.server.players:
            return self.wrapper.server.players[self.username]
        return False

    def editsign(self, position, line1, line2, line3, line4):
        self.server.send(self.pktSB.playerupdatesign,
                         "position|string|string|string|string", (position, line1, line2, line3, line4))

    def message(self, string):
        self.server.send(self.pktSB.chatmessage, "string", (string,))

    def parse(self, id):  # server - bound parse ("Client" class connection)
        if id == 0x00 and self.state != 3:  # 0x00 is a 1.9 gameplay packet of "spawn object"
            if self.state == 0:   # Handshake
                data = self.read(
                    "varint:version|string:address|ushort:port|varint:state")
                self.version = data["version"]
                self.packet.version = self.version
                if not self.wrapper.server.protocolVersion == self.version and data["state"] == 2:
                    if self.wrapper.server.protocolVersion == -1:
                        self.disconnect(
                            "Proxy was unable to connect to the server.")
                        return
                    else:
                        if UNIVERSAL_CONNECT is not True:
                            self.disconnect(
                                "You're not running the same Minecraft version as the server!")
                            return
                        if PROTOCOL_1_9START < self.version < PROTOCOLv1_9REL1:
                            # PROTOCOLv1_9REL1 = 107  # start of stable 1.9 release (or most current snapshop that is documented by protocol)
                            # PROTOCOL_1_9START = 48  # start of 1.9 snapshots
                            self.disconnect(
                                "You're running unsupported outdated snapshots!")
                            return
                if not self.wrapper.server.state == 2:
                    self.disconnect(
                        "Server has not finished booting. Please try connecting again in a few seconds")
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
                        sample.append(
                            {"name": player.username, "id": str(player.uuid)})
                    if len(sample) > 5:
                        break
                if UNIVERSAL_CONNECT:
                    reported_version = self.version
                    reported_name = "%s (Compatibility mode)" % self.wrapper.server.version
                else:
                    reported_version = self.wrapper.server.protocolVersion
                    reported_name = self.wrapper.server.version
                MOTD = {"description": json.loads(self.wrapper.server.processColorCodes(self.wrapper.server.motd.replace("\\", ""))),
                        "players": {"max": self.wrapper.server.maxPlayers, "online": len(self.wrapper.server.players), "sample": sample},
                        "version": {"name": reported_name, "protocol": reported_version}
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
                        self.send(0x01, "string|bytearray_short|bytearray_short",
                                  (self.serverID, self.publicKey, self.verifyToken))
                    else:
                        self.send(0x01, "string|bytearray|bytearray",
                                  (self.serverID, self.publicKey, self.verifyToken))
                else:
                    self.connect()
                    self.uuid = self.wrapper.UUIDFromName(
                        "OfflinePlayer:%s" % self.username)
                    self.serverUUID = self.wrapper.UUIDFromName(
                        "OfflinePlayer:%s" % self.username)
                    self.send(0x02, "string|string",
                              (str(self.uuid), self.username))
                    self.state = 3
                    self.log.info("%s logged in (IP: %s)" %
                                  (self.username, self.addr[0]))
                return False

        if id == 0x01:
            # Moved 'if state == 3' out and created the if id ==
            # self.pktSB.chatmessage

            if self.state == 4:  # Encryption Response Packet
                if self.wrapper.server.protocolVersion < 6:
                    data = self.read(
                        "bytearray_short:shared_secret|bytearray_short:verify_token")
                else:
                    data = self.read(
                        "bytearray:shared_secret|bytearray:verify_token")
                sharedSecret = encryption.decrypt_shared_secret(
                    data["shared_secret"], self.privateKey)
                verifyToken = encryption.decrypt_shared_secret(
                    data["verify_token"], self.privateKey)
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
                    r = requests.get(
                        "https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s&serverId=%s" % (self.username, serverId))
                    try:
                        data = r.json()
                        self.uuid = self.wrapper.formatUUID(data["id"])
                        self.uuid = uuid.UUID(self.uuid)
                        if data["name"] != self.username:
                            self.disconnect(
                                "Client's username did not match Mojang's record")
                            return False
                        for property in data["properties"]:
                            if property["name"] == "textures":
                                self.skinBlob = property["value"]
                                self.wrapper.proxy.skins[
                                    str(self.uuid)] = self.skinBlob
                        self.properties = data["properties"]
                    except Exception, e:
                        self.disconnect("Session Server Error (%s)" % e)
                        return False
                    newUsername = self.wrapper.lookupUsernamebyUUID(str(self.uuid))
                    if newUsername and not newUsername == self.username:
                        self.log.info("%s logged in with new name, falling back to %s" % (self.username, newUsername))
                        self.username = newUsername
                else:
                    self.uuid = uuid.uuid3(uuid.NAMESPACE_OID, "OfflinePlayer: %s" % self.username)
                # Rename UUIDs accordingly
                if self.config["Proxy"]["convert-player-files"]:
                    if self.config["Proxy"]["online-mode"]:
                        # Check player files, and rename them accordingly to
                        # offline-mode UUID
                        worldName = self.wrapper.server.worldName
                        if not os.path.exists("%s/playerdata/%s.dat" % (worldName, str(self.serverUUID))):
                            if os.path.exists("%s/playerdata/%s.dat" % (worldName, str(self.uuid))):
                                self.log.info(
                                    "Migrating %s's playerdata file to proxy mode" % self.username)
                                shutil.move("%s/playerdata/%s.dat" % (worldName, str(self.uuid)),
                                            "%s/playerdata/%s.dat" % (worldName, str(self.serverUUID)))
                                with open("%s/.wrapper-proxy-playerdata-migrate" % worldName, "a") as f:
                                    f.write("%s %s\n" % (
                                        str(self.uuid), str(self.serverUUID)))
                        # Change whitelist entries to offline mode versions
                        if os.path.exists("whitelist.json"):
                            data = None
                            with open("whitelist.json", "r") as f:
                                try:
                                    data = json.loads(f.read())
                                except Exception, e:
                                    pass
                            if data:
                                a = False
                                b = False
                                for player in data:
                                    try:
                                        if player["uuid"] == str(self.serverUUID):
                                            a = True
                                        if player["uuid"] == str(self.uuid):
                                            b = True
                                    except Exception, e:
                                        pass
                                if not a and b:
                                    self.log.info(
                                        "Migrating %s's whitelist entry to proxy mode" % self.username)
                                    data.append(
                                        {"uuid": str(self.serverUUID), "name": self.username})
                                    with open("whitelist.json", "w") as f:
                                        f.write(json.dumps(data))
                                    self.wrapper.server.console(
                                        "whitelist reload")
                                    with open("%s/.wrapper-proxy-whitelist-migrate" % worldName, "a") as f:
                                        f.write("%s %s\n" % (str(self.uuid), str(self.serverUUID)))

                self.serverUUID = self.wrapper.UUIDFromName(
                    "OfflinePlayer:%s" % self.username)

                if self.version > 26:
                    self.packet.setCompression(256)

                # Ban code should go here
                # IP ban
                if self.proxy.isAddressBanned(self.addr[0]):
                    self.disconnect(
                        "You have been IP-banned from this server!.")
                    return False

                if not self.wrapper.callEvent("player.preLogin", {"player": self.username, "online_uuid": str(self.uuid), "offline_uuid": str(self.serverUUID), "ip": self.addr[0]}):
                    self.disconnect("Login denied.")
                    return False

                self.send(0x02, "string|string",
                          (str(self.uuid), self.username))
                self.state = 3

                self.connect()

                self.log.info("%s logged in (UUID: %s | IP: %s)" %
                              (self.username, str(self.uuid), self.addr[0]))
                # lookup in cache and update IP
                # self.wrapper.setUUID(self.uuid, self.username)

                return False
            # ping packet during status request  (What is state 5?)
            elif self.state == 5:
                keepAlive = self.read("long:keepAlive")["keepAlive"]
                self.send(0x01, "long", (keepAlive,))
                pass
        if id == self.pktSB.chatmessage and self.state == 3:
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
                payload = self.wrapper.callEvent("player.rawMessage", {
                                                 "player": self.getPlayerObject(), "message": data["message"]})
                if not payload:
                    return False
                if type(payload) == str:
                    chatmsg = payload
                if chatmsg[0] == "/":
                    if self.wrapper.callEvent("player.runCommand", {"player": self.getPlayerObject(), "command": args(chatmsg.split(" "), 0)[1:].lower(), "args": argsAfter(chatmsg.split(" "), 1)}):
                        self.message(chatmsg)
                        return False
                    return
                # print chatmsg
                self.message(chatmsg)
                return False
            except Exception, e:
                print traceback.format_exc()

# line		if self.getPlayerObject().hasGroup("test"):
            # pass
        # player position
        if id == self.pktSB.playerposition:
            data = self.read("double:x|double:y|double:z|bool:on_ground")
            self.position = (data["x"], data["y"], data["z"])
        # player position and look
        if id == self.pktSB.playerposlook:
            data = self.read(
                "double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
            self.position = (data["x"], data["y"], data["z"])
            self.head = (data["yaw"], data["pitch"])
            if self.server.state != 3:
                return False
        # Player Look
        if id == self.pktSB.playerlook:
            data = self.read("float:yaw|float:pitch|bool:on_ground")
            yaw, pitch = data["yaw"], data["pitch"]
            self.head = (yaw, pitch)
        # Player Block Dig
        if id == self.pktSB.playerdigging:
            if not self.isLocal:
                return True
            if self.version < PROTOCOLv1_8START:
                data = self.read("byte:status|int:x|ubyte:y|int:z|byte:face")
                position = (data["x"], data["y"], data["z"])
            else:
                data = self.read("byte:status|position:position|byte:face")
                position = data["position"]
            if data is None:
                return False
            # finished digging
            if data["status"] == 2:
                if not self.wrapper.callEvent("player.dig",
                                              {"player": self.getPlayerObject(),
                                               "position": position,
                                               "action": "end_break",
                                               "face": data["face"]}):
                    return False  # stop packet if  player.dig returns False
            # started digging
            if data["status"] == 0:
                if not self.gamemode == 1:
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
                if not self.position == (0, 0, 0):
                    playerpos = self.position
                    if not self.wrapper.callEvent("player.interact",
                                                  {"player": self.getPlayerObject(),
                                                   "position": playerpos,
                                                   "action": "finish_using"}):
                        return False
            if not self.server.state == 3:
                return False
        # Player Block Placement
        if id == self.pktSB.playerblockplacement:
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
            if self.version < PROTOCOLv1_8START:
                data = self.read("int:x|ubyte:y|int:z|byte:face|slot:item")
                position = (data["x"], data["y"], data["z"])
                # just FYI, notchian servers have been ignoring this field
                helditem = data["item"]
                # for a long time, using server inventory instead.
            else:
                if self.version >= PROTOCOLv1_9REL1:
                    data = self.read(
                        "position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
                    hand = data["hand"]
                    # print("interaction : %s" % str(data))
                else:
                    data = self.read(
                        "position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
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
                if not self.wrapper.callEvent("player.interact",
                                              {"player": player,
                                               "position": position,
                                               "action": "useitem"}):
                    return False
            self.lastplacecoords = position
            if not self.wrapper.callEvent("player.place",
                                          {"player": player,
                                           "position": position,
                                           "clickposition": clickposition,
                                           "hand": hand,
                                           "item": helditem}):
                return False
            if self.server.state != 3:
                return False

        if id == self.pktSB.useitem:
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
                    # if helditem["id"] in (326, 326, 327):  # or just limit
                    # certain items use??
                    if not self.wrapper.callEvent("player.interact",
                                                  {"player": player,
                                                   "position": position,
                                                   "action": "useitem"}):
                        return False

        # Held Item Change
        if id == self.pktSB.helditemchange:
            slot = self.read("short:short")["short"]
            if self.slot > -1 and self.slot < 9:
                self.slot = slot
            else:
                return False
        # player update sign
        if id == self.pktSB.playerupdatesign:
            if self.isLocal is not True:
                return True  # ignore signs from child wrapper/server instance
            if self.version < PROTOCOLv1_8START:
                return True  # player.createsign not implemented for older minecraft versions
            data = self.read(
                "position:position|string:line1|string:line2|string:line3|string:line4")
            position = data["position"]
            l1 = data["line1"]
            l2 = data["line2"]
            l3 = data["line3"]
            l4 = data["line4"]
            payload = self.wrapper.callEvent("player.createsign", {"player": self.getPlayerObject(
            ), "position": position, "line1": l1, "line2": l2, "line3": l3, "line4": l4})
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
        # read Client Settings
        if id == self.pktSB.clientsettings:
            if self.version < PROTOCOL_1_9START:
                data = self.read(
                    "string:locale|byte:view_distance|byte:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts")
            else:
                data = self.read(
                    "string:locale|byte:view_distance|varint:chat_mode|bool:chat_colors|ubyte:displayed_skin_parts|varint:main_hand")
            self.clientSettings = data
        # click window
        if id == self.pktSB.clickwindow:
            data = self.read(
                "ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
            data['player'] = self.getPlayerObject()
            if not self.wrapper.callEvent("player.slotClick", data):
                return False
        # Spectate - convert packet to local server UUID
        if id == self.pktSB.spectate:
            data = self.read("uuid:target_player")
            for client in self.proxy.clients:
                if data["target_player"].hex == client.uuid.hex:
                    # Convert Spectate packet...
                    self.server.send(self.pktSB.spectate,
                                     "uuid", [client.serverUUID])
                    return False
        return True

    def handle(self):
        t = threading.Thread(target=self.flush, args=())
        t.daemon = True
        t.start()
        try:
            while not self.abort:
                try:
                    id, original = self.packet.grabPacket()
                    self.original = original
                except EOFError:
                    break
                except Exception, e:
                    if Config.debug:
                        print "Failed to grab packet (CLIENT):"
                        print traceback.format_exc()
                    break
                finally:
                    self.close()

                if False == True:  # time.time() - self.tPing > 1 and self.state == 3:
                    if self.version > 32:
                        self.send(self.pktCB.keepalive, "varint",
                                  (random.randrange(0, 99999),))
                        if self.clientSettings and not self.clientSettingsSent:
                            # print "Sending self.clientSettings..."
                            # print self.clientSettings
                            if self.version < PROTOCOL_1_9START:
                                self.server.send(self.pktSB.clientsettings, "string|byte|byte|bool|ubyte", (
                                    self.clientSettings["locale"],
                                    self.clientSettings["view_distance"],
                                    self.clientSettings["chat_mode"],
                                    self.clientSettings["chat_colors"],
                                    self.clientSettings["displayed_skin_parts"]
                                ))
                                self.clientSettingsSent = True
                            else:
                                self.server.send(self.pktSB.clientsettings, "string|byte|varint|bool|ubyte|varint", (
                                    self.clientSettings["locale"],
                                    self.clientSettings["view_distance"],
                                    self.clientSettings["chat_mode"],
                                    self.clientSettings["chat_colors"],
                                    self.clientSettings[
                                        "displayed_skin_parts"],
                                    self.clientSettings["main_hand"]
                                ))
                                self.clientSettingsSent = True

                    else:
                        # _OLD_ MC version
                        self.send(0x00, "int", (random.randrange(0, 99999),))
                    self.tPing = time.time()
                if self.parse(id) and self.server:
                    if self.server.state == 3:
                        self.server.sendRaw(original)
        except Exception, e:
            print "Error in the Client->Server method:"
            print traceback.format_exc()


class Server:  # Handle Server Connection  ("client bound" packets)

    def __init__(self, client, wrapper, ip=None, port=None):
        self.client = client
        self.wrapper = wrapper
        self.ip = ip
        self.port = port
        self.abort = False
        self.isServer = True
        self.proxy = wrapper.proxy
        self.lastPacketIDs = []

        self.state = 0  # 0 = init, 1 = motd, 2 = login, 3 = active, 4 = authorizing
        self.packet = None
        self.version = self.wrapper.server.protocolVersion
        self.log = wrapper.log
        self.safe = False
        self.eid = None

        # Determine packet set to use
        self.pktSB = defPacketsSB
        self.pktCB = defPacketsCB
        if self.version >= PROTOCOLv1_9REL1:
            self.pktSB = PacketsSB19
            self.pktCB = PacketsCB19

    def connect(self):
        self.socket = socket.socket()
        if self.ip is None:
            self.socket.connect(
                ("localhost", self.wrapper.config["Proxy"]["server-port"]))
        else:
            self.socket.connect((self.ip, self.port))
            self.client.isLocal = False

        self.packet = Packet(self.socket, self)
        self.packet.version = self.client.version
        self.username = self.client.username

        self.send = self.packet.send
        self.read = self.packet.read
        self.sendRaw = self.packet.sendRaw

        t = threading.Thread(target=self.flush, args=())
        t.daemon = True
        t.start()

    def close(self, reason="Disconnected", kill_client=True):
        if Config.debug:
            usernameofplayer = "unk"
            try:
                usernameofplayer = str(self.client.username)
            except Exception, e:
                pass
            print("Last packet IDs (Server->Client) of player %s before disconnection: \n%s\n" %
                  (usernameofplayer, str(self.lastPacketIDs)))
            # print self.lastPacketIDs
        self.abort = True
        self.packet = None
        try:
            self.socket.close()
        except:
            pass
        if not self.client.isLocal and kill_client:  # Ben's cross-server hack
            self.client.isLocal = True
            self.client.send(self.pktCB.changegamestate,
                             "ubyte|float", (1, 0))  # "end raining"
            self.client.send(self.pktCB.chatmessage, "string|byte", (
                "{text:'Disconnected from server: %s', color:red}" % reason.replace("'", "\\'"), 0))
            self.client.connect()
            return

        # I may remove this later so the client can remain connected upon server disconnection
        # self.client.send(0x02, "string|byte", (json.dumps({"text": "Disconnected from server. Reason: %s" % reason, "color": "red"}),0))
        # self.abort = True
        # self.client.connect()
        if kill_client:
            self.client.abort = True
            self.client.server = None
            self.client.close()

    def getPlayerByEID(self, eid):
        for client in self.wrapper.proxy.clients:
            try:
                if client.server.eid == eid:
                    return self.getPlayerContext(client.username)
            except Exception, e:
                self.log.error("client.server.eid failed!\nserverEid: %s\nEid: %s (%s)" % (str(client.server.eid), str(eid), e))
        return False

    def getPlayerContext(self, username):
        try:
            return self.wrapper.server.players[username]
        except Exception, e:
            return False

    def flush(self):
        while not self.abort:
            self.packet.flush()
        # try:
        #   self.packet.flush()
        # except:
        #   print "Error while flushing, stopping"
        #   print traceback.format_exc()
        #   self.close()
        #   break
            time.sleep(0.03)

    def parse(self, id, original):  # client - bound parse ("Server" class connection)
        """
        Client-bound "Server Class"
        """
        # disconnect, I suppose...
        if id == 0x00 and self.state < 3:
            message = self.read("string:string")
            self.log.info("Disconnected from server: %s" % message["string"])
            self.client.disconnect(message)
            return False

        # handle keep alive packets
        if False == True:  # id == self.pktCB.keepalive and self.state == 3:
            if self.client.version > 7:
                id = self.read("varint:i")["i"]
                if id is not None:
                    self.send(self.pktSB.keepalive, "varint", (id,))
            return False

        if id == 0x01 and self.state == 2:
            self.client.disconnect(
                "Server is online mode. Please turn it off in server.properties.\n\nWrapper.py will handle authentication on its own, so do not worry about hackers.")
            return False

        # Login Success - UUID & Username are sent in this packet
        if id == 0x02 and self.state == 2:
            self.state = 3
            return False

        if id == self.pktCB.joingame and self.state == 3:
            if self.version < PROTOCOL_1_9_1_PRE:
                data = self.read(
                    "int:eid|ubyte:gamemode|byte:dimension|ubyte:difficulty|ubyte:max_players|string:level_type")
            elif self.version >= PROTOCOL_1_9_1_PRE:
                data = self.read(
                    "int:eid|ubyte:gamemode|int:dimension|ubyte:difficulty|ubyte:max_players|string:level_type")
            oldDimension = self.client.dimension
            self.client.gamemode = data["gamemode"]
            self.client.dimension = data["dimension"]
            # This is the EID of the player on this particular server - not
            # always the EID that the client is aware of
            self.eid = data["eid"]
            if self.client.handshake:
                dimensions = [-1, 0, 1]
                if oldDimension == self.client.dimension:
                    for l in dimensions:
                        if l != oldDimension:
                            dim = l
                            break
                    self.client.send(self.pktCB.respawn, "int|ubyte|ubyte|string", (l, data[
                                     "difficulty"], data["gamemode"], data["level_type"]))
                self.client.send(self.pktCB.respawn, "int|ubyte|ubyte|string", (self.client.dimension, data[
                                 "difficulty"], data["gamemode"], data["level_type"]))
                #self.client.send(0x01, "int|ubyte|byte|ubyte|ubyte|string|bool", (self.eid, self.client.gamemode, self.client.dimension, data["difficulty"], data["max_players"], data["level_type"], False))
                self.eid = data["eid"]
                self.safe = True
                return False
            else:
                self.client.eid = data["eid"]
                self.safe = True
            self.client.handshake = True

            # print "Sending change game state packet..."
            self.client.send(self.pktCB.changegamestate,
                             "ubyte|float", (3, self.client.gamemode))
            if UNIVERSAL_CONNECT is True:
                clientversion = self.packet.version
                serverversion = self.wrapper.server.protocolVersion
                if clientversion < PROTOCOL_1_9_1_PRE <= serverversion:
                    self.client.send(self.pktCB.joingame, "int|ubyte|byte|ubyte|ubyte|string",
                                     (data["eid"], data["gamemode"], data["dimension"], data["difficulty"], data["max_players"], data["level_type"]))
                    return False
        if id == self.pktCB.chatmessage and self.state == 3:
            rawdata = self.read("string:json|byte:position")
            rawstring = rawdata["json"]
            position = rawdata["position"]
            try:
                data = json.loads(rawstring)
            except Exception, e:
                return

            # added code
            payload = self.wrapper.callEvent(
                "player.chatbox", {"player": self.client.getPlayerObject(), "json": data})
            if payload is False:
                return False

            if type(payload) == dict:  # return a "chat" protocol formatted dictionary http://wiki.vg/Chat
                chatmsg = json.dumps(payload)
                self.client.send(self.pktCB.chatmessage,
                                 "string|byte", (chatmsg, position))
                return False

            if type(payload) == str:  # return a string-only object
                print("player.Chatbox return payload sent as string")
                self.client.send(self.pktCB.chatmessage,
                                 "string|byte", (payload, position))
                return False

            if payload is True:
                return True

            #print("The payload \n '%s' \n was never typed because it is %s" % (payload, type(payload)))
            try:
                if data["translate"] == "chat.type.admin":
                    return False
            except:
                pass

        if id == 0x03 and self.state == 2:  # Set Compression:
            data = self.read("varint:threshold")
            if data["threshold"] != -1:
                self.packet.compression = True
                self.packet.compressThreshold = data["threshold"]
            else:
                self.packet.compression = False
                self.packet.compressThreshold = -1
            return False

        if self.state < 3:
            return True  # remaining packets are parsed solely per "play" state

        if id == self.pktCB.timeupdate:
            data = self.read("long:worldage|long:timeofday")
            self.wrapper.server.timeofday = data["timeofday"]
            return True
        if id == self.pktCB.spawnposition:  # Spawn Position
            data = self.read("position:spawn")
            self.wrapper.server.spawnPoint = data["spawn"]
            return True
        if id == self.pktCB.respawn:  # Respawn Packet
            data = self.read(
                "int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
            self.client.gamemode = data["gamemode"]
            self.client.dimension = data["dimension"]
            return True
        if id == self.pktCB.playerposlook:  # Player Position and Look
            data = self.read(
                "double:x|double:y|double:z|float:yaw|float:pitch")
            x, y, z, yaw, pitch = data["x"], data[
                "y"], data["z"], data["yaw"], data["pitch"]
            self.client.position = (x, y, z)
            return True
        if id == self.pktCB.usebed:  # Use Bed
            data = self.read("varint:eid|position:location")
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.usebed, "varint|position",
                                 (self.client.eid, data["location"]))
                return False
            return True
        if id == self.pktCB.animation:  # self.pktCB.Animation: # Animation
            data = self.read("varint:eid|ubyte:animation")
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.animation, "varint|ubyte",
                                 (self.client.eid, data["animation"]))
                return False
            return True
        if id == self.pktCB.spawnplayer:  # Spawn Player
            if self.version < PROTOCOL_1_9START:
                data = self.read(
                    "varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|short:item|rest:metadata")
                if data["item"] < 0:
                    # A negative Current Item crashes clients (just in ncase)
                    data["item"] = 0
                clientserverid = self.proxy.getClientByServerUUID(data["uuid"])
                if clientserverid:
                    self.client.send(self.pktCB.spawnplayer, "varint|uuid|int|int|int|byte|byte|short|raw", (
                        data["eid"],
                        clientserverid.uuid,
                        data["x"],
                        data["y"],
                        data["z"],
                        data["yaw"],
                        data["pitch"],
                        data["item"],
                        data["metadata"]))
                return False
            else:
                data = self.read(
                    "varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|rest:metadata")
                clientserverid = self.proxy.getClientByServerUUID(data["uuid"])
                if clientserverid:
                    self.client.send(self.pktCB.spawnplayer, "varint|uuid|int|int|int|byte|byte|raw", (
                        data["eid"],
                        clientserverid.uuid,
                        data["x"],
                        data["y"],
                        data["z"],
                        data["yaw"],
                        data["pitch"],
                        data["metadata"]))
                    return False
            return True
        if id == self.pktCB.spawnobject:  # self.pktCB.spawnobject and self.state >= 3: # Spawn Object
            if self.version < PROTOCOL_1_9START:
                data = self.read(
                    "varint:eid|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw")
                entityuuid = None
            else:
                data = self.read("varint:eid|uuid:objectUUID|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|int:info|"
                                 "short:velocityX|short:velocityY|short:velocityZ")
                entityuuid = data["objectUUID"]
            eid, type_, x, y, z, pitch, yaw = data["eid"], data["type_"], data[
                "x"], data["y"], data["z"], data["pitch"], data["yaw"]
            if not self.wrapper.server.world:
                return
            self.wrapper.server.world.entities[data["eid"]] = Entity(
                eid, entityuuid, type_, (x, y, z), (pitch, yaw), True)
            return True
        if id == self.pktCB.spawnmob:  # Spawn Mob
            if self.version < PROTOCOL_1_9START:
                data = self.read(
                    "varint:eid|ubyte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|byte:head_pitch|short:velocityX|short:velocityY|short:velocityZ|rest:metadata")
                entityuuid = None
            else:
                data = self.read(
                    "varint:eid|uuid:entityUUID|ubyte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|byte:head_pitch|short:velocityX|short:velocityY|short:velocityZ|rest:metadata")
                entityuuid = data["entityUUID"]
            eid, type_, x, y, z, pitch, yaw, head_pitch = data["eid"], data["type_"], data[
                "x"], data["y"], data["z"], data["pitch"], data["yaw"], data["head_pitch"]
            if not self.wrapper.server.world:
                return
            # this will need entity UUID's added at some point
            self.wrapper.server.world.entities[data["eid"]] = Entity(
                eid, entityuuid, type_, (x, y, z), (pitch, yaw, head_pitch), False)
        if id == self.pktCB.entityrelativemove:  # Entity Relative Move
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("varint:eid|byte:dx|byte:dy|byte:dz")
            if not self.wrapper.server.world:
                return
            if self.wrapper.server.world.getEntityByEID(data["eid"]) is not None:
                self.wrapper.server.world.getEntityByEID(
                    data["eid"]).moveRelative((data["dx"], data["dy"], data["dz"]))
        if id == self.pktCB.entityteleport:  # Entity Teleport
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read(
                "varint:eid|int:x|int:y|int:z|byte:yaw|byte:pitch")
            if not self.wrapper.server.world:
                return
            if self.wrapper.server.world.getEntityByEID(data["eid"]) is not None:
                self.wrapper.server.world.getEntityByEID(
                    data["eid"]).teleport((data["x"], data["y"], data["z"]))
        if id == self.pktCB.entityheadlook:
            data = self.read("varint:eid|byte:angle")
        if id == self.pktCB.entitystatus:  # Entity Status
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("int:eid|byte:status")
        if id == self.pktCB.attachentity:  # Attach Entity
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("varint:eid|varint:vid|bool:leash")
            eid, vid, leash = data["eid"], data["vid"], data["leash"]
            player = self.getPlayerByEID(eid)
            if player is None:
                return
            if eid == self.eid:
                if vid == -1:
                    self.wrapper.callEvent(
                        "player.unmount", {"player": player})
                    self.client.riding = None
                else:
                    self.wrapper.callEvent(
                        "player.mount", {"player": player, "vehicle_id": vid, "leash": leash})
                    if not self.wrapper.server.world:
                        return
                    self.client.riding = self.wrapper.server.world.getEntityByEID(
                        vid)
                    self.wrapper.server.world.getEntityByEID(
                        vid).rodeBy = self.client
                if eid != self.client.eid:
                    self.client.send(
                        self.pktCB.attachentity, "varint|varint|bool", (self.client.eid, vid, leash))
                    return False
        if id == self.pktCB.entitymetadata:  # Entity Metadata
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("varint:eid|rest:metadata")
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.entitymetadata,
                                 "varint|raw", (self.client.eid, data["metadata"]))
                return False
        if id == self.pktCB.entityeffect:  # Entity Effect
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read(
                "varint:eid|byte:effect_id|byte:amplifier|varint:duration|bool:hide")
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.entityeffect, "varint|byte|byte|varint|bool", (self.client.eid, data[
                                 "effect_id"], data["amplifier"], data["duration"], data["hide"]))
                return False
        if id == self.pktCB.removeentityeffect:  # Remove Entity Effect
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("varint:eid|byte:effect_id")
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.removeentityeffect,
                                 "varint|byte", (self.client.eid, data["effect_id"]))
                return False
        if id == self.pktCB.entityproperties:  # Entity Properties
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("varint:eid|rest:properties")
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.entityproperties,
                                 "varint|raw", (self.client.eid, data["properties"]))
                return False

        # if id == self.pktCB.chunkdata: # Chunk Data
        # if self.client.packet.compressThreshold == -1:
        #   print "CLIENT COMPRESSION ENABLED"
        #   self.client.packet.setCompression(256)

        if True == False:  # self.pktCB.blockchange: # Block Change - disabled - not doing anything at this point
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("position:location|varint:id")

        # Map Chunk Bulk (no longer exists in 1.9)
        if id == self.pktCB.mapchunkbulk:
            if self.version > PROTOCOLv1_8START and self.version < PROTOCOL_1_9START:
                data = self.read("bool:skylight|varint:chunks")
                chunks = []
                for i in range(data["chunks"]):
                    meta = self.read("int:x|int:z|ushort:primary")
                    chunks.append(meta)
                for i in range(data["chunks"]):
                    meta = chunks[i]
                    bitmask = bin(meta["primary"])[2:].zfill(16)
                    primary = []
                    for i in bitmask:
                        if i == "0":
                            primary.append(False)
                        if i == "1":
                            primary.append(True)
                    chunkColumn = bytearray()
                    for i in primary:
                        if i:
                            # packetanisc
                            chunkColumn += bytearray(
                                self.packet.read_data(16 * 16 * 16 * 2))
                            if self.client.dimension == 0:
                                metalight = bytearray(
                                    self.packet.read_data(16 * 16 * 16))
                            if data["skylight"]:
                                skylight = bytearray(
                                    self.packet.read_data(16 * 16 * 16))
                        else:
                            # Null Chunk
                            chunkColumn += bytearray(16 * 16 * 16 * 2)
                #self.wrapper.server.world.setChunk(meta["x"], meta["z"], world.Chunk(chunkColumn, meta["x"], meta["z"]))
                # print "Reading chunk %d,%d" % (meta["x"], meta["z"])
        if id == self.pktCB.changegamestate:  # Change Game State
            data = self.read("ubyte:reason|float:value")
            if data["reason"] == 3:
                self.client.gamemode = data["value"]
        if id == self.pktCB.setslot:  # Set Slot
            if self.version < PROTOCOLv1_8START:
                # Temporary! These packets need to be filtered for cross-server
                # stuff.
                return True
            data = self.read("byte:wid|short:slot|slot:data")
            if data["wid"] == 0:
                self.client.inventory[data["slot"]] = data["data"]
        # if id == 0x30: # Window Items
        # 	data = self.read("byte:wid|short:count")
        # 	print data["count"]
        # 	if data["wid"] == 0:
        # 		for slot in range(1, data["count"]):
        # 			data = self.read("slot:data")
        # 			self.client.inventory[slot] = data["data"]
        if id == self.pktCB.playerlistitem:  # player list item
            if self.version > PROTOCOLv1_8START:
                head = self.read("varint:action|varint:length")
                z = 0
                while z < head["length"]:
                    serverUUID = self.read("uuid:uuid")["uuid"]
                    playerclient = self.client.proxy.getClientByServerUUID(serverUUID)
                    if not playerclient:
                        z += 1
                        continue
                    try:
                        uuid = playerclient.uuid
                    except Exception, e:
                        # uuid = playerclient
                        self.log.warn("playercleint.uuid failed in playerlist item (%s)" % e)
                        z += 1
                        continue
                    z += 1
                    if head["action"] == 0:
                        properties = playerclient.properties
                        raw = ""
                        for i in properties:
                            # name
                            raw += self.client.packet.send_string(i["name"])
                            # value
                            raw += self.client.packet.send_string(i["value"])
                            if "signature" in i:
                                raw += self.client.packet.send_bool(True)
                                # signature
                                raw += self.client.packet.send_string(i["signature"])
                            else:
                                raw += self.client.packet.send_bool(False)
                        raw += self.client.packet.send_varInt(0)
                        raw += self.client.packet.send_varInt(0)
                        raw += self.client.packet.send_bool(False)
                        self.client.send(self.pktCB.playerlistitem, "varint|varint|uuid|string|varint|raw", (
                            0, 1, playerclient.uuid, playerclient.username, len(properties), raw))
                    elif head["action"] == 1:
                        data = self.read("varint:gamemode")
                        self.client.send(
                            self.pktCB.playerlistitem, "varint|varint|uuid|varint", (1, 1, uuid, data["gamemode"]))
                    elif head["action"] == 2:
                        data = self.read("varint:ping")
                        self.client.send(
                            self.pktCB.playerlistitem, "varint|varint|uuid|varint", (2, 1, uuid, data["ping"]))
                    elif head["action"] == 3:
                        data = self.read("bool:has_display")
                        if data["has_display"]:
                            data = self.read("string:displayname")
                            self.client.send(self.pktCB.playerlistitem, "varint|varint|uuid|bool|string", (
                                3, 1, uuid, True, data["displayname"]))
                        else:
                            self.client.send(
                                self.pktCB.playerlistitem, "varint|varint|uuid|varint", (3, 1, uuid, False))
                    elif head["action"] == 4:
                        self.client.send(
                            self.pktCB.playerlistitem, "varint|varint|uuid", (4, 1, uuid))
                    return False
        if id == self.pktCB.disconnect:  # disconnect
            message = self.read("json:json")["json"]
            self.log.info("Disconnected from server: %s" % message)
            if not self.client.isLocal:
                self.close()
            else:
                self.client.disconnect(message)
            return False
        return True

    def handle(self):
        try:
            while not self.abort:
                try:
                    id, original = self.packet.grabPacket()
                    self.lastPacketIDs.append((hex(id), len(original)))
                    if len(self.lastPacketIDs) > 10:
                        for i, v in enumerate(self.lastPacketIDs):
                            del self.lastPacketIDs[i]
                            break
                except EOFError:
                    print traceback.format_exc()
                    break
                except Exception, e:
                    if Config.debug:
                        print "Failed to grab packet (SERVER)"
                        print traceback.format_exc()
                    return
                finally:
                    self.close()
                if self.client.abort:
                    self.close()
                    break
                if self.parse(id, original) and self.safe:
                    self.client.sendRaw(original)
        except Exception, e:
            if Config.debug:
                print "Error in the Server->Client method:"
                print traceback.format_exc()
        finally:
            self.close()


class Packet:  # PACKET PARSING CODE

    def __init__(self, socket, obj):
        self.socket = socket

        self.obj = obj

        self.recvCipher = None
        self.sendCipher = None
        self.compressThreshold = -1
        self.version = 5
        self.bonk = False
        self.abort = False

        self.buffer = StringIO.StringIO()
        self.queue = []

        self._ENCODERS = {
            1: self.send_byte,
            2: self.send_short,
            3: self.send_int,
            4: self.send_long,
            5: self.send_float,
            6: self.send_double,
            7: self.send_byte_array,
            8: self.send_short_string,
            9: self.send_list,
            10: self.send_comp,
            11: self.send_int_array
        }
        self._DECODERS = {
            1: self.read_byte,
            2: self.read_short,
            3: self.read_int,
            4: self.read_long,
            5: self.read_float,
            6: self.read_double,
            7: self.read_bytearray,
            8: self.read_short_string,
            9: self.read_list,
            10: self.read_comp,
            11: self.read_int_array
        }

    def close(self):
        self.abort = True

    def hexdigest(self, sh):
        d = long(sh.hexdigest(), 16)
        if d >> 39 * 4 & 0x8:
            return "-%x" % ((-d) & (2 ** (40 * 4) - 1))
        return "%x" % d

    def grabPacket(self):
        length = self.unpack_varInt()
#		if length == 0: return None
#		if length > 256:
#			print "Length: %d" % length
        dataLength = 0
        if not self.compressThreshold == -1:
            dataLength = self.unpack_varInt()
            length = length - len(self.pack_varInt(dataLength))
        # $ part of the bad file descriptor rabbit trail
        payload = self.recv(length)
        if dataLength > 0:
            payload = zlib.decompress(payload)
        self.buffer = StringIO.StringIO(payload)
        id = self.read_varInt()
        return (id, payload)

    def pack_varInt(self, val):
        total = b''
        if val < 0:
            val = (1 << 32) + val
        while val >= 0x80:
            bits = val & 0x7F
            val >>= 7
            total += struct.pack('B', (0x80 | bits))
        bits = val & 0x7F
        total += struct.pack('B', bits)
        return total

    def unpack_varInt(self):
        total = 0
        shift = 0
        val = 0x80
        while val & 0x80:
            val = struct.unpack('B', self.recv(1))[0]
            total |= ((val & 0x7F) << shift)
            shift += 7
        if total & (1 << 31):
            total = total - (1 << 32)
        return total

    def setCompression(self, threshold):
        #		self.sendRaw("\x03\x80\x02")
        self.send(0x03, "varint", (threshold,))
        self.compressThreshold = threshold
        # time.sleep(1.5)

    def flush(self):
        for p in self.queue:
            packet = p[1]
            id = struct.unpack("B", packet[0])[0]
            if p[0] > -1:  # p[0] > -1:
                if len(packet) > self.compressThreshold:
                    packetCompressed = self.pack_varInt(
                        len(packet)) + zlib.compress(packet)
                    packet = self.pack_varInt(
                        len(packetCompressed)) + packetCompressed
                else:
                    packet = self.pack_varInt(0) + packet
                    packet = self.pack_varInt(len(packet)) + packet
            else:
                packet = self.pack_varInt(len(packet)) + packet
            # if not self.obj.isServer:
            #   print packet.encode("hex")
            if self.sendCipher is None:
                self.socket.send(packet)
            else:
                self.socket.send(self.sendCipher.encrypt(packet))
        self.queue = []

    def sendRaw(self, payload):
        if not self.abort:
            self.queue.append((self.compressThreshold, payload))
    # -- SENDING AND PARSING PACKETS --

    def read(self, expression):
        result = {}
        for exp in expression.split("|"):
            type_ = exp.split(":")[0]
            name = exp.split(":")[1]
            if type_ == "string":
                result[name] = self.read_string()
            if type_ == "json":
                result[name] = self.read_json()
            if type_ == "ubyte":
                result[name] = self.read_ubyte()
            if type_ == "byte":
                result[name] = self.read_byte()
            if type_ == "int":
                result[name] = self.read_int()
            if type_ == "short":
                result[name] = self.read_short()
            if type_ == "ushort":
                result[name] = self.read_ushort()
            if type_ == "long":
                result[name] = self.read_long()
            if type_ == "double":
                result[name] = self.read_double()
            if type_ == "float":
                result[name] = self.read_float()
            if type_ == "bool":
                result[name] = self.read_bool()
            if type_ == "varint":
                result[name] = self.read_varInt()
            if type_ == "bytearray":
                result[name] = self.read_bytearray()
            if type_ == "bytearray_short":
                result[name] = self.read_bytearray_short()
            if type_ == "position":
                result[name] = self.read_position()
            if type_ == "slot":
                result[name] = self.read_slot()
            if type_ == "uuid":
                result[name] = self.read_uuid()
            if type_ == "metadata":
                result[name] = self.read_metadata()
            if type_ == "rest":
                result[name] = self.read_rest()
        return result

    def send(self, id, expression, payload):
        result = ""
        result += self.send_varInt(id)
        if len(expression) > 0:
            for i, type_ in enumerate(expression.split("|")):
                pay = payload[i]
                if type_ == "string":
                    result += self.send_string(pay)
                if type_ == "json":
                    result += self.send_json(pay)
                if type_ == "ubyte":
                    result += self.send_ubyte(pay)
                if type_ == "byte":
                    result += self.send_byte(pay)
                if type_ == "int":
                    result += self.send_int(pay)
                if type_ == "short":
                    result += self.send_short(pay)
                if type_ == "ushort":
                    result += self.send_ushort(pay)
                if type_ == "varint":
                    result += self.send_varInt(pay)
                if type_ == "float":
                    result += self.send_float(pay)
                if type_ == "double":
                    result += self.send_double(pay)
                if type_ == "long":
                    result += self.send_long(pay)
                if type_ == "bytearray":
                    result += self.send_bytearray(pay)
                if type_ == "bytearray_short":
                    result += self.send_bytearray_short(pay)
                if type_ == "uuid":
                    result += self.send_uuid(pay)
                if type_ == "metadata":
                    result += self.send_metadata(pay)
                if type_ == "bool":
                    result += self.send_bool(pay)
                if type_ == "position":
                    result += self.send_position(pay)
                if type_ == "slot":
                    result += self.send_slot(pay)
                if type_ == "raw":
                    result += pay
        self.sendRaw(result)
        return result
    # -- SENDING DATA TYPES -- #

    def send_byte(self, payload):
        return struct.pack("b", payload)

    def send_ubyte(self, payload):
        return struct.pack("B", payload)

    def send_string(self, payload):
        try:
            returnitem = payload.encode("utf-8", errors="ignore")
        except:
            returnitem = str(payload)
        return self.send_varInt(len(returnitem)) + returnitem

    def send_json(self, payload):
        return self.send_string(json.dumps(payload))

    def send_int(self, payload):
        return struct.pack(">i", payload)

    def send_long(self, payload):
        return struct.pack(">q", payload)

    def send_short(self, payload):
        return struct.pack(">h", payload)

    def send_ushort(self, payload):
        return struct.pack(">H", payload)

    def send_float(self, payload):
        return struct.pack(">f", payload)

    def send_double(self, payload):
        return struct.pack(">d", payload)

    def send_varInt(self, payload):
        return self.pack_varInt(payload)

    def send_bytearray(self, payload):
        return self.send_varInt(len(payload)) + payload

    def send_bytearray_short(self, payload):
        return self.send_short(len(payload)) + payload

    def send_uuid(self, payload):
        return payload.bytes

    def send_position(self, payload):
        x, y, z = payload
        return struct.pack(">Q", ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF))

    def send_metadata(self, payload):
        b = ""
        for index in payload:
            type_ = payload[index][0]
            value = payload[index][1]
            header = (type_ << 5) | index
            b += self.send_ubyte(header)
            if type_ == 0:
                b += self.send_byte(value)
            if type_ == 1:
                b += self.send_short(value)
            if type_ == 2:
                b += self.send_int(value)
            if type_ == 3:
                b += self.send_float(value)
            if type_ == 4:
                b += self.send_string(value)
            if type_ == 5:
                print "WIP 5"
            if type_ == 6:
                print "WIP 6"
            if type_ == 6:
                print "WIP 7"
        b += self.send_ubyte(0x7f)
        return b

    def send_bool(self, payload):
        if payload:
            return self.send_byte(1)
        else:
            return self.send_byte(0)
        

    # Similar to send_string, but uses a short as length prefix
    def send_short_string(self, stri):
        return self.send_short(len(stri)) + stri.encode("utf8")

    def send_byte_array(self, payload):
        return self.send_int(len(payload)) + payload

    def send_int_array(self, values):
        r = self.send_int(len(values))
        return r + struct.pack(">%di" % len(values), *values)

    def send_list(self, tag):
        # Check that all values are the same type
        r = ""
        typesList = []
        for i in tag:
            #print("list element type: %s" %i['type'])
            typesList.append(i['type'])
            if len(set(typesList)) != 1:
                # raise Exception("Types in list dosn't match!")
                return b''
        # If ok, then continue
        r += self.send_byte(typesList[0])  # items type
        r += self.send_int(len(tag))  # lenght
        for e in tag:  # send every tag
            r += self._ENCODERS[typesList[0]](e["value"])
        return r

    def send_comp(self, tag):
        r = ""
        for tage in tag:  # Send every tag
            r += self.send_tag(tage)
        r += "\x00"  # close compbound
        return r

    def send_tag(self, tag):
        r = self.send_byte(tag['type'])  # send type indicator
        r += self.send_short(len(tag["name"]))  # send lenght prefix
        r += tag["name"].encode("utf8")  # send name
        r += self._ENCODERS[tag["type"]](tag["value"])  # send tag
        return r

    def send_slot(self, slot):
        """Sending slots, such as {"id":98,"count":64,"damage":0,"nbt":None}"""
        r = self.send_short(slot["id"])
        if slot["id"] == -1:
            return r
        r += self.send_byte(slot["count"])
        r += self.send_short(slot["damage"])
        if slot["nbt"]:
            r += self.send_tag(slot['nbt'])
            # print(r)
        else:
            r += "\x00"
        return r

    # -- READING DATA TYPES -- #
    def recv(self, length):
        if length > 200:
            d = ""
            while len(d) < length:
                m = length - len(d)
                if m > 5000:
                    m = 5000
                d += self.socket.recv(m)
        else:  # $ find out why next line sometimes errors out bad file descriptor
            d = self.socket.recv(length)
            if len(d) == 0:
                raise EOFError("Packet was zero length, disconnecting")
#		while length > len(d):
#			print "Need %d more" % length - len(d)
#			d += self.socket.recv(length - len(d))
#			if not length == len(d):
#				print "ACTUAL PACKET NOT LONG %d %d" % (length, len(d))
#				print "Read more: %d" % len(self.socket.recv(1024))
            #raise EOFError("Actual length of packet was not as long as expected!")
        if self.recvCipher is None:
            return d
        return self.recvCipher.decrypt(d)

    def read_data(self, length):
        d = self.buffer.read(length)
        if len(d) == 0 and length is not 0:
            # print(self.obj)
            self.obj.disconnect(
                "Received no data or less data than expected - connection closed")
            return ""
        return d

    def read_byte(self):
        return struct.unpack("b", self.read_data(1))[0]

    def read_ubyte(self):
        return struct.unpack("B", self.read_data(1))[0]

    def read_long(self):
        return struct.unpack(">q", self.read_data(8))[0]

    def read_ulong(self):
        return struct.unpack(">Q", self.read_data(8))[0]

    def read_float(self):
        return struct.unpack(">f", self.read_data(4))[0]

    def read_int(self):
        return struct.unpack(">i", self.read_data(4))[0]

    def read_double(self):
        return struct.unpack(">d", self.read_data(8))[0]

    def read_bool(self):
        if self.read_data(1) == 0x01:
            return True
        else:
            return False

    def read_short(self):
        return struct.unpack(">h", self.read_data(2))[0]

    def read_ushort(self):
        return struct.unpack(">H", self.read_data(2))[0]

    def read_bytearray(self):
        return self.read_data(self.read_varInt())

    def read_int_array(self):
        size = self.read_int()
        return [self.read_int() for _ in xrange(size)]

    def read_bytearray_short(self):
        return self.read_data(self.read_short())

    def read_position(self):
        position = struct.unpack(">Q", self.read_data(8))[0]
        if position == 0xFFFFFFFFFFFFFFFF:
            return None
        x = int(position >> 38)
        if (x & 0x2000000):
            x = (x & 0x1FFFFFF) - 0x2000000
        y = int((position >> 26) & 0xFFF)
        if (y & 0x800):
            y = (y & 0x4FF) - 0x800
        z = int(position & 0x3FFFFFF)
        if (z & 0x2000000):
            z = (z & 0x1FFFFFF) - 0x2000000
        return (x, y, z)

    def read_slot(self):
        id = self.read_short()
        if not id == -1:
            count = self.read_ubyte()
            damage = self.read_short()
            nbt = self.read_tag()
            #nbtCount = self.read_ubyte()
            #nbt = self.read_data(nbtCount)
            return {"id": id, "count": count, "damage": damage, "nbt": nbt}

    def read_varInt(self):
        total = 0
        shift = 0
        val = 0x80
        while val & 0x80:
            val = struct.unpack('B', self.read_data(1))[0]
            total |= ((val & 0x7F) << shift)
            shift += 7
        if total & (1 << 31):
            total = total - (1 << 32)
        return total

    def read_uuid(self):
        i = self.read_data(16)
        i = uuid.UUID(bytes=i)
        return i

    def read_string(self):
        return self.read_data(self.read_varInt())

    def read_json(self):
        return json.loads(self.read_string())

    def read_rest(self):
        return self.read_data(1024 * 1024)

    def read_metadata(self):
        data = {}
        while True:
            a = self.read_ubyte()
            if a == 0x7f:
                return data
            index = a & 0x1f
            type_ = a >> 5
            if type_ == 0:
                data[index] = (0, self.read_byte())
            if type_ == 1:
                data[index] = (1, self.read_short())
            if type_ == 2:
                data[index] = (2, self.read_int())
            if type_ == 3:
                data[index] = (3, self.read_float())
            if type_ == 4:
                data[index] = (4, self.read_string())
            if type_ == 5:
                data[index] = (5, self.read_slot())
            if type_ == 6:
                data[index] = (
                    6, (self.read_int(), self.read_int(), self.read_int()))
            # if type_ == 7:
            #	data[index] = ("float", (self.read_int(), self.read_int(), self.read_int()))
        return data

    def read_short_string(self):
        size = self.read_short()
        string = self.read_data(size)
        return string.decode("utf8")

    def read_comp(self):
        a = []
        done = 0
        while done == 0:
            b = self.read_tag()
            if b['type'] == 0:
                done = 1
                break
            a.append(b)
            # print(a)
        return a

    def read_tag(self):
        a = {}
        a["type"] = self.read_byte()
        if not a["type"] == 0:
            #print("NBT TYPE: %s" %a["type"])
            a["name"] = self.read_short_string()
            a["value"] = self._DECODERS[a["type"]]()
        return a

    def read_list(self):
        r = []
        type = self.read_byte()
        lenght = self.read_int()
        for l in range(lenght):
            b = {}
            b["type"] = type
            b["name"] = ""
            b["value"] = self._DECODERS[type]()
            r.append(b)
        return r
