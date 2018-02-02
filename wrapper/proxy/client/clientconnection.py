# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# Standard Library imports
import threading
import time
import json
import hashlib
import random
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

from proxy.utils.mcuuid import MCUUID

from api.helpers import processcolorcodes, processoldcolorcodes, chattocolorcodes


# noinspection PyMethodMayBeStatic
class Client(object):
    def __init__(self, proxy, clientsock, client_addr, banned=False):
        """
        Handle the client connection.

        This class Client is a "fake" server, accepting connections
        from clients.  It receives "SERVER BOUND" packets from client,
        parses them, and forards them on to the server.  It "sends" to the
        client (self.send() or self.sendpkt())

        Client receives the parent proxy as it's argument.
        No longer receives the proxy's wrapper instance!  All
        data is passed via servervitals from proxy's srv_data.
        """

        # basic __init__ items from passed arguments
        self.client_socket = clientsock
        self.client_address = client_addr
        self.proxy = proxy
        self.publicKey = self.proxy.publicKey
        self.privateKey = self.proxy.privateKey
        self.servervitals = self.proxy.srv_data

        self.log = self.proxy.log
        self.ipbanned = banned

        # constants from config:
        self.spigot_mode = self.proxy.config["spigot-mode"]
        self.hidden_ops = self.proxy.config["hidden-ops"]
        self.silent_bans = self.proxy.config["silent-ipban"]

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
        self.time_server_pinged = 0
        self.time_client_responded = 0
        self.keepalive_val = 0

        # client and server status
        self.abort = False
        # Proxy ServerConnection() (not the javaserver)
        self.server_connection = None
        self.state = HANDSHAKE

        # UUIDs - all should use MCUUID unless otherwise specified
        # --------------------------------------------------------
        # Server UUID - which is the local offline UUID.
        self.serveruuid = None
        # --------------------------------------------------------
        # The client UUID authenticated by connection to session server.
        self.uuid = None
        # --------------------------------------------------------
        # the formal, unique, mojang UUID as looked up on mojang servers.
        # This ID will be the same no matter what mode wrapper is in
        # or whether it is a lobby, etc.  This will be the formal uuid
        # to use for all wrapper internal functions for referencing a
        # unique player.

        # TODO - Unused except by plugin channel.
        # not to be confused with the fact that API player has a property
        # with the same name.
        self.mojanguuid = None

        # information gathered during login or socket connection processes
        # TODO in the future, we could use plugin channels to
        # communicate these to subworld wrappers From socket data
        self.address = None
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
        self.currentwindowid = -1
        self.noninventoryslotcount = 0
        self.lastitem = None

        # wrapper's own channel on each player client
        self.shared = {
            "username": "",
            "uuid": "",
            "ip": "",
            "received": False,
            "sent": False
        }

    def handle(self):
        t = threading.Thread(target=self.flush_loop, args=())
        t.daemon = True
        t.start()

        while not self.abort:
            try:
                pkid, original = self.packet.grabpacket()
            except EOFError:
                # This is not really an error.. It means the client
                # is not sending packet stream anymore
                if self.username != "PING REQUEST":
                    self.log.debug("%s Client Packet stream ended [EOF]", self.username)
                self.abort = True
                break
            except socket_error:
                # occurs anytime a socket is closed.
                if self.username != "PING REQUEST":
                    self.log.debug("%s Client Proxy Failed to grab packet", self.username)
                self.abort = True
                break
            except Exception as e:
                # anything that gets here is a bona-fide error
                # we need to become aware of
                self.log.error("%s Client Exception: Failed to grab packet "
                               "\n%s", self.username, e)
                self.abort = True
                break

            # self.parse(pkid)

            # send packet if server available and parsing passed.
            # already tested - Python will not attempt eval of
            # self.server_connection.state if self.server_connection is False

            if self.parse(pkid) and self.server_connection and \
                    self.server_connection.state in (PLAY, LOBBY):

                # sending to the server only happens in
                # PLAY/LOBBY (not IDLE, HANDSHAKE, or LOGIN)
                # wrapper handles LOGIN/HANDSHAKE with servers (via
                # self.parse(pkid), which DOES happen in all modes)
                self.server_connection.packet.send_raw(original)

        # sometimes (like during a ping request), a client may never enter PLAY
        # mode and will never be assigned a server connection...
        if self.server_connection:
            self.close_server_instance("Client Handle Ended")  # upon self.abort

    def flush_loop(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket_error:
                self.log.debug("%s client socket closed (socket_error).", self.username)
                break
            time.sleep(0.01)
        if self.username != "PING REQUEST":
            self.log.debug("%s clientconnection flush_loop thread ended", self.username)
        self.proxy.removestaleclients()  # from this instance from proxy.srv_data.clients

    def change_servers(self, ip=None, port=None):

        # close current connection and start new one
        was_lobby = False
        if self.state == LOBBY:
            was_lobby = True
        # get out of PLAY "NOW" to prevent second disconnect that kills client
        self.state = IDLE
        # keep server from sending disconnects
        self.server_connection.state = IDLE
        self.close_server_instance("Lobbification")
        # lobby_return = True
        time.sleep(1)

        # setup for connect
        self.clientSettingsSent = False

        # connect to server
        self.state = PLAY
        self.connect_to_server(ip, port)

        # if the client was in LOBBY state (connected to remote server)
        if was_lobby:
            self.log.info("%s's client Returned from remote server:"
                          " (UUID: %s | IP: %s | SecureConnection: %s)",
                          self.username, self.uuid.string,
                          self.ip, self.onlinemode)

            self._add_client()

        # TODO whatever respawn stuff works
        # send these right quick to client
        self._send_client_settings()

        self.packet.sendpkt(
            self.pktCB.CHANGE_GAME_STATE,
            [UBYTE, FLOAT],
            (1, 0))

        self.packet.sendpkt(
            self.pktCB.RESPAWN,
            [INT, UBYTE, UBYTE, STRING],
            [-1, 3, 0, 'default'])

        if self.version < PROTOCOL_1_8START:
            self.server_connection.packet.sendpkt(
                self.pktSB.CLIENT_STATUS,
                [BYTE, ],
                (0, ))
        else:
            self.packet.sendpkt(
                0x2c,
                [VARINT, INT, STRING, ],
                (self.server_eid, "DURNIT"))

            # self.packet.sendpkt(0x3e,
            #   [FLOAT, VARINT, FLOAT],
            #   (-1, 0, 0.0))

            self.server_connection.packet.sendpkt(
                self.pktSB.CLIENT_STATUS,
                [VARINT, ],
                (0, ))

            self.server_connection.packet.sendpkt(
                self.pktSB.PLAYER,
                [BOOL, ],
                (True,))

        self.state = LOBBY

    def logon_client_into_proxy(self):
        """  When the client first logs in to the wrapper proxy """

        # check for uuid ban
        if self.proxy.isuuidbanned(self.uuid.__str__()):
            banreason = self.proxy.getuuidbanreason(
                self.uuid.__str__())
            self.log.info("Banned player %s tried to"
                          " connect:\n %s" % (self.username, banreason))
            self.state = HANDSHAKE
            self.disconnect("Banned: %s" % banreason)
            return

        # Run the pre-login event
        if not self.proxy.eventhandler.callevent(
                "player.preLogin", {
                    "playername": self.username,
                    "player": self.username,  # not a real player object!
                    "online_uuid": self.uuid.string,
                    "offline_uuid": self.serveruuid.string,
                    "ip": self.ip,
                    "secure_connection": self.onlinemode
                }):
            """ eventdoc
                <group> Proxy <group>

                <description> Called before client logs on.
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
                "player": username (name only - player object does not yet exist)
                "online_uuid": online UUID,
                "offline_uuid": UUID on local server (offline),
                "ip": the user/client IP on the internet.
                "secure_connection": Proxy's online mode
                <payload>

            """

            self.state = HANDSHAKE
            self.disconnect("Login denied by a Plugin.")
            return

        self.log.info("%s's Proxy Client LOGON occurred: (UUID: %s"
                      " | IP: %s | SecureConnection: %s)",
                      self.username, self.uuid.string,
                      self.ip, self.onlinemode)
        self._inittheplayer()  # set up inventory and stuff
        self._add_client()

        # start keep alives

        # send login success to client
        self.packet.sendpkt(
            self.pktCB.LOGIN_SUCCESS,
            [STRING, STRING],
            (self.uuid.string, self.username))

        self.time_client_responded = time.time()

        t_keepalives = threading.Thread(
            target=self._keep_alive_tracker,
            args=())
        t_keepalives.daemon = True
        t_keepalives.start()

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
            self.disconnect("Proxy client could not connect to the server"
                            " (%s)" % e)
            return

        # start server handle() to read the packets
        t = threading.Thread(target=self.server_connection.handle, args=())
        t.daemon = True
        t.start()

        # switch server_connection to LOGIN to log in to (offline) server.
        self.server_connection.state = LOGIN

        # now we send it a handshake to request the server go to login mode
        server_addr = "localhost"
        if self.spigot_mode:
            server_addr = "localhost\x00%s\x00%s" % \
                          (self.client_address[0], self.uuid.hex)
        if self.proxy.forge:
            server_addr = "localhost\x00FML\x00"

        self.server_connection.packet.sendpkt(
            self.server_connection.pktSB.HANDSHAKE,
            [VARINT, STRING, USHORT, VARINT],
            (self.clientversion, server_addr, self.serverport,
             LOGIN))

        # send the login request (server is offline, so it will
        # accept immediately by sending login_success)
        self.server_connection.packet.sendpkt(
            self.server_connection.pktSB.LOGIN_START,
            [STRING],
            [self.username])

        # LOBBY code and such to go elsewhere

    def close_server_instance(self, term_message):
        """ Close the server connection gracefully if possible. """
        if self.server_connection:
            self.server_connection.close_server(term_message)

    def disconnect(self, message):
        """
        disconnects the client (runs close_server(), which will
         also shut off the serverconnection.py)

        Not used to disconnect from a server!  This disconnects the client.
        """
        jsonmessage = message  # server packets are read as json

        if type(message) is dict:
            if "text" in message:
                jsonmessage = {"text": message}
                if "color" in message:
                    jsonmessage["color"] = message["color"]
                if "bold" in message:
                    jsonmessage["bold"] = message["bold"]
                message = jsonmessage["text"]
                jsonmessage = json.dumps(jsonmessage)
        else:
            jsonmessage = message  # server packets are read as json

        if self.state in (PLAY, LOBBY):
            self.packet.sendpkt(
                self.pktCB.DISCONNECT,
                [JSON],
                [jsonmessage])

            self.log.debug("Sent PLAY state DISCONNECT packet to %s", self.username)
        else:
            self.packet.sendpkt(
                self.pktCB.LOGIN_DISCONNECT,
                [JSON],
                [message])

            if self.username != "PING REQUEST":
                self.log.debug(
                    "State was 'other': sent LOGIN_DISCONNECT to %s", self.username)

        time.sleep(1)
        self.state = HANDSHAKE
        self.close_server_instance("run Disconnect() client.  Aborting client thread")
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
            self.inventory[i] = None
        self.time_server_pinged = time.time()
        self.time_client_responded = time.time()

    def _getclientpacketset(self):
        # Determine packet types  - in this context, pktSB/pktCB is
        # what is being received/sent from/to the client.
        # That is why we refresh to the clientversion.
        self.pktSB = mcpackets_sb.Packets(self.clientversion)
        self.pktCB = mcpackets_cb.Packets(self.clientversion)
        self._define_parsers()

    # api related
    # -----------------------------
    def getplayerobject(self):
        if self.username in self.servervitals.players:
            return self.servervitals.players[self.username]
        self.log.error("In playerlist:\n%s\nI could not locate player: %s\n"
                       "This resulted in setting the player object to FALSE!",
                       self.servervitals.players, self.username)
        return False

    def editsign(self, position, line1, line2, line3, line4, pre18=False):
        if pre18:
            x = position[0]
            y = position[1]
            z = position[2]
            self.server_connection.packet.sendpkt(
                self.pktSB.PLAYER_UPDATE_SIGN,
                [INT, SHORT, INT, STRING, STRING, STRING, STRING],
                (x, y, z, line1, line2, line3, line4))
        else:
            self.server_connection.packet.sendpkt(
                self.pktSB.PLAYER_UPDATE_SIGN,
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
                            (message, position))

    # internal client login methods
    # -----------------------------
    def _keep_alive_tracker(self):
        """ Send keep alives to client and send client settings to server. """
        while not self.abort:
            time.sleep(.1)
            if self.state in (PLAY, LOBBY):
                # client expects < 20sec
                # sending more frequently (5 seconds) seems to help with
                # some slower connections.
                if time.time() - self.time_server_pinged > 5:
                    # create the keep alive value
                    # MC 1.12 .2 uses a time() value.
                    # Old way takes almost full second to generate:
                    if self.version < PROTOCOL_1_12_2:
                        self.keepalive_val = random.randrange(0, 99999)
                    else:
                        self.keepalive_val = int((time.time() * 100) % 10000000)

                    # challenge the client with it
                    self.packet.sendpkt(
                        self.pktCB.KEEP_ALIVE[PKT],
                        self.pktCB.KEEP_ALIVE[PARSER],
                        [self.keepalive_val])

                    self.time_server_pinged = time.time()

                # check for active client keep alive status:
                # server can allow up to 30 seconds for response
                if time.time() - self.time_client_responded > 25:  # \
                        # and not self.abort:
                    self.disconnect("Client closed due to lack of"
                                    " keepalive response")
                    self.log.debug("Closed %s's client thread due to "
                                   "lack of keepalive response", self.username)
                    return
        self.log.debug("%s Client keepalive tracker aborted", self.username)

    def _login_authenticate_client(self, server_id):
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
                #             "signature": "<base64 string; signed data using Yggdrasil's private key>"
                #         }
                #     ]
                # }
                requestdata = r.json()
                self.uuid = MCUUID(requestdata["id"])  # TODO

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
                            self.uuid.string] = self.skin_blob
                self.properties = requestdata["properties"]
            else:
                self.disconnect("Proxy Client Session Error"
                                " (HTTP Status Code %d)" % r.status_code)
                return False
            currentname = self.proxy.uuids.getusernamebyuuid(
                self.uuid.string)
            if currentname:
                if currentname != self.username:
                    self.log.info("%s's client performed LOGON in with"
                                  " new name, falling back to %s",
                                  self.username, currentname)
                    self.username = currentname
            self.serveruuid = self.proxy.uuids.getuuidfromname(self.username)

        # Wrapper offline and not authenticating
        # maybe it is the destination of a hub? or you use another
        # way to authenticate (passwords?)
        else:
            # I'll take your word for it, bub...  You are:
            self.serveruuid = self.proxy.uuids.getuuidfromname(self.username)
            self.uuid = self.serveruuid
            self.log.debug("Client logon with wrapper offline-"
                           " 'self.uuid = OfflinePlayer:<name>'")

        # no idea what is special about version 26
        if self.clientversion > 26:
            self.packet.setcompression(256)

    def _add_client(self):
        # Put XXXplayer_object_andXXX client into server data. (player login
        #  will be called later by mcserver.py)
        if self not in self.proxy.srv_data.clients:
            self.proxy.srv_data.clients.append(self)

    def _send_client_settings(self):
        if self.clientSettings and not self.clientSettingsSent:
            self.server_connection.packet.sendpkt(
                self.pktSB.CLIENT_SETTINGS,
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
                self.pktCB.PLUGIN_MESSAGE,
                [STRING, SHORT, BYTE],
                [channel, 1, 254])

        else:
            self.packet.sendpkt(
                self.pktCB.PLUGIN_MESSAGE,
                [STRING, BYTE],
                [channel, 254])

    def _transmit_downstream(self):
        """ transmit wrapper channel status info to the server's
         direction to help sync hub/lobby wrappers """

        channel = "WRAPPER.PY|PING"
        state = self.state
        if self.server_connection:
            if self.version < PROTOCOL_1_8START:
                self.server_connection.packet.sendpkt(
                    self.pktSB.PLUGIN_MESSAGE,
                    [STRING, SHORT, BYTE],
                    [channel, 1,  state])
            else:
                self.server_connection.packet.sendpkt(
                    self.pktSB.PLUGIN_MESSAGE,
                    [STRING, BOOL],
                    [channel, state])

    def _whitelist_processing(self):
        pass
        # This needs re-worked.  should likely be in main wrapper of server
        #  instance, not at each client connection

        # Rename UUIDs accordingly
        # if self.config["Proxy"]["convert-player-files"]:
        #    if self.config["Proxy"]["online-mode"]:
        #        # Check player files, and rename them accordingly
        #        #  to offline-mode UUID
        #        worldname = self.servervitals.worldname
        #        if not os.path.exists("%s/playerdata/%s.dat" % (
        #                worldname, self.serveruuid.string)):
        #            if os.path.exists("%s/playerdata/%s.dat" % (
        #                    worldname, self.uuid.string)):
        #                self.log.info("Migrating %s's playerdata"
        #                              " file to proxy mode", self.username)
        #                shutil.move("%s/playerdata/%s.dat" %
        #                            (worldname, self.uuid.string),
        #                            "%s/playerdata/%s.dat" % (
        #                                worldname, self.serveruuid.string))
        #                with open("%s/.wrapper-proxy-playerdata-migrate" %
        #                          worldname, "a") as f:
        #                    f.write("%s %s\n" % (self.uuid.string,
        #                                         self.serveruuid.string))
        #        # Change whitelist entries to offline mode versions
        #        if os.path.exists("whitelist.json"):
        #            with open("whitelist.json", "r") as f:
        #                jsonwhitelistdata = json.loads(f.read())
        #            if jsonwhitelistdata:
        #                for player in jsonwhitelistdata:
        #                    if not player["uuid"] == self.serveruuid.string\
        #                            and player["uuid"] == self.uuid.string:
        #                        self.log.info("Migrating %s's whitelist entry"
        #                                      " to proxy mode", self.username)
        #                        jsonwhitelistdata.append(
        #                            {"uuid": self.serveruuid.string,
        #                             "name": self.username})
        #                        with open("whitelist.json", "w") as f:
        #                            f.write(json.dumps(jsonwhitelistdata))
        #                        ##self.XXXservervitalsXXX.console(
        #                            "##whitelist reload")
        #                        => self.proxy.eventhandler.callevent("proxy.console", {"command": "whitelist reload"})
        """ eventdoc
                                <description> internalfunction <description>

                            """
        #                        with open("%s/.wrapper-proxy-whitelist-"
        #                                  "migrate" % worldname, "a") as f:
        #                            f.write("%s %s\n" % (
        #                                self.uuid.string,
        #                                self.serveruuid.string))

    # PARSERS SECTION
    # -----------------------------

    def _parse_keep_alive(self):
        data = self.packet.readpkt(self.pktSB.KEEP_ALIVE[PARSER])

        if data[0] == self.keepalive_val:
            self.time_client_responded = time.time()
        return False

    # plugin channel handler
    # -----------------------
    def _parse_plugin_message(self):
        channel = self.packet.readpkt([STRING, ])[0]

        if channel not in self.proxy.registered_channels:
            # we are not actually registering our channels with the MC server.
            return True

        if channel == "WRAPPER.PY|PING":
            self.proxy.pinged = True
            return False

        if channel == "WRAPPER.PY|":
            if self.clientversion < PROTOCOL_1_8START:
                datarest = self.packet.readpkt([SHORT, REST])[1]
            else:
                datarest = self.packet.readpkt([REST, ])[0]

            print("\nDATA REST = %s\n" % datarest)
            response = json.loads(datarest.decode('utf-8'),
                                  encoding='utf-8')
            self._plugin_response(response)
            return True

        return True

    def _plugin_response(self, response):
        if "ip" in response:
            self.shared = {
                "username": response["username"],
                "uuid": response["uuid"],
                "ip": response["ip"],
                "received": True,
            }
            self.ip = response["ip"]
            self.mojanguuid = response["uuid"]

    # Login parsers
    # -----------------------
    def _parse_handshaking(self):
        # self.log.debug("HANDSHAKE")
        # "version|address|port|state"
        data = self.packet.readpkt([VARINT, STRING, USHORT, VARINT])

        self.clientversion = data[0]
        self._getclientpacketset()

        self.serveraddressplayerused = data[1]
        self.serverportplayerused = data[2]
        requestedstate = data[3]

        if requestedstate == STATUS:
            self.state = STATUS
            # wrapper will handle responses, so do not pass this to the server.
            return False

        if requestedstate == LOGIN:
            # TODO - coming soon: allow client connections
            # despite lack of server connection

            if self.servervitals.protocolVersion == -1:
                #  ... returns -1 to signal no server
                self.disconnect("The server is not started.")
                return False

            if not self.servervitals.state == 2:
                self.disconnect("Server has not finished booting. Please try"
                                " connecting again in a few seconds")
                return False

            if PROTOCOL_1_9START < self.clientversion < PROTOCOL_1_9REL1:
                self.disconnect("You're running an unsupported snapshot"
                                " (protocol: %s)!" % self.clientversion)
                return False

            if self.servervitals.protocolVersion == self.clientversion:
                # login start...
                self.state = LOGIN
                # packet passes to server, which will also switch to Login
                return True
            else:
                self.disconnect("You're not running the same Minecraft"
                                " version as the server!")
                return False

        self.disconnect("Invalid HANDSHAKE: 'requested state:"
                        " %d'" % requestedstate)
        return False

    def _parse_status_ping(self):
        # self.log.debug("SB -> STATUS PING")
        data = self.packet.readpkt([LONG])
        self.packet.sendpkt(self.pktCB.PING_PONG, [LONG], [data[0]])
        # self.log.debug("CB (W)-> STATUS PING")
        self.state = HANDSHAKE
        return False

    def _parse_status_request(self):
        # self.log.debug("SB -> STATUS REQUEST")
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
            motdtext = json.loads(processcolorcodes(motdtext.replace(
                "\\", "")))
        self.MOTD = {
            "description": motdtext,
            "players": {
                "max": int(self.servervitals.maxPlayers),
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
            self.pktCB.PING_JSON_RESPONSE,
            [STRING],
            [json.dumps(self.MOTD)])

        # self.log.debug("CB (W)-> JSON RESPONSE")
        # after this, proxy waits for the expected PING to
        #  go back to Handshake mode
        return False

    def _parse_login_start(self):
        # self.log.debug("SB -> LOGIN START")
        data = self.packet.readpkt([STRING, NULL])

        # "username"
        self.username = data[0]

        # just to be clear, this refers to wrapper's mode, not the server.
        if self.onlinemode:
            # Wrapper sends client a login encryption request

            # 1.7.x versions
            if self.servervitals.protocolVersion < 6:
                # send to client 1.7
                self.packet.sendpkt(
                    self.pktCB.LOGIN_ENCR_REQUEST,
                    [STRING, BYTEARRAY_SHORT, BYTEARRAY_SHORT],
                    (self.serverID, self.publicKey, self.verifyToken))
            else:
                # send to client 1.8 +
                self.packet.sendpkt(
                    self.pktCB.LOGIN_ENCR_REQUEST,
                    [STRING, BYTEARRAY, BYTEARRAY],
                    (self.serverID, self.publicKey, self.verifyToken))

            # self.log.debug("CB (W)-> LOGIN ENCR REQUEST")

            # Server UUID is always offline (at the present time)
            # MCUUID object
            self.serveruuid = self.proxy.uuids.getuuidfromname(self.username)

        else:
            # Wrapper offline and not authenticating
            # maybe it is the destination of a hub? or you use another
            #  way to authenticate (password plugin?)

            # Server UUID is always offline (at the present time)
            self.uuid = self.proxy.uuids.getuuidfromname(self.username)

            # Since wrapper is offline, we are using offline for self.uuid also
            self.serveruuid = self.uuid  # MCUUID object

            # log the client on
            self.state = PLAY
            self.logon_client_into_proxy()
            # connect to server
            self.connect_to_server()
        return False

    def _parse_login_encr_response(self):
        # the client is RESPONDING to our request for
        #  encryption (if we sent one above)

        # read response Tokens - "shared_secret|verify_token"
        # self.log.debug("SB -> LOGIN ENCR RESPONSE")
        if self.servervitals.protocolVersion < 6:
            data = self.packet.readpkt([BYTEARRAY_SHORT, BYTEARRAY_SHORT])
        else:
            data = self.packet.readpkt([BYTEARRAY, BYTEARRAY])

        sharedsecret = encryption.decrypt_shared_secret(
            data[0], self.privateKey)
        verifytoken = encryption.decrypt_shared_secret(
            data[1], self.privateKey)
        h = hashlib.sha1()
        # self.serverID already encoded
        h.update(self.serverID)
        h.update(sharedsecret)
        h.update(self.publicKey)
        serverid = self.packet.hexdigest(h)

        # feed info to packet.py for parsing
        self.packet.sendCipher = encryption.AES128CFB8(sharedsecret)
        self.packet.recvCipher = encryption.AES128CFB8(sharedsecret)

        # verify correct response
        if not verifytoken == self.verifyToken:
            self.disconnect("Verify tokens are not the same")
            return False

        # determine if IP is silent banned:
        if self.ipbanned:
            self.log.info("Player %s tried to connect from banned ip:"
                          " %s", self.username, self.ip)
            self.state = HANDSHAKE
            if self.silent_bans:
                self.disconnect("unknown host")
            else:
                # self disconnect does not "return" anything.
                self.disconnect("Your address is IP-banned from this server!.")
            return False

        # begin Client logon process
        # Wrapper in online mode, taking care of authentication
        if self._login_authenticate_client(serverid) is False:
            return False  # client failed to authenticate

        # TODO Whitelist processing Here (or should it be at javaserver start?)

        # log the client on
        self.state = PLAY
        self.logon_client_into_proxy()

        # connect to server
        self.connect_to_server()
        return False

    # Lobby parsers
    # -----------------------
    def _parse_lobby_chat_message(self):
        data = self.packet.readpkt([STRING])
        if data is None:
            return True

        # Get the packet chat message contents
        chatmsg = data[0]

        if chatmsg in ("/lobby", "/hub"):
            # stop any raining
            # close current connection and start new one
            # noinspection PyBroadException

            self.change_servers()
            return False

        # we are just sniffing this packet for lobby return
        # commands, so send it on to the destination.
        return True

    def parse(self, pkid):
        if pkid in self.parsers[self.state]:
            return self.parsers[self.state][pkid]()
        else:
            return True

    def _define_parsers(self):
        # the packets we parse and the methods that parse them.
        self.parsers = {
            HANDSHAKE: {
                self.pktSB.HANDSHAKE:
                    self._parse_handshaking,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            STATUS: {
                self.pktSB.STATUS_PING:
                    self._parse_status_ping,
                self.pktSB.REQUEST:
                    self._parse_status_request,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            LOGIN: {
                self.pktSB.LOGIN_START:
                    self._parse_login_start,
                self.pktSB.LOGIN_ENCR_RESPONSE:
                    self._parse_login_encr_response,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            PLAY: {
                self.pktSB.CHAT_MESSAGE[PKT]:
                    self.parse_sb.parse_play_chat_message,
                self.pktSB.CLICK_WINDOW:
                    self.parse_sb.parse_play_click_window,
                self.pktSB.CLIENT_SETTINGS:
                    self.parse_sb.parse_play_client_settings,
                self.pktSB.HELD_ITEM_CHANGE:
                    self.parse_sb.parse_play_held_item_change,
                self.pktSB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktSB.PLAYER_BLOCK_PLACEMENT:
                    self.parse_sb.parse_play_player_block_placement,
                self.pktSB.PLAYER_DIGGING:
                    self.parse_sb.parse_play_player_digging,
                self.pktSB.PLAYER_LOOK:
                    self.parse_sb.parse_play_player_look,
                self.pktSB.PLAYER_POSITION:
                    self.parse_sb.parse_play_player_position,
                self.pktSB.PLAYER_POSLOOK[PKT]:
                    self.parse_sb.parse_play_player_poslook,
                self.pktSB.PLAYER_UPDATE_SIGN:
                    self.parse_sb.parse_play_player_update_sign,
                self.pktSB.SPECTATE:
                    self.parse_sb.parse_play_spectate,
                self.pktSB.USE_ITEM:
                    self.parse_sb.parse_play_use_item,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            LOBBY: {
                self.pktSB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktSB.CHAT_MESSAGE[PKT]:
                    self._parse_lobby_chat_message,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            IDLE: {
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
            }
        }
