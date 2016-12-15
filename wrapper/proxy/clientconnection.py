# -*- coding: utf-8 -*-

# region Imports

# Standard Library imports
import threading
import time
import json
import hashlib
import random
from socket import error as socket_error
import requests

# import shutil  # these are part of commented out code below for whitelist and name processing
# import os

# Local imports
import utils.encryption as encryption

from proxy.serverconnection import ServerConnection
from proxy.packet import Packet
from proxy import mcpackets
from api.player import Player
from core.mcuuid import MCUUID

from utils.helpers import processcolorcodes

# region Constants
# ------------------------------------------------

HANDSHAKE = 0  # this is the default mode of a server awaiting packets from a client out in the ether..
# client will send a handshake (a 0x00 packet WITH payload) asking for STATUS or LOGIN mode
STATUS = 1
# Status mode will await either a ping (0x01) containing a unique long int and will respond with same integer.
#     ... OR if it receives a 0x00 packet (with no payload), that signals server (client.py) to send
#         the MOTD json response packet.
#         The ping will follow the 0x00 request for json response.  The ping will set wrapper/server
#         back to HANDSHAKE mode (to await next handshake).
LOGIN = 2
PLAY = 3
LOBBY = 4  # in lobby state, client is connected to clientconnection, but nothing is passed to the server.
#            the actual client will be in play mode.

_STRING = 0
_JSON = 1
_UBYTE = 2
_BYTE = 3
_INT = 4
_SHORT = 5
_USHORT = 6
_LONG = 7
_DOUBLE = 8
_FLOAT = 9
_BOOL = 10
_VARINT = 11
_BYTEARRAY = 12
_BYTEARRAY_SHORT = 13
_POSITION = 14
_SLOT = 15
_SLOT_NO_NBT = 18
_UUID = 16
_METADATA = 17
_REST = 90
_RAW = 90
_NULL = 100
# endregion


