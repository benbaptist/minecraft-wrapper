# -*- coding: utf-8 -*-

import socket
import threading
import time
import json

import mcpacket

from api.entity import Entity

from packet import Packet

UNIVERSAL_CONNECT = False # tells the client "same version as you" or does not disconnect dissimilar clients
HIDDEN_OPS = ["SurestTexas00", "BenBaptist"]

class Server:
    def __init__(self, client, wrapper, ip=None, port=None):
        self.client = client
        self.wrapper = wrapper
        self.ip = ip
        self.port = port
        self.abort = False
        self.isServer = True
        self.proxy = wrapper.proxy
        self.lastPacketIDs = []

        self.state = State.INIT
        self.packet = None
        self.version = self.wrapper.server.protocolVersion
        self.log = wrapper.log
        self.safe = False
        self.eid = None

        # Determine packet set to use (backwards compatibility)
        if self.version >= mcpacket.PROTOCOLv1_9REL1:
            self.pktSB = mcpacket.ServerBound19
            self.pktCB = mcpacket.ClientBound19
        else:
            self.pktSB = mcpacket.ServerBound18
            self.pktCB = mcpacket.ClientBound18

    def connect(self):
        self.socket = socket.socket()
        if self.ip is None:
            self.socket.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
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
        self.log.debug("Last packet IDs (Server -> Client) of player %s before disconnection: \n%s", self.username, self.lastPacketIDs)
        self.abort = True
        self.packet = None
        try:
            self.socket.close()
        except Exception as e:
            pass

        if not self.client.isLocal and kill_client:  # Ben's cross-server hack
            self.client.isLocal = True
            self.client.send(self.pktCB.CHANGE_GAME_STATE, "ubyte|float", (1, 0))  # "end raining"
            self.client.send(self.pktCB.CHAT_MESSAGE, "string|byte", ("{text:'Disconnected from server: %s', color:red}" % reason.replace("'", "\\'"), 0))
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
            except Exception as e:
                self.log.exception("Failed to set client.server.eid! serverEid: %s, Eid: %s", client.server.eid, eid)
        return False

    def getPlayerContext(self, username):
        try:
            return self.wrapper.server.players[username]
        except Exception as e:
            return False

    def flush(self):
        while not self.abort:
            self.packet.flush()
        # try:
        #   self.packet.flush()
        # except Exception as e:
        #   self.exception("Error while flushing, stopping")
        #   self.close()
        #   break
            time.sleep(0.03)

    def parse(self, pkid, original):  # client - bound parse ("Server" class connection)
        """
        Client-bound "Server Class"
        """
        if pkid == 0x00 and self.state < State.ACTIVE: # disconnect, I suppose...
            message = self.read("string:string")
            self.log.info("Disconnected from server: %s", message["string"])
            self.client.disconnect(message)
            self.log.trace("(PROXY SERVER) -> Parsed 0x00 packet with server state < 3")
            return False

        # handle keep alive packets - DISABLED until github #5 is resolved
        # if pkid == self.pktCB.KEEP_ALIVE and self.state == State.ACTIVE:
        #     if self.client.version > 7:
        #         pkid = self.read("varint:i")["i"]
        #         if pkid is not None:
        #             self.send(self.pktSB.KEEP_ALIVE, "varint", (pkid,))
        #     self.log.trace("(PROXY SERVER) -> Parsed KEEP_ALIVE packet with server state 3 (ACTIVE)")
        #     return False

        if pkid == 0x01 and self.state == State.LOGIN:
            # This is throwing a malformed json exception when online mode is set to true, this should be a json string
            self.client.disconnect("Server is online mode. Please turn it off in server.properties. Wrapper.py will handle authentication on its own, so do not worry about hackers.")
            self.log.trace("(PROXY SERVER) -> Parsed 0x01 packet with server state 2 (LOGIN)")
            return False

        if pkid == 0x02 and self.state == State.LOGIN: # Login Success - UUID & Username are sent in this packet
            self.state = State.ACTIVE
            self.log.trace("(PROXY SERVER) -> Parsed 0x02 packet with server state 2 (LOGIN)")
            return False

        if pkid == self.pktCB.JOIN_GAME and self.state == State.ACTIVE:
            if self.version < mcpacket.PROTOCOL_1_9_1_PRE:
                data = self.read("int:eid|ubyte:gamemode|byte:dimension|ubyte:difficulty|ubyte:max_players|string:level_type")
            else:
                data = self.read("int:eid|ubyte:gamemode|int:dimension|ubyte:difficulty|ubyte:max_players|string:level_type")
            self.log.trace("(PROXY SERVER) -> Parsed JOIN_GAME packet with server state 3 (ACTIVE):\n%s", data)
            oldDimension = self.client.dimension
            self.client.gamemode = data["gamemode"]
            self.client.dimension = data["dimension"]
            self.client.eid = data["eid"] # This is the EID of the player on this particular server - not always the EID that the client is aware of  
            if self.client.handshake:
                dimensions = [-1, 0, 1]
                if oldDimension == self.client.dimension:
                    for i in dimensions:
                        if i != oldDimension:
                            dim = i
                            break
                    self.client.send(self.pktCB.RESPAWN, "int|ubyte|ubyte|string", (i, data["difficulty"], data["gamemode"], data["level_type"]))
                self.client.send(self.pktCB.RESPAWN, "int|ubyte|ubyte|string", (self.client.dimension, data["difficulty"], data["gamemode"], data["level_type"]))
                # self.client.send(0x01, "int|ubyte|byte|ubyte|ubyte|string|bool", (self.eid, self.client.gamemode, self.client.dimension, data["difficulty"], data["max_players"], data["level_type"], False))
                self.eid = data["eid"]
                self.safe = True
                return False
            else:
                self.client.eid = data["eid"]
                self.safe = True
            self.client.handshake = True
            self.client.send(self.pktCB.CHANGE_GAME_STATE, "ubyte|float", (3, self.client.gamemode))
            
            if UNIVERSAL_CONNECT is True:
                clientversion = self.packet.version
                serverversion = self.wrapper.server.protocolVersion
                if clientversion < mcpacket.PROTOCOL_1_9_1_PRE <= serverversion:
                    self.client.send(self.pktCB.JOIN_GAME, "int|ubyte|byte|ubyte|ubyte|string", (data["eid"], data["gamemode"], data["dimension"], data["difficulty"], data["max_players"], data["level_type"]))
                    return False

        if pkid == self.pktCB.CHAT_MESSAGE and self.state == State.ACTIVE:
            rawdata = self.read("string:json|byte:position")
            rawstring = rawdata["json"]
            position = rawdata["position"]
            try:
                data = json.loads(rawstring)
                self.log.trace("(PROXY SERVER) -> Parsed CHAT_MESSAGE packet with server state 3 (ACTIVE):\n%s", data)
            except Exception as e:
                return

            payload = self.wrapper.callEvent("player.chatbox", {"player": self.client.getPlayerObject(), "json": data})

            if payload:
                return True
            elif not payload:
                return False
            elif type(payload) == dict:  # return a "chat" protocol formatted dictionary http://wiki.vg/Chat
                chatmsg = json.dumps(payload)
                self.client.send(self.pktCB.CHAT_MESSAGE, "string|byte", (chatmsg, position))
                return False
            elif type(payload) == str:  # return a string-only object
                self.client.send(self.pktCB.CHAT_MESSAGE, "string|byte", (payload, position))
                return False

            if "translate" in data:
                if data["translate"] == "chat.type.admin":
                    return False

        if pkid == 0x03 and self.state == State.LOGIN:  # Set Compression
            data = self.read("varint:threshold")
            if data["threshold"] != -1:
                self.packet.compression = True
                self.packet.compressThreshold = data["threshold"]
            else:
                self.packet.compression = False
                self.packet.compressThreshold = -1
            self.log.trace("(PROXY SERVER) -> Parsed 0x03 packet with server state 2 (LOGIN):\n%s", data)
            return False

        if self.state < State.ACTIVE:
            return True  # remaining packets are parsed solely per "play" state

        if pkid == self.pktCB.TIME_UPDATE:
            data = self.read("long:worldage|long:timeofday")
            self.wrapper.server.timeofday = data["timeofday"]
            self.log.trace("(PROXY SERVER) -> Parsed TIME_UPDATE packet:\n%s", data)
            return True

        if pkid == self.pktCB.SPAWN_POSITION:  # Spawn Position
            data = self.read("position:spawn")
            self.wrapper.server.spawnPoint = data["spawn"]
            self.log.trace("(PROXY SERVER) -> Parsed SPAWN_POSITION packet:\n%s", data)
            return True

        if pkid == self.pktCB.RESPAWN:  # Respawn Packet
            data = self.read("int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
            self.client.gamemode = data["gamemode"]
            self.client.dimension = data["dimension"]
            self.log.trace("(PROXY SERVER) -> Parsed RESPAWN packet:\n%s", data)
            return True

        if pkid == self.pktCB.PLAYER_POSLOOK:  # Player Position and Look
            data = self.read("double:x|double:y|double:z|float:yaw|float:pitch")
            x, y, z, yaw, pitch = data["x"], data["y"], data["z"], data["yaw"], data["pitch"]
            self.client.position = (x, y, z)
            self.log.trace("(PROXY SERVER) -> Parsed PLAYER_POSLOOK packet:\n%s", data)
            return True

        if pkid == self.pktCB.USE_BED:  # Use Bed
            data = self.read("varint:eid|position:location")
            self.log.trace("(PROXY SERVER) -> Parsed USE_BED packet:\n%s", data)
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.USE_BED, "varint|position", (self.client.eid, data["location"]))
                return False
            return True

        if pkid == self.pktCB.ANIMATION: # Animation
            data = self.read("varint:eid|ubyte:animation")
            self.log.trace("(PROXY SERVER) -> Parsed ANIMATION packet:\n%s", data)
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.ANIMATION, "varint|ubyte", (self.client.eid, data["animation"]))
                return False
            return True

        if pkid == self.pktCB.SPAWN_PLAYER:  # Spawn Player
            if self.version < mcpacket.PROTOCOL_1_9START:
                data = self.read("varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|short:item|rest:metadata")
                if data["item"] < 0: # A negative Current Item crashes clients (just in case)
                    data["item"] = 0
                clientserverid = self.proxy.getClientByOfflineServerUUID(data["uuid"])
                if clientserverid:
                    self.client.send(self.pktCB.SPAWN_PLAYER, "varint|uuid|int|int|int|byte|byte|short|raw", (
                        data["eid"],
                        clientserverid.uuid, # This is an MCUUID object
                        data["x"],
                        data["y"],
                        data["z"],
                        data["yaw"],
                        data["pitch"],
                        data["item"],
                        data["metadata"])
                    )
                self.log.trace("(PROXY SERVER) -> Parsed SPAWN_PLAYER packet:\n%s", data)
                return False
            else:
                data = self.read("varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|rest:metadata")
                clientserverid = self.proxy.getClientByOfflineServerUUID(data["uuid"])
                if clientserverid:
                    self.client.send(self.pktCB.SPAWN_PLAYER, "varint|uuid|int|int|int|byte|byte|raw", (
                        data["eid"],
                        clientserverid.uuid, # This is an MCUUID object
                        data["x"],
                        data["y"],
                        data["z"],
                        data["yaw"],
                        data["pitch"],
                        data["metadata"])
                    )
                    self.log.trace("(PROXY SERVER) -> Parsed SPAWN_PLAYER packet:\n%s", data)
                    return False
            return True

        if pkid == self.pktCB.SPAWN_OBJECT:  # self.pktCB.SPAWN_OBJECT and self.state >= State.ACTIVE: # Spawn Object
            if self.version < mcpacket.PROTOCOL_1_9START:
                data = self.read("varint:eid|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw")
                entityuuid = None
            else:
                data = self.read("varint:eid|uuid:objectUUID|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|int:info|short:velocityX|short:velocityY|short:velocityZ")
                entityuuid = data["objectUUID"]
            eid, type_, x, y, z, pitch, yaw = data["eid"], data["type_"], data["x"], data["y"], data["z"], data["pitch"], data["yaw"]
            self.log.trace("(PROXY SERVER) -> Parsed SPAWN_OBJECT packet:\n%s", data)
            if not self.wrapper.server.world:
                return
            self.wrapper.server.world.entities[data["eid"]] = Entity(eid, entityuuid, type_, (x, y, z), (pitch, yaw), True)
            return True

        if pkid == self.pktCB.SPAWN_MOB:  # Spawn Mob
            if self.version < mcpacket.PROTOCOL_1_9START:
                data = self.read("varint:eid|ubyte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|byte:head_pitch|short:velocityX|short:velocityY|short:velocityZ|rest:metadata")
                entityuuid = None
            else:
                data = self.read("varint:eid|uuid:entityUUID|ubyte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|byte:head_pitch|short:velocityX|short:velocityY|short:velocityZ|rest:metadata")
                entityuuid = data["entityUUID"]
            eid, type_, x, y, z, pitch, yaw, head_pitch = data["eid"], data["type_"], data["x"], data["y"], data["z"], data["pitch"], data["yaw"], data["head_pitch"]
            self.log.trace("(PROXY SERVER) -> Parsed SPAWN_MOB packet:\n%s", data)
            if not self.wrapper.server.world:
                return
            # this will need entity UUID's added at some point
            self.wrapper.server.world.entities[data["eid"]] = Entity(eid, entityuuid, type_, (x, y, z), (pitch, yaw, head_pitch), False)
        
        if pkid == self.pktCB.ENTITY_RELATIVE_MOVE:  # Entity Relative Move
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("varint:eid|byte:dx|byte:dy|byte:dz")
            self.log.trace("(PROXY SERVER) -> Parsed ENTITY_RELATIVE_MOVE packet:\n%s", data)
            if not self.wrapper.server.world:
                return
            if self.wrapper.server.world.getEntityByEID(data["eid"]) is not None:
                self.wrapper.server.world.getEntityByEID(data["eid"]).moveRelative((data["dx"], data["dy"], data["dz"]))

        if pkid == self.pktCB.ENTITY_TELEPORT:  # Entity Teleport
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("varint:eid|int:x|int:y|int:z|byte:yaw|byte:pitch")
            self.log.trace("(PROXY SERVER) -> Parsed ENTITY_TELEPORT packet:\n%s", data)
            if not self.wrapper.server.world:
                return
            if self.wrapper.server.world.getEntityByEID(data["eid"]) is not None:
                self.wrapper.server.world.getEntityByEID(data["eid"]).teleport((data["x"], data["y"], data["z"]))
        
        if pkid == self.pktCB.ENTITY_HEAD_LOOK:
            data = self.read("varint:eid|byte:angle")
            self.log.trace("(PROXY SERVER) -> Parsed ENTITY_HEAD_LOOK packet:\n%s", data)
        
        if pkid == self.pktCB.ENTITY_STATUS:  # Entity Status
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("int:eid|byte:status")
            self.log.trace("(PROXY SERVER) -> Parsed ENTITY_STATUS packet:\n%s", data)
        
        if pkid == self.pktCB.ATTACH_ENTITY:  # Attach Entity
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("varint:eid|varint:vid|bool:leash")
            eid, vid, leash = data["eid"], data["vid"], data["leash"]
            player = self.getPlayerByEID(eid)
            self.log.trace("(PROXY SERVER) -> Parsed ATTACH_ENTITY packet:\n%s", data)
            if player is None:
                return
            if eid == self.eid:
                if vid == -1:
                    self.wrapper.callEvent("player.unmount", {"player": player})
                    self.client.riding = None
                else:
                    self.wrapper.callEvent("player.mount", {"player": player, "vehicle_id": vid, "leash": leash})
                    if not self.wrapper.server.world:
                        return
                    self.client.riding = self.wrapper.server.world.getEntityByEID(vid)
                    self.wrapper.server.world.getEntityByEID(vid).rodeBy = self.client
                if eid != self.client.eid:
                    self.client.send(self.pktCB.ATTACH_ENTITY, "varint|varint|bool", (self.client.eid, vid, leash))
                    return False
        
        if pkid == self.pktCB.ENTITY_METADATA:  # Entity Metadata
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("varint:eid|rest:metadata")
            self.log.trace("(PROXY SERVER) -> Parsed ENTITY_METADATA packet:\n%s", data)
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.ENTITY_METADATA,"varint|raw", (self.client.eid, data["metadata"]))
                return False
        
        if pkid == self.pktCB.ENTITY_EFFECT: # Entity Effect
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("varint:eid|byte:effect_id|byte:amplifier|varint:duration|bool:hide")
            self.log.trace("(PROXY SERVER) -> Parsed ENTITY_EFFECT packet:\n%s", data)
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.ENTITY_EFFECT, "varint|byte|byte|varint|bool", (self.client.eid, data["effect_id"], data["amplifier"], data["duration"], data["hide"]))
                return False
        
        if pkid == self.pktCB.REMOVE_ENTITY_EFFECT: # Remove Entity Effect
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("varint:eid|byte:effect_id")
            self.log.trace("(PROXY SERVER) -> Parsed REMOVE_ENTITY_EFFECT packet:\n%s", data)
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.REMOVE_ENTITY_EFFECT, "varint|byte", (self.client.eid, data["effect_id"]))
                return False
        
        if pkid == self.pktCB.ENTITY_PROPERTIES:  # Entity Properties
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("varint:eid|rest:properties")
            self.log.trace("(PROXY SERVER) -> Parsed ENTITY_PROPERTIES packet:\n%s", data)
            if data["eid"] == self.eid:
                self.client.send(self.pktCB.ENTITY_PROPERTIES, "varint|raw", (self.client.eid, data["properties"]))
                return False

        # if pkid == self.pktCB.CHUNK_DATA: # Chunk Data
        #     if self.client.packet.compressThreshold == -1:
        #         self.log.debug("Client compression enabled, setting to 256")
        #         self.client.packet.setCompression(256)
        #     self.log.trace("(PROXY SERVER) -> Parsed CHUNK_DATA packet")


        # if self.pktCB.BLOCK_CHANGE: # Block Change - disabled - not doing anything at this point
        #     if self.version < mcpacket.PROTOCOLv1_8START:
        #         # TODO: These packets need to be filtered for cross-server stuff.
        #         return True
        #     data = self.read("position:location|varint:pkid")
        #     self.log.trace("(PROXY SERVER) -> Parsed BLOCK_CHANGE packet:\n%s", data)
        
        if pkid == self.pktCB.MAP_CHUNK_BULK: # Map Chunk Bulk (no longer exists in 1.9)
            if self.version > mcpacket.PROTOCOLv1_8START and self.version < mcpacket.PROTOCOL_1_9START:
                data = self.read("bool:skylight|varint:chunks")
                self.log.trace("(PROXY SERVER) -> Parsed MAP_CHUNK_BULK packet:\n%s", data)
                for chunk in xrange(data["chunks"]):
                    meta = self.read("int:x|int:z|ushort:primary")
                    bitmask = bin(meta["primary"])[2:].zfill(16)
                    chunkColumn = bytearray()
                    for bit in bitmask:
                        if bit == "1":
                            # packetanisc
                            chunkColumn += bytearray(self.packet.read_data(16 * 16 * 16 * 2))
                            if self.client.dimension == 0:
                                metalight = bytearray(self.packet.read_data(16 * 16 * 16))
                            if data["skylight"]:
                                skylight = bytearray(self.packet.read_data(16 * 16 * 16))
                        else:
                            # Null Chunk
                            chunkColumn += bytearray(16 * 16 * 16 * 2)
        
        if pkid == self.pktCB.CHANGE_GAME_STATE:  # Change Game State
            data = self.read("ubyte:reason|float:value")
            if data["reason"] == 3:
                self.client.gamemode = data["value"]
            self.log.trace("(PROXY SERVER) -> Parsed CHANGE_GAME_STATE packet:\n%s", data)
        
        if pkid == self.pktCB.SET_SLOT:  # Set Slot
            if self.version < mcpacket.PROTOCOLv1_8START:
                # TODO: These packets need to be filtered for cross-server stuff.
                return True
            data = self.read("byte:wid|short:slot|slot:data")
            if data["wid"] == 0:
                self.client.inventory[data["slot"]] = data["data"]
            self.log.trace("(PROXY SERVER) -> Parsed SET_SLOT packet:\n%s", data)

        # if pkid == 0x30: # Window Items
        #   data = self.read("byte:wid|short:count")
        #   if data["wid"] == 0:
        #       for slot in range(1, data["count"]):
        #           data = self.read("slot:data")
        #           self.client.inventory[slot] = data["data"]
        #   self.log.trace("(PROXY SERVER) -> Parsed 0x30 packet:\n%s", data)

        if pkid == self.pktCB.PLAYER_LIST_ITEM:  # player list item
            if self.version > mcpacket.PROTOCOLv1_8START:
                head = self.read("varint:action|varint:length")
                z = 0
                while z < head["length"]:
                    serverUUID = self.read("uuid:uuid")["uuid"]
                    playerclient = self.client.proxy.getClientByOfflineServerUUID(serverUUID)
                    if not playerclient:
                        z += 1
                        continue
                    try:
                        uuid = playerclient.uuid # This is an MCUUID object, how could this fail? All clients have a uuid attribute
                    except Exception as e:
                        # uuid = playerclient
                        self.log.exception("playercleint.uuid failed in playerlist item (%s)", e)
                        z += 1
                        continue
                    z += 1
                    if head["action"] == 0:
                        properties = playerclient.properties
                        raw = ""
                        for prop in properties:
                            raw += self.client.packet.send_string(prop["name"])
                            raw += self.client.packet.send_string(prop["value"])
                            if "signature" in prop:
                                raw += self.client.packet.send_bool(True)
                                raw += self.client.packet.send_string(prop["signature"])
                            else:
                                raw += self.client.packet.send_bool(False)
                        raw += self.client.packet.send_varInt(0)
                        raw += self.client.packet.send_varInt(0)
                        raw += self.client.packet.send_bool(False)
                        self.client.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|string|varint|raw", (0, 1, playerclient.uuid, playerclient.username, len(properties), raw))
                    elif head["action"] == 1:
                        data = self.read("varint:gamemode")
                        self.log.trace("(PROXY SERVER) -> Parsed PLAYER_LIST_ITEM packet:\n%s", data)
                        self.client.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|varint", (1, 1, uuid, data["gamemode"]))
                    elif head["action"] == 2:
                        data = self.read("varint:ping")
                        self.log.trace("(PROXY SERVER) -> Parsed PLAYER_LIST_ITEM packet:\n%s", data)
                        self.client.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|varint", (2, 1, uuid, data["ping"]))
                    elif head["action"] == 3:
                        data = self.read("bool:has_display")
                        if data["has_display"]:
                            data = self.read("string:displayname")
                            self.log.trace("(PROXY SERVER) -> Parsed PLAYER_LIST_ITEM packet:\n%s", data)
                            self.client.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|bool|string", (3, 1, uuid, True, data["displayname"]))
                        else:
                            self.client.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|varint", (3, 1, uuid, False))
                    elif head["action"] == 4:
                        self.client.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid", (4, 1, uuid))
                    return False

        if pkid == self.pktCB.DISCONNECT:  # Disconnect
            message = self.read("json:json")["json"]
            self.log.info("Disconnected from server: %s", message)
            if not self.client.isLocal:
                self.close()
            else:
                self.client.disconnect(message)
            self.log.trace("(PROXY SERVER) -> Parsed DISCONNECT packet")
            return False

        return True # Default case

    def handle(self):
        try:
            while not self.abort:
                try:
                    pkid, original = self.packet.grabPacket()
                    self.lastPacketIDs.append((hex(pkid), len(original)))
                    if len(self.lastPacketIDs) > 10:
                        for i, v in enumerate(self.lastPacketIDs):
                            del self.lastPacketIDs[i]
                            break
                except EOFError as eof:
                    # This error is often erroneous, see https://github.com/suresttexas00/minecraft-wrapper/issues/30
                    self.log.exception("Packet EOF (%s)", eof)
                    self.close()
                    break
                except Exception as e1:
                    # Bad file descriptor often occurs, see https://github.com/suresttexas00/minecraft-wrapper/issues/30
                    self.log.exception("Failed to grab packet [SERVER] (%s):", e1)
                    return
                if self.client.abort:
                    self.close()
                    break
                if self.parse(pkid, original) and self.safe:
                    self.client.sendRaw(original)
        except Exception as e2:
            self.log.exception("Error in the [SERVER] -> [CLIENT] handle (%s):", e2)
            self.close()

class State:
    """
    This class represents proxy Server states
    """
    # TODO: Provide details on each state
    INIT = 0
    MOTD = 1
    LOGIN = 2
    ACTIVE = 3
    AUTHORIZING = 4
