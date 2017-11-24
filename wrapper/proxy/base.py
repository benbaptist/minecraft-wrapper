# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import socket
import threading
import time
import json

from api.helpers import getjsonfile, putjsonfile, find_in_json
from api.helpers import epoch_to_timestr, read_timestr
from api.helpers import isipv4address

from proxy.utils import mcuuid
from proxy.entity.entitycontrol import EntityControl

try:
    import requests
    # noinspection PyUnresolvedReferences
    import proxy.utils.encryption as encryption
except ImportError:
    requests = False

try:
    from proxy.client.clientconnection import Client
    from proxy.packets.packet import Packet

except ImportError:
    Client = False
    Packet = False


class NullEventHandler(object):
    def __init__(self):
        pass

    def callevent(self, event, payload):
        """An event handler must have this method that expects
        two positional arguments:
         :event: The string name of the event.
         :payload: A dictionary of items describing the event (varies 
          with event.
        """
        pass


class HaltSig(object):
    """HaltSig is simply a sort of dummy class created for the
    proxy.  proxy expects this object with a self.halt property
    that tells proxy to shutdown.  The caller maintains control
    of the Haltsig object and uses it to signal the proxy to 
    shut down.  The caller will import this class, instantiate 
    it, and then pass the object to proxy as the argument for
    termsignal."""
    def __init__(self):
        self.halt = False


class ServerVitals(object):
    """This class permits sharing of server information between
    the caller (such as a Wrapper instance) and proxy."""
    def __init__(self, playerobjects):

        # operational info
        self.serverpath = ""
        self.state = 0
        self.server_port = "25564"
        self.onlineMode = True
        self.command_prefix = "/"

        # Shared data structures and run-time
        self.players = playerobjects

        # TODO - I don't think this is used or needed (same name as proxy.entity_control!)
        self.entity_control = None
        # -1 until a player logs on and server sends a time update
        self.timeofday = -1
        self.spammy_stuff = ["found nothing", "vehicle of", "Wrong location!",
                             "Tried to add entity"]

        # PROPOSE
        self.clients = []

        # owner/op info
        self.ownernames = {}
        self.operator_list = []

        # server properties and folder infos
        self.properties = {}
        self.worldname = None
        self.maxPlayers = 20
        self.motd = None
        self.serverIcon = None

        # # Version information
        # -1 until proxy mode checks the server's MOTD on boot
        self.protocolVersion = -1
        # this is string name of the version, collected by console output
        self.version = ""
        # a comparable number = x0y0z, where x, y, z = release,
        #  major, minor, of version.
        self.version_compute = 0


class ProxyConfig(object):
    def __init__(self):
        self.proxy = {
            "convert-player-files": False,
            "hidden-ops": [],
            "max-players": 1024,
            "online-mode": True,
            "proxy-bind": "0.0.0.0",
            "proxy-enabled": True,
            "proxy-port": 25570,
            "proxy-sub-world": False,
            "silent-ipban": True,
            "spigot-mode": False
        }
        self.entity = {
            "enable-entity-controls": False,
            "entity-update-frequency": 4,
            "thin-Chicken": 30,
            "thin-Cow": 40,
            "thin-Sheep": 40,
            "thin-cow": 40,
            "thin-zombie_pigman": 200,
            "thinning-activation-threshhold": 100,
            "thinning-frequency": 30
          }