# noinspection PyMethodMayBeStatic
class Client:
    def __init__(self, proxy, clientsock, client_addr, banned=False):
        """
        Handle the client connection.

        This class Client is a "fake" server, accepting connections from clients.
        It receives "SERVER BOUND" packets from client, parses them, and forards them on to the server.

        Client receives the parent proxy as it's argument.  Accordingly, it receives the proxy's wrapper instance.
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
        self.command_prefix = self.wrapper.command_prefix
        self.command_prefix_non_standard = self.command_prefix != "/"
        self.command_prefix_len = len(self.command_prefix)
        self.hidden_ops = self.config["Proxy"]["hidden-ops"]

        # client setup and operating paramenters
        self.packet = Packet(self.client_socket, self)
        self.verifyToken = encryption.generate_challenge_token()
        self.serverID = encryption.generate_server_id()
        self.MOTD = {}
        self.serverversion = self.wrapper.javaserver.protocolVersion
        self.clientversion = self.serverversion  # client will reset this later, if need be..
        self.server_port = self.wrapper.javaserver.server_port  # default server port (to this wrapper's server)
        self.wrapper_onlinemode = self.config["Proxy"]["online-mode"]

        # packet stuff
        self.pktSB = mcpackets.ServerBound(self.clientversion)
        self.pktCB = mcpackets.ClientBound(self.clientversion)
        self.parsers = {}  # dictionary of parser packet constants and associated parsing methods
        self._getclientpacketset()
        self.buildmode = False

        # keep alive data
        self.time_server_pinged = 0
        self.time_client_responded = 0
        self.keepalive_val = 0

        # client and server status
        self.abort = False
        self.server_connection = None  # Proxy ServerConnection() (not the javaserver)
        self.state = HANDSHAKE

        # UUIDs - all should use MCUUID unless otherwise specified
        # --------------------------------------------------------
        # Server UUID - which is the local offline UUID.
        self.serveruuid = None
        # --------------------------------------------------------
        # this is the client UUID authenticated by connection to session server.
        self.uuid = None
        # --------------------------------------------------------
        # the formal, unique, mojang UUID as looked up on mojang servers.  This ID will be the same
        #  no matter what mode wrapper is in or whether it is a lobby, etc.  This will be the formal
        #  uuid to use for all wrapper internal functions for referencing a unique player.
        self.mojanguuid = None

        # information gathered during login or socket connection processes
        # TODO in the future, we could use plugin channels to communicate these to subworld wrappers
        # From socket data
        self.address = None
        self.ip = self.client_address[0]  # this will store the client IP for use by player.py
        # From client handshake
        self.serveraddressplayeruses = None
        self.serverportplayeruses = None

        # player api Items
        self.username = "PING REQUEST"
        self.gamemode = 0
        self.dimension = 0
        self.position = (0, 0, 0)  # X, Y, Z
        self.head = (0, 0)  # Yaw, Pitch
        self.inventory = {}
        self.slot = 0
        self.riding = None
        self.lastplacecoords = (0, 0, 0)  # last placement (for use in cases of bucket use)
        self.properties = {}
        self.clientSettings = False
        self.clientSettingsSent = False
        self.skinBlob = {}
        self.windowCounter = 2  # restored this
        self.lastitem = None

    def handle(self):
        t = threading.Thread(target=self.flush_loop, args=())
        t.daemon = True
        t.start()

        while not self.abort:
            try:
                pkid, original = self.packet.grabpacket()
            except EOFError:
                # This is not really an error.. It means the client is not sending packet stream anymore
                self.log.debug("Client Packet stream ended [EOF] (%s)", self.username)
                break
            except socket_error:  # occurs anytime a socket is closed.
                self.log.debug("client proxy Failed to grab packet [socket_error] (%s)", self.username)
                break
            except Exception as e:
                # anything that gets here is a bona-fide error we need to become aware of
                self.log.error("Exception: Failed to grab packet [CLIENT (%s)] (%s):", self.username, e)
                break

            # self.parse(pkid)

            # send packet if server available and parsing passed.
            # already tested - Python will not attempt eval of self.server.state if self.server is False
            if self.parse(pkid) and self.server_connection and self.server_connection.state == 3:
                self.server_connection.packet.send_raw(original)
        self.close_server()

    def flush_loop(self):
        while not self.abort:
            try:
                self.packet.flush()
            except socket_error:
                self.log.debug("client socket closed (socket_error).")
                break
            time.sleep(0.01)
        self.log.debug("client connection flush_loop thread ended")

    def connect_to_server(self, ip=None, port=None):
        """
        Connects the client to a server.  Creates a new server instance and tries to connect to it.
        leave ip and port blank to connect to the local wrapped javaserver instance.

        it is the responsibility of the calling method to shutdown any existing server connection first.
        It is also the caller's responsibility to track LOBBY modes and handle respawns, rain, etc.
        """

        self.server_connection = ServerConnection(self, ip, port)

        try:
            self.server_connection.connect()
        except Exception as e:
            self.disconnect("Proxy client could not connect to the server (%s)" % e)

        # start server handle()
        t = threading.Thread(target=self.server_connection.handle, args=())
        t.daemon = True
        t.start()

        # log in to (offline) server.
        self.server_connection.state = LOGIN
        if self.spigot_mode:
            payload = "localhost\x00%s\x00%s" % (self.client_address[0], self.uuid.hex)
            self.server_connection.packet.sendpkt(self.server_connection.pktSB.HANDSHAKE,
                                                  [_VARINT, _STRING, _USHORT, _VARINT],
                                                  (self.clientversion, payload, self.server_port, LOGIN))
        else:
            self.server_connection.packet.sendpkt(self.server_connection.pktSB.HANDSHAKE,
                                                  [_VARINT, _STRING, _USHORT, _VARINT],
                                                  (self.clientversion, "localhost", self.server_port, LOGIN))

        self.server_connection.packet.sendpkt(self.server_connection.pktSB.LOGIN_START, [_STRING], [self.username])

        # LOBBY code and such to go elsewhere

    def change_servers(self, ip=None, port=None):

        # stop any raining
        self.packet.sendpkt(self.pktCB.CHANGE_GAME_STATE, [_UBYTE, _FLOAT], (1, 0))
        # respawn them in the end or nether so that when they "respawn" in world, the downloading terrain closes.
        self.packet.sendpkt(self.pktCB.RESPAWN, [_INT, _UBYTE, _UBYTE, _STRING], [-1, 3, 0, 'default'])

        # del self.wrapper.javaserver.players[str(client.username)]
        if self.username in self.wrapper.javaserver.players:
            del self.wrapper.javaserver.players[self.username]
        # close current connection and start new one
        # noinspection PyBroadException
        try:
            self.server_connection.close_server(reason="Lobbification", lobby_return=True)
            self.state = LOBBY
            self.connect_to_server(ip, port)
            self.clientSettingsSent = False
            self._send_client_settings()
        except:
            # if there is a problem, close the client and disconnect player
            self.close_server()

    def close_server(self):
        # close the server connection gracefully first, if possible.

        # noinspection PyBroadException
        try:
            self.server_connection.close_server("Client Disconnecting...")
        except:
            self.log.debug("Client socket for %s already closed!", self.username)
        self.abort = True  # TODO investigate this

    def disconnect(self, message):
        """
        disconnects the client (runs close_server(), which will also shut off the serverconnection.py)

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

        if self.state == PLAY:
            self.packet.sendpkt(self.pktCB.DISCONNECT, [_JSON], [jsonmessage])
            self.log.debug("upon disconnect, state was PLAY (sent PLAY state DISCONNECT)")
        else:
            self.packet.sendpkt(self.pktCB.LOGIN_DISCONNECT, [_JSON], [message])
            self.log.debug("upon disconnect, state was 'other' (sent LOGIN_DISCONNECT)")
        time.sleep(1)
        self.state = STATUS
        self.close_server()

    # internal init and properties
    # -----------------------------
    @property
    def version(self):
        return self.clientversion

    def _inittheplayer(self):
        # so few items and so infrequently run that fussing with xrange/range PY2 difference is not needed.
        for i in range(46):  # there are 46 items 0-45 in 1.9 (shield) versus 45 (0-44) in 1.8 and below.
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
        # Determine packet types  - in this context, pktSB/pktCB is what is being received/sent from/to the client.
        #   that is why we refresh to the clientversion.
        self.pktSB = mcpackets.ServerBound(self.clientversion)
        self.pktCB = mcpackets.ClientBound(self.clientversion)
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
            self.server_connection.packet.sendpkt(self.pktSB.PLAYER_UPDATE_SIGN,
                                                  [_INT, _SHORT, _INT, _STRING, _STRING, _STRING, _STRING],
                                                  (x, y, z, line1, line2, line3, line4))
        else:
            self.server_connection.packet.sendpkt(
                self.pktSB.PLAYER_UPDATE_SIGN, [_POSITION, _STRING, _STRING, _STRING, _STRING],
                (position, line1, line2, line3, line4))

    def message(self, string):
        self.server_connection.packet.sendpkt(self.pktSB.CHAT_MESSAGE, [_STRING], [string])

    # internal client login methods
    # -----------------------------
    def _keep_alive_tracker(self, playername):
        # send keep alives to client and send client settings to server.
        # TODO future - use a plugin channel to see if the client is actually another wrapper
        while not self.abort:
            time.sleep(1)
            if self.state in (PLAY, LOBBY):
                # client expects < 20sec
                if time.time() - self.time_server_pinged > 5:

                    # create the keep alive value
                    self.keepalive_val = random.randrange(0, 99999)

                    # challenge the client with it
                    if self.clientversion > mcpackets.PROTOCOL_1_8START:
                        self.packet.sendpkt(self.pktCB.KEEP_ALIVE, [_VARINT], [self.keepalive_val])
                    else:
                        # pre- 1.8
                        self.packet.sendpkt(self.pktCB.KEEP_ALIVE, [_INT], [self.keepalive_val])
                    self.time_server_pinged = time.time()

                # check for active client keep alive status:
                # server can allow up to 30 seconds for response
                if time.time() - self.time_client_responded > 25 and not self.abort:
                    self.disconnect("Client closed due to lack of keepalive response")
                    self.log.debug("Closed %s's client thread due to lack of keepalive response", playername)
                    return
        self.log.debug("Client keepalive tracker aborted (%s's client thread)", playername)

    def _login_authenticate_client(self, server_id):
        if self.wrapper_onlinemode:
            r = requests.get("https://sessionserver.mojang.com/session/minecraft/hasJoined?username=%s"
                             "&serverId=%s" % (self.username, server_id))
            if r.status_code == 200:
                requestdata = r.json()
                self.uuid = MCUUID(requestdata["id"])  # TODO

                if requestdata["name"] != self.username:
                    self.disconnect("Client's username did not match Mojang's record")
                    self.log.info("Client's username did not match Mojang's record %s != %s",
                                  requestdata["name"], self.username)
                    return False

                for prop in requestdata["properties"]:
                    if prop["name"] == "textures":
                        self.skinBlob = prop["value"]
                        self.wrapper.proxy.skins[self.uuid.string] = self.skinBlob
                self.properties = requestdata["properties"]
            else:
                self.disconnect("Proxy Client Session Error (HTTP Status Code %d)" % r.status_code)
                return False
            currentname = self.wrapper.uuids.getusernamebyuuid(self.uuid.string)
            if currentname:
                if currentname != self.username:
                    self.log.info("%s's client performed LOGON in with new name, falling back to %s",
                                  self.username, currentname)
                    self.username = currentname
            self.serveruuid = self.wrapper.uuids.getuuidfromname(self.username)

        # Wrapper offline and not authenticating
        # maybe it is the destination of a hub? or you use another way to authenticate (passwords?)
        else:
            # I'll take your word for it, bub...  You are:
            self.serveruuid = self.wrapper.uuids.getuuidfromname(self.username)
            self.uuid = self.serveruuid
            self.log.debug("Client logon with wrapper offline- 'self.uuid = OfflinePlayer:<name>'")

        # no idea what is special about version 26
        if self.clientversion > 26:
            self.packet.setcompression(256)

    def _add_player_and_client_objects_to_wrapper(self, new_client=True):
        # Put player object and client into server. (player login will be called later by mcserver.py)
        if new_client:
            self.wrapper.proxy.clients.append(self)

        if self.username not in self.wrapper.javaserver.players:
            self.wrapper.javaserver.players[self.username] = Player(self.username, self.wrapper)
        self._inittheplayer()  # set up inventory and stuff

    def _login_client_logon(self):

        if self.wrapper.proxy.isuuidbanned(self.uuid.__str__()):
            banreason = self.wrapper.proxy.getuuidbanreason(self.uuid.__str__())
            self.log.info("Banned player %s tried to connect:\n %s" % (self.username, banreason))
            self.state = HANDSHAKE
            self.disconnect("Banned: %s" % banreason)
            return False

        # Run the pre-login event -  A great place for AuthMe type plugins.
        if not self.wrapper.events.callevent("player.preLogin",
                                             {
                                                 "player": self.username,
                                                 "online_uuid": self.uuid.string,
                                                 "offline_uuid": self.serveruuid.string,
                                                 "ip": self.ip,
                                                 "secure_connection": self.wrapper_onlinemode
                                             }):
            self.state = HANDSHAKE
            self.disconnect("Login denied by a Plugin.")
            return False

        self.log.info("%s's client LOGON occurred: (UUID: %s | IP: %s | SecureConnection: %s)",
                      self.username, self.uuid.string, self.ip, self.wrapper_onlinemode)

        self._add_player_and_client_objects_to_wrapper()

        # send login success to client
        self.packet.sendpkt(self.pktCB.LOGIN_SUCCESS, [_STRING, _STRING], (self.uuid.string, self.username))
        self.time_client_responded = time.time()
        self.state = PLAY

        # start keep alives
        t_keepalives = threading.Thread(target=self._keep_alive_tracker, kwargs={'playername': self.username})
        t_keepalives.daemon = True
        t_keepalives.start()

        # connect to server
        self.connect_to_server()

        return False

    def _send_client_settings(self):
        if self.clientSettings and not self.clientSettingsSent:
            self.server_connection.packet.sendpkt(self.pktSB.CLIENT_SETTINGS, [_RAW], (self.clientSettings,))
            self.clientSettingsSent = True

    def _read_keep_alive(self):
        if self.serverversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_INT])
        else:  # self.version >= mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_VARINT])
        if data[0] == self.keepalive_val:
            self.time_client_responded = time.time()
        return False

    def _whitelist_processing(self):
        pass
        # This needs re-worked.
        # if self.config["Proxy"]["convert-player-files"]:  # Rename UUIDs accordingly
        #     if self.config["Proxy"]["online-mode"]:
        #         # Check player files, and rename them accordingly to offline-mode UUID
        #         worldname = self.wrapper.javaserver.worldname
        #         if not os.path.exists("%s/playerdata/%s.dat" % (worldname, self.serveruuid.string)):
        #             if os.path.exists("%s/playerdata/%s.dat" % (worldname, self.uuid.string)):
        #                 self.log.info("Migrating %s's playerdata file to proxy mode", self.username)
        #                 shutil.move("%s/playerdata/%s.dat" % (worldname, self.uuid.string),
        #                             "%s/playerdata/%s.dat" % (worldname, self.serveruuid.string))
        #                 with open("%s/.wrapper-proxy-playerdata-migrate" % worldname, "a") as f:
        #                     f.write("%s %s\n" % (self.uuid.string, self.serveruuid.string))
        #         # Change whitelist entries to offline mode versions
        #         if os.path.exists("whitelist.json"):
        #             with open("whitelist.json", "r") as f:
        #                 jsonwhitelistdata = json.loads(f.read())
        #             if jsonwhitelistdata:
        #                 for player in jsonwhitelistdata:
        #                     if not player["uuid"] == self.serveruuid.string and \
        #                                     player["uuid"] == self.uuid.string:
        #                         self.log.info("Migrating %s's whitelist entry to proxy mode", self.username)
        #                         jsonwhitelistdata.append({"uuid": self.serveruuid.string,
        #                                                   "name": self.username})
        #                         with open("whitelist.json", "w") as f:
        #                             f.write(json.dumps(jsonwhitelistdata))
        #                         self.wrapper.javaserver.console("whitelist reload")
        #                         with open("%s/.wrapper-proxy-whitelist-migrate" % worldname, "a") as f:
        #                             f.write("%s %s\n" % (self.uuid.string, self.serveruuid.string))

    # PARSERS SECTION
    # -----------------------------
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

    def _define_parsers(self):
        # the packets we parse and the methods that parse them.
        self.parsers = {
            HANDSHAKE: {
                self.pktSB.HANDSHAKE: self._parse_handshaking
                },
            STATUS: {
                self.pktSB.STATUS_PING: self._parse_status_ping,
                self.pktSB.REQUEST: self._parse_status_request
                },
            LOGIN: {
                self.pktSB.LOGIN_START: self._parse_login_start,
                self.pktSB.LOGIN_ENCR_RESPONSE: self._parse_login_encr_response
                },
            PLAY: {
                self.pktSB.CHAT_MESSAGE: self._parse_play_chat_message,
                self.pktSB.CLICK_WINDOW: self._parse_play_click_window,
                self.pktSB.CLIENT_SETTINGS: self._parse_play_client_settings,
                self.pktSB.CLIENT_STATUS: self._parse_built,
                self.pktSB.HELD_ITEM_CHANGE: self._parse_play_held_item_change,
                self.pktSB.KEEP_ALIVE: self._parse_play_keep_alive,
                self.pktSB.PLAYER: self._parse_built,
                self.pktSB.PLAYER_ABILITIES: self._parse_built,
                self.pktSB.PLAYER_BLOCK_PLACEMENT: self._parse_play_player_block_placement,
                self.pktSB.PLAYER_DIGGING: self._parse_play_player_digging,
                self.pktSB.PLAYER_LOOK: self._parse_play_player_look,
                self.pktSB.PLAYER_POSITION: self._parse_play_player_position,
                self.pktSB.PLAYER_POSLOOK: self._parse_play_player_poslook,
                self.pktSB.PLAYER_UPDATE_SIGN: self._parse_play_player_update_sign,
                self.pktSB.SPECTATE: self._parse_play_spectate,
                self.pktSB.TELEPORT_CONFIRM: self._parse_play_teleport_confirm,
                self.pktSB.USE_ENTITY: self._parse_built,
                self.pktSB.USE_ITEM: self._parse_play_use_item,
                },
            LOBBY: {
                self.pktSB.KEEP_ALIVE: self._parse_lobby_keep_alive,
                self.pktSB.CHAT_MESSAGE: self._parse_lobby_chat_message
            }
        }

    # Do nothing parser
    # -----------------------
    def _parse_built(self):
        return True

    # Login parsers
    # -----------------------
    def _parse_handshaking(self):
        data = self.packet.readpkt([_VARINT, _STRING, _USHORT, _VARINT])  # "version|address|port|state"

        self.clientversion = data[0]
        self._getclientpacketset()

        self.serveraddressplayeruses = data[1]
        self.serverportplayeruses = data[2]
        requestedstate = data[3]

        if requestedstate == STATUS:
            self.state = STATUS
            return False  # wrapper will handle responses, so we do not pass this to the server.

        if requestedstate == LOGIN:
            # TODO - coming soon: allow client connections despite lack of server connection

            if self.serverversion == -1:
                #  ... returns -1 to signal no server
                self.disconnect("The server is not started.")
                return False

            if not self.wrapper.javaserver.state == 2:
                self.disconnect("Server has not finished booting. Please try connecting again in a few seconds")
                return False

            if mcpackets.PROTOCOL_1_9START < self.clientversion < mcpackets.PROTOCOL_1_9REL1:
                self.disconnect("You're running an unsupported snapshot (protocol: %s)!" % self.clientversion)
                return False

            if self.serverversion == self.clientversion:
                # login start...
                self.state = LOGIN
                return True  # packet passes to server, which will also switch to Login

            if self.serverversion != self.clientversion:
                self.disconnect("You're not running the same Minecraft version as the server!")
                return False

        self.disconnect("Invalid HANDSHAKE: 'requested state: %d'" % requestedstate)
        return False

    def _parse_status_ping(self):
        data = self.packet.readpkt([_LONG])
        self.packet.sendpkt(self.pktCB.PING_PONG, [_LONG], [data[0]])
        self.state = HANDSHAKE
        return False

    def _parse_status_request(self):
        sample = []
        for player in self.wrapper.javaserver.players:
            playerobj = self.wrapper.javaserver.players[player]
            if playerobj.username not in self.hidden_ops:
                sample.append({"name": playerobj.username, "id": str(playerobj.mojangUuid)})
            if len(sample) > 5:
                break
        reported_version = self.serverversion
        reported_name = self.wrapper.javaserver.version

        if self.clientversion < mcpackets.PROTOCOL_1_8START:
            motdtext = self.wrapper.javaserver.motd
        else:
            motdtext = json.loads(processcolorcodes(self.wrapper.javaserver.motd.replace("\\", "")))
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
        if self.wrapper.javaserver.serverIcon:  # add Favicon, if it exists
            self.MOTD["favicon"] = self.wrapper.javaserver.serverIcon
        self.packet.sendpkt(self.pktCB.PING_JSON_RESPONSE, [_STRING], [json.dumps(self.MOTD)])
        # after this, proxy waits for the expected PING to go back to Handshake mode
        return False

    def _parse_login_start(self):
        data = self.packet.readpkt([_STRING, _NULL])

        # "username"
        self.username = data[0]

        # just to be clear... this refers to wrapper's online mode, not the server.
        if self.wrapper_onlinemode:
            # Wrapper sends client a login encryption request
            if self.serverversion < 6:  # 1.7.x versions
                # send to client 1.7
                self.packet.sendpkt(self.pktCB.LOGIN_ENCR_REQUEST,
                                    [_STRING, _BYTEARRAY_SHORT, _BYTEARRAY_SHORT],
                                    (self.serverID, self.publicKey, self.verifyToken))
            else:
                # send to client 1.8 +
                self.packet.sendpkt(self.pktCB.LOGIN_ENCR_REQUEST,
                                    [_STRING, _BYTEARRAY, _BYTEARRAY],
                                    (self.serverID, self.publicKey, self.verifyToken))

            # Server UUID is always offline (at the present time)
            self.serveruuid = self.wrapper.uuids.getuuidfromname(self.username)  # MCUUID object

        else:
            # Wrapper offline and not authenticating
            # maybe it is the destination of a hub? or you use another way to authenticate (password plugin?)

            # Server UUID is always offline (at the present time)
            self.uuid = self.wrapper.uuids.getuuidfromname(self.username)

            # Since wrapper is offline, we are using offline for self.uuid also
            self.serveruuid = self.uuid  # MCUUID object
            return self._login_client_logon()

        # Don't send this packet on to the actual server because WE are handling client's logon.
        return False

    def _parse_login_encr_response(self):
        # the client is RESPONDING to our request for encryption (if we sent one above)
        # read response Tokens
        # "shared_secret|verify_token"
        if self.serverversion < 6:
            data = self.packet.readpkt([_BYTEARRAY_SHORT, _BYTEARRAY_SHORT])
        else:
            data = self.packet.readpkt([_BYTEARRAY, _BYTEARRAY])

        sharedsecret = encryption.decrypt_shared_secret(data[0], self.privateKey)
        verifytoken = encryption.decrypt_shared_secret(data[1], self.privateKey)
        h = hashlib.sha1()
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
        if self.ipbanned:  # client never gets to this point if 'silent-ipban' is enabled
            self.log.info("Player %s tried to connect from banned ip: %s", self.username, self.ip)
            self.state = HANDSHAKE
            self.disconnect("Your address is IP-banned from this server!.")
            return False

        # begin Client login process
        # Wrapper in online mode, taking care of authentication
        if self._login_authenticate_client(serverid) is False:
            return False  # client failed to authenticate

        # TODO Whitelist processing Here

        # log the client on
        return self._login_client_logon()

    # Play parsers
    # -----------------------
    def _parse_play_chat_message(self):
        data = self.packet.readpkt([_STRING])
        if data is None:
            return False

        # Get the packet chat message contents
        chatmsg = data[0]

        payload = self.wrapper.events.callevent("player.rawMessage", {
            "player": self.getplayerobject(),
            "message": chatmsg
        })

        # This part allows the player plugin event "player.rawMessage" to...
        if payload is False:
            return False  # ..reject the packet (by returning False)

        # This is here for compatibility.  older plugins may attempt to send a string back
        if type(payload) == str:  # or, if it can return a substitute payload
            chatmsg = payload

        # Newer plugins return a modified version of the original payload (i.e., a dictionary).
        if type(payload) == dict and "message" in payload:  # or, if it can return a substitute payload
            chatmsg = payload["message"]

        # determine if this is a command. act appropriately
        if chatmsg[0:self.command_prefix_len] == self.command_prefix:  # it IS a command of some kind
            if self.wrapper.events.callevent(
                    "player.runCommand", {
                        "player": self.getplayerobject(),
                        "command": chatmsg.split(" ")[0][1:].lower(),
                        "args": chatmsg.split(" ")[1:]}):

                return False  # wrapper processed this command.. it goes no further

        if chatmsg[0] == "/" and self.command_prefix_non_standard:
            chatmsg = chatmsg[1:]  # strip out any leading slash if using a non-slash command  prefix

        # NOW we can send it (possibly modded) on to server...
        self.message(chatmsg)
        return False  # and cancel this original packet

    def _parse_play_keep_alive(self):
        return self._read_keep_alive()

    def _parse_play_player_position(self):
        if self.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _DOUBLE, _BOOL])
            # ("double:x|double:y|double:yhead|double:z|bool:on_ground")
        elif self.clientversion >= mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_DOUBLE, _DOUBLE, _NULL, _DOUBLE, _BOOL])
            # ("double:x|double:y|double:z|bool:on_ground")
        else:
            data = [0, 0, 0, 0]
        self.position = (data[0], data[1], data[3])  # skip 1.7.10 and lower protocol yhead args
        return True

    def _parse_play_player_poslook(self):  # player position and look
        if self.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _DOUBLE, _FLOAT, _FLOAT, _BOOL])
        else:
            data = self.packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _FLOAT, _FLOAT, _BOOL])
        # ("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
        self.position = (data[0], data[1], data[4])
        self.head = (data[4], data[5])
        return True

    def _parse_play_teleport_confirm(self):
        # don't interfere with this and self.pktSB.PLAYER_POSLOOK... doing so will glitch the client
        # data = self.packet.readpkt([_VARINT])
        return True

    def _parse_play_player_look(self):
        data = self.packet.readpkt([_FLOAT, _FLOAT, _BOOL])
        # ("float:yaw|float:pitch|bool:on_ground")
        self.head = (data[0], data[1])
        return True

    def _parse_play_player_digging(self):
        if self.clientversion < mcpackets.PROTOCOL_1_7:
            data = None
            position = data
        elif mcpackets.PROTOCOL_1_7 <= self.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_BYTE, _INT, _UBYTE, _INT, _BYTE])
            # "byte:status|int:x|ubyte:y|int:z|byte:face")
            position = (data[1], data[2], data[3])
        else:
            data = self.packet.readpkt([_BYTE, _POSITION, _NULL, _NULL, _BYTE])
            # "byte:status|position:position|byte:face")
            position = data[1]

        if data is None:
            return True

        # finished digging
        if data[0] == 2:
            if not self.wrapper.events.callevent("player.dig", {
                "player": self.getplayerobject(),
                "position": position,
                "action": "end_break",
                "face": data[4]
            }):
                return False  # stop packet if  player.dig returns False

        # started digging
        if data[0] == 0:
            if self.gamemode != 1:
                if not self.wrapper.events.callevent("player.dig", {
                    "player": self.getplayerobject(),
                    "position": position,
                    "action": "begin_break",
                    "face": data[4]
                }):
                    return False
            else:
                if not self.wrapper.events.callevent("player.dig", {
                    "player": self.getplayerobject(),
                    "position": position,
                    "action": "end_break",
                    "face": data[4]
                }):
                    return False
        if data[0] == 5 and data[4] == 255:
            if self.position != (0, 0, 0):
                playerpos = self.position
                if not self.wrapper.events.callevent("player.interact", {
                    "player": self.getplayerobject(),
                    "position": playerpos,
                    "action": "finish_using"
                }):
                    return False
        return True

    def _parse_play_player_block_placement(self):
        player = self.getplayerobject()
        hand = 0  # main hand
        helditem = player.getHeldItem()

        if self.clientversion < mcpackets.PROTOCOL_1_7:
            data = None
            position = data

        elif mcpackets.PROTOCOL_1_7 <= self.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_INT, _UBYTE, _INT, _BYTE, _SLOT_NO_NBT, _REST])
            # "int:x|ubyte:y|int:z|byte:face|slot:item")  _REST includes cursor positions x-y-z
            position = (data[0], data[1], data[2])

            # just FYI, notchian servers have been ignoring this field ("item")
            # for a long time, using server inventory instead.
            helditem = data[4]  # "item" - _SLOT

        elif mcpackets.PROTOCOL_1_8START <= self.clientversion < mcpackets.PROTOCOL_1_9REL1:
            data = self.packet.readpkt([_POSITION, _NULL, _NULL, _BYTE, _SLOT, _REST])
            # "position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
            # helditem = data["item"]  -available in packet, but server ignores it (we should too)!
            # starting with 1.8, the server maintains inventory also.
            position = data[0]

        else:  # self.clientversion >= mcpackets.PROTOCOL_1_9REL1:
            data = self.packet.readpkt([_POSITION, _NULL, _NULL, _VARINT, _VARINT, _BYTE, _BYTE, _BYTE])
            # "position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
            hand = data[4]  # used to be the spot occupied by "slot"
            position = data[0]

        # Face and Position exist in all version protocols at this point
        clickposition = position
        face = data[3]

        if face == 0:  # Compensate for block placement coordinates
            position = (position[0], position[1] - 1, position[2])
        elif face == 1:
            position = (position[0], position[1] + 1, position[2])
        elif face == 2:
            position = (position[0], position[1], position[2] - 1)
        elif face == 3:
            position = (position[0], position[1], position[2] + 1)
        elif face == 4:
            position = (position[0] - 1, position[1], position[2])
        elif face == 5:
            position = (position[0] + 1, position[1], position[2])

        if helditem is None:
            # if no item, treat as interaction (according to wrappers
            # inventory :(, return False  )
            if not self.wrapper.events.callevent("player.interact", {
                "player": player,
                "position": position,
                "action": "useitem",
                "origin": "pktSB.PLAYER_BLOCK_PLACEMENT"
            }):
                return False

        # block placement event
        self.lastplacecoords = position
        if not self.wrapper.events.callevent("player.place", {"player": player,
                                                              "position": position,  # where new block goes
                                                              "clickposition": clickposition,  # block clicked
                                                              "hand": hand,
                                                              "item": helditem}):
            return False
        return True

    def _parse_play_use_item(self):  # no 1.8 or prior packet
        data = self.packet.readpkt([_REST])
        # "rest:pack")
        player = self.getplayerobject()
        position = self.lastplacecoords
        if "pack" in data:
            if data[0] == '\x00':
                if not self.wrapper.events.callevent("player.interact", {
                    "player": player,
                    "position": position,
                    "action": "useitem",
                    "origin": "pktSB.USE_ITEM"
                }):
                    return False
        return True

    def _parse_play_held_item_change(self):
        slot = self.packet.readpkt([_SHORT])
        # "short:short")  # ["short"]
        if 9 > slot[0] > -1:
            self.slot = slot[0]
        else:
            return False
        return True

    def _parse_play_player_update_sign(self):
        if self.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_INT, _SHORT, _INT, _STRING, _STRING, _STRING, _STRING])
            # "int:x|short:y|int:z|string:line1|string:line2|string:line3|string:line4")
            position = (data[0], data[1], data[2])
            pre_18 = True
        else:
            data = self.packet.readpkt([_POSITION, _NULL, _NULL, _STRING, _STRING, _STRING, _STRING])
            # "position:position|string:line1|string:line2|string:line3|string:line4")
            position = data[0]
            pre_18 = False

        l1 = data[3]
        l2 = data[4]
        l3 = data[5]
        l4 = data[6]
        payload = self.wrapper.events.callevent("player.createsign", {
            "player": self.getplayerobject(),
            "position": position,
            "line1": l1,
            "line2": l2,
            "line3": l3,
            "line4": l4
        })
        if not payload:  # plugin can reject sign entirely
            return False

        if type(payload) == dict:  # send back edits
            if "line1" in payload:
                l1 = payload["line1"]
            if "line2" in payload:
                l2 = payload["line2"]
            if "line3" in payload:
                l3 = payload["line3"]
            if "line4" in payload:
                l4 = payload["line4"]

        self.editsign(position, l1, l2, l3, l4, pre_18)
        return False

    def _parse_play_client_settings(self):  # read Client Settings
        """ This is read for later sending to servers we connect to """
        self.clientSettings = self.packet.readpkt([_RAW])
        self.clientSettingsSent = True  # the packet is not stopped, sooo...
        return True

    def _parse_play_click_window(self):  # click window
        if self.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([_BYTE, _SHORT, _BYTE, _SHORT, _BYTE, _SLOT_NO_NBT])
            # ("byte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
        elif mcpackets.PROTOCOL_1_8START < self.clientversion < mcpackets.PROTOCOL_1_9START:
            data = self.packet.readpkt([_UBYTE, _SHORT, _BYTE, _SHORT, _BYTE, _SLOT])
            # ("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
        elif mcpackets.PROTOCOL_1_9START <= self.clientversion < mcpackets.PROTOCOL_MAX:
            data = self.packet.readpkt([_UBYTE, _SHORT, _BYTE, _SHORT, _VARINT, _SLOT])
            # ("ubyte:wid|short:slot|byte:button|short:action|varint:mode|slot:clicked")
        else:
            data = [False, 0, 0, 0, 0, 0, 0]

        datadict = {
            "player": self.getplayerobject(),
            "wid": data[0],  # window id ... always 0 for inventory
            "slot": data[1],  # slot number
            "button": data[2],  # mouse / key button
            "action": data[3],  # unique action id - incrementing counter
            "mode": data[4],
            "clicked": data[5]  # item data
        }

        if not self.wrapper.events.callevent("player.slotClick", datadict):
            return False

        # for inventory control, the most straightforward way to update wrapper's inventory is
        # to use the data from each click.  The server will make other updates and corrections
        # via SET_SLOT

        # yes, this probably breaks for double clicks that send the item to who-can-guess what slot
        # we can fix that in a future update... this gets us 98% fixed (versus 50% before)
        # another source of breakage is if lagging causes server to deny the changes.  Our code
        # is not checking if the server accepted these changes with a CONFIRM_TRANSACTION.

        if data[0] == 0 and data[2] in (0, 1):  # window 0 (inventory) and right or left click
            if self.lastitem is None and data[5] is None:  # player first clicks on an empty slot - mark empty.
                self.inventory[data[1]] = None

            if self.lastitem is None:  # player first clicks on a slot where there IS some data..
                # having clicked on it puts the slot into NONE status (since it can now be moved)
                self.inventory[data[1]] = None  # we set the current slot to empty/none
                self.lastitem = data[5]  # ..and we cache the new slot data to see where it goes
                return True

            # up to this point, there was not previous item
            if self.lastitem is not None and data[5] is None:  # now we have a previous item to process
                self.inventory[data[1]] = self.lastitem  # that previous item now goes into the new slot.
                self.lastitem = None  # since the slot was empty, there is no newer item to cache.
                return True

            if self.lastitem is not None and data[5] is not None:
                # our last item now occupies the space clicked and the new item becomes the cached item.
                self.inventory[data[1]] = self.lastitem  # set the cached item into the clicked slot.
                self.lastitem = data[5]  # put the item that was in the clicked slot into the cache now.
                return True
        return True

    def _parse_play_spectate(self):  # Spectate - convert packet to local server UUID
        # !? WHAT!?
        # ___________
        # "Teleports the player to the given entity. The player must be in spectator mode.
        # The Notchian client only uses this to teleport to players, but it appears to accept
        #  any type of entity. The entity does not need to be in the same dimension as the
        # player; if necessary, the player will be respawned in the right world."
        """ Inter-dimensional player-to-player TP ! """  # TODO !

        data = self.packet.readpkt([_UUID, _NULL])  # solves the uncertainty of dealing with what gets returned.
        # ("uuid:target_player")
        for client in self.wrapper.proxy.clients:
            if data[0] == client.uuid:
                self.server_connection.packet.sendpkt(self.pktSB.SPECTATE, [_UUID], [client.serveruuid])
                return False
        return True

    # Lobby parsers
    # -----------------------
    def _parse_lobby_keep_alive(self):
        return self._read_keep_alive()

    def _parse_lobby_chat_message(self):
        data = self.packet.readpkt([_STRING])
        if data is None:
            return True

        # Get the packet chat message contents
        chatmsg = data[0]

        if chatmsg in ("/lobby", "/hub"):
            # stop any raining
            self.packet.sendpkt(self.pktCB.CHANGE_GAME_STATE, [_UBYTE, _FLOAT], (1, 0))
            # spawn them and end or nether respawn so that when they "respawn" in world, the downloading terrain closes.
            self.packet.sendpkt(self.pktCB.RESPAWN, [_INT, _UBYTE, _UBYTE, _STRING], [-1, 3, 0, 'default'])

            # close current connection and start new one
            # noinspection PyBroadException
            try:
                self.server_connection.close_server(reason="Lobbification", lobby_return=True)
                self.state = PLAY
                self.connect_to_server()  # with no arguments, this reconnects to local server
                self._add_player_and_client_objects_to_wrapper(new_client=False)
                self.clientSettingsSent = False
                self._send_client_settings()
            except:
                # if there is a problem, close the client and disconnect player
                self.close_server()
            return False

        # we are just sniffing this packet for lobby return commands, so send it on to the destination.
        return True
