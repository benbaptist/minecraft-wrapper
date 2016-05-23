# -*- coding: utf-8 -*-

# py3 compliant (syntax only)

import socket
import threading
import time
import json

import proxy.mcpacket as mcpacket
from proxy.packet import Packet

from api.entity import Entity

try:  # Manually define an xrange builtin that works indentically on both (to take advantage of xrange's speed in 2)
    xxrange = xrange
except NameError:
    xxrange = range


# noinspection PyBroadException,PyUnusedLocal
class ServerConnection:
    def __init__(self, client, wrapper, ip=None, port=None):
        """
        Server receives "CLIENT BOUND" packets from server.  These are what get parsed (CLIENT BOUND format).
        'client.packet.send' - sends a packet to the client (use CLIENT BOUND packet format)
        'self.packet.send' - sends a packet back to the server (use SERVER BOUND packet format)
        This part of proxy 'pretends' to be the client interacting with the server.


        Args:
            client: The client to connect to the server
            wrapper:
            ip:
            port:

        Returns:

        """
        self.client = client
        self.wrapper = wrapper
        self.proxy = wrapper.proxy
        self.log = wrapper.log
        self.ip = ip
        self.port = port

        self.abort = False
        self.isServer = True
        self.server_socket = socket.socket()

        self.state = ProxServState.HANDSHAKE
        self.packet = None
        self.lastPacketIDs = []

        self.version = self.wrapper.javaserver.protocolVersion
        self._refresh_server_version()
        self.username = self.client.username

        self.eid = None

        self.headlooks = 0

    def _refresh_server_version(self):
        # Get serverversion for mcpacket use
        try:
            self.version = self.wrapper.javaserver.protocolVersion
        except AttributeError:
            # Default to 1.8 if no server is running
            # This can be modified to any version
            self.version = 47

        # Determine packet types - currently 1.8 is the lowest version supported.
        if mcpacket.Server194.end() >= self.version >= mcpacket.Server194.start():  # 1.9.4
            self.pktSB = mcpacket.Server194
            self.pktCB = mcpacket.Client194
        elif mcpacket.Server19.end() >= self.version >= mcpacket.Server19.start():  # 1.9 - 1.9.3 Pre 3
            self.pktSB = mcpacket.Server19
            self.pktCB = mcpacket.Client19
        else:  # 1.8 default
            self.pktSB = mcpacket.Server18
            self.pktCB = mcpacket.Client18

    def send(self, packetid, xpr, payload):  # not supported... no docstring. For backwards compatability purposes only.
        self.log.debug("deprecated server.send() called (by a plugin)")
        self.packet.send(packetid, xpr, payload)
        pass

    def connect(self):
        if self.ip is None:
            self.server_socket.connect(("localhost", self.wrapper.config["Proxy"]["server-port"]))
        else:
            self.server_socket.connect((self.ip, self.port))
            self.client.isLocal = False

        self.packet = Packet(self.server_socket, self)
        self.packet.version = self.client.clientversion

        t = threading.Thread(target=self.flush, args=())
        t.daemon = True
        t.start()

    def close(self, reason="Disconnected", kill_client=True):
        self.log.debug("Last packet IDs (Server -> Client) of player %s before disconnection: \n%s", self.username,
                       self.lastPacketIDs)
        self.abort = True
        self.packet = None
        try:
            self.server_socket.close()
        except OSError:
            pass

        if not self.client.isLocal and kill_client:  # Ben's cross-server hack
            self.client.isLocal = True
            self.client.packet.send(self.pktCB.CHANGE_GAME_STATE, "ubyte|float", (1, 0))  # "end raining"
            self.client.packet.send(self.pktCB.CHAT_MESSAGE, "string|byte",
                                    ("{text:'Disconnected from server: %s', color:red}" %
                                     reason.replace("'", "\\'"), 0))
            self.client.connect()
            return

        # I may remove this later so the client can remain connected upon server disconnection
        # self.client.packet.send(0x02, "string|byte",
        #                         (json.dumps({"text": "Disconnected from server. Reason: %s" % reason,
        #                                       "color": "red"}),0))
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
            return self.wrapper.javaserver.players[username]
        except Exception as e:  # This could be masking an issue and would result in "False" player objects
            self.log.error("getPlayerContext failed to get player %s: %s", username, e)
            return False

    def flush(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket.error:
                self.log.debug("serverconnection socket closed (bad file descriptor), closing flush..")
                self.abort = True
                break
            time.sleep(0.03)

    def parse(self, pkid):  # client - bound parse ("Server" class connection)

        if pkid == 0x00 and self.state < ProxServState.PLAY:  # disconnect, I suppose...
            message = self.packet.read("string:string")
            self.log.info("Disconnected from server: %s", message["string"])
            self.client.disconnect(message)
            self.log.trace("(PROXY SERVER) -> Parsed 0x00 packet with server state < 3")
            return False

        if self.state == ProxServState.PLAY:
            # handle keep alive packets from server... nothing special here; we will just keep the server connected.
            if pkid == self.pktCB.KEEP_ALIVE:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    data = self.packet.read("int:payload")
                    self.packet.send(self.pktSB.KEEP_ALIVE, "int", (data["payload"],))
                else:  # self.version >= mcpacket.PROTOCOL_1_8START: - future elif in case protocol changes again.
                    data = self.packet.read("varint:payload")
                    self.packet.send(self.pktSB.KEEP_ALIVE, "varint", (data["payload"],))
                self.log.trace("(PROXY SERVER) -> Parsed KEEP_ALIVE packet with server state 3 (PLAY)")
                return False

            elif pkid == self.pktCB.CHAT_MESSAGE:
                rawdata = self.packet.read("string:json|byte:position")
                rawstring = rawdata["json"]
                position = rawdata["position"]
                try:
                    data = json.loads(rawstring.decode('utf-8'))  # py3
                    self.log.trace("(PROXY SERVER) -> Parsed CHAT_MESSAGE packet with server state 3 (PLAY):\n%s", data)
                except Exception as e:
                    return

                payload = self.wrapper.events.callevent("player.chatbox", {"player": self.client.getPlayerObject(),
                                                                           "json": data})

                if payload is False:  # reject the packet .. no chat gets sent to the client
                    return False
                #
                # - this packet is headed to a client.  The plugin's modification could be just a simple "Hello There"
                #   or the more complex minecraft json dictionary - or just a dictionary written as text:
                # """{"text":"hello there"}"""
                #   the minecraft protocol is just json-formatted string, but python users find dealing with a
                # dictionary easier
                #   when creating complex items like the minecraft chat object.
                elif type(payload) == dict:  # if payload returns a "chat" protocol dictionary http://wiki.vg/Chat
                    chatmsg = json.dumps(payload)
                    # send fake packet with modded payload
                    self.client.packet.send(self.pktCB.CHAT_MESSAGE, "string|byte", (chatmsg, position))
                    return False  # reject the orginal packet (it will not reach the client)
                elif type(payload) == str:  # if payload (plugin dev) returns a string-only object...
                    self.log.warning("player.Chatbox return payload sent as string")
                    self.client.packet.send(self.pktCB.CHAT_MESSAGE, "string|byte", (payload, position))
                    return False
                else:  # no payload, nor was the packet rejected.. packet passes to the client (and his chat)
                    return True  # just gathering info with these parses.

            elif pkid == self.pktCB.JOIN_GAME:
                if self.version < mcpacket.PROTOCOL_1_9_1PRE:
                    data = self.packet.read("int:eid|ubyte:gm|byte:dim|ubyte:diff|ubyte:max_players|string:level_type")
                else:
                    data = self.packet.read("int:eid|ubyte:gm|int:dim|ubyte:diff|ubyte:max_players|string:level_type")
                self.log.trace("(PROXY SERVER) -> Parsed JOIN_GAME packet with server state 3 (PLAY):\n%s", data)
                self.client.gamemode = data["gm"]
                self.client.dimension = data["dim"]
                self.client.eid = data["eid"]  # This is the EID of the player on this particular server -
                # not always the EID that the client is aware of.

                # this is an attempt to clear the gm3 noclip issue on relogging.
                self.client.packet.send(self.pktCB.CHANGE_GAME_STATE, "ubyte|float", (3, self.client.gamemode))
                return True

            elif pkid == self.pktCB.TIME_UPDATE:
                data = self.packet.read("long:worldage|long:timeofday")
                self.wrapper.javaserver.timeofday = data["timeofday"]
                self.log.trace("(PROXY SERVER) -> Parsed TIME_UPDATE packet:\n%s", data)
                return True

            elif pkid == self.pktCB.SPAWN_POSITION:
                data = self.packet.read("position:spawn")
                self.wrapper.javaserver.spawnPoint = data["spawn"]
                if self.client.position == (0, 0, 0):  # this is the actual point of a players "login: to the "server"
                    self.client.position = data["spawn"]
                    self.wrapper.events.callevent("player.spawned", {"player": self.client.getPlayerObject()})
                self.log.trace("(PROXY SERVER) -> Parsed SPAWN_POSITION packet:\n%s", data)
                return True

            elif pkid == self.pktCB.RESPAWN:
                data = self.packet.read("int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
                self.client.gamemode = data["gamemode"]
                self.client.dimension = data["dimension"]
                self.log.trace("(PROXY SERVER) -> Parsed RESPAWN packet:\n%s", data)
                return True

            elif pkid == self.pktCB.PLAYER_POSLOOK:
                data = self.packet.read("double:x|double:y|double:z|float:yaw|float:pitch")
                x, y, z, yaw, pitch = data["x"], data["y"], data["z"], data["yaw"], data["pitch"]
                self.client.position = (x, y, z)
                self.log.trace("(PROXY SERVER) -> Parsed PLAYER_POSLOOK packet:\n%s", data)
                return True

            elif pkid == self.pktCB.USE_BED:
                data = self.packet.read("varint:eid|position:location")
                self.log.trace("(PROXY SERVER) -> Parsed USE_BED packet:\n%s", data)
                if data["eid"] == self.eid:
                    self.client.packet.send(self.pktCB.USE_BED, "varint|position", (self.client.eid, data["location"]))
                    return False
                return True

            elif pkid == self.pktCB.ANIMATION:
                data = self.packet.read("varint:eid|ubyte:animation")
                self.log.trace("(PROXY SERVER) -> Parsed ANIMATION packet:\n%s", data)
                if data["eid"] == self.eid:
                    self.client.packet.send(self.pktCB.ANIMATION, "varint|ubyte", (self.client.eid, data["animation"]))
                    return False
                return True

            elif pkid == self.pktCB.SPAWN_PLAYER:
                if self.version < mcpacket.PROTOCOL_1_9START:
                    data = self.packet.read(
                        "varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|short:item|rest:metadata")
                    if data["item"] < 0:  # A negative Current Item crashes clients (just in case)
                        data["item"] = 0
                    clientserverid = self.proxy.getClientByOfflineServerUUID(data["uuid"])
                    if clientserverid:
                        self.client.packet.send(self.pktCB.SPAWN_PLAYER, "varint|uuid|int|int|int|byte|byte|short|raw",
                                                (
                                                 data["eid"],
                                                 clientserverid.uuid,  # This is an MCUUID object
                                                 data["x"],
                                                 data["y"],
                                                 data["z"],
                                                 data["yaw"],
                                                 data["pitch"],
                                                 data["item"],
                                                 data["metadata"]))

                    self.log.trace("(PROXY SERVER) -> Parsed SPAWN_PLAYER packet:\n%s", data)
                    return False
                else:
                    data = self.packet.read("varint:eid|uuid:uuid|int:x|int:y|int:z|byte:yaw|byte:pitch|rest:metadata")
                    clientserverid = self.proxy.getClientByOfflineServerUUID(data["uuid"])
                    if clientserverid:
                        self.client.packet.send(self.pktCB.SPAWN_PLAYER, "varint|uuid|int|int|int|byte|byte|raw", (
                            data["eid"],
                            clientserverid.uuid,  # This is an MCUUID object
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

            elif pkid == self.pktCB.SPAWN_OBJECT:
                if self.version < mcpacket.PROTOCOL_1_9START:
                    data = self.packet.read("varint:eid|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw")
                    entityuuid = None
                else:
                    data = self.packet.read("varint:eid|uuid:objectUUID|byte:type_|int:x|int:y|int:z|byte:pitch|"
                                            "byte:yaw|int:info|short:velocityX|short:velocityY|short:velocityZ")
                    entityuuid = data["objectUUID"]
                eid, type_, x, y, z, pitch, yaw = \
                    data["eid"], data["type_"], data["x"], data["y"], data["z"], data["pitch"], data["yaw"]
                self.log.trace("(PROXY SERVER) -> Parsed SPAWN_OBJECT packet:\n%s", data)
                if not self.wrapper.javaserver.world:
                    return
                self.wrapper.javaserver.world.entities[data["eid"]] = Entity(
                        eid, entityuuid, type_, (x, y, z), (pitch, yaw), True)
                return True

            elif pkid == self.pktCB.SPAWN_MOB:
                if self.version < mcpacket.PROTOCOL_1_9START:
                    data = self.packet.read("varint:eid|ubyte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|"
                                            "byte:head_pitch|short:velocityX|short:velocityY|short:velocityZ|"
                                            "rest:metadata")
                    entityuuid = None
                else:
                    data = self.packet.read("varint:eid|uuid:entityUUID|ubyte:type_|int:x|int:y|int:z|"
                                            "byte:pitch|byte:yaw|byte:head_pitch|short:velocityX|short:velocityY|"
                                            "short:velocityZ|rest:metadata")
                    entityuuid = data["entityUUID"]
                eid, type_, x, y, z, pitch, yaw, head_pitch = \
                    data["eid"], data["type_"], data["x"], data["y"], data["z"], data["pitch"], data["yaw"], \
                    data["head_pitch"]
                self.log.trace("(PROXY SERVER) -> Parsed SPAWN_MOB packet:\n%s", data)
                if not self.wrapper.javaserver.world:
                    return
                # this will need entity UUID's added at some point
                self.wrapper.javaserver.world.entities[data["eid"]] = Entity(eid, entityuuid, type_, (x, y, z),
                                                                             (pitch, yaw, head_pitch), False)
                return True

            elif pkid == self.pktCB.ENTITY_RELATIVE_MOVE:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("varint:eid|byte:dx|byte:dy|byte:dz")
                self.log.trace("(PROXY SERVER) -> Parsed ENTITY_RELATIVE_MOVE packet:\n%s", data)
                if not self.wrapper.javaserver.world:
                    return
                if self.wrapper.javaserver.world.getEntityByEID(data["eid"]) is not None:
                    self.wrapper.javaserver.world.getEntityByEID(data["eid"]).moveRelative((data["dx"],
                                                                                            data["dy"], data["dz"]))
                return True

            elif pkid == self.pktCB.ENTITY_TELEPORT:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("varint:eid|int:x|int:y|int:z|byte:yaw|byte:pitch")
                self.log.trace("(PROXY SERVER) -> Parsed ENTITY_TELEPORT packet:\n%s", data)
                if not self.wrapper.javaserver.world:
                    return
                if self.wrapper.javaserver.world.getEntityByEID(data["eid"]) is not None:
                    self.wrapper.javaserver.world.getEntityByEID(data["eid"]).teleport((data["x"],
                                                                                        data["y"],
                                                                                        data["z"]))
                return True

            elif pkid == self.pktCB.ENTITY_HEAD_LOOK:
                # these packets are insanely numerous
                if self.headlooks > 20:
                    self.headlooks = 0
                    return True
                # reading these often causes disconnection
                # data = self.packet.read("varint:eid|byte:angle")
                # self.log.trace("(PROXY SERVER) -> Parsed ENTITY_HEAD_LOOK packet:\n%s", data)
                return False  # discard 95% of them

            elif pkid == self.pktCB.ENTITY_STATUS:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("int:eid|byte:status")
                self.log.trace("(PROXY SERVER) -> Parsed ENTITY_STATUS packet:\n%s", data)
                return True

            elif pkid == self.pktCB.ATTACH_ENTITY:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("varint:eid|varint:vid|bool:leash")
                eid, vid, leash = data["eid"], data["vid"], data["leash"]
                player = self.getPlayerByEID(eid)
                self.log.trace("(PROXY SERVER) -> Parsed ATTACH_ENTITY packet:\n%s", data)
                if player is None:
                    return
                if eid == self.eid:
                    if vid == -1:
                        self.wrapper.events.callevent("player.unmount", {"player": player})
                        self.client.riding = None
                    else:
                        self.wrapper.events.callevent("player.mount", {"player": player, "vehicle_id": vid,
                                                                       "leash": leash})
                        if not self.wrapper.javaserver.world:
                            return
                        self.client.riding = self.wrapper.javaserver.world.getEntityByEID(vid)
                        self.wrapper.javaserver.world.getEntityByEID(vid).rodeBy = self.client
                    if eid != self.client.eid:
                        self.client.packet.send(self.pktCB.ATTACH_ENTITY, "varint|varint|bool",
                                                (self.client.eid, vid, leash))
                        return False
                return True

            elif pkid == self.pktCB.ENTITY_METADATA:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("varint:eid|rest:metadata")
                self.log.trace("(PROXY SERVER) -> Parsed ENTITY_METADATA packet:\n%s", data)
                if data["eid"] == self.eid:
                    self.client.packet.send(self.pktCB.ENTITY_METADATA, "varint|raw",
                                            (self.client.eid, data["metadata"]))
                    return False
                return True

            elif pkid == self.pktCB.ENTITY_EFFECT:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("varint:eid|byte:effect_id|byte:amplifier|varint:duration|bool:hide")
                self.log.trace("(PROXY SERVER) -> Parsed ENTITY_EFFECT packet:\n%s", data)
                if data["eid"] == self.eid:
                    self.client.packet.send(self.pktCB.ENTITY_EFFECT, "varint|byte|byte|varint|bool",
                                            (self.client.eid, data["effect_id"], data["amplifier"], data["duration"],
                                             data["hide"]))
                    return False
                return True

            elif pkid == self.pktCB.REMOVE_ENTITY_EFFECT:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("varint:eid|byte:effect_id")
                self.log.trace("(PROXY SERVER) -> Parsed REMOVE_ENTITY_EFFECT packet:\n%s", data)
                if data["eid"] == self.eid:
                    self.client.packet.send(self.pktCB.REMOVE_ENTITY_EFFECT, "varint|byte",
                                            (self.client.eid, data["effect_id"]))
                    return False
                return True

            elif pkid == self.pktCB.ENTITY_PROPERTIES:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("varint:eid|rest:properties")
                self.log.trace("(PROXY SERVER) -> Parsed ENTITY_PROPERTIES packet:\n%s", data)
                if data["eid"] == self.eid:
                    self.client.packet.send(self.pktCB.ENTITY_PROPERTIES, "varint|raw",
                                            (self.client.eid, data["properties"]))
                    return False
                return True

            # elif pkid == self.pktCB.CHUNK_DATA:
            #     if self.client.packet.compressThreshold == -1:
            #         self.log.debug("Client compression enabled, setting to 256")
            #         self.client.packet.setCompression(256)
            #     self.log.trace("(PROXY SERVER) -> Parsed CHUNK_DATA packet")
            #    return True

            # elif self.pktCB.BLOCK_CHANGE:  # disabled - not doing anything at this point
            #     if self.version < mcpacket.PROTOCOL_1_8START:
            #         # NOTE: These packets need to be filtered for cross-server stuff.
            #         return True
            #     data = self.packet.read("position:location|varint:pkid")
            #     self.log.trace("(PROXY SERVER) -> Parsed BLOCK_CHANGE packet:\n%s", data)
            #    return True

            elif pkid == self.pktCB.MAP_CHUNK_BULK:  # (no longer exists in 1.9)
                if mcpacket.PROTOCOL_1_9START > self.version > mcpacket.PROTOCOL_1_8START:
                    data = self.packet.read("bool:skylight|varint:chunks")
                    self.log.trace("(PROXY SERVER) -> Parsed MAP_CHUNK_BULK packet:\n%s", data)
                    for chunk in xxrange(data["chunks"]):
                        meta = self.packet.read("int:x|int:z|ushort:primary")
                        bitmask = bin(meta["primary"])[2:].zfill(16)
                        chunkcolumn = bytearray()
                        for bit in bitmask:
                            if bit == "1":
                                # packetanisc
                                chunkcolumn += bytearray(self.packet.read_data(16 * 16 * 16 * 2))
                                if self.client.dimension == 0:
                                    metalight = bytearray(self.packet.read_data(16 * 16 * 16))
                                if data["skylight"]:
                                    skylight = bytearray(self.packet.read_data(16 * 16 * 16))
                            else:
                                # Null Chunk
                                chunkcolumn += bytearray(16 * 16 * 16 * 2)
                return True

            elif pkid == self.pktCB.CHANGE_GAME_STATE:
                data = self.packet.read("ubyte:reason|float:value")
                if data["reason"] == 3:
                    self.client.gamemode = data["value"]
                self.log.trace("(PROXY SERVER) -> Parsed CHANGE_GAME_STATE packet:\n%s", data)
                return True

            elif pkid == self.pktCB.SET_SLOT:
                if self.version < mcpacket.PROTOCOL_1_8START:
                    # NOTE: These packets need to be filtered for cross-server stuff.
                    return True
                data = self.packet.read("byte:wid|short:slot|slot:data")
                if data["wid"] == 0:
                    self.client.inventory[data["slot"]] = data["data"]
                self.log.trace("(PROXY SERVER) -> Parsed SET_SLOT packet:\n%s", data)
                return True

            # if pkid == 0x30: # Window Items
            #   data = self.packet.read("byte:wid|short:count")
            #   if data["wid"] == 0:
            #       for slot in range(1, data["count"]):
            #           data = self.packet.read("slot:data")
            #           self.client.inventory[slot] = data["data"]
            #   self.log.trace("(PROXY SERVER) -> Parsed 0x30 packet:\n%s", data)
            #    return True

            elif pkid == self.pktCB.PLAYER_LIST_ITEM:
                if self.version > mcpacket.PROTOCOL_1_8START:
                    head = self.packet.read("varint:action|varint:length")
                    z = 0
                    while z < head["length"]:
                        serveruuid = self.packet.read("uuid:uuid")["uuid"]
                        playerclient = self.client.proxy.getClientByOfflineServerUUID(serveruuid)
                        if not playerclient:
                            z += 1
                            continue
                        try:
                            # This is an MCUUID object, how could this fail? All clients have a uuid attribute
                            uuid = playerclient.uuid
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
                            self.client.packet.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|string|varint|raw",
                                                    (0, 1, playerclient.uuid, playerclient.username,
                                                     len(properties), raw))
                        elif head["action"] == 1:
                            data = self.packet.read("varint:gamemode")
                            self.log.trace("(PROXY SERVER) -> Parsed PLAYER_LIST_ITEM packet:\n%s", data)
                            self.client.packet.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|varint",
                                                    (1, 1, uuid, data["gamemode"]))
                        elif head["action"] == 2:
                            data = self.packet.read("varint:ping")
                            self.log.trace("(PROXY SERVER) -> Parsed PLAYER_LIST_ITEM packet:\n%s", data)
                            self.client.packet.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|varint",
                                                    (2, 1, uuid, data["ping"]))
                        elif head["action"] == 3:
                            data = self.packet.read("bool:has_display")
                            if data["has_display"]:
                                data = self.packet.read("string:displayname")
                                self.log.trace("(PROXY SERVER) -> Parsed PLAYER_LIST_ITEM packet:\n%s", data)
                                self.client.packet.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|bool|string",
                                                        (3, 1, uuid, True, data["displayname"]))
                            else:
                                self.client.packet.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid|varint",
                                                        (3, 1, uuid, False))
                        elif head["action"] == 4:
                            self.client.packet.send(self.pktCB.PLAYER_LIST_ITEM, "varint|varint|uuid", (4, 1, uuid))
                        return False
                return True

            elif pkid == self.pktCB.DISCONNECT:
                message = self.packet.read("json:json")["json"]
                self.log.info("Disconnected from server: %s", message)
                if not self.client.isLocal:
                    self.close()
                else:
                    self.client.disconnect(message)
                self.log.trace("(PROXY SERVER) -> Parsed DISCONNECT packet")
                return False

            else:
                return True  # no packets parsed - passing to client

        if self.state == ProxServState.LOGIN:
            if pkid == 0x01:
                # This is throwing a malformed json exception when online mode is set to true, this should be a json
                # string
                self.client.disconnect("Server is online mode. Please turn it off in server.properties. Wrapper.py "
                                       "will handle authentication on its own, so do not worry about hackers.")
                self.log.trace("(PROXY SERVER) -> Parsed 0x01 packet with server state 2 (LOGIN)")
                return False

            if pkid == 0x02:  # Login Success - UUID & Username are sent in this packet
                self.state = ProxServState.PLAY
                self.log.trace("(PROXY SERVER) -> Parsed 0x02 packet with server state 2 (LOGIN)")
                return False

            if pkid == 0x03 and self.state == ProxServState.LOGIN:  # Set Compression
                data = self.packet.read("varint:threshold")
                if data["threshold"] != -1:
                    self.packet.compression = True
                    self.packet.compressThreshold = data["threshold"]
                else:
                    self.packet.compression = False
                    self.packet.compressThreshold = -1
                self.log.trace("(PROXY SERVER) -> Parsed 0x03 packet with server state 2 (LOGIN):\n%s", data)
                time.sleep(10)
                return  # False

    def handle(self):
        try:
            while not self.abort:
                if self.abort:
                    self.close()
                    break
                try:
                    pkid, original = self.packet.grabPacket()
                    self.lastPacketIDs.append((hex(pkid), len(original)))
                    if len(self.lastPacketIDs) > 10:
                        for i, v in enumerate(self.lastPacketIDs):
                            del self.lastPacketIDs[i]
                            break
                except EOFError as eof:
                    # This error is often erroneous, see https://github.com/suresttexas00/minecraft-wrapper/issues/30
                    self.log.debug("Packet EOF (%s)", eof)
                    self.abort = True
                    self.close()
                    break
                except socket.error:  # Bad file descriptor occurs anytime a socket is closed.
                    self.log.debug("Failed to grab packet [SERVER] socket closed; bad file descriptor")
                    self.abort = True
                    self.close()
                    break
                except Exception as e1:
                    # anything that gets here is a bona-fide error we need to become aware of
                    self.log.debug("Failed to grab packet [SERVER] (%s):", e1)
                    return
                if self.parse(pkid) and self.client:
                    self.client.packet.sendRaw(original)
        except Exception as e2:
            self.log.exception("Error in the [SERVER] -> [PROXY] handle (%s):", e2)
            self.close()


class ProxServState:
    """
    This class represents proxy Server states
    """
    HANDSHAKE = 0  # actually unused here because, as a fake "client", we are not listening for connections
    # So we don't have to listen for a handshake.  We simply send a handshake to the server
    # followed by a login start packet and go straight to LOGIN mode.  HANDSHAKE in this
    # context might mean a server that is not started?? (proposed idea).

    # MOTD = 1  # not used. client.py handles MOTD functions

    LOGIN = 2  # login state packets
    PLAY = 3  # packet play state

    def __init__(self):
        pass
