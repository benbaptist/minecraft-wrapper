# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# standard
import json
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
from proxy.utils.mcuuid import MCUUID


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

    # ----------------------------------------------
    # Client calls connect(), then handle()
    # ----------------------------------------------

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
                pkid, original, orig_packet = self.packet.grabpacket()  # noqa

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
            # send packet if parsing passed and client in play mode.
            # all packets are parsed, but only play mode ones are transmitted.
            if self.parse(pkid) and self.client.state == PLAY:
                try:
                    # self.parse will reject (False) any packet proxy modifies.
                    self.client.packet.send_raw_untouched(orig_packet)
                except Exception as e:
                    return self.close_server(
                        "handle could not send packet '%s'.  "
                        "Exception: %s TRACEBACK: \n%s" % (
                            pkid, e, traceback)
                    )

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

    # PARSERS SECTION
    # -----------------------------

    def _parse_keep_alive(self):
        data = self.packet.readpkt(
            self.pktSB.KEEP_ALIVE[PARSER])
        # data is a list of one item  and will be sent back that way
        self.packet.sendpkt(
            self.pktSB.KEEP_ALIVE[PKT],
            self.pktSB.KEEP_ALIVE[PARSER],
            data)
        return False

    # Plugin channel senders
    # -----------------------

    # SB RESP
    def plugin_response(self):
        channel = "WRAPPER.PY|RESP"
        self.client.info["server-is-wrapper"] = True
        data = json.dumps(self.client.info)
        # only our wrappers communicate with this, so, format is not critical.
        self.packet.sendpkt(self.pktSB.PLUGIN_MESSAGE[PKT],
                            [STRING, STRING],
                            (channel, data))

    # SB PING
    def plugin_ping(self):
        """ this is initiated by server/parse_cb.py parse_play_join_game """
        channel = "WRAPPER.PY|PING"
        data = int(time.time())
        self.packet.sendpkt(self.pktSB.PLUGIN_MESSAGE[PKT],
                            [STRING, INT],
                            (channel, data))

    def _parse_plugin_message(self):
        """server-bound"""
        channel = self.packet.readpkt([STRING, ])[0]

        if channel not in self.proxy.registered_channels:
            # we are not actually registering our channels with the MC server
            # and there will be no parsing of other channels.
            return True

        # SB PING
        if channel == "WRAPPER.PY|PONG":
            # then we now know this wrapper is a child wrapper since
            # minecraft clients will not ping us
            self.proxy.info_mine["client-is-wrapper"] = True
            self.plugin_response()

        # do not pass Wrapper.py registered plugin messages
        return False

    # Plugin channel parsers
    # -----------------------

    # Login parsers
    # -----------------------
    def _parse_login_disconnect(self):
        message = self.packet.readpkt([STRING])[0]
        self.log.info("Disconnected from server: %s", message)
        self.close_server(message)
        self.client.notify_disconnect(message)
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
        self.client.local_uuid = MCUUID(data[0])
        # print("UUID: %s" % self.client.local_uuid)
        return False

    def _parse_login_set_compression(self):
        data = self.packet.readpkt([VARINT])[0]
        # ("varint:threshold")
        if data == -1:
            self.packet.compression = False
        else:
            self.packet.compression = True
        self.packet.compressThreshold = data
        # no point - client connection already has the client waiting in
        #  compression enabled mode
        return False

    def parse(self, pkid):
        if pkid in self.parsers[self.state]:
            return self.parsers[self.state][pkid]()
        return True

    def _define_parsers(self):
        # the packets we parse and the methods that parse them.
        self.parsers = {
            HANDSHAKE: {},  # maps identically to OFFLINE ( '0' )
            LOGIN: {
                self.pktCB.LOGIN_DISCONNECT[PKT]:
                    self._parse_login_disconnect,
                self.pktCB.LOGIN_ENCR_REQUEST[PKT]:
                    self._parse_login_encr_request,
                self.pktCB.LOGIN_SUCCESS[PKT]:
                    self._parse_login_success,
                self.pktCB.LOGIN_SET_COMPRESSION[PKT]:
                    self._parse_login_set_compression,
                self.pktCB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message
            },
            PLAY: {
                self.pktCB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktCB.CHAT_MESSAGE[PKT]:
                    self.parse_cb.parse_play_chat_message,
                self.pktCB.JOIN_GAME[PKT]:
                    self.parse_cb.parse_play_join_game,
                self.pktCB.TIME_UPDATE[PKT]:
                    self.parse_cb.parse_play_time_update,
                self.pktCB.SPAWN_POSITION[PKT]:
                    self.parse_cb.parse_play_spawn_position,
                self.pktCB.RESPAWN[PKT]:
                    self.parse_cb.parse_play_respawn,
                self.pktCB.PLAYER_POSLOOK[PKT]:
                    self.parse_cb.parse_play_player_poslook,
                self.pktCB.USE_BED[PKT]:
                    self.parse_cb.parse_play_use_bed,
                self.pktCB.SPAWN_PLAYER[PKT]:
                    self.parse_cb.parse_play_spawn_player,
                self.pktCB.CHANGE_GAME_STATE[PKT]:
                    self.parse_cb.parse_play_change_game_state,
                self.pktCB.OPEN_WINDOW[PKT]:
                    self.parse_cb.parse_play_open_window,
                self.pktCB.TAB_COMPLETE[PKT]:
                    self.parse_cb.parse_play_tab_complete,
                self.pktCB.SET_SLOT[PKT]:
                    self.parse_cb.parse_play_set_slot,
                self.pktCB.PLAYER_LIST_ITEM[PKT]:
                    self.parse_cb.parse_play_player_list_item,
                self.pktCB.DISCONNECT[PKT]:
                    self.parse_cb.parse_play_disconnect,
                self.pktCB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message
                }
        }

        if self.entity_controls:
            self.parsers[PLAY][
                self.pktCB.SPAWN_OBJECT[PKT]] = self.parse_cb.parse_play_spawn_object  # noqa
            self.parsers[PLAY][
                self.pktCB.SPAWN_MOB[PKT]] = self.parse_cb.parse_play_spawn_mob
            self.parsers[PLAY][
                self.pktCB.ENTITY_RELATIVE_MOVE[PKT]] = self.parse_cb.parse_play_entity_relative_move  # noqa
            self.parsers[PLAY][
                self.pktCB.ENTITY_TELEPORT[PKT]] = self.parse_cb.parse_play_entity_teleport  # noqa
            self.parsers[PLAY][
                self.pktCB.ATTACH_ENTITY[PKT]] = self.parse_cb.parse_play_attach_entity  # noqa
            self.parsers[PLAY][
                self.pktCB.DESTROY_ENTITIES[PKT]] = self.parse_cb.parse_play_destroy_entities  # noqa
