# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# standard
import socket
import threading
import time
import traceback

# local
from proxy.packets.packet import Packet
from proxy.server.parse_cb import ParseCB
from proxy.packets import mcpackets_sb
from proxy.packets import mcpackets_cb

from proxy.utils.constants import *


# noinspection PyMethodMayBeStatic,PyBroadException
class ServerConnection(object):
    def __init__(self, client, ip=None, port=None):
        """
        This class ServerConnection is a "fake" client connecting
        to the server.  It receives "CLIENT BOUND" packets from
        server, parses them, and sends them on to the client.

        ServerConnection receives the parent client as it's argument.
        It receives the proxy instance from the Client.
        Therefore, a server instance does not really validly exist
        unless it has a valid parent client.

        Client, by contrast, can exist and run in the absence
        of a server.
        """

        # TODO server needs to be a true child of clientconnection process.
        # It should not close its own instance, etc

        # basic __init__ items from passed arguments
        self.client = client
        self.proxy = client.proxy
        self.log = client.log
        self.ip = ip
        self.port = port

        # server setup and operating paramenters
        self.abort = False
        self.state = HANDSHAKE
        self.packet = None
        self.parse_cb = None

        # dictionary of parser packet constants and associated parsing methods
        self.parsers = {}
        self.entity_controls = self.proxy.ent_config["enable-entity-controls"]
        self.version = -1

        # self parsers get updated here
        self._refresh_server_version()

        # temporary assignment.  The actual socket is assigned later.
        self.server_socket = socket.socket()

        self.infos_debug = "(player=%s, IP=%s, Port=%s)" % (
            self.client.username, self.ip, self.port)

    def _refresh_server_version(self):
        """Get serverversion for mcpackets use"""

        self.version = self.proxy.srv_data.protocolVersion
        self.pktSB = mcpackets_sb.Packets(self.version)
        self.pktCB = mcpackets_cb.Packets(self.version)
        self.parse_cb = ParseCB(self, self.packet)
        self._define_parsers()

    def send(self, packetid, xpr, payload):
        """ Not supported. A wrapper of packet.send(), which is
        further a wrapper for  packet.sendpkt(); both wrappers
        exist for older code compatability purposes only for
        0.7.x version plugins that might use it."""

        self.log.debug("deprecated server.send() called.  Use "
                       "server.packet.sendpkt() for best performance.")
        self.packet.send(packetid, xpr, payload)
        pass

    def connect(self):
        """ This simply establishes the tcp socket connection and
        starts the flush loop, NOTHING MORE. """
        self.state = LOGIN
        # Connect to a local server address
        if self.ip is None:
            self.server_socket.connect((
                "localhost", self.proxy.srv_data.server_port))

        # Connect to some specific server address
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

    def close_server(self, reason="Disconnected"):
        """
        Client is responsible for closing the server connection and handling
        lobby states.
        """

        self.log.debug("%s called serverconnection.close_server(): %s",
                       self.client.username, reason)

        # end 'handle' and 'flush_loop' cleanly
        self.abort = True
        time.sleep(0.1)

        # noinspection PyBroadException
        try:
            self.server_socket.shutdown(2)
            self.log.debug("Sucessfully closed server socket for"
                           " %s", self.client.username)
        except:
            self.log.debug("Server socket for %s already "
                           "closed", self.infos_debug)
            pass

        # allow packet instance to be Garbage Collected
        self.packet = None

    def flush_loop(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket.error:
                self.log.debug("Socket_error- server socket was closed"
                               " %s", self.infos_debug)
                break
            time.sleep(0.01)
        self.log.debug("%s serverconnection flush_loop thread ended.",
                       self.client.username)

    def handle(self):
        while not self.abort:
            # get packet
            try:
                pkid, original = self.packet.grabpacket()

            # possible connection losses:
            except EOFError:
                # This is not a true error, but means the connection closed.
                return self.close_server("handle EOF")
            except socket.error:
                return self.close_server("handle socket.error")
            except Exception as e:
                return self.close_server(
                    "handle Exception: %s TRACEBACK: \n%s" % (e, traceback))

            # parse it
            if self.parse(pkid) and self.client.state == PLAY:
                try:
                    self.client.packet.send_raw(original)
                except Exception as e:
                    return self.close_server(
                        "handle could not send packet '%s'.  "
                        "Exception: %s TRACEBACK: \n%s" % (
                            pkid, e, traceback)
                    )

    def _parse_keep_alive(self):
        data = self.packet.readpkt(
            self.pktSB.KEEP_ALIVE[PARSER])
        self.packet.sendpkt(
            self.pktSB.KEEP_ALIVE[PKT],
            self.pktSB.KEEP_ALIVE[PARSER],
            data)
        return False

    def _transmit_upstream(self):
        # TODO this probably needs to be removed.  Wrapper's proxy is fragile/slow enought ATM
        """ transmit wrapper channel status info to the server's
         direction to help sync hub/lobby wrappers """

        channel = "WRAPPER|SYNC"

        # received SYNC from the client (this is a child wrapper)
        received = self.proxy.shared["received"]

        # if true, this is a multiworld (child wrapper instance)
        sent = self.proxy.shared["sent"]
        state = self.state

        if self.version < PROTOCOL_1_8START:
            self.packet.sendpkt(
                self.pktCB.PLUGIN_MESSAGE,
                [STRING, SHORT, BOOL, BOOL, BYTE],
                [channel, 3, received, sent, state])
        else:
            self.packet.sendpkt(
                self.pktCB.PLUGIN_MESSAGE,
                [STRING, BOOL, BOOL, BYTE],
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
        self.close_server("Server is in online mode. Please turn it off "
                          "in server.properties and allow Proxy to "
                          "handle the authetication.")
        return False

    # Login Success - UUID & Username are sent in this packet as strings
    def _parse_login_success(self):
        self.state = PLAY
        # todo - we may not need to assign this to a variable.
        # (we supplied uuid/name anyway!)
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

    def parse(self, pkid):
        if pkid in self.parsers[self.state]:
            return self.parsers[self.state][pkid]()
        return True

    def _define_parsers(self):
        # the packets we parse and the methods that parse them.
        self.parsers = {
            HANDSHAKE: {},  # maps identically to OFFLINE ( '0' )
            LOGIN: {
                self.pktCB.LOGIN_DISCONNECT:
                    self._parse_login_disconnect,
                self.pktCB.LOGIN_ENCR_REQUEST:
                    self._parse_login_encr_request,
                self.pktCB.LOGIN_SUCCESS:
                    self._parse_login_success,
                self.pktCB.LOGIN_SET_COMPRESSION:
                    self._parse_login_set_compression
            },
            PLAY: {
                self.pktCB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktCB.CHAT_MESSAGE[PKT]:
                    self.parse_cb.parse_play_chat_message,
                self.pktCB.JOIN_GAME[PKT]:
                    self.parse_cb.parse_play_join_game,
                self.pktCB.TIME_UPDATE:
                    self.parse_cb.parse_play_time_update,
                self.pktCB.SPAWN_POSITION:
                    self.parse_cb.parse_play_spawn_position,
                self.pktCB.RESPAWN:
                    self.parse_cb.parse_play_respawn,
                self.pktCB.PLAYER_POSLOOK[PKT]:
                    self.parse_cb.parse_play_player_poslook,
                self.pktCB.USE_BED:
                    self.parse_cb.parse_play_use_bed,
                self.pktCB.SPAWN_PLAYER:
                    self.parse_cb.parse_play_spawn_player,
                self.pktCB.CHANGE_GAME_STATE:
                    self.parse_cb.parse_play_change_game_state,
                self.pktCB.OPEN_WINDOW[PKT]:
                    self.parse_cb.parse_play_open_window,

                self.pktCB.SET_SLOT[PKT]:
                    self.parse_cb.parse_play_set_slot,
                self.pktCB.PLAYER_LIST_ITEM:
                    self.parse_cb.parse_play_player_list_item,
                self.pktCB.DISCONNECT:
                    self.parse_cb.parse_play_disconnect,
                }
        }

        if self.entity_controls:
            self.parsers[PLAY][
                self.pktCB.SPAWN_OBJECT] = self.parse_cb.parse_play_spawn_object
            self.parsers[PLAY][
                self.pktCB.SPAWN_MOB] = self.parse_cb.parse_play_spawn_mob
            self.parsers[PLAY][
                self.pktCB.ENTITY_RELATIVE_MOVE] = self.parse_cb.parse_play_entity_relative_move
            self.parsers[PLAY][
                self.pktCB.ENTITY_TELEPORT] = self.parse_cb.parse_play_entity_teleport
            self.parsers[PLAY][
                self.pktCB.ATTACH_ENTITY] = self.parse_cb.parse_play_attach_entity
            self.parsers[PLAY][
                self.pktCB.DESTROY_ENTITIES] = self.parse_cb.parse_play_destroy_entities
