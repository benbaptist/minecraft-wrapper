# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# Standard Library imports
import copy
import threading
import time
import json
import hashlib
from socket import error as socket_error
import requests
import logging

# Local imports
import proxy.utils.encryption as encryption

from proxy.server.serverconnection import ServerConnection
from proxy.packets.packet import Packet
from proxy.client.parse_sb import ParseSB
from proxy.packets import mcpackets_sb
from proxy.packets import mcpackets_cb
from proxy.utils.constants import *

from proxy.utils.mcuuid import MCUUID
from api.helpers import processcolorcodes, getjsonfile, putjsonfile


# noinspection PyMethodMayBeStatic
class Client(object):
    def __init__(self, proxy, clientsock, client_addr, banned=False):
        """
        Handle the client connection.

        This class Client is a "fake" server, accepting connections
        from clients.  It receives "SERVER BOUND" packets from client,
        parses them, and forards them on to the server.  It "sends" to the
        client (self.sendpkt())

        Client receives the parent proxy as it's argument.
        No longer receives the proxy's wrapper instance!  All
        data is passed via servervitals from proxy's srv_data.
        """

        # basic __init__ items from passed arguments
        self.client_socket = clientsock
        self.client_address = client_addr
        self.proxy = proxy
        self.public_key = self.proxy.public_key
        self.private_key = self.proxy.private_key
        self.servervitals = self.proxy.srv_data

        self.log = self.proxy.log
        self.ipbanned = banned

        # constants from config:
        # self.spigot_mode = self.proxy.config["spigot-mode"]
        self.hidden_ops = self.proxy.config["hidden-ops"]
        self.silent_bans = self.proxy.config["silent-ipban"]
        self.names_change = self.proxy.config["auto-name-changes"]

        # Tracer items
        self.sb_names = self.proxy.sb_names
        self.cb_names = self.proxy.cb_names

        # names:
        # {
        # 0: ('PING_JSON_RESPONSE', '0x0'),
        # 1: ('SPAWN_EXPERIENCE_ORB', '0x1'),
        # 2: ('LOGIN_SUCCESS', '0x2'),
        #     ...
        # 78: ('ENTITY_PROPERTIES', '0x4e'),
        # 79: ('ENTITY_EFFECT', '0x4f'),
        # 238: ('REMOVED1_9', '0xee')
        # }
        self.ignored_cb = self.proxy.ignored_cb
        self.ignored_sb = self.proxy.ignored_sb
        self.display_len = self.proxy.display_len
        self.group_dupl = self.proxy.group_dupl
        self.lastCB = 255
        self.lastSB = 255
        self.packetloglevel = self.proxy.packetloglevel
        self.packetlog = self.getlogger("trace", self.packetloglevel)

        # client setup and operating paramenters
        self.username = "PING REQUEST"
        self.packet = Packet(self.client_socket, self)
        self.verifyToken = encryption.generate_challenge_token()
        self.serverID = encryption.generate_server_id().encode('utf-8')
        self.MOTD = {}

        # client will reset this later, if need be..
        self.clientversion = self.servervitals.protocolVersion
        # default server port (to this wrapper's server)
        self.serverport = self.servervitals.server_port
        self.onlinemode = self.proxy.config["online-mode"]

        # packet stuff
        self.pktSB = mcpackets_sb.Packets(self.clientversion)
        self.pktCB = mcpackets_cb.Packets(self.clientversion)
        self.parse_sb = ParseSB(self, self.packet)

        # dictionary of parser packet constants and associated parsing methods
        self.parsers = {}
        self._getclientpacketset()
        self.buildmode = False

        # keep alive data
        self.time_last_ping_to_client = 0
        self.time_client_responded = 0
        self.keepalive_val = 0

        # client and server status
        self.health = 10
        self.food = 10
        self.food_sat = 2.0
        self.usehub = self.proxy.config["built-in-hub"]
        self.first_chunks = []
        self.raining = False
        self.wait_wait_for_auth = False
        self.local = True
        self.disc_request = False
        self.disc_reason = "No connection"
        self.abort = False
        self.info = {
            "client-is-wrapper": False,
            "server-is-wrapper": False,
            "username": "",
            # these uuids are stored as strings
            "realuuid": "",  # if set, the real UUID from mojang API.
            "serveruuid": "",
            "wrapperuuid": "",  # usually the real uuid if wrapper is online.
            "ip": ""
        }

        # Proxy ServerConnection()
        self.server_connection = None
        self.state = HANDSHAKE
        self.permit_disconnect_from_server = True

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
        # unique player.
        self.mojanguuid = None

        # information gathered during login or socket connection processes
        # this will store the client IP for use by player.py
        self.ip = self.client_address[0]

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

        self.position = (0, 0, 0)  # X, Y, Z
        self.head = (0, 0)  # Yaw, Pitch
        self.inventory = {}
        self.slot = 0
        self.riding = None
        # last placement (for use in cases of bucket use)
        self.lastplacecoords = (0, 0, 0)
        self.properties = {}
        self.clientSettings = False
        self.clientSettingsSent = False
        self.skin_blob = {}
        self.windowCounter = 2
        # this should be zero to get updates for inventory
        self.currentwindowid = 0
        self.noninventoryslotcount = 0
        self.lastitem = None

    def notify_disconnect(self, message):
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
                self.change_servers("127.0.0.1", self.serverport)
            else:
                self.disc_request = True

    def handle(self):
        """ Main client connection loop """
        t = threading.Thread(target=self.flush_loop, args=())
        t.daemon = True
        t.start()
        pktcounter = 1
        lastcount = 1
        while not self.abort:
            try:
                # last three items are for sending a compressed unparsed packet.
                pkid, orig_packet = self.packet.grabpacket()  # noqa
            except EOFError:
                # This is not really an error.. It means the client
                # is not sending packet stream anymore
                if self.username != "PING REQUEST":
                    self.log.debug("%s Client Packet stream ended [EOF]",
                                   self.username)
                self.abort = True
                break
            except socket_error:
                # occurs anytime a socket is closed.
                if self.username != "PING REQUEST":
                    self.log.debug("%s Client Proxy Failed to grab packet",
                                   self.username)
                self.abort = True
                break
            except Exception as e:
                # anything that gets here is a bona-fide error
                # we need to become aware of
                self.log.error("%s Client Exception: Failed to grab packet "
                               "\n%s", self.username, e)
                self.abort = True
                break

            # send packet if parsing passes and server available.
            # Python will not attempt eval of self.server_connection.state
            #  if self.server_connection is first False; so this will not raise
            #  an exception of the server_connection stops.
            if self.parse(pkid) and \
                    self.server_connection and \
                    self.server_connection.packet and \
                    self.server_connection.state == PLAY:

                # sending to the server only happens in
                # PLAY (not IDLE, HANDSHAKE, or LOGIN)
                # wrapper handles LOGIN/HANDSHAKE with servers (via
                # self.parse(pkid), which DOES happen in all modes)
                self.server_connection.packet.send_raw_untouched(orig_packet)

                if pkid in self.ignored_sb:
                    pktcounter = 1
                    lastcount = 1
                    self.lastSB = 255
                    continue
                if self.group_dupl and pkid == self.lastSB:
                    pktcounter += 1
                    lastcount = pktcounter
                    self.lastSB = pkid
                    continue
                else:
                    pktcounter = 1
                    self.lastSB = pkid
                try:
                    name = self.sb_names[pkid][0]
                except AttributeError:
                    name = "NOT_FOUND"
                hexrep = hex(pkid)
                textualrep = str(orig_packet[2:self.display_len], encoding="cp437")
                mapping = [('\x00', 'x_'), ('\n', 'xn'), ('\b', 'xb'),
                           ('\t', 'xt'),
                           ('\a', 'xa'), ('\r', 'xr')]
                for k, v in mapping:
                    textualrep = textualrep.replace(k, v)

                self.packetlog.debug(
                    "SB%s==>> (id_%d)%s-%s: '%s'",
                    self.state,
                    pkid,
                    name,
                    hexrep,
                    textualrep)
                if lastcount > 1:
                    self.packetlog.debug(
                        "       There were %s more of these: SB==>> '%s'",
                        lastcount - 1,
                        name)

        # sometimes (like during a ping request), a client may never enter PLAY
        # mode and will never be assigned a server connection...
        if self.server_connection:
            self.close_server_instance("Client Handle Ended")  # upon self.abort

    def flush_loop(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket_error:
                self.log.debug("%s client socket closed (socket_error).",
                               self.username)
                break
            time.sleep(0.01)
        if self.username != "PING REQUEST":
            self.log.debug("%s clientconnection flush_loop thread ended",
                           self.username)
        self.proxy.removestaleclients()  # from proxy.srv_data.clients

    def parse(self, pkid):
        if pkid in self.parsers[self.state]:
            # parser can return false
            return self.parsers[self.state][pkid]()
        return True

    def _define_parsers(self):
        # the packets we parse and the methods that parse them.
        # this is the rough order they happen in, as well.
        self.parsers = {
            HANDSHAKE: {
                self.pktSB.LEGACY_HANDSHAKE[PKT]:
                    self._parse_handshaking_legacy,
                self.pktSB.HANDSHAKE[PKT]:
                    self._parse_handshaking,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message,
                },
            STATUS: {
                self.pktSB.STATUS_PING[PKT]:
                    self._parse_status_ping,
                self.pktSB.REQUEST[PKT]:
                    self._parse_status_request,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message,
                },
            LOGIN: {
                self.pktSB.LOGIN_START[PKT]:
                    self._parse_login_start,
                self.pktSB.LOGIN_ENCR_RESPONSE[PKT]:
                    self._parse_login_encr_response,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message,
                },
            PLAY: {
                self.pktSB.CHAT_MESSAGE[PKT]:
                    self.parse_sb.parse_play_chat_message,
                self.pktSB.CLICK_WINDOW[PKT]:
                    self.parse_sb.parse_play_click_window,
                self.pktSB.CLIENT_SETTINGS[PKT]:
                    self.parse_sb.parse_play_client_settings,
                self.pktSB.HELD_ITEM_CHANGE[PKT]:
                    self.parse_sb.parse_play_held_item_change,
                self.pktSB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktSB.PLAYER_BLOCK_PLACEMENT[PKT]:
                    self.parse_sb.parse_play_player_block_placement,
                self.pktSB.PLAYER_DIGGING[PKT]:
                    self.parse_sb.parse_play_player_digging,
                self.pktSB.PLAYER_LOOK[PKT]:
                    self.parse_sb.parse_play_player_look,
                self.pktSB.PLAYER_POSITION[PKT]:
                    self.parse_sb.parse_play_player_position,
                self.pktSB.PLAYER_POSLOOK[PKT]:
                    self.parse_sb.parse_play_player_poslook,
                self.pktSB.PLAYER_UPDATE_SIGN[PKT]:
                    self.parse_sb.parse_play_player_update_sign,
                self.pktSB.SPECTATE[PKT]:
                    self.parse_sb.parse_play_spectate,
                self.pktSB.USE_ITEM[PKT]:
                    self.parse_sb.parse_play_use_item,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message,
                },
            LOBBY: {
                self.pktSB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message,
                self.pktSB.CHAT_MESSAGE[PKT]:
                    self.parse_sb.parse_play_chat_message,
                },
            IDLE: {
                self.pktSB.PLUGIN_MESSAGE[PKT]:
                    self._parse_plugin_message,
            }
        }

    def _plugin_response(self, response):
        if "ip" in response:
            self.info["username"] = response["username"]
            self.info["realuuid"] = MCUUID(response["realuuid"]).string
            self.info["ip"] = response["ip"]

            self.ip = response["ip"]
            if response["realuuid"] != "":
                self.mojanguuid = MCUUID(response["realuuid"])
            self.username = response["username"]
            return True
        else:
            self.log.debug(
                "some kind of error with _plugin_response - no 'ip' key"
            )
            return False

    # CB PONG
    def _plugin_poll_client_wrapper(self):
        channel = "WRAPPER.PY|PONG"
        data = json.dumps(self.info)
        # only our wrappers communicate with this, so, format is not critical
        self.packet.sendpkt(self.pktCB.PLUGIN_MESSAGE[PKT], [STRING, STRING],
                            (channel, data), serverbound=False)
    # PARSERS SECTION
    # -----------------------------

    # plugin channel handler
    # -----------------------

    def _parse_plugin_message(self):
        """server-bound"""
        channel = self.packet.readpkt([STRING, ])[0]

        if channel == "MC|Brand":
            data = self.packet.readpkt([RAW, ])[0]
            print(data)
            return True

        if channel not in self.proxy.registered_channels:
            # we are not actually registering our channels with the MC server
            # and there will be no parsing of other channels.
            return True

        # SB PING
        if channel == "WRAPPER.PY|PING":
            # then we now know this wrapper is a child wrapper since
            # minecraft clients will not ping us
            self.info["client-is-wrapper"] = True
            self._plugin_poll_client_wrapper()

        # SB RESP
        elif channel == "WRAPPER.PY|RESP":
            # read some info the client wrapper sent
            # since we are only communicating with wrappers; we use the modern
            #  format:
            datarest = self.packet.readpkt([STRING, ])[0]
            response = json.loads(datarest, encoding='utf-8')
            if self._plugin_response(response):
                pass  # for now...

        # do not pass Wrapper.py registered plugin messages
        return False

    def _parse_keep_alive(self):
        data = self.packet.readpkt(self.pktSB.KEEP_ALIVE[PARSER])

        if data[0] == self.keepalive_val:
            self.time_client_responded = time.time()
        return False

    # Login parsers
    # -----------------------
    def _parse_handshaking_legacy(self):
        # just disconnect them.
        self.packet.send_raw(0xff+0x00+0x00+0x00)

    def _parse_handshaking(self):
        # "version|address|port|state"
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
            if len(splitaddress) > 2 and self.onlinemode is False:
                # Spigot and Wrapper share this in common:
                self.mojanguuid = MCUUID(splitaddress[2])
                self.info["realuuid"] = self.mojanguuid.string
                self.ip = splitaddress[1]
                if len(splitaddress) > 3 and splitaddress[3] == "WPY":
                    self.info["client-is-wrapper"] = True

            if self.servervitals.protocolVersion == -1:
                #  ... returns -1 to signal no server
                self.disconnect(
                    "The server is not started (protocol not established)."
                )
                return False

            if not self.servervitals.state == 2:
                self.disconnect(
                    "Server has not finished booting. Please try"
                    " connecting again in a few seconds"
                )
                return False

            if PROTOCOL_1_9START < self.clientversion < PROTOCOL_1_9REL1:
                self.disconnect("You're running an unsupported snapshot"
                                " (protocol: %s)!" % self.clientversion)
                return False
            if self.servervitals.protocolVersion != self.clientversion:
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
        data = self.packet.readpkt([LONG])
        self.packet.sendpkt(self.pktCB.PING_PONG[PKT], [LONG], [data[0]], serverbound=False)
        self.state = HANDSHAKE
        return False

    def _parse_status_request(self):
        sample = []
        for player in self.servervitals.players:
            playerobj = self.servervitals.players[player]
            if playerobj.username not in self.hidden_ops:
                sample.append({"name": playerobj.username,
                               "id": str(playerobj.mojangUuid)})
            if len(sample) > 5:
                break
        reported_version = self.servervitals.protocolVersion
        reported_name = self.servervitals.version
        motdtext = self.servervitals.motd
        if self.clientversion >= PROTOCOL_1_8START:
            motdtext = processcolorcodes(motdtext.replace(
                "\\", ""))
        self.MOTD = {
            "description": motdtext,
            "players": {
                "max": int(self.proxy.config["max-players"]),
                "online": len(self.servervitals.players),
                "sample": sample
            },
            "version": {
                "name": reported_name,
                "protocol": reported_version
            }
        }

        # add Favicon, if it exists
        if self.servervitals.serverIcon:
            self.MOTD["favicon"] = self.servervitals.serverIcon

        # add Forge information, if applicable.
        if self.proxy.forge:
            self.MOTD["modinfo"] = self.proxy.mod_info["modinfo"]

        self.packet.sendpkt(
            self.pktCB.PING_JSON_RESPONSE[PKT],
            [STRING],
            [json.dumps(self.MOTD)],
            serverbound=False
        )

        # after this, proxy waits for the expected PING to
        #  go back to Handshake mode
        return False

    def _parse_login_start(self):
        data = self.packet.readpkt([STRING, NULL])
        self.username = data[0]
        t = threading.Thread(target=self._continue_login_start,
                             name="Login", args=())
        t.daemon = True

        # just to be clear, this refers to wrapper's mode, not the server.
        if self.onlinemode:
            # Wrapper sends client a login encryption request
            self.packet.sendpkt(
                self.pktCB.LOGIN_ENCR_REQUEST[PKT],
                self.pktCB.LOGIN_ENCR_REQUEST[PARSER],
                (self.serverID, self.public_key, self.verifyToken), serverbound=False
            )

            # Server UUID (or other offline wrapper) is always offline
            self.local_uuid = self.proxy.uuids.getuuidfromname(self.username)
            self.wait_wait_for_auth = True
        else:
            # Wrapper proxy offline and not authenticating
            # maybe it is the destination of a hub? or you use another
            #  way to authenticate (password plugin?)

            # Wrapper UUID is offline in this case.
            self.wrapper_uuid = self.proxy.uuids.getuuidfromname(self.username)

            # Of course local server is offline too...
            self.local_uuid = self.wrapper_uuid

        # allow the socket connection to keep moving..
        t.start()
        return False

    def _continue_login_start(self):
        while self.wait_wait_for_auth:
            continue

        # log the client on
        if self.logon_client_into_proxy():
            # connect to server
            if self.connect_to_server()[0]:
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

                # Our client does not get into play mode fast enough to
                # get this when the server first sends it.
                # print("FIRING CHANGE GAME STATE (CS) %s" % self.gamemode)
                # self.packet.sendpkt(
                #    self.pktCB.CHANGE_GAME_STATE[PKT],
                #    self.pktCB.CHANGE_GAME_STATE[PARSER],
                #    (3, self.gamemode))

    def _parse_login_encr_response(self):
        # the client is RESPONDING to our request for
        #  encryption (if we sent one above)

        # read response Tokens - "shared_secret|verify_token"
        if self.servervitals.protocolVersion < 6:
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

    def logon_client_into_proxy(self):
        """  When the client first logs in to the wrapper proxy """

        # add client (or disconnect if full
        if len(self.proxy.srv_data.clients) < self.proxy.config["max-players"]:
            self._add_client()
        else:
            uuids = getjsonfile(
                "bypass-maxplayers",
                "wrapper-data/json",
                self.proxy.encoding
            )
            if uuids:
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

        # check for uuid ban
        if self.proxy.isuuidbanned(self.wrapper_uuid.string):
            banreason = self.proxy.getuuidbanreason(
                self.wrapper_uuid.string)  # changed from __str__()
            self.log.info("Banned player %s tried to"
                          " connect:\n %s" % (self.username, banreason))
            self.state = HANDSHAKE
            self.disconnect("Banned: %s" % banreason)
            return

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
            del self.servervitals.players[self.username]
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
            if "network-compression-threshold" in self.proxy.srv_data.properties:  # noqa
                comp = self.proxy.srv_data.properties[
                    "network-compression-threshold"]
                self.packet.sendpkt(
                    self.pktCB.LOGIN_SET_COMPRESSION[PKT], [VARINT], [comp], serverbound=False)
                self.packet.compressThreshold = comp

        # send login success to client
        self.packet.sendpkt(
            self.pktCB.LOGIN_SUCCESS[PKT],
            [STRING, STRING],
            (self.wrapper_uuid.string, self.username), serverbound=False)
        self.state = PLAY

        # start keep alives
        self.time_client_responded = time.time()
        t_keepalives = threading.Thread(
            target=self._keep_alive_tracker,
            args=())
        t_keepalives.daemon = True
        t_keepalives.start()
        return True

    def connect_to_server(self, ip=None, port=None):
        """
        Connects the client to a server.  Creates a new server
        instance and tries to connect to it.  Leave ip and port
        blank to connect to the local wrapped javaserver instance.

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
            mess = "Proxy client could not connect to the server (%s)" % e
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

    def close_server_instance(self, term_message):
        """ Close the server connection gracefully if possible. """
        if self.server_connection:
            self.server_connection.close_server(term_message)

    def lobbify(self):
        """spawn client to different non-overworld dimension and end any
            raining.  Prepare to collect RAW chunk data."""
        self.first_chunks = []

        # stop local rain fall.
        if self.raining:
            self.raining = False
            self.packet.sendpkt(self.pktCB.CHANGE_GAME_STATE[PKT],
                                self.pktCB.CHANGE_GAME_STATE[PARSER],
                                (1, 0), serverbound=False)

        self.chat_to_client("§5§lHold still.. changing worlds!", 2)
        # This sleep gives client time to read the message above
        time.sleep(1)

        # get fresh inventory setup
        self._inittheplayer()

        # This respawns in a different dimension in preparation for respawning.
        self.toggle_dim()

        self.log.debug("LOBBIFY LEFT DIM: %s", self.dimension)

    def get_port_text(self, portnumber):
        for worlds in self.proxy.proxy_worlds:
            if self.proxy.proxy_worlds[worlds]["port"] == portnumber:
                infos = [worlds,
                         self.proxy.proxy_worlds[worlds]["desc"]]
                return infos
        return [portnumber, "wrapper hub"]

    def toggle_dim(self):

        if self.dimension in (-1, 0):
            self.dimension = 1
        else:
            self.dimension = -1
        self.packet.sendpkt(self.pktCB.RESPAWN[PKT],
                            self.pktCB.RESPAWN[PARSER],
                            (self.dimension, self.difficulty,
                             self.gamemode, self.level_type), serverbound=False)

    def change_servers(self, ip="127.0.0.1", port=25600):
        self.log.debug("leaving server instance id %s ; Port %s",
                       id(self.server_connection),
                       port)
        self.permit_disconnect_from_server = self.serverport == port
        self.state = LOBBY
        self.close_server_instance("Leaving this world...")
        # This sleep gives server connection time to finish flush and close.
        time.sleep(.5)

        # save these in case server can't be reached
        oldchunks = self.first_chunks
        oldinv = self.inventory
        self.lobbify()
        despawn_dimension = self.dimension
        self.log.debug("OLD DIM %s", despawn_dimension)

        # connect to server
        self.state = PLAY
        self.local = True
        self.permit_disconnect_from_server = False
        server_try = self.connect_to_server(ip, port)
        time.sleep(.1)
        world = self.get_port_text(port)
        confirmation = "§6Connected to %s (%s)!" % (world[1], world[0])
        if not server_try[0] or self.disc_request:
            self.disc_request = False
            self.log.debug(
                "connection to port %s failed: %s", world[0], server_try[1]
            )
            confirmation = {"text": "Could not connect to %s: %s" % (
                world[0], self.disc_reason),
                            "color": "dark_purple", "bold": "true"}
            self.disc_reason = "No connection"
            port = self.proxy.srv_data.server_port
            ip = "localhost"
            self.permit_disconnect_from_server = False
            self.first_chunks = oldchunks
            self.inventory = oldinv
            self.state = LOBBY
            self.close_server_instance("Unsuccessful connection...")
            time.sleep(.4)
            self.state = PLAY
            time.sleep(.1)
            server = self.connect_to_server(ip, port)
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

        # give server time to get all chunks before respawn
        time.sleep(.3)
        new_dimension = self.dimension
        self.log.debug("NEW DIM %s", new_dimension)
        if new_dimension == despawn_dimension:
            # self.toggle_dim()

            confirmation = {"text": "Could not connect properly!  Wait and "
                                    "see if you re-spawn or type: `/hub` to "
                                    "re-spawn in the hub world",
                            "color": "red"}

        # re-send chunks
        for chunks in copy.copy(self.first_chunks):
            self.packet.sendpkt(self.pktCB.CHUNK_DATA[PKT], [RAW], chunks, serverbound=False)

        health = (self.health, self.food, self.food_sat)
        # spawn to overworld dimension
        self.packet.sendpkt(self.pktCB.RESPAWN[PKT],
                            self.pktCB.RESPAWN[PARSER],
                            (new_dimension, self.difficulty,
                             self.gamemode, self.level_type), serverbound=False)

        # send player position & look
        self.packet.sendpkt(self.pktCB.PLAYER_POSLOOK[PKT],
                            self.pktCB.PLAYER_POSLOOK[PARSER],
                            (self.position[0],
                             self.position[1] + 1,
                             self.position[2],
                             self.head[0], self.head[1], 0, 123), serverbound=False)

        # re-set inventory in client GUI
        for items in self.inventory:
            self.packet.sendpkt(self.pktCB.SET_SLOT[PKT],
                                self.pktCB.SET_SLOT[PARSER],
                                (0, items, self.inventory[items]), serverbound=False)

        self.packet.sendpkt(self.pktCB.UPDATE_HEALTH[PKT],
                            self.pktCB.UPDATE_HEALTH[PARSER],
                            health, serverbound=False)

        self.local = self.serverport == port
        self.permit_disconnect_from_server = self.serverport == port

        self.chat_to_client(confirmation)

    # noinspection PyBroadException
    def disconnect(self, message):
        """
        disconnects the client (runs close_server(), which will
         also shut off the serverconnection.py)

        Not used to disconnect from a server!  This disconnects the client.
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
                except Exception:  # JSONDecodeError is not defined, so broadexception  # noqa
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
                [jsondict], serverbound=False)

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
                    "State was 'other': sent chat reason to %s",
                    self.username)
                self.chat_to_client(jsondict)
                time.sleep(5)
                self.packet.sendpkt(
                    self.pktCB.LOGIN_DISCONNECT[PKT],
                    [JSON],
                    [message], serverbound=False)
                self._remove_client_and_player()
            else:
                self.packet.sendpkt(
                        self.pktCB.LOGIN_DISCONNECT[PKT],
                        [JSON],
                        [message], serverbound=False)

        time.sleep(1)
        self.state = HANDSHAKE
        self.close_server_instance(
            "run Disconnect() client.  Aborting client thread")
        self.abort = True

    # internal init and properties
    # -----------------------------
    @property
    def version(self):
        return self.clientversion

    def _inittheplayer(self):
        # so few items and so infrequently run that fussing with
        #  xrange/range PY2 difference is not needed.
        # there are 46 items 0-45 in 1.9 (shield) versus
        #  45 (0-44) in 1.8 and below.
        for i in self.proxy.inv_slots:
            self.inventory[i] = {"id": -1}
        self.time_last_ping_to_client = time.time()
        self.time_client_responded = time.time()

    def _getclientpacketset(self):
        # Determine packet types  - in this context, pktSB/pktCB is
        # what is being received/sent from/to the client.
        # That is why we refresh to the clientversion.
        self.pktSB = mcpackets_sb.Packets(self.clientversion)
        self.pktCB = mcpackets_cb.Packets(self.clientversion)
        self._define_parsers()

    def editsign(self, position, line1, line2, line3, line4, pre18=False):
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
        """ used to resend modified chat packets.  Also to mimic
        player in API player for say() and execute() methods """
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
        """ used by player API to player.message().

        sendpacket for chat knows how to process either a chat dictionary
        or a string message!

        don't try sending a json.dumps string... it will simply be sent
        as a chat string inside a chat.message translate item...
        """
        self.packet.sendpkt(self.pktCB.CHAT_MESSAGE[PKT],
                            self.pktCB.CHAT_MESSAGE[PARSER],
                            (message, position), serverbound=False)

    # internal client login methods
    # -----------------------------
    def _keep_alive_tracker(self):
        """ Send keep alives to client. """
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
                        [self.keepalive_val], serverbound=False)

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
                self.wrapper_uuid = MCUUID(playerid)

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
                self.wrapper_uuid.string)
            if mojang_name:
                if mojang_name != self.username:
                    if self.names_change:
                        self.username, self.local_uuid = self.proxy.use_newname(
                            self.username, mojang_name, self.wrapper_uuid.string
                        )
                        self.info["username"] = self.username
                    else:
                        self.log.info("%s's client performed LOGON in with "
                                      "new name, falling back to %s",
                                      self.username, mojang_name)

            self.local_uuid = self.proxy.uuids.getuuidfromname(self.username)

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
            # I'll take your word for it, bub...  You are:
            self.local_uuid = self.proxy.uuids.getuuidfromname(self.username)
            self.wrapper_uuid = self.local_uuid
            self.info["wrapperuuid"] = self.wrapper_uuid.string
            self.info["serveruuid"] = self.wrapper_uuid.string
            self.info["username"] = self.username
            self.log.debug("Client logon with wrapper offline-"
                           " 'self.wrapper_uuid = OfflinePlayer:<name>'")

        self.wait_wait_for_auth = False

    def _add_client(self):
        # Put client into server data. (player login
        #  will be called later by mcserver.py)
        if self not in self.proxy.srv_data.clients:
            self.proxy.srv_data.clients.append(self)

    def _remove_client_and_player(self):
        """ This is needed when the player is logged into wrapper, but not
        onto the local server (which normally keeps tabs on player
        and client objects)."""
        if self.username in self.proxy.srv_data.players:
            if self.proxy.srv_data.players[self.username].client.state != LOBBY:
                self.proxy.srv_data.players[self.username].abort = True
                del self.proxy.srv_data.players[self.username]

    def _send_client_settings(self):
        if self.clientSettings and not self.clientSettingsSent:
            self.server_connection.packet.sendpkt(
                self.pktSB.CLIENT_SETTINGS[PKT],
                [RAW, ],
                (self.clientSettings,))

            self.clientSettingsSent = True

    def _send_forge_client_handshakereset(self):
        """
        Sends a forge plugin channel packet to causes the client
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
                [channel, 1, 254], serverbound=False)

        else:
            self.packet.sendpkt(
                self.pktCB.PLUGIN_MESSAGE[PKT],
                [STRING, BYTE],
                [channel, 254], serverbound=False)

    @staticmethod
    def getlogger(name, level):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s (%(levelname)s) - %(message)s')
        handler = logging.FileHandler('/home/surest/Desktop/%s.log' % name)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
