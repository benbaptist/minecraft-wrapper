# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

# standard
import socket
import threading
import time
import traceback

# local
from proxy.packet import Packet
from proxy.parse_cb import ParseCB
from proxy import mcpackets

# noinspection PyPep8Naming
from utils import pkt_datatypes as D

# Py3-2
import sys
PY3 = sys.version_info > (3,)

if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range


# noinspection PyMethodMayBeStatic
class ServerConnection:
    def __init__(self, client, ip=None, port=None):
        """
        This class ServerConnection is a "fake" client connecting to the server.
        It receives "CLIENT BOUND" packets from server, parses them, and forards them on to the client.

        ServerConnection receives the parent client as it's argument. It's wrapper and proxy instances are passed
        from the Client.  Therefore, a server instance does not really validly exist unless it has a valid parent
        client. Client, by contrast, can exist and run in the absence of a server.
        """

        # basic __init__ items from passed arguments
        self.client = client
        self.wrapper = client.wrapper
        self.proxy = client.proxy
        self.log = client.wrapper.log
        self.ip = ip
        self.port = port

        # server setup and operating paramenters
        self.abort = False
        self.state = self.proxy.HANDSHAKE
        self.packet = None
        self.parse_cb = None
        self.buildmode = False
        self.parsers = {}  # dictionary of parser packet constants and associated parsing methods

        self.infos_debug = "(player=%s, IP=%s, Port=%s)" % (self.client.username, self.ip, self.port)
        self.version = -1
        self._refresh_server_version()  # self parsers get updated here

        # player/client variables in this server instance
        self.username = self.client.username
        self.eid = None
        self.currentwindowid = -1
        self.noninventoryslotcount = 0

        self.server_socket = socket.socket()  # temporary assignment.  The actual socket is assigned later.
        self.infos_debug = "(player=%s, IP=%s, Port=%s)" % (self.username, self.ip, self.port)

    def _refresh_server_version(self):
        """Get serverversion for mcpackets use"""

        self.version = self.wrapper.javaserver.protocolVersion
        self.pktSB = mcpackets.ServerBound(self.version)
        self.pktCB = mcpackets.ClientBound(self.version)
        self.parse_cb = ParseCB(self, self.packet)
        self._define_parsers()

        if self.version > mcpackets.PROTOCOL_1_7:
            # used by ban code to enable wrapper group help display for ban items.
            self.wrapper.api.registerPermission("mc1.7.6", value=True)

    def send(self, packetid, xpr, payload):
        """ Not supported. A wrapper of packet.send(), which is further a wrapper for  packet.sendpkt(); both wrappers
         exist for older code compatability purposes only for 0.7.x version plugins that might use it."""
        self.log.debug("deprecated server.send() called.  Use server.packet.sendpkt() for best performance.")
        self.packet.send(packetid, xpr, payload)
        pass

    def connect(self):
        """ This simply establishes the tcp socket connection and starts the flush loop, NOTHING MORE. """
        self.state = self.proxy.LOGIN
        # Connect to this wrapper's javaserver (core/mcserver.py)
        if self.ip is None:
            self.server_socket.connect(("localhost", self.wrapper.javaserver.server_port))

        # Connect to some other server (or an offline wrapper)
        else:
            self.server_socket.connect((self.ip, self.port))

        # start packet handler
        self.packet = Packet(self.server_socket, self)
        self.packet.version = self.client.clientversion

        # define parsers
        self.parse_cb = ParseCB(self, self.packet)
        self._define_parsers()

        t = threading.Thread(target=self.flush_loop, args=())
        t.daemon = True
        t.start()

    def close_server(self, reason="Disconnected", lobby_return=False):
        """
        :lobby_return: determines whether the client should be aborted too.
        :return:
        """
        if lobby_return:
            self.state = self.proxy.LOBBY  # stop parsing PLAY packets to prevent further "disconnects"
        self.log.debug("Disconnecting proxy server socket connection. %s", self.infos_debug)
        self.abort = True  # end 'handle' cleanly
        time.sleep(0.1)
        try:
            self.server_socket.shutdown(2)
            self.log.debug("Sucessfully closed server socket for %s", self.infos_debug)
        except:
            self.log.debug("Server socket for %s already closed", self.infos_debug)
            pass

        if not lobby_return:
            self.client.abort = True

        # allow packet to be GC'ed
        self.packet = None

    def flush_loop(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket.error:
                self.log.debug("Socket_error- server socket was closed %s", self.infos_debug)
                break
            time.sleep(0.01)
        self.log.debug("server connection flush_loop thread ended. %s", self.infos_debug)

    def handle(self):
        while not self.abort:
            # get packet
            try:
                pkid, original = self.packet.grabpacket()
            except EOFError as eof:
                # This error is often erroneous, see https://github.com/suresttexas00/minecraft-wrapper/issues/30
                self.log.debug("%s server Packet EOF (%s)", self.infos_debug, eof)
                return self._break_handle()
            except socket.error:  # Bad file descriptor occurs anytime a socket is closed.
                self.log.debug("%s Failed to grab packet [SERVER] socket error", self.infos_debug)
                return self._break_handle()
            except Exception as e:
                # anything that gets here is a bona-fide error we need to become aware of
                self.log.debug("%s Failed to grab packet [SERVER] (%s):", self.infos_debug, e)
                return self._break_handle()

            # parse it
            if self.parse(pkid) and self.client.state in (self.proxy.PLAY, self.proxy.LOBBY):
                try:
                    self.client.packet.send_raw(original)
                    if self.proxy.trace:
                        self._do_trace(pkid, self.state)

                except Exception as e:
                    self.log.debug("[SERVER %s] Could not send packet (%s): (%s): \n%s",
                                   self.infos_debug, pkid, e, traceback)
                    return self._break_handle()

    def _do_trace(self, pkid, state):
        name = str(self.parsers[state][pkid]).split(" ")[0]
        if pkid not in self.proxy.ignoredCB:
            self.log.warn("<=CB %s (%s)", hex(pkid), name)

    def _break_handle(self):
        if self.state == self.proxy.LOBBY:
            self.log.info("%s is without a server now.", self.username)
            # self.close_server("%s server connection closing..." % self.username, lobby_return=True)
        else:
            self.close_server("%s server connection closing..." % self.username)
        return

    def _keep_alive_response(self):
        if self.version < mcpackets.PROTOCOL_1_8START:
            # readpkt returns this as [123..] (a list with a single integer)
            data = self.packet.readpkt([D.INT])
            self.packet.sendpkt(self.pktSB.KEEP_ALIVE, [D.INT], data)  # which is why no need to [data] as a list
        else:  # self.version >= mcpackets.PROTOCOL_1_8START: - future elif in case protocol changes again.
            data = self.packet.readpkt([D.VARINT])
            self.packet.sendpkt(self.pktSB.KEEP_ALIVE, [D.VARINT], data)
        return False

    def _transmit_upstream(self):
        """ transmit wrapper channel status info to the server's direction to help sync hub/lobby wrappers """

        channel = "WRAPPER|SYNC"
        received = self.proxy.shared["received"]  # received SYNC from the client (this is a child wrapper)
        sent = self.proxy.shared["sent"]  # if true, this is a multiworld (child wrapper instance)
        state = self.state

        if self.version < mcpackets.PROTOCOL_1_8START:
            self.packet.sendpkt(self.pktCB.PLUGIN_MESSAGE, [D.STRING, D.SHORT, D.BOOL, D.BOOL, D.BYTE],
                                [channel, 3, received, sent, state])
        else:
            self.packet.sendpkt(self.pktCB.PLUGIN_MESSAGE, [D.STRING, D.BOOL, D.BOOL, D.BYTE],
                                [channel, received, sent, state])

    # PARSERS SECTION
    # -----------------------------
    def parse(self, pkid):
        try:
            return self.parsers[self.state][pkid]()
        except KeyError:
            self.parsers[self.state][pkid] = self._parse_built
            if self.buildmode:
                # some code here to document un-parsed packets?
                pass
            return True

    def _define_parsers(self):
        # the packets we parse and the methods that parse them.
        self.parsers = {
            self.proxy.HANDSHAKE: {},  # maps identically to OFFLINE ( '0' )
            self.proxy.LOGIN: {
                self.pktCB.LOGIN_DISCONNECT: self._parse_login_disconnect,
                self.pktCB.LOGIN_ENCR_REQUEST: self._parse_login_encr_request,
                self.pktCB.LOGIN_SUCCESS: self._parse_login_success,
                self.pktCB.LOGIN_SET_COMPRESSION: self._parse_login_set_compression
            },
            self.proxy.PLAY: {
                self.pktCB.COMBAT_EVENT: self.parse_cb.parse_play_combat_event,
                self.pktCB.KEEP_ALIVE: self._parse_play_keep_alive,
                self.pktCB.CHAT_MESSAGE: self.parse_cb.parse_play_chat_message,
                self.pktCB.JOIN_GAME: self.parse_cb.parse_play_join_game,
                self.pktCB.TIME_UPDATE: self.parse_cb.parse_play_time_update,
                self.pktCB.SPAWN_POSITION: self.parse_cb.parse_play_spawn_position,
                self.pktCB.RESPAWN: self.parse_cb.parse_play_respawn,
                self.pktCB.PLAYER_POSLOOK: self.parse_cb.parse_play_player_poslook,
                self.pktCB.USE_BED: self.parse_cb.parse_play_use_bed,
                self.pktCB.SPAWN_PLAYER: self.parse_cb.parse_play_spawn_player,
                self.pktCB.SPAWN_OBJECT: self.parse_cb.parse_play_spawn_object,
                self.pktCB.SPAWN_MOB: self.parse_cb.parse_play_spawn_mob,
                self.pktCB.ENTITY_RELATIVE_MOVE: self.parse_cb.parse_play_entity_relative_move,
                self.pktCB.ENTITY_TELEPORT: self.parse_cb.parse_play_entity_teleport,
                self.pktCB.ATTACH_ENTITY: self.parse_cb.parse_play_attach_entity,
                self.pktCB.DESTROY_ENTITIES: self.parse_cb.parse_play_destroy_entities,
                self.pktCB.MAP_CHUNK_BULK: self._parse_play_map_chunk_bulk,
                self.pktCB.CHANGE_GAME_STATE: self._parse_play_change_game_state,
                self.pktCB.OPEN_WINDOW: self._parse_play_open_window,
                self.pktCB.SET_SLOT: self._parse_play_set_slot,
                self.pktCB.WINDOW_ITEMS: self._parse_play_window_items,
                self.pktCB.ENTITY_PROPERTIES: self._parse_play_entity_properties,
                self.pktCB.PLAYER_LIST_ITEM: self._parse_play_player_list_item,
                self.pktCB.DISCONNECT: self._parse_play_disconnect,
                self.pktCB.ENTITY_METADATA: self._parse_entity_metadata,
                },
            self.proxy.LOBBY: {
                self.pktCB.DISCONNECT: self._parse_lobby_disconnect,
                self.pktCB.KEEP_ALIVE: self._parse_lobby_keep_alive
            }
        }

    # Do nothing parser
    # -----------------------
    def _parse_built(self):
        return True

    # Login parsers
    # -----------------------
    def _parse_login_disconnect(self):
        message = self.packet.readpkt([D.STRING])
        self.log.info("Disconnected from server: %s", message)
        self.close_server(message)
        return False

    def _parse_login_encr_request(self):
        self.close_server("Server is in online mode. Please turn it off in server.properties and "
                          "allow wrapper to handle the authetication.")
        return False

    def _parse_login_success(self):  # Login Success - UUID & Username are sent in this packet as strings
        self.state = self.proxy.PLAY
        data = self.packet.readpkt([D.STRING, D.STRING])
        return False

    def _parse_login_set_compression(self):
        data = self.packet.readpkt([D.VARINT])
        # ("varint:threshold")
        if data[0] != -1:
            self.packet.compression = True
            self.packet.compressThreshold = data[0]
        else:
            self.packet.compression = False
            self.packet.compressThreshold = -1
        time.sleep(10)
        return  # False

    # Play parsers
    # -----------------------
    def _parse_play_keep_alive(self):
        return self._keep_alive_response()

    def _parse_play_map_chunk_bulk(self):  # (packet no longer exists in 1.9)
        #  no idea why this is parsed.. we are not doing anything with the data...
        # if mcpackets.PROTOCOL_1_9START > self.version > mcpackets.PROTOCOL_1_8START:
        #     data = self.packet.readpkt([D.BOOL, D.VARINT])
        #     chunks = data[1]
        #     skylightbool = data[0]
        #     # ("bool:skylight|varint:chunks")
        #     for chunk in xxrange(chunks):
        #         meta = self.packet.readpkt([D.INT, D.INT, _USHORT])
        #         # ("int:x|int:z|ushort:primary")
        #         primary = meta[2]
        #         bitmask = bin(primary)[2:].zfill(16)
        #         chunkcolumn = bytearray()
        #         for bit in bitmask:
        #             if bit == "1":
        #                 # packetanisc
        #                 chunkcolumn += bytearray(self.packet.read_data(16 * 16 * 16 * 2))
        #                 if self.client.dimension == 0:
        #                     metalight = bytearray(self.packet.read_data(16 * 16 * 16))
        #                 if skylightbool:
        #                     skylight = bytearray(self.packet.read_data(16 * 16 * 16))
        #             else:
        #                 # Null Chunk
        #                 chunkcolumn += bytearray(16 * 16 * 16 * 2)
        return True

    def _parse_play_change_game_state(self):
        data = self.packet.readpkt([D.UBYTE, D.FLOAT])
        # ("ubyte:reason|float:value")
        if data[0] == 3:
            self.client.gamemode = data[1]
        return True

    def _parse_play_open_window(self):
        # This works together with SET_SLOT to maintain accurate inventory in wrapper
        if self.version < mcpackets.PROTOCOL_1_8START:
            parsing = [D.UBYTE, D.UBYTE, D.STRING, D.UBYTE]
        else:
            parsing = [D.UBYTE, D.STRING, D.JSON, D.UBYTE]
        data = self.packet.readpkt(parsing)
        self.currentwindowid = data[0]
        self.noninventoryslotcount = data[3]
        return True

    def _parse_play_set_slot(self):
        # ("byte:wid|short:slot|slot:data")
        if self.version < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.BYTE, D.SHORT, D.SLOT_NO_NBT])
            inventoryslots = 35
        elif self.version < mcpackets.PROTOCOL_1_9START:
            data = self.packet.readpkt([D.BYTE, D.SHORT, D.SLOT])
            inventoryslots = 35
        elif self.version > mcpackets.PROTOCOL_1_8END:
            data = self.packet.readpkt([D.BYTE, D.SHORT, D.SLOT])
            inventoryslots = 36  # 1.9 minecraft with shield / other hand
        else:
            data = [-12, -12, None]
            inventoryslots = 35

        # this only works on startup when server sends WID = 0 with 45/46 items and when an item is moved into
        # players inventory from outside (like a chest or picking something up)
        # after this, these are sent on chest opens and so forth, each WID incrementing by +1 per object opened.
        # the slot numbers that correspond to player hotbar will depend on what window is opened...
        # the last 10 (for 1.9) or last 9 (for 1.8 and earlier) will be the player hotbar ALWAYS.
        # to know how many packets and slots total to expect, we have to parse server-bound pktCB.OPEN_WINDOW.
        if data[0] == 0:
            self.client.inventory[data[1]] = data[2]

        # Sure.. as though we are done ;)

        if data[0] < 0:
            return True

        # This part updates our inventory from additional windows the player may open
        if data[0] == self.currentwindowid:
            currentslot = data[1]
            slotdata = data[2]
            if currentslot >= self.noninventoryslotcount:  # any number of slot above the
                # pktCB.OPEN_WINDOW declared self.(..)slotcount is an inventory slot for up to update.
                self.client.inventory[currentslot - self.noninventoryslotcount + 9] = data[2]
        return True

    def _parse_play_window_items(self):
        # I am interested to see when this is used and in what versions.  It appears to be superfluous, as
        # SET_SLOT seems to do the purported job nicely.
        data = self.packet.readpkt([D.UBYTE, D.SHORT])
        windowid = data[0]
        elementcount = data[1]
        # data = self.packet.read("byte:wid|short:count")
        # if data["wid"] == 0:
        #     for slot in range(1, data["count"]):
        #         data = self.packet.readpkt("slot:data")
        #         self.client.inventory[slot] = data["data"]
        elements = []
        if self.version > mcpackets.PROTOCOL_1_7_9:  # just parsing for now; not acting on, so OK to skip 1.7.9
            for _ in xrange(elementcount):
                elements.append(self.packet.read_slot())
        jsondata = {
            "windowid": windowid,
            "elementcount": elementcount,
            "elements": elements
        }
        return True

    def _parse_play_entity_properties(self):
        """ Not sure why I added this.  Based on the wiki, it looked like this might
        contain a player uuid buried in the lowdata (wiki - "Modifier Data") area
        that might need to be parsed and reset to the server local uuid.  Thus far,
        I have not seen it used.

        IF there is a uuid, it may need parsed.

        parser_three = [D.UUID, D.DOUBLE, D.BYTE]
        if self.version < mcpackets.PROTOCOL_1_8START:
            parser_one = [D.INT, D.INT]
            parser_two = [D.STRING, D.DOUBLE, D.SHORT]
            writer_one = self.packet.send_int
            writer_two = self.packet.send_short
        else:
            parser_one = [D.VARINT, D.INT]
            parser_two = [D.STRING, D.DOUBLE, D.VARINT]
            writer_one = self.packet.send_varint
            writer_two = self.packet.send_varint
        raw = b""  # use bytes

        # read first level and repack
        pass1 = self.packet.readpkt(parser_one)
        isplayer = self.proxy.getplayerby_eid(pass1[0])
        if not isplayer:
            return True
        raw += writer_one(pass1[0])
        print(pass1[0], pass1[1])
        raw += self.packet.send_int(pass1[1])

        # start level 2
        for _x in range(pass1[1]):
            pass2 = self.packet.readpkt(parser_two)
            print(pass2[0], pass2[1], pass2[2])
            raw += self.packet.send_string(pass2[0])
            raw += self.packet.send_double(pass2[1])
            raw += writer_two(pass2[2])
            print(pass2[2])
            for _y in range(pass2[2]):
                lowdata = self.packet.readpkt(parser_three)
                print(lowdata)
                packetuuid = lowdata[0]
                playerclient = self.wrapper.proxy.getclientbyofflineserveruuid(packetuuid)
                if playerclient:
                    raw += self.packet.send_uuid(playerclient.uuid.hex)
                else:
                    raw += self.packet.send_uuid(lowdata[0])
                raw += self.packet.send_double(lowdata[1])
                raw += self.packet.send_byte(lowdata[2])
                print("Low data: ", lowdata)
        # self.packet.sendpkt(self.pktCB.ENTITY_PROPERTIES, [D.RAW], (raw,))
        return True
        """
        return True

    def _parse_play_player_list_item(self):
        if self.version >= mcpackets.PROTOCOL_1_8START:
            head = self.packet.readpkt([D.VARINT, D.VARINT])
            # ("varint:action|varint:length")
            lenhead = head[1]
            action = head[0]
            z = 0
            while z < lenhead:
                serveruuid = self.packet.readpkt([D.UUID])[0]
                playerclient = self.wrapper.proxy.getclientbyofflineserveruuid(serveruuid)
                if not playerclient:
                    z += 1
                    continue
                try:
                    # This is an MCUUID object, how could this fail? All clients have a uuid attribute
                    uuid = playerclient.uuid
                except Exception as e:
                    # uuid = playerclient
                    self.log.exception("playerclient.uuid failed in playerlist item (%s)", e)
                    z += 1
                    continue
                z += 1
                if action == 0:
                    properties = playerclient.properties
                    raw = b""
                    for prop in properties:
                        raw += self.client.packet.send_string(prop["name"])
                        raw += self.client.packet.send_string(prop["value"])
                        if "signature" in prop:
                            raw += self.client.packet.send_bool(True)
                            raw += self.client.packet.send_string(prop["signature"])
                        else:
                            raw += self.client.packet.send_bool(False)
                    raw += self.client.packet.send_varint(0)
                    raw += self.client.packet.send_varint(0)
                    raw += self.client.packet.send_bool(False)
                    self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                               [D.VARINT, D.VARINT, D.UUID, D.STRING, D.VARINT, D.RAW],
                                               (0, 1, playerclient.uuid, playerclient.username,
                                                len(properties), raw))
                elif action == 1:
                    data = self.packet.readpkt([D.VARINT])
                    gamemode = data[0]
                    # ("varint:gamemode")
                    self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                               [D.VARINT, D.VARINT, D.UUID, D.VARINT],
                                               (1, 1, uuid, data[0]))
                    # print(1, 1, uuid, gamemode)
                elif action == 2:
                    data = self.packet.readpkt([D.VARINT])
                    ping = data[0]
                    # ("varint:ping")
                    self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM, [D.VARINT, D.VARINT, D.UUID, D.VARINT],
                                               (2, 1, uuid, ping))
                elif action == 3:
                    data = self.packet.readpkt([D.BOOL])
                    # ("bool:has_display")
                    hasdisplay = data[0]
                    if hasdisplay:
                        data = self.packet.readpkt([D.STRING])
                        displayname = data[0]
                        # ("string:displayname")
                        self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                                   [D.VARINT, D.VARINT, D.UUID, D.BOOL, D.STRING],
                                                   (3, 1, uuid, True, displayname))
                    else:
                        self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                                   [D.VARINT, D.VARINT, D.UUID, D.VARINT],
                                                   (3, 1, uuid, False))
                elif action == 4:
                    self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                               [D.VARINT, D.VARINT, D.UUID], (4, 1, uuid))
                return False
        else:  # version < 1.7.9 needs no processing
            return True
        return True

    def _parse_play_disconnect(self):
        # def __str__():
        #    return "PLAY_DISCONNECT"
        message = self.packet.readpkt([D.JSON])
        self.log.info("%s disconnected from Server", self.username)
        self.close_server(message)

    def _parse_entity_metadata(self):
        """
        This packet is parsed, then re-constituted, the original rejected, and and new packet formed to the client.
        if the entity is a baby, we rename it.. All of this, just for fun! (and as a demo)  Otherwise,
        this is a pretty useless parse, unless we opt to pump this data into the entity API.
        """
        eid, metadata = self.packet.readpkt([D.VARINT, D.METADATA_1_9])
        if 12 in metadata:  # ageable
            if 6 in metadata[12]:  # boolean isbaby
                if metadata[12][1] is True:  # it's a baby!

                    # print the data for reference
                    # see http://wiki.vg/Entities#Entity_Metadata_Format
                    self.log.debug("EID: %s - %s", eid, metadata)
                    # name the baby and make tag visible (no index/type checking; accessing base entity class)
                    metadata[2] = (3, "Entity_%s" % eid)
                    metadata[3] = (6, True)

        self.client.packet.sendpkt(self.pktCB.ENTITY_METADATA, [D.VARINT, D.METADATA_1_9], (eid, metadata))
        return False

    # Lobby parsers
    # -----------------------
    def _parse_lobby_disconnect(self):
        message = self.packet.readpkt([D.JSON])
        self.log.info("%s went back to Hub", self.username)
        self.close_server(message, lobby_return=True)

    def _parse_lobby_keep_alive(self):
        return self._keep_alive_response()
