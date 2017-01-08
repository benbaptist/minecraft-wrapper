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

from utils.pkt_datatypes import *


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

        # TODO server needs to be a true child of clientconnection process.  It should not close its own instance, etc
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
        self.eid = None

        self.server_socket = socket.socket()  # temporary assignment.  The actual socket is assigned later.
        self.infos_debug = "(player=%s, IP=%s, Port=%s)" % (self.client.username, self.ip, self.port)

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
        # noinspection PyBroadException
        try:
            self.server_socket.shutdown(2)
            self.log.debug("Sucessfully closed server socket for %s", self.infos_debug)
        # todo - discover our expected error
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
            self.log.info("%s is without a server now.", self.client.username)
            # self.close_server("%s server connection closing..." % self.client.username, lobby_return=True)
        else:
            self.close_server("%s server connection closing..." % self.client.username)
        return

    def _keep_alive_response(self):
        if self.version < mcpackets.PROTOCOL_1_8START:
            # readpkt returns this as [123..] (a list with a single integer)
            data = self.packet.readpkt([INT])
            self.packet.sendpkt(self.pktSB.KEEP_ALIVE, [INT], data)  # which is why no need to [data] as a list
        else:  # self.version >= mcpackets.PROTOCOL_1_8START: - future elif in case protocol changes again.
            data = self.packet.readpkt([VARINT])
            self.packet.sendpkt(self.pktSB.KEEP_ALIVE, [VARINT], data)
        return False

    def _transmit_upstream(self):
        """ transmit wrapper channel status info to the server's direction to help sync hub/lobby wrappers """

        channel = "WRAPPER|SYNC"
        received = self.proxy.shared["received"]  # received SYNC from the client (this is a child wrapper)
        sent = self.proxy.shared["sent"]  # if true, this is a multiworld (child wrapper instance)
        state = self.state

        if self.version < mcpackets.PROTOCOL_1_8START:
            self.packet.sendpkt(self.pktCB.PLUGIN_MESSAGE, [STRING, SHORT, BOOL, BOOL, BYTE],
                                [channel, 3, received, sent, state])
        else:
            self.packet.sendpkt(self.pktCB.PLUGIN_MESSAGE, [STRING, BOOL, BOOL, BYTE],
                                [channel, received, sent, state])

    # PARSERS SECTION
    # -----------------------------

    # Login parsers
    # -----------------------
    def _parse_login_disconnect(self):
        message = self.packet.readpkt([STRING])
        self.log.info("Disconnected from server: %s", message)
        self.close_server(message)
        return False

    def _parse_login_encr_request(self):
        self.close_server("Server is in online mode. Please turn it off in server.properties and "
                          "allow wrapper to handle the authetication.")
        return False

    def _parse_login_success(self):  # Login Success - UUID & Username are sent in this packet as strings
        self.state = self.proxy.PLAY
        # todo - we may not need to assign this to a variable. (we supplied uuid/name anyway!)
        # noinspection PyUnusedLocal
        data = self.packet.readpkt([STRING, STRING])
        return False

    def _parse_login_set_compression(self):
        data = self.packet.readpkt([VARINT])
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

    def _parse_play_entity_properties(self):
        """ Not sure why I added this.  Based on the wiki, it looked like this might
        contain a player uuid buried in the lowdata (wiki - "Modifier Data") area
        that might need to be parsed and reset to the server local uuid.  Thus far,
        I have not seen it used.

        IF there is a uuid, it may need parsed.

        parser_three = [UUID, DOUBLE, BYTE]
        if self.version < mcpackets.PROTOCOL_1_8START:
            parser_one = [INT, INT]
            parser_two = [STRING, DOUBLE, SHORT]
            writer_one = self.packet.send_int
            writer_two = self.packet.send_short
        else:
            parser_one = [VARINT, INT]
            parser_two = [STRING, DOUBLE, VARINT]
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
        # self.packet.sendpkt(self.pktCB.ENTITY_PROPERTIES, [RAW], (raw,))
        return True
        """
        return True

    def _parse_play_player_list_item(self):
        if self.version >= mcpackets.PROTOCOL_1_8START:
            head = self.packet.readpkt([VARINT, VARINT])
            # ("varint:action|varint:length")
            lenhead = head[1]
            action = head[0]
            z = 0
            while z < lenhead:
                serveruuid = self.packet.readpkt([UUID])[0]
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
                                               [VARINT, VARINT, UUID, STRING, VARINT, RAW],
                                               (0, 1, playerclient.uuid, playerclient.username,
                                                len(properties), raw))
                elif action == 1:
                    data = self.packet.readpkt([VARINT])

                    # noinspection PyUnusedLocal
                    gamemode = data[0]  # todo should we be using this to set client gamemode?
                    # ("varint:gamemode")
                    self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                               [VARINT, VARINT, UUID, VARINT],
                                               (1, 1, uuid, data[0]))
                    # print(1, 1, uuid, gamemode)
                elif action == 2:
                    data = self.packet.readpkt([VARINT])
                    ping = data[0]
                    # ("varint:ping")
                    self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM, [VARINT, VARINT, UUID, VARINT],
                                               (2, 1, uuid, ping))
                elif action == 3:
                    data = self.packet.readpkt([BOOL])
                    # ("bool:has_display")
                    hasdisplay = data[0]
                    if hasdisplay:
                        data = self.packet.readpkt([STRING])
                        displayname = data[0]
                        # ("string:displayname")
                        self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                                   [VARINT, VARINT, UUID, BOOL, STRING],
                                                   (3, 1, uuid, True, displayname))
                    else:
                        self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                                   [VARINT, VARINT, UUID, VARINT],
                                                   (3, 1, uuid, False))
                elif action == 4:
                    self.client.packet.sendpkt(self.pktCB.PLAYER_LIST_ITEM,
                                               [VARINT, VARINT, UUID], (4, 1, uuid))
                return False
        else:  # version < 1.7.9 needs no processing
            return True
        return True

    def _parse_play_disconnect(self):
        # def __str__():
        #    return "PLAY_DISCONNECT"
        message = self.packet.readpkt([JSON])
        self.log.info("%s disconnected from Server", self.client.username)
        self.close_server(message)

    def _parse_entity_metadata(self):
        """
        This packet is parsed, then re-constituted, the original rejected, and and new packet formed to the client.
        if the entity is a baby, we rename it.. All of this, just for fun! (and as a demo)  Otherwise,
        this is a pretty useless parse, unless we opt to pump this data into the entity API.
        """
        eid, metadata = self.packet.readpkt([VARINT, METADATA_1_9])
        if 12 in metadata:  # ageable
            if 6 in metadata[12]:  # boolean isbaby
                if metadata[12][1] is True:  # it's a baby!

                    # print the data for reference
                    # see http://wiki.vg/Entities#Entity_Metadata_Format
                    self.log.debug("EID: %s - %s", eid, metadata)
                    # name the baby and make tag visible (no index/type checking; accessing base entity class)
                    metadata[2] = (3, "Entity_%s" % eid)
                    metadata[3] = (6, True)

        self.client.packet.sendpkt(self.pktCB.ENTITY_METADATA, [VARINT, METADATA_1_9], (eid, metadata))
        return False

    # Lobby parsers
    # -----------------------
    def _parse_lobby_disconnect(self):
        message = self.packet.readpkt([JSON])
        self.log.info("%s went back to Hub", self.client.username)
        self.close_server(message, lobby_return=True)

    def _parse_lobby_keep_alive(self):
        return self._keep_alive_response()

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
                self.pktCB.MAP_CHUNK_BULK: self.parse_cb.parse_play_map_chunk_bulk,
                self.pktCB.CHANGE_GAME_STATE: self.parse_cb.parse_play_change_game_state,
                self.pktCB.OPEN_WINDOW: self.parse_cb.parse_play_open_window,
                self.pktCB.SET_SLOT: self.parse_cb.parse_play_set_slot,
                self.pktCB.WINDOW_ITEMS: self.parse_cb.parse_play_window_items,
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
