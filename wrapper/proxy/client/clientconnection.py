# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# future imports
from __future__ import division

# Standard Library imports
import copy
import threading
import time
import json
import hashlib
from socket import error as socket_error
import requests

# Local imports
import proxy.utils.encryption as encryption

from proxy.server.serverconnection import ServerConnection
from proxy.packets.packet import Packet
from proxy.client.parse_sb import ParseSB
from proxy.packets import mcpackets_sb
from proxy.packets import mcpackets_cb
from proxy.utils.constants import *

from api.helpers import processcolorcodes, getjsonfile, putjsonfile


# noinspection PyMethodMayBeStatic
class Client(object):
    """
           Handles the client connection.

           Client is accessible as `api.player.client`

           This class is a "fake" server, accepting connections
           from clients.  It receives "SERVER BOUND" packets from client,
           parses them, and forards them on to the server.  It "sends" to the
           client (self.packet.sendpkt())

           Client receives the parent proxy as it's argument.

    """
    def __init__(self, proxy, clientsock, client_addr, banned=False):

        # basic __init__ items from passed arguments
        self.client_socket = clientsock
        self.client_address = client_addr
        self.proxy = proxy
        self.wrapper = self.proxy.wrapper
        self.javaserver = self.wrapper.javaserver
        self.public_key = self.proxy.public_key
        self.private_key = self.proxy.private_key
        self.log = self.proxy.log
        self.ipbanned = banned

        # read items from config:
        # self.spigot_mode = self.proxy.config["spigot-mode"]
        self.hidden_ops = self.proxy.config["hidden-ops"]
        self.silent_bans = self.proxy.config["silent-ipban"]
        self.names_change = self.proxy.config["auto-name-changes"]
        self.flush_rate = self.proxy.config["flush-rate-ms"] / 1000
        self.onlinemode = self.proxy.onlinemode

        # client setup and operating paramenters
        self.abort = False
        self.username = "PING REQUEST"
        self.packet = Packet(self.client_socket, self)
        self.verifyToken = encryption.generate_challenge_token()
        self.serverID = encryption.generate_server_id().encode('utf-8')
        self.MOTD = {}

        # client will reset this later, if need be..
        self.clientversion = self.javaserver.protocolVersion
        # default server port (to this wrapper's server)
        self.serverport = self.javaserver.server_port

        # packet stuff
        self.pktSB = mcpackets_sb.Packets(self.clientversion)
        self.pktCB = mcpackets_cb.Packets(self.clientversion)
        self.parse_sb = ParseSB(self, self.packet)
        # dictionary of parser packet constants and associated parsing methods
        self.parsers = {}
        self._getclientpacketset()

        # keep alive data
        self.time_last_ping_to_client = 0
        self.time_client_responded = 0
        self.keepalive_val = 0

        # client and server status

        # ------------------------
        # health items
        self.health = False
        self.food = 0
        self.food_sat = 0.0
        # raw chunk data for re-spawning player
        self.first_chunks = []
        # track rain states to ensure client and server are in same rain state
        self.raining = False
        self.usehub = self.proxy.usehub

        # Proxy ServerConnection()
        self.server_connection = None
        self.state = HANDSHAKE
        self.permit_disconnect_from_server = True

        # Hub controls
        # tells wrapper when the player login is authenticated
        self.wait_wait_for_auth = False
        # whether or not the player is on this wrapper world
        self.local = True
        # Handle disconnections based on what world player is in
        self.disc_request = False
        self.disc_reason = "No connection"
        # client info shared between wrappers:
        self.info = {
            "client-is-wrapper": False,
            "server-is-wrapper": False,
            "username": "",
            # these uuids are stored as strings
            "realuuid": "",  # if set, the real UUID from mojang API.
            "serveruuid": "",
            "wrapperuuid": "",  # usually the usernamereal uuid if wrapper is online.
            "ip": ""
        }

        # UUIDs - all should use MCUUID unless otherwise specified
        # --------------------------------------------------------
        # Server UUID - which is the local offline UUID.
        self.local_uuid = None
        # --------------------------------------------------------
        # The client UUID authenticated by connection to session server.  It
        # is the uuid by which wrapper has auth'ed the player.  If wrapper is
        # in offline mode, this could be the offline uuid
        # I changed this from uuid/online_uuid to be clearer that this
        # the uuid wrapper is accepting from it's proxy client.
        self.wrapper_uuid = None
        # --------------------------------------------------------
        # the formal, unique, mojang UUID as looked up on mojang servers.
        # This ID will be the same no matter what mode wrapper is in
        # or whether it is a lobby, etc.  This will be the formal uuid
        # to use for all wrapper internal functions for referencing a
        # unique player.Test
        self.mojanguuid = None

        # information gathered during login or socket connection processes
        # this will store the client IP for use by player.py
        if self.onlinemode:
            self.ip = self.client_address[0]
        else:
            self.ip = None

        # From client handshake.  For vanilla clients, it is what
        # the user entered to connect to your wrapper.
        self.serveraddressplayerused = None
        self.serverportplayerused = None

        # player api Items

        # EID collected by serverconnection (changes on each server)
        self.server_eid = 0
        self.gamemode = 0
        self.dimension = 0
        self.difficulty = 0
        self.level_type = "default"

        # player location and such
        self.position = (0, 0, 0)  # X, Y, Z # player.getPosition is pos+head
        self.head = (0, 0)  # Yaw, Pitch
        self.riding = None
        # last placement (for use in cases of bucket use)
        self.lastplacecoords = (0, 0, 0), 0

        # misc client attributes
        self.properties = {}
        self.clientSettings = False
        self.skin_blob = {}

        # inventory tracking
        self.inventory = {}
        self.slot = 0
        self.windowCounter = 2
        self.currentwindowid = 0  # zero for inventory
        self.noninventoryslotcount = 0
        self.lastitem = None

    def notify_disconnect(self, message):
        """
        Used to request a disconnection of the client.
        
        :param message: disconnect message.

        :Other arguments used from self:
            :Reads:
                :self.permit_disconnect_from_server: Whether the client
                 will be disconnected.  if set to False, the client is
                 not disconnected.
                :self.local: determines whether wrapper attempts to
                 respawn the player at the hub.
            :Sets:
                :self.disc_request: Flag- if set to True, this tells wrapper
                 that the disconnection/reconnection(for hubs) did not succeed.

        """
        self.disc_reason = message
        self.disc_request = True
        if self.permit_disconnect_from_server:
            self.disconnect(message)
            self.disc_request = False
        else:
            if not self.local:
                self.chat_to_client(
                    {"text": "Lost server connection: %s" % message,
                     "color": "red"}
                )
                time.sleep(.4)
                self.disc_request = False
                self.change_servers("localhost", self.serverport)
            else:
                self.disc_request = True

    def handle(self):
        # Main client connection loop thread started by proxy.base.py

        t = threading.Thread(target=self._flush_loop, args=())
        t.daemon = True
        t.start()
        while not self.abort:
            try:
                # last three items are for sending a compressed unparsed packet.
                pkid, orig_packet = self.packet.grabpacket()  # noqa
            except EOFError:
                # The client closed the socket connection
                self.abort = True
                break
            except socket_error:
                # Socket closed (abruptly).
                self.abort = True
                break
            except Exception as e:
                # anything that gets here is a bona-fide error
                # we need to become aware of
                self.log.error("%s Client Exception: Failed to grab packet "
                               "\n%s", self.username, e)
                self.abort = True
                break

            # Each condition is executed and evaluated in sequence:
            if self._parse(pkid) and \
                    self.server_connection and \
                    self.server_connection.packet and \
                    self.server_connection.state == PLAY:

                # wrapper handles LOGIN/HANDSHAKE with servers (via
                # self._parse(pkid), which DOES happen in all modes
                # as part of the `if` statement evaluation).

                # sending on to the server only happens in PLAY.
                self.server_connection.packet.send_raw_untouched(orig_packet)

        # upon self.abort
        self._close_server_instance("Client Handle Ended")
        try:
            self.client_socket.shutdown(2)
            self.client_socket.close()
        except (AttributeError, socket_error):
            self.log.debug(
                "(%s, %s) handle ending and client_socket does not "
                "exist any longer", self.username, self.ip
            )

    def _flush_loop(self):
        """
        packets accumulate in the packet.queue.  They are periodically 
        sent to the client in intervals.  The '.05' interval, which is also
        a minecraft tick, seems ideal.  Any shorter and packets seem to 
        get lost (Dropped items are invisible, etc).  Any longer makes the 
        game kind of jerky. '.1' would be tolerable unless in a combat
        situation.
        """
        rate = self.flush_rate
        while not self.abort:
            time.sleep(rate)
            try:
                self.packet.flush()
            except AttributeError:
                self.log.debug(
                    "%s client packet instance gone.", self.username
                )

            except socket_error:
                self.log.debug("%s client socket closed (socket_error).",
                               self.username)
                self.abort = True
                break
        if self.username != "PING REQUEST":
            self.log.debug("%s clientconnection _flush_loop thread ended",
                           self.username)
        self.proxy.removestaleclients()  # from proxy.clients

    def _parse(self, pkid):
        """
        A wrapper into our parsing functions.
        """
        if pkid in self.parsers[self.state]:
            # parser can return false
            return self.parsers[self.state][pkid]()
        return True

    def _set_parsers(self):
        """
        The packets we parse and the methods that parse them.
        """
        self.parsers = {
            HANDSHAKE: {
                self.pktSB.LEGACY_HANDSHAKE[PKT]:
                    self._parse_handshaking_legacy,
                self.pktSB.HANDSHAKE[PKT]:
                    self._parse_handshaking,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self.parse_sb.plugin_message,
                },
            STATUS: {
                self.pktSB.STATUS_PING[PKT]:
                    self._parse_status_ping,
                self.pktSB.REQUEST[PKT]:
                    self._parse_status_request,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self.parse_sb.plugin_message,
                },
            LOGIN: {
                self.pktSB.LOGIN_START[PKT]:
                    self._parse_login_start,
                self.pktSB.LOGIN_ENCR_RESPONSE[PKT]:
                    self._parse_login_encr_response,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self.parse_sb.plugin_message,
                },
            PLAY: {
                self.pktSB.CHAT_MESSAGE[PKT]:
                    self.parse_sb.play_chat_message,
                self.pktSB.CLICK_WINDOW[PKT]:
                    self.parse_sb.play_click_window,
                self.pktSB.CLIENT_SETTINGS[PKT]:
                    self.parse_sb.play_client_settings,
                self.pktSB.HELD_ITEM_CHANGE[PKT]:
                    self.parse_sb.play_held_item_change,
                self.pktSB.KEEP_ALIVE[PKT]:
                    self.parse_sb.keep_alive,
                self.pktSB.PLAYER_BLOCK_PLACEMENT[PKT]:
                    self.parse_sb.play_player_block_placement,
                self.pktSB.PLAYER_DIGGING[PKT]:
                    self.parse_sb.play_player_digging,
                self.pktSB.PLAYER_LOOK[PKT]:
                    self.parse_sb.play_player_look,
                self.pktSB.PLAYER_POSITION[PKT]:
                    self.parse_sb.play_player_position,
                self.pktSB.PLAYER_POSLOOK[PKT]:
                    self.parse_sb.play_player_poslook,
                self.pktSB.PLAYER_UPDATE_SIGN[PKT]:
                    self.parse_sb.play_player_update_sign,
                self.pktSB.SPECTATE[PKT]:
                    self.parse_sb.play_spectate,
                self.pktSB.USE_ITEM[PKT]:
                    self.parse_sb.play_use_item,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self.parse_sb.plugin_message,
                },
            # LOBBY is the state in which a player is not connected to a server.
            LOBBY: {
                self.pktSB.KEEP_ALIVE[PKT]:
                    self.parse_sb.keep_alive,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self.parse_sb.plugin_message,
                self.pktSB.CHAT_MESSAGE[PKT]:
                    self.parse_sb.play_chat_message,
                }
        }

    # LOGIN PARSERS SECTION
    # -----------------------
    def _parse_handshaking_legacy(self):
        # just disconnect them.
        self.log.debug(
            "Received Lagacy Handshake (closed unceremoniously) from %s." % (
                self.ip
            )
        )
        self.packet.send_raw(0xff+0x00+0x00+0x00)
        self.client_socket.shutdown(2)
        self.client_socket.close()
        self.abort = True

    def _parse_handshaking(self):
        """
        Client sends:
        version|address|port|state

        State is a request for either Status or Login.  From this,
        Wrapper garners the IP and UUID of the player, if it was
        sent with the handshake (which wrapper does).

        STATUS will cause wrapper to wait for a _parse_status_request,
        followed by a _parse_status_ping.

        LOGIN will initiate the login process into wrapper.

        """
        data = self.packet.readpkt([VARINT, STRING, USHORT, VARINT])

        self.clientversion = data[0]
        self._getclientpacketset()

        self.serveraddressplayerused = data[1]
        self.serverportplayerused = data[2]
        requested_state = data[3]

        if requested_state == STATUS:
            self.state = STATUS
            # wrapper will wait for REQUEST, so do nothing further.
            return False

        elif requested_state == LOGIN:
            # TODO - allow client connections despite lack of server connection

            splitaddress = self.serveraddressplayerused.split("\x00")
            # vanilla clients only send ip + x00 + port.
            # wrapper adds IP(the one that connected to it) and the UUID
            # Spigot and some others may also add these same two fields;
            # Wrapper adds /x00WPY to set itself apart.

            if len(splitaddress) > 2 and self.onlinemode is False:
                # wrapper will only accept this info if it is offline
                # and cannot be sure of the info itself
                if not self.onlinemode:
                    # Spigot and Wrapper share this in common:
                    self.mojanguuid = self.proxy.wrapper.mcuuid(splitaddress[2])
                    self.info["realuuid"] = self.mojanguuid.string
                    self.ip = splitaddress[1]
                if len(splitaddress) > 3 and splitaddress[3] == "WPY":
                    self.info["client-is-wrapper"] = True

            if self.javaserver.protocolVersion == -1:
                #  ... returns -1 to signal no server
                self.disconnect(
                    "The server is not started (protocol not established)."
                )
                return False

            if not self.javaserver.state == 2:
                self.disconnect(
                    "Server has not finished booting. Please try"
                    " connecting again in a few seconds"
                )
                return False

            if PROTOCOL_1_9START < self.clientversion < PROTOCOL_1_9REL1:
                self.disconnect("You're running an unsupported snapshot"
                                " (protocol: %s)!" % self.clientversion)
                return False
            if self.javaserver.protocolVersion != self.clientversion:
                self.disconnect("You're not running the same Minecraft"
                                " version as the server!")
                return False
            self.state = LOGIN
            # packet passes to server, which will also switch to Login
            return True

        # Wrong state in handshake
        else:
            self.disconnect("Invalid HANDSHAKE: 'requested state:"
                            " %d'" % requested_state)
        return False

    def _parse_status_ping(self):
        """
        Ping used to develop server ping values. Ping is sent after
        the Status Request
        """
        data = self.packet.readpkt([LONG])
        self.packet.sendpkt(self.pktCB.PING_PONG[PKT], [LONG], [data[0]])
        self.state = HANDSHAKE

        # self.abort = True
        return False

    def _parse_status_request(self):
        """
        Status Request - client sends server info in response and goes
        back to HANDSHAKE mode.
        """
        sample = []
        for player in self.proxy.wrapper.players:
            playerobj = self.proxy.wrapper.players[player]
            if playerobj.username not in self.hidden_ops:
                sample.append({"name": playerobj.username,
                               "id": str(playerobj.mojangUuid)})
            if len(sample) > 5:
                break
        reported_version = self.javaserver.protocolVersion
        reported_name = self.javaserver.version
        motdtext = self.javaserver.motd
        if self.clientversion >= PROTOCOL_1_8START:
            motdtext = processcolorcodes(motdtext.replace(
                "\\", ""))
        self.MOTD = {
            "description": motdtext,
            "players": {
                "max": int(self.proxy.config["max-players"]),
                "online": len(self.proxy.wrapper.players),
                "sample": sample
            },
            "version": {
                "name": reported_name,
                "protocol": reported_version
            }
        }

        # add Favicon, if it exists
        if self.javaserver.servericon:
            self.MOTD["favicon"] = self.javaserver.servericon

        # add Forge information, if applicable.
        if self.proxy.forge:
            self.MOTD["modinfo"] = self.proxy.mod_info["modinfo"]

        self.packet.sendpkt(
            self.pktCB.PING_JSON_RESPONSE[PKT],
            [STRING],
            [json.dumps(self.MOTD)]
        )

        # after this, proxy waits for the expected PING to
        #  go back to Handshake mode
        return False

    def _parse_login_start(self):
        """
        client requests a login NOW.
        """
        # This blocks waiting for _login_authenticate_client to finish.
        self.wait_wait_for_auth = True
        t = threading.Thread(target=self._continue_login_start,
                             name="Login", args=())
        t.daemon = True
        t.start()
        data = self.packet.readpkt([STRING, NULL])
        self.username = data[0]

        # just to be clear, this refers to wrapper's proxy mode, not the server.
        if self.onlinemode:
            # Wrapper sends client a login encryption request
            self.packet.sendpkt(
                self.pktCB.LOGIN_ENCR_REQUEST[PKT],
                self.pktCB.LOGIN_ENCR_REQUEST[PARSER],
                (self.serverID, self.public_key, self.verifyToken)
            )

            # Server UUID (or other offline wrapper) is always offline
            self.local_uuid = self.proxy.uuids.getuuidfromname(self.username)

            # allow the socket to keep moving while _continue_login_start
            #  continues to wait for auth..
            return False

        else:
            # Wrapper proxy offline and not authenticating
            # maybe it is the destination of a hub? or you use another
            #  way to authenticate (password plugin?)
            self._login_authenticate_client(None)

            # _login_authenticate_client already blocking since we called it...
            self.wait_wait_for_auth = False
            return False

    def _continue_login_start(self):
        """
        Wait for client authentication to complete before sending login event.
        """
        while self.wait_wait_for_auth:
            continue

        # log the client on
        if self._logon_client_into_proxy():
            # connect to server
            if self._connect_to_server()[0]:
                self.player_login()

    def player_login(self):
        self.proxy.eventhandler.callevent(
            "player.login",
            {"playername": self.username},
            abortable=False
        )

        """ eventdoc
            <group> core/mcserver.py <group>

            <description> internalfunction <description>

            <abortable> No <abortable>

            <comments> The event is really part of mcserver.py login()
            <comments>

            <payload>
            "player": will be generated by the event code.
            "playername": user name of client/player
            <payload>

        """

    def _parse_login_encr_response(self):
        """
        the client is RESPONDING to our request for encryption, if sent.
        """

        # read response Tokens - "shared_secret|verify_token"
        if self.javaserver.protocolVersion < 6:
            data = self.packet.readpkt([BYTEARRAY_SHORT, BYTEARRAY_SHORT])
        else:
            data = self.packet.readpkt([BYTEARRAY, BYTEARRAY])

        sharedsecret = encryption.decrypt_PKCS1v15_shared_data(
            data[0], self.private_key)
        verifytoken = encryption.decrypt_PKCS1v15_shared_data(
            data[1], self.private_key)
        h = hashlib.sha1()
        # self.serverID already encoded
        h.update(self.serverID)
        h.update(sharedsecret)
        h.update(self.public_key)
        serverid = self.packet.hexdigest(h)

        # feed info to packet.py for parsing
        self.packet.sendCipher = encryption.aes128cfb8(sharedsecret).encryptor()
        self.packet.recvCipher = encryption.aes128cfb8(sharedsecret).decryptor()

        # verify correct response
        if not verifytoken == self.verifyToken:
            self.state = HANDSHAKE
            self.disconnect("Verify tokens are not the same")
            return False

        # silent IP bans already occured in proxy/base.py host()
        # determine if IP is banned:
        if self.ipbanned:
            self.log.info("Player %s tried to connect from banned ip:"
                          " %s", self.username, self.ip)
            self.state = HANDSHAKE
            self.disconnect("Your address is IP-banned from this server!.")
            return False

        # begin Client logon process
        # Wrapper in online mode, taking care of authentication
        if self._login_authenticate_client(serverid) is False:
            self.state = HANDSHAKE
            self.disconnect("Your client authentication failed.")
            return False  # client failed to authenticate
        return False

    def _logon_client_into_proxy(self):
        """
        When the client first logs in to the wrapper proxy
        """

        # check for uuid ban
        if self.proxy.isuuidbanned(self.wrapper_uuid.string):
            banreason = self.proxy.getuuidbanreason(
                self.wrapper_uuid.string)
            self.log.info("Banned player %s tried to"
                          " connect:\n %s" % (self.username, banreason))
            self.state = HANDSHAKE
            self.disconnect("Banned: %s" % banreason)
            return

        # add client (or disconnect if full
        if len(self.proxy.clients) < self.proxy.config["max-players"]:
            self._add_client()
        else:
            uuids = getjsonfile(
                "bypass-maxplayers",
                "wrapper-data/json",
                self.proxy.encoding
            )
            if uuids:
                # people {uuid: name} in bypass-maxplayers can join anytime
                if self.mojanguuid.string in uuids:
                    self._add_client()
                else:
                    self.notify_disconnect("I'm sorry, the server is full!")
                    return False
            else:
                uuids = {
                    "uuiduuid-uuid-uuid-uuid-uuiduuiduuid": "playername",
                }
                putjsonfile(uuids, "bypass-maxplayers", "wrapper-data/json")
                self.notify_disconnect("I'm sorry, the server is full!")
                return False

        # Run the pre-login event
        if not self.proxy.eventhandler.callevent(
                "player.preLogin", {
                    "playername": self.username,
                    "online_uuid": self.wrapper_uuid.string,
                    "server_uuid": self.local_uuid.string,
                    "ip": self.ip,
                    "secure_connection": self.onlinemode
                }):
            """ eventdoc
                <group> Proxy <group>

                <description> Called before client logs on.  This event marks the 
                birth of the player object in wrapper (when in proxy mode)
                <description>

                <abortable> Yes, return False to disconnect the client. <abortable>

                <comments>
                - If aborted, the client is disconnnected with message 
                 "Login denied by a Plugin."
                - Event occurs after proxy ban code runs right after a 
                 successful handshake with Proxy.
                <comments>
                <payload>
                "playername": self.username,
                "player": Player object will be created by the event code
                "online_uuid": online UUID,
                "server_uuid": UUID on local server (offline),
                "ip": the user/client IP on the internet.
                "secure_connection": Proxy's online mode
                <payload>

            """  # noqa

            self.state = HANDSHAKE
            self.disconnect("Login denied by a Plugin.")
            del self.proxy.wrapper.players[self.username]
            return

        self.permit_disconnect_from_server = True
        self.log.info("%s's Proxy Client LOGON occurred: (UUID: %s"
                      " | IP: %s | SecureConnection: %s)",
                      self.username, self.wrapper_uuid.string,
                      self.ip, self.onlinemode)
        self._inittheplayer()  # set up inventory and stuff

        # set compression
        # compression was at the bottom of _login_authenticate_client...
        if self.clientversion >= PROTOCOL_1_8START:
            if "network-compression-threshold" in self.javaserver.properties:  # noqa
                comp = self.javaserver.properties[
                    "network-compression-threshold"]
                self.packet.sendpkt(
                    self.pktCB.LOGIN_SET_COMPRESSION[PKT], [VARINT], [comp])
                self.packet.compressThreshold = comp

        # send login success to client
        self.packet.sendpkt(
            self.pktCB.LOGIN_SUCCESS[PKT],
            [STRING, STRING],
            (self.wrapper_uuid.string, self.username))
        self.state = PLAY

        # start keep alives
        self.time_client_responded = time.time()
        t_keepalives = threading.Thread(
            target=self._keep_alive_tracker,
            args=())
        t_keepalives.daemon = True
        t_keepalives.start()
        return True

    def _connect_to_server(self, ip=None, port=None):
        """
        Connects the client to a server.  Creates a new server
        instance and tries to connect to it.  Leave ip and port
        blank to connect to the local wrapped javaserver instance.

        :param ip:  None will use localhost.
        :param port: port to connect to.
        
        it is the responsibility of the calling method to
        shutdown any existing server connection first.  It is
        also the caller's responsibility to track LOBBY modes
        and handle respawns, rain, etc.

        """

        self.server_connection = ServerConnection(self, ip, port)

        # connect the socket and start its flush_loop
        try:
            self.server_connection.connect()
        except Exception as e:
            mess = "Could not connect: %s" % e
            self.notify_disconnect(mess)
            return False, mess

        # start server handle() to read the packets
        t = threading.Thread(target=self.server_connection.handle, args=())
        t.daemon = True
        t.start()

        # switch server_connection to LOGIN to log in to (offline) server.
        # already done at server.connect()
        # self.server_connection.state = LOGIN

        # This means the wrapper is Offline AND a client connected directly!
        if not self.mojanguuid:
            self.notify_disconnect("Your client is not auth'ed to connect.")
            self.log.error(
                "Unauth'ed connection to this wrapper. %s" % str(
                    self.client_address)
            )
            return False, "Unauth'ed connection to this offline wrapper."
        # now we send it a handshake to request the server go to login mode
        # This format is compatible with wrapper, spitgot and vanilla:
        server_addr = "localhost\x00%s\x00%s\x00WPY\x00" % (
            self.client_address[0],
            self.mojanguuid.hex,
        )
        # if self.spigot_mode:
        #    server_addr = "localhost\x00%s\x00%s" % (
        #        self.client_address[0],
        #        # pretty sure spigot is doing this for the same reason we are.
        #        self.mojanguuid.hex
        #    )
        if self.proxy.forge:
            server_addr = "localhost\x00FML\x00%s\x00WPY\x00" % (
                self.mojanguuid.hex
            )

        self.server_connection.packet.sendpkt(
            self.server_connection.pktSB.HANDSHAKE[PKT],
            [VARINT, STRING, USHORT, VARINT],
            (self.clientversion, server_addr, self.serverport,
             LOGIN))

        # send the login request (server is offline, so it will
        # accept immediately by sending login_success)
        self.server_connection.packet.sendpkt(
            self.server_connection.pktSB.LOGIN_START[PKT],
            [STRING],
            [self.username])
        # give it a sec to get to play mode
        time.sleep(.5)
        return True, "Success"

    def close_server(self, term_message):
        """
        Wraps `_close_server_instance`.  This would be called by packet.py
        where its' self.obj would equal the clientconnection instance (since
        packet.py handles both client and server packets).

        :param term_message:
        """
        self._close_server_instance(term_message)

    def _close_server_instance(self, term_message):
        """
        Close the server connection gracefully if possible.
        """
        if self.server_connection:
            self.server_connection.close_server(term_message)

    def change_servers(self, ip="localhost", port=25600):
        """
        Leaves the current proxy server connection and attempts a
        new server connection.  If it fails, it attempts to re-connect
        to the server it just left.

        :param ip: the IP to connect to
        :param port: the local port.  These ports should not generally
         be accessible to outside networks.

        """
        # save these in case server can't be reached
        oldchunks = self.first_chunks
        oldinv = self.inventory
        oldhealth = (self.health, self.food, self.food_sat)
        oldport = self.server_connection.port
        oldip = self.server_connection.ip

        # Leave server
        self.log.debug("leaving server instance id %s ; Port %s",
                       id(self.server_connection),
                       port)
        self.permit_disconnect_from_server = self.serverport == port
        self.state = LOBBY
        self._close_server_instance("Leaving this world...")
        # This sleep gives server connection time to finish flush and close.
        time.sleep(.5)

        # enter lobby (close the client's rendering of the world).
        self._lobbify()
        despawn_dimension = self.dimension

        # set up for connect to server
        self.state = PLAY
        self.local = True
        self.permit_disconnect_from_server = False
        world = self._get_port_text(port)
        confirmation = "§6Connected to %s (%s)!" % (world[1], world[0])

        # connect to new server
        server_try = self._connect_to_server(ip, port)
        time.sleep(.3)
        if not server_try[0] or self.disc_request:

            # Could not connect...
            self.disc_request = False
            if server_try[1] and server_try[1] != "Success":
                self.disc_reason = server_try[1]

            self.log.debug(
                "connection to port %s failed: %s", world[0], server_try[1]
            )
            confirmation = {"text": "Could not connect to %s: %s" % (
                world[0], self.disc_reason),
                            "color": "dark_purple", "bold": "true"}

            # restore settings
            self.permit_disconnect_from_server = False
            port = oldport
            ip = oldip
            self.first_chunks = oldchunks
            self.inventory = oldinv
            self.health, self.food, self.food_sat = oldhealth

            # close attempted server and try to reconnect to former server.
            self.state = LOBBY
            self._close_server_instance("Unsuccessful connection...")
            time.sleep(.4)
            self.state = PLAY
            time.sleep(.1)
            server = self._connect_to_server(ip, port)
            time.sleep(.5)
            if not server[0]:
                self.disconnect(
                    "Could not return to HUB from failed subworld! %s|%s" % (
                        ip, port
                    )
                )
            self.permit_disconnect_from_server = True
        else:
            self.log.debug("connected to server instance id %s ; Port %s",
                           id(self.server_connection),
                           port)
        # We are now back on the original or a new server
        # give server time to get all chunks before respawn
        time.sleep(.3)
        new_dimension = self.dimension
        if new_dimension == despawn_dimension:
            # self._toggle_dim()

            confirmation = {"text": "Could not connect properly!  Wait and "
                                    "see if you re-spawn or type: `/hub` to "
                                    "re-spawn in the hub world",
                            "color": "red"}

        # We must re-send a few things to re-sync the client and (new) server.
        # re-send chunks
        for chunks in copy.copy(self.first_chunks):
            self.packet.sendpkt(self.pktCB.CHUNK_DATA[PKT], [RAW], chunks)

        self.send_client_settings()

        # spawn to overworld dimension
        self.packet.sendpkt(self.pktCB.RESPAWN[PKT],
                            self.pktCB.RESPAWN[PARSER],
                            (new_dimension, self.difficulty,
                             self.gamemode, self.level_type))

        # send player position & look
        self.packet.sendpkt(self.pktCB.PLAYER_POSLOOK[PKT],
                            self.pktCB.PLAYER_POSLOOK[PARSER],
                            (self.position[0],
                             self.position[1] + 1,
                             self.position[2],
                             self.head[0], self.head[1], 0, 123))

        # re-set inventory in client GUI
        for items in self.inventory:
            self.packet.sendpkt(self.pktCB.SET_SLOT[PKT],
                                self.pktCB.SET_SLOT[PARSER],
                                (0, items, self.inventory[items]))

        health = (self.health, self.food, self.food_sat)
        self.packet.sendpkt(self.pktCB.UPDATE_HEALTH[PKT],
                            self.pktCB.UPDATE_HEALTH[PARSER],
                            health)

        self.local = self.serverport == port
        if self.local:
            self.player_login()
        self.permit_disconnect_from_server = self.serverport == port

        self.chat_to_client(confirmation)

    def _lobbify(self):
        """
        Spawn client to different non-overworld dimension and end any
        raining.  Prepare to collect RAW chunk data (TODO and maybe health/inv).
        """
        self.first_chunks = []

        # stop local rain fall.
        if self.raining:
            self.raining = False
            self.packet.sendpkt(self.pktCB.CHANGE_GAME_STATE[PKT],
                                self.pktCB.CHANGE_GAME_STATE[PARSER],
                                (1, 0))

        self.chat_to_client("§5§lHold still.. changing worlds!", 2)
        # This sleep gives client time to read the message above
        time.sleep(1)

        # This respawns in a different dimension in preparation for respawning.
        self._toggle_dim()

    def _get_port_text(self, portnumber):
        """
        Get world and port descriptions from the config.
        """
        for worlds in self.proxy.proxy_worlds:
            if int(self.proxy.proxy_worlds[worlds]["port"]) == portnumber:
                infos = [worlds,
                         self.proxy.proxy_worlds[worlds]["desc"]]
                return infos
        return [portnumber, "wrapper hub"]

    def _toggle_dim(self):

        if self.dimension in (-1, 0):
            self.dimension = 1
        else:
            self.dimension = -1
        self.packet.sendpkt(self.pktCB.RESPAWN[PKT],
                            self.pktCB.RESPAWN[PARSER],
                            (self.dimension, self.difficulty,
                             self.gamemode, self.level_type))

    # noinspection PyBroadException
    def disconnect(self, message):
        """
        disconnects the client (runs close_server(), which will
         also shut off the serverconnection.py)

        Not used to disconnect from a server!

        This disconnects the client from this wrapper!  a `notify_disconnect`
        is the proper way to request a client's disconnection.

        """
        jsondict = {"text": "bye"}
        if type(message) is dict:
            jsondict = message
        elif type(message) is list:
            if type(message[0]) is dict:
                jsondict = message[0]
            if type(message[0]) is str:
                try:
                    jsondict = json.loads(message[0])
                # JSONDecodeError is not defined, so broadexception
                except Exception:
                    jsondict = message

        elif type(message) is str:
                jsonmessage = message  # server packets are read as json
                try:
                    jsondict = json.loads(jsonmessage)
                except Exception:
                    jsondict = jsonmessage

        if self.state in (PLAY, LOBBY):
            self.packet.sendpkt(
                self.pktCB.DISCONNECT[PKT],
                [JSON],
                [jsondict])

            self.log.debug("Sent PLAY state DISCONNECT packet to %s",
                           self.username)
        else:
            # self.packet.sendpkt(
            #    self.pktCB.LOGIN_DISCONNECT[PKT],
            #    [JSON],
            #    [message])
            # self.packet.sendpkt(
            #    self.pktCB.DISCONNECT[PKT],
            #    [JSON],
            #    [jsondict])

            if self.username != "PING REQUEST":
                self.log.debug(
                    "Client '%s', IP: '%s', State: %s': \n Disconnected: "
                    "'%s'", self.username, self.client_address[0], self.state,
                    message)

                self.chat_to_client(jsondict)
                time.sleep(5)
                self.packet.sendpkt(
                    self.pktCB.LOGIN_DISCONNECT[PKT],
                    [JSON],
                    [message])
                self._remove_client_and_player()
            else:
                self.packet.sendpkt(
                        self.pktCB.LOGIN_DISCONNECT[PKT],
                        [JSON],
                        [message])

        time.sleep(1)
        self.state = HANDSHAKE
        self._close_server_instance(
            "Just ran Disconnect() client.  Aborting client thread")
        self.abort = True

    # internal init and properties
    # -----------------------------
    @property
    def version(self):
        return self.clientversion

    def _inittheplayer(self):
        """
        There are 46 items 0-45 in 1.9 (shield) versus
        45 (0-44) in 1.8 and below.
        """
        for i in self.proxy.inv_slots:
            self.inventory[i] = {"id": -1}
        self.time_last_ping_to_client = time.time()
        self.time_client_responded = time.time()

    def _getclientpacketset(self):
        """
        Determine packet types - in this context, pktSB/pktCB is
         what is being received/sent from/to the client.
        That is why we refresh to the clientversion.
        """
        self.pktSB = mcpackets_sb.Packets(self.clientversion)
        self.pktCB = mcpackets_cb.Packets(self.clientversion)
        self._set_parsers()

    # client API things
    # -----------------
    def editsign(self, position, line1, line2, line3, line4, pre18=False):
        """
        Edits a sign that is being created.  Used by the editsign event.

        :param position:  x, y, x position of sign being placed/edited.
        :param line1: Lines of text (each sign has four lines).
        :param line2:
        :param line3:
        :param line4:
        :param pre18: (optional) set to True if sending to a 1.7.10 or
         earlier client.

        """
        if pre18:
            x = position[0]
            y = position[1]
            z = position[2]
            self.server_connection.packet.sendpkt(
                self.pktSB.PLAYER_UPDATE_SIGN[PKT],
                [INT, SHORT, INT, STRING, STRING, STRING, STRING],
                (x, y, z, line1, line2, line3, line4))
        else:
            self.server_connection.packet.sendpkt(
                self.pktSB.PLAYER_UPDATE_SIGN[PKT],
                [POSITION, STRING, STRING, STRING, STRING],
                (position, line1, line2, line3, line4))

    def chat_to_server(self, message, position=0):
        """
        Used to resend modified chat packets.  Also to mimic
        player in API player for say() and execute() methods

        :For position, see: http://wiki.vg/Chat#Processing_chat
         Should never be anything other than 0 (or maybe 1) since
         this is going to the server.

        """
        if self.version < PROTOCOL_1_11:
            if len(message) > 100:
                self.log.error(
                    "chat to server exceeded 100 characters "
                    "(%s probably got kicked)", self.username)
        if len(message) > 256:
            self.log.error(
                "chat to server exceeded 256 characters "
                "(%s probably got kicked)", self.username)

        self.server_connection.packet.sendpkt(
            self.pktSB.CHAT_MESSAGE[PKT], self.pktSB.CHAT_MESSAGE[PARSER],
            (message, position))

    def chat_to_client(self, message, position=0):
        """
        Used by player API to player.message().

        sendpacket for chat knows how to process either a chat dictionary
        or a string message!

        don't try sending a json.dumps string... it will simply be sent
        as a chat string inside a chat.message.translate item...

            :param message: Chat Dict or string
            :param position: See http://wiki.vg/Chat#Processing_chat
                0 = player chat message
                1 = Feedback from running a command (same position as 1)
                2 = displayed above the hot bar

        """
        self.packet.sendpkt(self.pktCB.CHAT_MESSAGE[PKT],
                            self.pktCB.CHAT_MESSAGE[PARSER],
                            (message, position))

    # internal client login methods
    # -----------------------------

    def _login_authenticate_client(self, server_id):
        # future TODO have option to be online but bypass session server.
        if self.onlinemode:
            r = requests.get("https://sessionserver.mojang.com"
                             "/session/minecraft/hasJoined?username=%s"
                             "&serverId=%s" % (self.username, server_id))
            if r.status_code == 200:
                # {
                #     "id": "<profile identifier>",
                #     "name": "<player name>",
                #     "properties": [
                #         {
                #             "name": "textures",
                #             "value": "<base64 string>",
                #             "signature": "<base64 string; signed data using Yggdrasil's private key>"  # noqa
                #         }
                #     ]
                # }
                requestdata = r.json()
                playerid = requestdata["id"]
                self.wrapper_uuid = self.proxy.wrapper.mcuuid(playerid)

                if requestdata["name"] != self.username:
                    self.disconnect("Client's username did not"
                                    " match Mojang's record")
                    self.log.info("Client's username did not"
                                  " match Mojang's record %s != %s",
                                  requestdata["name"], self.username)
                    return False

                for prop in requestdata["properties"]:
                    if prop["name"] == "textures":
                        self.skin_blob = prop["value"]
                        self.proxy.skins[
                            self.wrapper_uuid.string] = self.skin_blob
                self.properties = requestdata["properties"]
            else:
                self.disconnect("Proxy Client Session-Server Error"
                                " (HTTP Status Code %d)" % r.status_code)
                return False
            mojang_name = self.proxy.uuids.getusernamebyuuid(
                self.wrapper_uuid.string, uselocalname=False)
            self.local_uuid = self.proxy.uuids.getuuidfromname(self.username)
            local_name = self.proxy.usercache[
                self.wrapper_uuid.string]["localname"]
            if mojang_name:
                if mojang_name != local_name:
                    if self.names_change:
                        self.local_uuid = self.proxy.use_newname(
                            local_name, self.username, self.wrapper_uuid.string,
                            self
                        )
                    else:
                        self.log.info("%s's client performed LOGON in with "
                                      "new name, falling back to %s",
                                      self.username, local_name)
                        self.username = local_name

            # verified info we can now store:
            self.info["ip"] = self.ip
            self.mojanguuid = self.wrapper_uuid
            self.info["wrapperuuid"] = self.mojanguuid.string
            self.info["realuuid"] = self.mojanguuid.string
            self.info["serveruuid"] = self.local_uuid.string
            self.info["username"] = self.username
            self.info["client-is-wrapper"] = False

        # Wrapper offline and not authenticating
        # maybe it is the destination of a hub? or you use another
        # way to authenticate (passwords?)
        else:
            local_name = self.username
            mojanguuid = self.proxy.uuids.getuuidfromname(local_name).string

            if self.mojanguuid:
                mojanguuid = self.mojanguuid.string

            if len(self.info["realuuid"]) > 0:
                mojanguuid = self.info["realuuid"]
                local_name = self.proxy.usercache[mojanguuid]["localname"]
            if local_name != self.username:
                if self.names_change:
                    self.local_uuid = self.proxy.use_newname(
                        local_name, self.username, mojanguuid, self
                    )

                else:
                    self.log.info("%s's client performed LOGON in with "
                                  "new name, falling back to %s",
                                  self.username, local_name)
                    self.username = local_name
            self.local_uuid = self.proxy.uuids.getuuidfromname(self.username)
            self.wrapper_uuid = self.local_uuid
            self.info["wrapperuuid"] = self.wrapper_uuid.string
            self.info["serveruuid"] = self.wrapper_uuid.string
            self.info["username"] = self.username
            self.log.debug("Client logon with wrapper offline-"
                           " 'self.wrapper_uuid = OfflinePlayer:<name>'")

        self.wait_wait_for_auth = False

    def _add_client(self):
        """
        Put client into server data. (player login will be called
        later by mcserver.py)
        """
        if self not in self.proxy.clients:
            self.proxy.clients.append(self)

    def _keep_alive_tracker(self):
        """
        Send keep alives to client.
        """
        while not self.abort:
            time.sleep(1)
            if self.state in (PLAY, LOBBY):
                # client expects < 20sec
                # sending more frequently (5 seconds) seems to help with
                # some slower connections.
                if time.time() - self.time_last_ping_to_client > 9:
                    # vanilla MC 1.12 .2 uses a time() value.
                    # I use simple incrementing numbers vs randoms... I mean,
                    # what is the point of a random keepalive?
                    if self.version < PROTOCOL_1_12_2:
                        # sending a keepalive every second for more than 68
                        # years would be required to exceed the VARINT capacity
                        self.keepalive_val += 1
                    else:
                        # running forever would not allow keepalive to exceed
                        # LONG contraints
                        self.keepalive_val += 1

                    # challenge the client with it
                    self.packet.sendpkt(
                        self.pktCB.KEEP_ALIVE[PKT],
                        self.pktCB.KEEP_ALIVE[PARSER],
                        [self.keepalive_val])

                    self.time_last_ping_to_client = time.time()

                # check for active client keep alive status:
                # server can allow up to 30 seconds for response
                if time.time() - self.time_client_responded > 30:
                    self.disconnect("Client closed due to lack of"
                                    " keepalive response")
                    self.log.debug("Closed %s's client thread due to "
                                   "lack of keepalive response", self.username)
                    return
        self.log.debug("%s Client keepalive tracker aborted", self.username)
        self.disconnect("Client disconnected.")
        self.state = HANDSHAKE

    def _remove_client_and_player(self):
        """
        This is needed when the player is logged into wrapper, but not
        onto the local server (which normally keeps tabs on player
        and client objects).
        """
        if self.username in self.proxy.wrapper.players:
            if self.proxy.wrapper.players[self.username].client.state != LOBBY:
                self.proxy.wrapper.players[self.username].abort = True
                del self.proxy.wrapper.players[self.username]

    def send_client_settings(self):
        """
        Send the client settings.  This is normally done by wrapper when
        proxy receives the CB play_spawn_position.  change_servers() should do
        it also.

        Clientsettings is a raw bytes of the packet we read from the client.

        """
        if self.clientSettings:
            try:
                self.server_connection.packet.sendpkt(
                    self.pktSB.CLIENT_SETTINGS[PKT],
                    [RAW, ],
                    (self.clientSettings,))
            except AttributeError:
                # this will fail under certain circumstances when a player
                # disconnects abruptly.
                pass

    def _send_forge_client_handshakereset(self):
        """
        Sends a forge plugin channel packet to cause the client
         to recomplete its entire handshake from the start.

        from 'http://wiki.vg/Minecraft_Forge_Handshake':
         The normal forge server does not ever use this packet,
         but it is used when connecting through a BungeeCord
         instance, specifically when transitioning from a vanilla
         server to a modded one or from a modded server to
         another modded server.
         """
        channel = "FML|HS"
        if self.clientversion < PROTOCOL_1_8START:
            self.packet.sendpkt(
                self.pktCB.PLUGIN_MESSAGE[PKT],
                [STRING, SHORT, BYTE],
                [channel, 1, 254])

        else:
            self.packet.sendpkt(
                self.pktCB.PLUGIN_MESSAGE[PKT],
                [STRING, BYTE],
                [channel, 254])
