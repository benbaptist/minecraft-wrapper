# -*- coding: utf-8 -*-

import socket
import threading
import time
import traceback
import json
import uuid

import utils.encryption as encryption

from core.storage import Storage
from client import Client
from packet import Packet

try:
    import requests
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False

UNIVERSAL_CONNECT = False # tells the client "same version as you" or does not disconnect dissimilar clients
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
        self.storage = Storage("proxy-data")

        self.privateKey = encryption.generate_key_pair()
        self.publicKey = encryption.encode_public_key(self.privateKey)

    def host(self):
        # get the protocol version from the server
        while not self.wrapper.server.state == 2:
            time.sleep(.2)
        try:
            self.pollServer()
        except Exception as e:
            self.log.error("Proxy could not poll the Minecraft server - are you sure that the ports are configured properly? (%s)" % e)
            self.log.getTraceback()

        while not self.socket:
            try:
                self.socket = socket.socket()
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind((self.wrapper.config["Proxy"]["proxy-bind"], self.wrapper.config["Proxy"]["proxy-port"]))
                self.socket.listen(5)
            except Exception as e:
                self.log.error("Proxy mode could not bind - retrying in five seconds (%s)" % e)
                self.log.getTraceback()
                self.socket = False
            time.sleep(5)
        while not self.wrapper.halt:
            try:
                sock, addr = self.socket.accept()
                client = Client(sock, addr, self.wrapper, self.publicKey, self.privateKey, self)

                t = threading.Thread(target=client.handle, args=())
                t.daemon = True
                t.start()

                self.clients.append(client)

                self.removeStaleClients()
                
            except Exception as e:  # Not quite sure what's going on
                self.log.error("An error has occured in the proxy (%s)" % e)
                self.log.error(traceback.format_exc())
                try:
                    client.disconnect(e)
                except Exception as ex:
                    self.log.error("Failed to disconnect client (%s)" % ex)

    def removeStaleClients(self):
        try:
            for i, client in enumerate(self.wrapper.proxy.clients):
                if client.abort:
                    del self.wrapper.proxy.clients[i]
        except Exception as e:
            raise e # rethrow exception


    def pollServer(self):
        sock = socket.socket()
        sock.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
        packet = Packet(sock, self)

        packet.send(0x00, "varint|string|ushort|varint", (5, "localhost", self.wrapper.config["Proxy"]["server-port"], 1))
        packet.send(0x00, "", ())
        packet.flush()

        while True:
            pkid, original = packet.grabPacket()
            if pkid == 0x00:
                data = json.loads(packet.read("string:response")["response"])
                self.wrapper.server.protocolVersion = data["version"]["protocol"]
                self.wrapper.server.version = data["version"]["name"]
                break
        sock.close()

    def getClientByServerUUID(self, uuid):
        for client in self.clients:
            if str(client.serverUUID) == str(uuid):
                self.uuidTranslate[str(uuid)] = str(client.uuid)
                return client
        # if uuid in self.uuidTranslate:
        #     return uuid.UUID(hex=self.uuidTranslate[uuid])
        return False # no client

    def banUUID(self, uuid, reason="Banned by an operator", source="Server"):
        """This is all wrong - needs to ban uuid, not username """
        if not self.storage.key("banned-uuid"):
            self.storage.key("banned-uuid", {})
        self.storage.key("banned-uuid")[str(uuid)] = {
            "reason": reason,
            "source": source,
            "created": time.time(), 
            "name": self.lookupUUID(uuid)["name"] # wrong
        }

    def banIP(self, ipaddress, reason="Banned by an operator", source="Server"):
        if not self.storage.key("banned-ip"):
            self.storage.key("banned-ip", {})
        self.storage.key("banned-ip")[ipaddress] = {
            "reason": reason, 
            "source": source, 
            "created": time.time()
        }
        for i in self.wrapper.server.players:
            player = self.wrapper.server.players[i]
            if str(player.client.addr[0]) == str(ipaddress):
                self.wrapper.server.console("kick %s Your IP is Banned!" % str(player.username))

    def pardonIP(self, ipaddress):
        if self.storage.key("banned-ip"):
            if str(ipaddress) in self.storage.key("banned-ip"):
                try:
                    del self.storage.key("banned-ip")[str(ipaddress)]
                    return True
                except Exception as e:
                    self.log.warn("Failed to pardon %s (%s)" % (str(ipaddress), e))
                    return False
        self.log.warn("Could not find %s to pardon them" % str(ipaddress))
        return False

    def isUUIDBanned(self, uuid):  # Check if the UUID of the user is banned
        if not self.storage.key("banned-uuid"):
            self.storage.key("banned-uuid", {})
        return (uuid in self.storage.key("banned-uuid"))

    def isAddressBanned(self, address):  # Check if the IP address is banned
        if not self.storage.key("banned-ip"):
            self.storage.key("banned-ip", {})
        return (address in self.storage.key("banned-ip"))

    def getSkinTexture(self, uuid):
        if uuid not in self.skins:
            return False
        if uuid in self.skinTextures:
            return self.skinTextures[uuid]
        skinBlob = json.loads(self.skins[uuid].decode("base64"))
        if "SKIN" not in skinBlob["textures"]: # Player has no skin, so set to Alex [fix from #160]
            skinBlob["textures"]["SKIN"] = {
                "url": "http://hydra-media.cursecdn.com/minecraft.gamepedia.com/f/f2/Alex_skin.png"
            }
        r = requests.get(skinBlob["textures"]["SKIN"]["url"])
        if r.status_code == 200:
            self.skinTextures[str(uuid)] = r.content.encode("base64")
            return self.skinTextures[uuid]
        else:
            self.log.warn("Could not fetch skin texture! (status code %d)" % r.status_code)
            return False