class Proxy(object):
    def __init__(self, termsignal, config, servervitals, loginstance,
                 usercache, eventhandler):

        self.srv_data = servervitals
        self.config = config.proxy
        self.ent_config = config.entity

        if not requests and self.config["proxy-enabled"]:
            raise Exception("You must have requests and pycrypto installed "
                            "to run the Proxy!")

        self.log = loginstance
        self.usercache = usercache
        self.eventhandler = eventhandler
        self.uuids = mcuuid.UUIDS(self.log, self.usercache)

        # termsignal is an object with a `halt` property set to True/False
        # it represents the calling program's run status
        self.caller = termsignal
        # Proxy's run status (set True to shutdown/ end `host()` while loop
        self.abort = False

        # self assignments (gets specific values)
        self.proxy_bind = self.config["proxy-bind"]
        self.proxy_port = self.config["proxy-port"]
        self.silent_ip_banning = self.config["silent-ipban"]

        # proxy internal workings
        #
        # proxy_socket is only defined here to make the IDE type checking
        #  happy.  The actual socket connection is created later.
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.usingSocket = False

        self.skins = {}
        self.skinTextures = {}
        self.uuidTranslate = {}
        # define the slot once here and not at each clients Instantiation:
        self.inv_slots = range(46)

        # various contructions for non-standard
        # client/servers (forge?) and wrapper's own channel
        self.mod_info = {}
        self.forge = False
        self.forge_login_packet = None
        self.registered_channels = ["WRAPPER.PY|", "WRAPPER.PY|PING", ]
        self.pinged = False

        # trace variables
        self.trace = False
        self.ignoredSB = [0x05, 0x0a, 0x00, 0x0f, 0x1a, 0x0d, 0x0e, 0x10, 0x15,
                          0x03]
        self.ignoredCB = [0x23, 0x18, 0x0d, 0x2b, 0x39, 0x1b, 0x30, 0x2d, 0x2e,
                          0x37, 0x46, 0x45, 0x14, 0x16, 0x20, 0x03, 0x3b, 0x4d,
                          0x3e, 0x3f, 0x27, 0x35, 0x26, 0x4c, 0x40, 0x00, 0x3d,
                          0x4b, 0x0b, 0x31, 0x48, 0x1d, 0x21, 0x28]

        self.privateKey = encryption.generate_key_pair()
        self.publicKey = encryption.encode_public_key(self.privateKey)

        self.entity_control = None

    def host(self):
        """ the caller should ensure host() is not called before the 
        server is fully up and running."""

        # loops while server is not started (STARTED = 2)
        while not self.srv_data.state == 2:
            time.sleep(.2)

        # get the protocol version from the server
        try:
            self.pollserver()
        except Exception as e:
            self.log.exception("Proxy could not poll the Minecraft server - "
                               "check server/wrapper configs? (%s)", e)

        # open proxy port to accept client connections
        while not self.usingSocket:
            self.proxy_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
            try:
                self.proxy_socket.bind((self.proxy_bind, self.proxy_port))
            except Exception as e:
                self.log.exception("Proxy mode could not bind - retrying"
                                   " in ten seconds (%s)", e)
                self.usingSocket = False
                time.sleep(10)
            self.usingSocket = True
            self.proxy_socket.listen(5)

        # proxy now up and running, bound to server port.
        self.entity_control = EntityControl(self)

        # accept clients and start their threads
        while not (self.abort or self.caller.halt):
            try:
                sock, addr = self.proxy_socket.accept()
            except Exception as e:
                self.log.exception("An error has occured while trying to "
                                   "accept a socket connection \n(%s)", e)
                continue

            banned_ip = self.isipbanned(addr)
            if self.silent_ip_banning and banned_ip:
                sock.shutdown(0)  # 0: done receiving, 1: done sending, 2: both
                continue

            # spur off client thread
            # self.server_temp = ServerConnection(self, ip, port)
            client = Client(self, sock, addr, banned=banned_ip)
            t = threading.Thread(target=client.handle, args=())
            t.daemon = True
            t.start()
            # self.srv_data.clients.append(client)  # append later (login)
            self.removestaleclients()

        # received self.abort or caller.halt signal...
        self.entity_control._abortep = True

    def removestaleclients(self):
        """only removes aborted clients"""
        for i, client in enumerate(self.srv_data.clients):
            if self.srv_data.clients[i].abort:
                self.srv_data.clients.pop(i)

    def pollserver(self, host="localhost", port=None):
        if port is None:
            port = self.srv_data.server_port

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # server_sock = socket.socket()
        server_sock.settimeout(5)
        server_sock.connect((host, port))
        packet = Packet(server_sock, self)

        packet.send(0x00, "varint|string|ushort|varint", (5, host, port, 1))
        packet.send(0x00, "", ())
        packet.flush()
        self.srv_data.protocolVersion = -1
        while True:
            pkid, original = packet.grabpacket()
            if pkid == 0x00:
                data = json.loads(packet.read("string:response")["response"])
                self.srv_data.protocolVersion = data["version"][
                    "protocol"]
                self.srv_data.version = data["version"]["name"]
                if "modinfo" in data and data["modinfo"]["type"] == "FML":
                    self.forge = True
                    self.mod_info["modinfo"] = data["modinfo"]

                break
        server_sock.close()

    def getclientbyofflineserveruuid(self, uuid):
        """
        :param uuid: - MCUUID
        :return: the matching client
        """
        attempts = ["Search: %s" % str(uuid)]
        for client in self.srv_data.clients:
            attempts.append("try: client-%s uuid-%s serveruuid-%s name-%s" %
                            (client, client.uuid.string,
                             client.serveruuid.string, client.username))
            if client.serveruuid.string == str(uuid):
                self.uuidTranslate[uuid] = client.uuid.string
                return client
        self.log.debug("getclientbyofflineserveruuid failed: \n %s", attempts)
        self.log.debug("POSSIBLE CLIENTS: \n %s", self.srv_data.clients)
        return False  # no client

    def banplayer(self, playername, reason="Banned by an operator",
                  source="Wrapper", expires="forever"):
        """
        * placeholder code for future feature* - This will be the
        pre-1.7.6 ban method (name only).  This is not used by code yet...
        for banning by username only for pre-uuid servers
        :param playername:
        :param reason:
        :param source:
        :param expires:
        :return:
        """
        print(" # TODO - legacy server support (pre-1.7.6) %s%s%s%s%s" %
              (self, reason, source, expires, playername))

    def getuuidbanreason(self, uuid):
        """
        :param uuid: uuid of player as string
        :return: string representing ban reason
        """
        banlist = getjsonfile("banned-players", self.srv_data.serverpath)
        if banlist:
            banrecord = find_in_json(banlist, "uuid", uuid)
            return "%s by %s" % (banrecord["reason"], banrecord["source"])
        return "Banned by server"

    def banuuid(self, uuid, reason="The Ban Hammer has spoken!",
                source="Wrapper", expires=False):
        """
        Ban someone by UUID  This is the 1.7.6 way to ban..
        :param uuid - uuid to ban (MCUUID)
        :param reason - text reason for ban
        :param source - source (author/op) of ban.
        :param expires - expiration in seconds from epoch time.  Field exists
         but not used by the vanilla server
        - implement it for tempbans in future?
          Gets converted to string representation in the ban file.

        This probably only works on 1.7.10 servers or later
        """
        banlist = getjsonfile("banned-players", self.srv_data.serverpath)
        if banlist is not False:  # file and directory exist.
            if banlist is None:  # file was empty or not valid
                banlist = dict()  # ensure valid dict before operating on it
            if find_in_json(banlist, "uuid", str(uuid)):
                return "player already banned"  # error text
            else:
                if expires:
                    try:
                        expiration = epoch_to_timestr(expires)
                    except Exception as e:
                        print('Exception: %s' % e)
                        return "expiration date invalid"  # error text
                else:
                    expiration = "forever"
                name = self.uuids.getusernamebyuuid(uuid.string)
                banlist.append({"uuid": uuid.string,
                                "name": name,
                                "created": epoch_to_timestr(time.time()),
                                "source": source,
                                "expires": expiration,
                                "reason": reason})
                if putjsonfile(banlist, "banned-players", self.srv_data.serverpath):

                    console_command = "kick %s Banned: %s" % (name, reason)
                    self.eventhandler.callevent("proxy.console",
                                                {"command": console_command})
                    """ eventdoc
                                            <description> internalfunction <description>

                                        """
                    return "Banned %s: %s" % (name, reason)
                return "Could not write banlist to disk"
        else:
            return "Banlist not found on disk"

    def banuuidraw(self, uuid, username, reason="The Ban Hammer has spoken!",
                   source="Wrapper", expires=False):
        """
        Ban a raw uuid/name combination with no mojang error checks
        :param uuid - uuid to ban (MCUUID)
        :param username - Name of player to ban
        :param reason - text reason for ban
        :param source - source (author/op) of ban.
        :param expires - expiration in seconds from epoch time.  Field exists
         but not used by the vanilla server
        - implement it for tempbans in future?
          Gets converted to string representation in the ban file.

        This probably only works on 1.7.10 servers or later
        """
        banlist = getjsonfile("banned-players", self.srv_data.serverpath)
        if banlist is not False:  # file and directory exist.
            if banlist is None:  # file was empty or not valid
                banlist = dict()  # ensure valid dict before operating on it
            if find_in_json(banlist, "uuid", str(uuid)):
                return "player already banned"  # error text
            else:
                if expires:
                    try:
                        expiration = epoch_to_timestr(expires)
                    except Exception as e:
                        print('Exception: %s' % e)
                        return "expiration date invalid"  # error text
                else:
                    expiration = "forever"
                banlist.append({"uuid": uuid.string,
                                "name": username,
                                "created": epoch_to_timestr(time.time()),
                                "source": source,
                                "expires": expiration,
                                "reason": reason})
                if putjsonfile(banlist, "banned-players", self.srv_data.serverpath):
                    self.log.info("kicking %s... %s", username, reason)

                    console_command = "kick %s Banned: %s" % (username, reason)
                    self.eventhandler.callevent("proxy.console",
                                                {"command": console_command})
                    """ eventdoc
                                            <description> internalfunction <description>

                                        """
                    return "Banned %s: %s - %s" % (username, uuid, reason)
                return "Could not write banlist to disk"
        else:
            return "Banlist not found on disk"

    def banip(self, ipaddress, reason="The Ban Hammer has spoken!",
              source="Wrapper", expires=False):
        """
        Ban an IP address (IPV-4)
        :param ipaddress - ip address to ban
        :param reason - text reason for ban
        :param source - source (author/op) of ban.
        :param expires - expiration in seconds from epoch time.  Field exists
        but not used by the vanilla server.
        - implement it for tempbans in future?
        - Gets converted to string representation in the ban file.

        This probably only works on 1.7.10 servers or later
        """
        if not isipv4address(ipaddress):
            return "Invalid IPV4 address: %s" % ipaddress
        banlist = getjsonfile("banned-ips", self.srv_data.serverpath)
        if banlist is not False:  # file and directory exist.
            if banlist is None:  # file was empty or not valid
                banlist = dict()  # ensure valid dict before operating on it
            if find_in_json(banlist, "ip", ipaddress):
                return "address already banned"  # error text
            else:
                if expires:
                    try:
                        expiration = epoch_to_timestr(expires)
                    except Exception as e:
                        print('Exception: %s' % e)
                        return "expiration date invalid"  # error text
                else:
                    expiration = "forever"
                banlist.append({"ip": ipaddress,
                                "created": epoch_to_timestr(time.time()),
                                "source": source,
                                "expires": expiration,
                                "reason": reason})
                if putjsonfile(banlist, "banned-ips", self.srv_data.serverpath):
                    banned = ""
                    for client in self.srv_data.clients:
                        if client.ip == str(ipaddress):

                            console_command = "kick %s Your IP is Banned!" % client.username
                            self.eventhandler.callevent("proxy.console",
                                                        {"command": console_command})
                            """ eventdoc
                                                    <description> internalfunction <description>

                                                """
                            banned += "\n%s" % client.username
                    return "Banned ip address: %s\nPlayers kicked as " \
                           "a result:%s" % (ipaddress, banned)
                return "Could not write banlist to disk"
        else:
            return "Banlist not found on disk"

    def pardonip(self, ipaddress):
        if not isipv4address(ipaddress):
            return "Invalid IPV4 address: %s" % ipaddress
        banlist = getjsonfile("banned-ips", self.srv_data.serverpath)
        if banlist is not False:  # file and directory exist.
            if banlist is None:  # file was empty or not valid
                return "No IP bans have ever been recorded."
            banrecord = find_in_json(banlist, "ip", ipaddress)
            if banrecord:
                for x in banlist:
                    if x == banrecord:
                        banlist.remove(x)
                if putjsonfile(banlist, "banned-ips", self.srv_data.serverpath):
                    return "pardoned %s" % ipaddress
                return "Could not write banlist to disk"
            else:
                return "That address was never banned"  # error text

        else:
            return "Banlist not found on disk"  # error text

    def pardonuuid(self, uuid):
        banlist = getjsonfile("banned-players", self.srv_data.serverpath)
        if banlist is not False:  # file and directory exist.
            if banlist is None:  # file was empty or not valid
                return "No bans have ever been recorded..?"
            banrecord = find_in_json(banlist, "uuid", str(uuid))
            if banrecord:
                for x in banlist:
                    if x == banrecord:
                        banlist.remove(x)
                if putjsonfile(banlist, "banned-players", self.srv_data.serverpath):
                    name = self.uuids.getusernamebyuuid(str(uuid))
                    return "pardoned %s" % name
                return "Could not write banlist to disk"
            else:
                return "That person was never banned"  # error text
        else:
            return "Banlist not found on disk"  # error text

    def pardonname(self, username):
        banlist = getjsonfile("banned-players", self.srv_data.serverpath)
        if banlist is not False:  # file and directory exist.
            if banlist is None:  # file was empty or not valid
                return "No bans have ever been recorded..?"
            banrecord = find_in_json(banlist, "name", str(username))
            if banrecord:
                for x in banlist:
                    if x == banrecord:
                        banlist.remove(x)
                if putjsonfile(banlist, "banned-players", self.srv_data.serverpath):
                    return "pardoned %s" % username
                return "Could not write banlist to disk"
            else:
                return "That person was never banned"  # error text
        else:
            return "Banlist not found on disk"  # error text

    def isuuidbanned(self, uuid):  # Check if the UUID of the user is banned
        banlist = getjsonfile("banned-players", self.srv_data.serverpath)
        if banlist:  # make sure banlist exists
            banrecord = find_in_json(banlist, "uuid", str(uuid))
            if banrecord:
                # if ban has expired
                if read_timestr(banrecord["expires"]) < int(time.time()):
                    pardoning = self.pardonuuid(str(uuid))
                    if pardoning[:8] == "pardoned":
                        self.log.info("UUID: %s was pardoned "
                                      "(expired ban)", str(uuid))
                        return False  # player is "NOT" banned (anymore)
                    else:
                        self.log.warning("isuuidbanned attempted a pardon of"
                                         " uuid: %s (expired ban), "
                                         "but it failed:\n %s",
                                         uuid, pardoning)
                return True  # player is still banned
        return False  # banlist empty or record not found

    def isipbanned(self, ipaddress):  # Check if the IP address is banned
        banlist = getjsonfile("banned-ips", self.srv_data.serverpath)
        if banlist:  # make sure banlist exists
            for record in banlist:
                _ip = record["ip"]
                if _ip in ipaddress:
                    _expires = read_timestr(record["expires"])
                    if _expires < int(time.time()):  # if ban has expired
                        pardoning = self.pardonip(ipaddress)
                        if pardoning[:8] == "pardoned":
                            self.log.info("IP: %s was pardoned "
                                          "(expired ban)", ipaddress)
                            return False  # IP is "NOT" banned (anymore)
                        else:
                            self.log.warning("isipbanned attempted a pardon "
                                             "of IP: %s (expired ban),  but"
                                             " it failed:\n %s",
                                             ipaddress, pardoning)
                    return True  # IP is still banned
        return False  # banlist empty or record not found

    def getskintexture(self, uuid):
        """
        Args:
            uuid: uuid (accept MCUUID or string)
        Returns:
            skin texture (False if request fails)
        """
        if "MCUUID" in str(type(uuid)):
            uuid = uuid.string

        if uuid not in self.skins:
            return False

        if uuid in self.skinTextures:
            return self.skinTextures[uuid]
        skinblob = json.loads(self.skins[uuid].decode("base64"))
        # Player has no skin, so set to Alex [fix from #160]
        if "SKIN" not in skinblob["textures"]:
            skinblob["textures"]["SKIN"] = {
                "url": "http://hydra-media.cursecdn.com/mine"
                       "craft.gamepedia.com/f/f2/Alex_skin.png"
            }
        r = requests.get(skinblob["textures"]["SKIN"]["url"])
        if r.status_code == 200:
            self.skinTextures[uuid] = r.content.encode("base64")
            return self.skinTextures[uuid]
        else:
            self.log.warning("Could not fetch skin texture! "
                             "(status code %d)", r.status_code)
            return False
