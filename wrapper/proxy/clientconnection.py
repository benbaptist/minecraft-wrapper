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
import utils.encryption as encryption

from proxy.serverconnection import ServerConnection
from proxy.packet import Packet
from proxy.parse_sb import ParseSB
from proxy import mcpackets_sb
from proxy import mcpackets_cb
from proxy.constants import *

from api.player import Player
from core.mcuuid import MCUUID

from api.helpers import processcolorcodes


# noinspection PyMethodMayBeStatic
class Client(object):
    def __init__(self, proxy, clientsock, client_addr, banned=False):
        """
        Handle the client connection.

        This class Client is a "fake" server, accepting connections
        from clients.  It receives "SERVER BOUND" packets from client,
        parses them, and forards them on to the server.

        Client receives the parent proxy as it's argument.
        Accordingly, it receives the proxy's wrapper instance.
        """

        # basic __init__ items from passed arguments
        self.client_socket = clientsock
        self.client_address = client_addr
        self.proxy = proxy
        self.wrapper = self.proxy.wrapper
        self.publicKey = self.proxy.publicKey
        self.privateKey = self.proxy.privateKey
        self.log = self.proxy.wrapper.log
        self.config = self.proxy.wrapper.config
        self.ipbanned = banned

        # constants from config:
        self.spigot_mode = self.config["Proxy"]["spigot-mode"]
        self.hidden_ops = self.config["Proxy"]["hidden-ops"]

        # client setup and operating paramenters
        self.username = "PING REQUEST"
        self.packet = Packet(self.client_socket, self)
        self.parse_sb = ParseSB(self, self.packet)
        self.verifyToken = encryption.generate_challenge_token()
        self.serverID = encryption.generate_server_id().encode('utf-8')
        self.MOTD = {}
        self.serverversion = self.wrapper.javaserver.protocolVersion
        # client will reset this later, if need be..
        self.clientversion = self.serverversion
        # default server port (to this wrapper's server)
        self.server_port = self.wrapper.javaserver.server_port
        self.wrapper_onlinemode = self.config["Proxy"]["online-mode"]

        # packet stuff
        self.pktSB = mcpackets_sb.Packets(self.clientversion)
        self.pktCB = mcpackets_cb.Packets(self.clientversion)

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
        self.state = self.proxy.HANDSHAKE

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

        # TODO - Unused except by plugin channel.  This should be
        #  integrated better with wrapper's uuid lookups
        #  and the player API.
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
        self.skinBlob = {}
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
                self.log.debug("Client Packet stream ended [EOF]"
                               " (%s)", self.username)
                break
            except socket_error:
                # occurs anytime a socket is closed.
                self.log.debug("client proxy Failed to grab packet"
                               " [socket_error] (%s)", self.username)
                break
            except Exception as e:
                # anything that gets here is a bona-fide error
                # we need to become aware of
                self.log.error("Exception: Failed to grab packet "
                               "[CLIENT (%s)] (%s):", self.username, e)
                break

            # self.parse(pkid)

            # send packet if server available and parsing passed.
            # already tested - Python will not attempt eval of
            # self.server.state if self.server is False
            if self.parse(pkid) and \
                    self.server_connection and \
                    self.server_connection.state in (
                            self.proxy.PLAY, self.proxy.LOBBY):

                # sending to the server only happens in
                # PLAY/LOBBY (not IDLE, HANDSHAKE, or LOGIN)
                # wrapper handles LOGIN/HANDSHAKE with servers (via
                # self.parse(pkid), which DOES happen in all modes)
                self.server_connection.packet.send_raw(original)
                if self.proxy.trace:
                    self._do_trace(pkid, self.state)

        self.close_server()  # upon self.abort

    def _do_trace(self, pkid, state):
        name = str(self.parsers[state][pkid]).split(" ")[0]
        if pkid not in self.proxy.ignoredSB:
            self.log.debug("SB=> %s (%s)", hex(pkid), name)

    def flush_loop(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket_error:
                self.log.debug("client socket closed (socket_error).")
                break
            time.sleep(0.01)
        self.log.debug("client connection flush_loop thread ended")

    def change_servers(self, ip=None, port=None):

        # close current connection and start new one
        was_lobby = False
        if self.state == self.proxy.LOBBY:
            was_lobby = True
        # get out of PLAY "NOW" to prevent second disconnect that kills client
        self.state = self.proxy.IDLE
        # keep server from sending disconnects
        self.server_connection.state = self.proxy.IDLE
        self.server_connection.close_server(
            reason="Lobbification", lobby_return=True)
        time.sleep(1)

        # setup for connect
        self.clientSettingsSent = False

        # connect to server
        self.state = self.proxy.PLAY
        self.connect_to_server(ip, port)

        # if the client was in LOBBY state (connected to remote server)
        if was_lobby:
            self.log.info("%s's client Returned from remote server:"
                          " (UUID: %s | IP: %s | SecureConnection: %s)",
                          self.username, self.uuid.string,
                          self.ip, self.wrapper_onlinemode)

            self._add_player_and_client_objects_to_wrapper()

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

        self.state = self.proxy.LOBBY

    def client_logon(self, start_keep_alives=True, ip=None, port=None):
        """  When the client first logs in to wrapper """
        self._inittheplayer()  # set up inventory and stuff

        if self.wrapper.proxy.isuuidbanned(self.uuid.__str__()):
            banreason = self.wrapper.proxy.getuuidbanreason(
                self.uuid.__str__())
            self.log.info("Banned player %s tried to"
                          " connect:\n %s" % (self.username, banreason))
            self.state = self.proxy.HANDSHAKE
            self.disconnect("Banned: %s" % banreason)
            return False

        # Run the pre-login event
        if not self.wrapper.events.callevent(
                "player.preLogin", {
                    "player": self.username,
                    "online_uuid": self.uuid.string,
                    "offline_uuid": self.serveruuid.string,
                    "ip": self.ip,
                    "secure_connection": self.wrapper_onlinemode
                }):

            self.state = self.proxy.HANDSHAKE
            self.disconnect("Login denied by a Plugin.")
            return False

        self.log.info("%s's client LOGON occurred: (UUID: %s"
                      " | IP: %s | SecureConnection: %s)",
                      self.username, self.uuid.string,
                      self.ip, self.wrapper_onlinemode)

        self._add_player_and_client_objects_to_wrapper()

        # start keep alives
        if start_keep_alives:
            # send login success to client (the real client is already
            # logged in if keep alives are running)
            self.packet.sendpkt(
                self.pktCB.LOGIN_SUCCESS,
                [STRING, STRING],
                (self.uuid.string, self.username))

            self.time_client_responded = time.time()

            t_keepalives = threading.Thread(
                target=self._keep_alive_tracker,
                kwargs={'playername': self.username})
            t_keepalives.daemon = True
            t_keepalives.start()

        # connect to server
        self.connect_to_server(ip, port)
        return False

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
        self.server_connection.state = self.proxy.LOGIN

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
            (self.clientversion, server_addr, self.server_port,
             self.proxy.LOGIN))

        # send the login request (server is offline, so it will
        # accept immediately by sending login_success)
        self.server_connection.packet.sendpkt(
            self.server_connection.pktSB.LOGIN_START,
            [STRING],
            [self.username])

        # LOBBY code and such to go elsewhere

    def close_server(self):
        # close the server connection gracefully first, if possible.

        # noinspection PyBroadException
        try:
            self.server_connection.close_server("Client Disconnecting...")
        except:
            self.log.debug("Client socket for %s already"
                           " closed!", self.username)
        self.abort = True  # TODO investigate this

    def disconnect(self, message):
        """
        disconnects the client (runs close_server(), which will
         also shut off the serverconnection.py)

        Not used to disconnect from a server!
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

        if self.state in (self.proxy.PLAY, self.proxy.LOBBY):
            self.packet.sendpkt(
                self.pktCB.DISCONNECT,
                [JSON],
                [jsonmessage])

            self.log.debug("upon disconnect, state was PLAY"
                           " (sent PLAY state DISCONNECT)")
        else:
            self.packet.sendpkt(
                self.pktCB.LOGIN_DISCONNECT,
                [JSON],
                [message])

            self.log.debug("upon disconnect, state was 'other'"
                           " (sent LOGIN_DISCONNECT)")
        time.sleep(1)
        self.state = self.proxy.HANDSHAKE
        self.close_server()

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
        for i in self.wrapper.inv_slots:
            self.inventory[i] = None
        self.time_server_pinged = time.time()
        self.time_client_responded = time.time()
        self._refresh_server_version()

    def _refresh_server_version(self):
        # Get serverversion for mcpackets use
        try:
            self.serverversion = self.wrapper.javaserver.protocolVersion
        except AttributeError:
            self.serverversion = -1

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
        if self.username in self.wrapper.javaserver.players:
            return self.wrapper.javaserver.players[self.username]
        self.log.error("In playerlist:\n%s\nI could not locate player: %s\n"
                       "This resulted in setting the player object to FALSE!",
                       self.wrapper.javaserver.players, self.username)
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

    def chat_to_server(self, string):
        """ used to resend modified chat packets.  Also to mimic
        player in API player """
        self.server_connection.packet.sendpkt(
            self.pktSB.CHAT_MESSAGE,
            [STRING],
            [string])

    def chat_to_cleint(self, message):
        if self.version < PROTOCOL_1_8START:
            parsing = [STRING, NULL]
        else:
            parsing = [JSON, BYTE]
        self.packet.sendpkt(self.pktCB.CHAT_MESSAGE, parsing, (message, 0))

    # internal client login methods
    # -----------------------------
    def _keep_alive_tracker(self, playername):
        # send keep alives to client and send client settings to server.
        # TODO future - use a plugin channel to see if the client is
        # actually another wrapper

        while not self.abort:
            time.sleep(1)
            if self.state in (self.proxy.PLAY, self.proxy.LOBBY):
                # client expects < 20sec
                if time.time() - self.time_server_pinged > 10:

                    # create the keep alive value
                    self.keepalive_val = random.randrange(0, 99999)

                    # challenge the client with it
                    self.packet.sendpkt(
                        self.pktCB.KEEP_ALIVE[PKT],
                        self.pktCB.KEEP_ALIVE[PARSER],
                        [self.keepalive_val])

                    self.time_server_pinged = time.time()

                # check for active client keep alive status:
                # server can allow up to 30 seconds for response
                if time.time() - self.time_client_responded > 25 \
                        and not self.abort:
                    self.disconnect("Client closed due to lack of"
                                    " keepalive response")
                    self.log.debug("Closed %s's client thread due to "
                                   "lack of keepalive response", playername)
                    return
        self.log.debug("Client keepalive tracker aborted"
                       " (%s's client thread)", playername)

    def _login_authenticate_client(self, server_id):
        if self.wrapper_onlinemode:
            r = requests.get("https://sessionserver.mojang.com"
                             "/session/minecraft/hasJoined?username=%s"
                             "&serverId=%s" % (self.username, server_id))
            if r.status_code == 200:
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
                        self.skinBlob = prop["value"]
                        self.wrapper.proxy.skins[
                            self.uuid.string] = self.skinBlob
                self.properties = requestdata["properties"]
            else:
                self.disconnect("Proxy Client Session Error"
                                " (HTTP Status Code %d)" % r.status_code)
                return False
            currentname = self.wrapper.uuids.getusernamebyuuid(
                self.uuid.string)
            if currentname:
                if currentname != self.username:
                    self.log.info("%s's client performed LOGON in with"
                                  " new name, falling back to %s",
                                  self.username, currentname)
                    self.username = currentname
            self.serveruuid = self.wrapper.uuids.getuuidfromname(self.username)

        # Wrapper offline and not authenticating
        # maybe it is the destination of a hub? or you use another
        # way to authenticate (passwords?)
        else:
            # I'll take your word for it, bub...  You are:
            self.serveruuid = self.wrapper.uuids.getuuidfromname(self.username)
            self.uuid = self.serveruuid
            self.log.debug("Client logon with wrapper offline-"
                           " 'self.uuid = OfflinePlayer:<name>'")

        # no idea what is special about version 26
        if self.clientversion > 26:
            self.packet.setcompression(256)

    def _add_player_and_client_objects_to_wrapper(self):
        # Put player object and client into server. (player login
        #  will be called later by mcserver.py)
        if self not in self.wrapper.proxy.clients:
            self.wrapper.proxy.clients.append(self)

        if self.username not in self.wrapper.javaserver.players:
            self.wrapper.javaserver.players[self.username] = Player(
                self.username, self.wrapper)

        self._inittheplayer()  # set up inventory and stuff

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
        #        worldname = self.wrapper.javaserver.worldname
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
        #                        self.wrapper.javaserver.console(
        #                            "whitelist reload")
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
            response = json.loads(datarest.decode(self.wrapper.encoding),
                                  encoding=self.wrapper.encoding)
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
        self.log.debug("HANDSHAKE")
        # "version|address|port|state"
        data = self.packet.readpkt([VARINT, STRING, USHORT, VARINT])

        self.clientversion = data[0]
        self._getclientpacketset()

        self.serveraddressplayerused = data[1]
        self.serverportplayerused = data[2]
        requestedstate = data[3]

        if requestedstate == self.proxy.STATUS:
            self.state = self.proxy.STATUS
            # wrapper will handle responses, so do not pass this to the server.
            return False

        if requestedstate == self.proxy.LOGIN:
            # TODO - coming soon: allow client connections
            # despite lack of server connection

            if self.serverversion == -1:
                #  ... returns -1 to signal no server
                self.disconnect("The server is not started.")
                return False

            if not self.wrapper.javaserver.state == 2:
                self.disconnect("Server has not finished booting. Please try"
                                " connecting again in a few seconds")
                return False

            if PROTOCOL_1_9START < self.clientversion < PROTOCOL_1_9REL1:
                self.disconnect("You're running an unsupported snapshot"
                                " (protocol: %s)!" % self.clientversion)
                return False

            if self.serverversion == self.clientversion:
                # login start...
                self.state = self.proxy.LOGIN
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
        self.log.debug("SB -> STATUS PING")
        data = self.packet.readpkt([LONG])
        self.packet.sendpkt(self.pktCB.PING_PONG, [LONG], [data[0]])
        self.log.debug("CB (W)-> STATUS PING")
        self.state = self.proxy.HANDSHAKE
        return False

    def _parse_status_request(self):
        self.log.debug("SB -> STATUS REQUEST")
        sample = []
        for player in self.wrapper.javaserver.players:
            playerobj = self.wrapper.javaserver.players[player]
            if playerobj.username not in self.hidden_ops:
                sample.append({"name": playerobj.username,
                               "id": str(playerobj.mojangUuid)})
            if len(sample) > 5:
                break
        reported_version = self.serverversion
        reported_name = self.wrapper.javaserver.version
        motdtext = self.wrapper.javaserver.motd
        if self.clientversion >= PROTOCOL_1_8START:
            motdtext = json.loads(processcolorcodes(motdtext.replace(
                "\\", "")))
        self.MOTD = {
            "description": motdtext,
            "players": {
                "max": int(self.wrapper.javaserver.maxPlayers),
                "online": len(self.wrapper.javaserver.players),
                "sample": sample
            },
            "version": {
                "name": reported_name,
                "protocol": reported_version
            }
        }

        # add Favicon, if it exists
        if self.wrapper.javaserver.serverIcon:
            self.MOTD["favicon"] = self.wrapper.javaserver.serverIcon

        # add Forge information, if applicable.
        if self.proxy.forge:
            self.MOTD["modinfo"] = self.proxy.mod_info["modinfo"]

        self.packet.sendpkt(
            self.pktCB.PING_JSON_RESPONSE,
            [STRING],
            [json.dumps(self.MOTD)])

        self.log.debug("CB (W)-> JSON RESPONSE")
        # after this, proxy waits for the expected PING to
        #  go back to Handshake mode
        return False

    def _parse_login_start(self):
        self.log.debug("SB -> LOGIN START")
        data = self.packet.readpkt([STRING, NULL])

        # "username"
        self.username = data[0]

        # just to be clear, this refers to wrapper's mode, not the server.
        if self.wrapper_onlinemode:
            # Wrapper sends client a login encryption request

            # 1.7.x versions
            if self.serverversion < 6:
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

            self.log.debug("CB (W)-> LOGIN ENCR REQUEST")

            # Server UUID is always offline (at the present time)
            # MCUUID object
            self.serveruuid = self.wrapper.uuids.getuuidfromname(self.username)

        else:
            # Wrapper offline and not authenticating
            # maybe it is the destination of a hub? or you use another
            #  way to authenticate (password plugin?)

            # Server UUID is always offline (at the present time)
            self.uuid = self.wrapper.uuids.getuuidfromname(self.username)

            # Since wrapper is offline, we are using offline for self.uuid also
            self.serveruuid = self.uuid  # MCUUID object

            # log the client on
            self.state = self.proxy.PLAY
            self.client_logon()

    def _parse_login_encr_response(self):
        # the client is RESPONDING to our request for
        #  encryption (if we sent one above)

        # read response Tokens - "shared_secret|verify_token"
        self.log.debug("SB -> LOGIN ENCR RESPONSE")
        if self.serverversion < 6:
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

        # determine if IP is banned:

        # client never gets to this point if 'silent-ipban' is enabled
        if self.ipbanned:
            self.log.info("Player %s tried to connect from banned ip:"
                          " %s", self.username, self.ip)
            self.state = self.proxy.HANDSHAKE
            self.disconnect("Your address is IP-banned from this server!.")
            return False

        # begin Client login process
        # Wrapper in online mode, taking care of authentication
        if self._login_authenticate_client(serverid) is False:
            return False  # client failed to authenticate

        # TODO Whitelist processing Here (or should it be at javaserver start?)

        # log the client on
        self.state = self.proxy.PLAY
        self.client_logon()

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
        try:
            return self.parsers[self.state][pkid]()
        except KeyError:
            # Add unparsed packetID to the 'Do nothing parser'
            self.parsers[self.state][pkid] = self._parse_built
            if self.buildmode:
                # some code here to document un-parsed packets?
                pass
            return True

    # Do nothing parser
    def _parse_built(self):
        return True

    def _define_parsers(self):
        # the packets we parse and the methods that parse them.
        self.parsers = {
            self.proxy.HANDSHAKE: {
                self.pktSB.HANDSHAKE:
                    self._parse_handshaking,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            self.proxy.STATUS: {
                self.pktSB.STATUS_PING:
                    self._parse_status_ping,
                self.pktSB.REQUEST:
                    self._parse_status_request,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            self.proxy.LOGIN: {
                self.pktSB.LOGIN_START:
                    self._parse_login_start,
                self.pktSB.LOGIN_ENCR_RESPONSE:
                    self._parse_login_encr_response,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            self.proxy.PLAY: {
                self.pktSB.CHAT_MESSAGE:
                    self.parse_sb.parse_play_chat_message,
                self.pktSB.CLICK_WINDOW:
                    self.parse_sb.parse_play_click_window,
                self.pktSB.CLIENT_SETTINGS:
                    self.parse_sb.parse_play_client_settings,
                self.pktSB.CLIENT_STATUS:
                    self._parse_built,
                self.pktSB.HELD_ITEM_CHANGE:
                    self.parse_sb.parse_play_held_item_change,
                self.pktSB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktSB.PLAYER:
                    self._parse_built,
                self.pktSB.PLAYER_ABILITIES:
                    self._parse_built,
                self.pktSB.PLAYER_BLOCK_PLACEMENT:
                    self.parse_sb.parse_play_player_block_placement,
                self.pktSB.PLAYER_DIGGING:
                    self.parse_sb.parse_play_player_digging,
                self.pktSB.PLAYER_LOOK:
                    self.parse_sb.parse_play_player_look,
                self.pktSB.PLAYER_POSITION:
                    self.parse_sb.parse_play_player_position,
                self.pktSB.PLAYER_POSLOOK:
                    self.parse_sb.parse_play_player_poslook,
                self.pktSB.PLAYER_UPDATE_SIGN:
                    self.parse_sb.parse_play_player_update_sign,
                self.pktSB.SPECTATE:
                    self.parse_sb.parse_play_spectate,
                self.pktSB.TELEPORT_CONFIRM:
                    self.parse_sb.parse_play_teleport_confirm,
                self.pktSB.USE_ENTITY:
                    self._parse_built,
                self.pktSB.USE_ITEM:
                    self.parse_sb.parse_play_use_item,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            self.proxy.LOBBY: {
                self.pktSB.KEEP_ALIVE[PKT]:
                    self._parse_keep_alive,
                self.pktSB.CHAT_MESSAGE:
                    self._parse_lobby_chat_message,
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
                },
            self.proxy.IDLE: {
                self.pktSB.PLUGIN_MESSAGE:
                    self._parse_plugin_message,
            }
        }
