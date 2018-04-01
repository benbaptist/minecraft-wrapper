# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.
from __future__ import absolute_import

import base64
import socket
import threading
import time
import json
import requests

# imports that are still dependent upon wrapper:
from api.helpers import getjsonfile, putjsonfile, find_in_json
from api.helpers import epoch_to_timestr, read_timestr
from api.helpers import isipv4address
from utils.py23 import py_str
from proxy.utils.constants import *

from proxy.utils import mcuuid
from proxy.entity.entitycontrol import EntityControl

# encryption requires 'cryptography' package.
try:
    import proxy.utils.encryption as encryption
except ImportError:
    encryption = False

# for reading skins out of our Wrapper.py:
try:
    import pkg_resources
except ImportError:
    pkg_resources = False

try:
    from proxy.client.clientconnection import Client
    from proxy.packets.packet import Packet

except ImportError:
    Client = False
    Packet = False

""" The whole point of what follows was originally intended to 
support making proxy an independent thing that does not need 
a wrapper or server instance to function.  Not sure it was a 
great idea, but... We shall see."""


class NullEventHandler(object):
    def __init__(self):
        pass

    def callevent(self, event, payload):
        """
        An event handler must have this method that expects
        two positional arguments:
         :event: The string name of the event.
         :payload: A dictionary of items describing the event (varies 
          with event.
        """
        pass


class HaltSig(object):
    """
    HaltSig is simply a sort of dummy class created for the
    proxy.  proxy expects this object with a self.halt property
    that tells proxy to shutdown.  The caller maintains control
    of the Haltsig object and uses it to signal the proxy to 
    shut down.  The caller will import this class, instantiate 
    it, and then pass the object to proxy as the argument for
    termsignal."""
    def __init__(self):
        self.halt = False


class ProxyConfig(object):
    def __init__(self):
        self.proxy = {
            "auto-name-changes": True,
            "hidden-ops": [],
            "max-players": 1024,
            "online-mode": True,
            "proxy-bind": "0.0.0.0",
            "proxy-enabled": True,
            "proxy-port": 25570,
            "silent-ipban": True,
        }
        self.entity = {
            "enable-entity-controls": False,
            "entity-update-frequency": 4,
            "thin-chicken": 30,
            "thin-cow": 40,
            "thin-sheep": 40,
            "thin-zombie_pigman": 200,
            "thinning-activation-threshhold": 100,
            "thinning-frequency": 30
          }


"""
class ServerVitals(object):
    def __init__(self, playerobjects):
        self.serverpath = ""
        self.state = 0
        self.server_port = "25564"
        self.command_prefix = "/"
        self.players = playerobjects
        self.entity_control = None
        self.timeofday = -1
        self.spammy_stuff = ["found nothing", "vehicle of", "Wrong location!",
                             "Tried to add entity", ]
        self.clients = []
        self.ownernames = {}
        self.operator_list = []
        self.properties = {}
        self.worldname = None
        self.worldsize = 0
        self.maxplayers = 20
        self.motd = None
        self.serverIcon = None
        self.protocolVersion = -1
        self.version = ""
        self.version_compute = 0
"""


class Proxy(object):
    def __init__(self, termsignal, config, servervitals, loginstance,
                 usercache_object, eventhandler, encoding="utf-8"):

        self.encoding = encoding
        self.srv_data = servervitals
        self.config = config.proxy
        self.ent_config = config.entity

        self.log = loginstance
        # encryption = False if proxy.utils.encryption does not import
        if not encryption and self.config["proxy-enabled"]:
            self.log.error("You must have the package 'cryptography' "
                           "installed to run the Proxy!")
            raise ImportError()
        if not pkg_resources:
            self.log.error("You must have the package `pkg_resources` "
                           "installed to run the Proxy!  It is usually "
                           "distributed with setuptools. Check https://stackov"
                           "erflow.com/questions/7446187/no-module-named-pkg-r"
                           "esources for possible solutions")
            raise ImportError()

        self.usercache = usercache_object.Data
        self.usercache_obj = usercache_object
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
        self.srv_data.maxPlayers = self.config["max-players"]
        self.proxy_worlds = self.config["worlds"]
        self.usehub = self.config["built-in-hub"]
        self.onlinemode = self.config["online-mode"]

        # proxy internal workings
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.usingSocket = False

        self.skins = {}
        self.skinTextures = {}
        self.uuidTranslate = {}
        # define the slot once here and not at each clients Instantiation:
        self.inv_slots = list(range(46))
        self.entity_control = None

        # various contructions for non-standard
        # client/servers (forge?)
        self.mod_info = {}
        self.forge = False
        self.forge_login_packet = None

        # Channels monitored by wrapper.  We don't register our channels
        # because they are only used between wrapper instances.  Minecraft
        # servers and clients will ignore them.
        self.registered_channels = ["MC|Brand",
                                    "WRAPPER.PY|PONG",
                                    "WRAPPER.PY|PING",
                                    "WRAPPER.PY|RESP",
                                    "WRAPPER.PY|INFO"]

        # Encryption keys
        self.private_key = encryption.generate_private_key_set()
        self.public_key = encryption.get_public_key_bytes(self.private_key)

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
                # 0: done receiving, 1: done sending, 2: both
                sock.shutdown(2)
                self.log.info("Someone tried to connect from a banned ip:"
                              " %s  (connection refused)", addr)
                continue

            # spur off client thread
            # self.server_temp = ServerConnection(self, ip, port)
            client = Client(self, sock, addr, banned=banned_ip)
            t = threading.Thread(target=client.handle, args=())
            t.daemon = True
            t.start()

        # received self.abort or caller.halt signal...
        self.entity_control._abortep = True

    def removestaleclients(self):
        """removes aborted client and player objects"""
        for i, client in enumerate(self.srv_data.clients):
            if self.srv_data.clients[i].abort:
                if self.srv_data.clients[i].username in self.srv_data.players:
                    del self.srv_data.players[self.srv_data.clients[i].username]
                self.srv_data.clients.pop(i)

    def pollserver(self, host="localhost", port=None):
        if port is None:
            port = self.srv_data.server_port

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # server_sock = socket.socket()
        server_sock.connect((host, port))
        packet = Packet(server_sock, self)

        packet.sendpkt(
            # 340 is protocol and 1 means "Next State = status"
            0x00, [VARINT, STRING, USHORT, VARINT], (340, host, port, STATUS))
        # Disconnect
        packet.sendpkt(0x00, [NULL, ], ["", ])
        packet.flush()
        self.srv_data.protocolVersion = -1
        while True:
            pkid, packet_tuple = packet.grabpacket()
            if pkid == 0x00:
                data = json.loads(packet.readpkt([STRING, ])[0])
                self.srv_data.protocolVersion = data["version"][
                    "protocol"]
                self.srv_data.version = data["version"]["name"]
                if "modinfo" in data and data["modinfo"]["type"] == "FML":
                    self.forge = True
                    self.mod_info["modinfo"] = data["modinfo"]

                break
        server_sock.close()

    def run_command(self, command):
        """
        Runs a command on the wrapped server.

        :param minecraft server command:
        :return:
        """
        self.eventhandler.callevent(
            "proxy.console", {"command": command},
            abortable=False
        )

        """ eventdoc
    
        <description> internalfunction <description>
    
        """

    def use_newname(self, oldname, newname, realuuid: str, client):
        """
        Convert a player from old to new name.
        :param oldname: The players old name
        :param newname: The player's new name
        :param realuuid: The actual string UUID used by wrapper's cache (mojang)

        :returns: A tuple of the (new string name, string uuid)
        """
        old_local_uuid = self.uuids.getuuidfromname(oldname)
        new_local_uuid = self.uuids.getuuidfromname(newname)
        cwd = "%s/%s" % (
            self.srv_data.serverpath, self.srv_data.worldname)
        self.uuids.convert_files(old_local_uuid, new_local_uuid, cwd)
        self.usercache[realuuid]["localname"] = newname
        client.info["username"] = newname
        client.username = newname
        self.usercache_obj.save()
        return new_local_uuid

    def getclientbyofflineserveruuid(self, uuid):
        """
        :param uuid: - MCUUID
        :return: the matching client
        """
        attempts = ["Search: %s" % str(uuid)]
        for client in self.srv_data.clients:
            attempts.append("try: client-%s uuid-%s serveruuid-%s name-%s" %
                            (client, client.wrapper_uuid.string,
                             client.local_uuid.string, client.username))
            if client.local_uuid.string == str(uuid):
                self.uuidTranslate[uuid] = client.wrapper_uuid.string
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
                if putjsonfile(banlist,
                               "banned-players",
                               self.srv_data.serverpath):
                    # this actually is not needed. Commands now handle the kick.
                    console_command = "kick %s %s" % (name, reason)
                    self.run_command(console_command)

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
                if putjsonfile(banlist,
                               "banned-players",
                               self.srv_data.serverpath):
                    self.log.info("kicking %s... %s", username, reason)

                    console_command = "kick %s Banned: %s" % (username, reason)
                    self.run_command(console_command)

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

                            console_command = "kick %s Your IP is Banned!" % client.username  # noqa
                            self.run_command(console_command)

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
                if putjsonfile(banlist,
                               "banned-players",
                               self.srv_data.serverpath):
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
                if putjsonfile(banlist,
                               "banned-players",
                               self.srv_data.serverpath):
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
        import pprint
        """
        Args:
            uuid: uuid (accept MCUUID or string)
        Returns:
            skin texture (False if request fails)
        """
        if "MCUUID" in str(type(uuid)):
            uuid = uuid.string

        pprint.pprint(self.skins)
        pprint.pprint(self.skinTextures)
        if uuid not in self.skins:
            return False

        if uuid in self.skinTextures:
            return py_str(self.skinTextures[uuid], self.encoding)

        textual = base64.b64decode(self.skins[uuid]).decode("utf-8", "ignore")
        skinblob = json.loads(textual)

        # Player has no skin, so set to Alex [fix from #160]
        if "SKIN" not in skinblob["textures"]:
            skin = pkg_resources.resource_stream(
                __name__, "./utils/skin.png"
            ).read()
            pprint.pprint(skin)
            skinblob["textures"]["SKIN"] = {
                "url": "http://hydra-media.cursecdn.com/mine"
                       "craft.gamepedia.com/f/f2/Alex_skin.png"
            }
        r = requests.get(skinblob["textures"]["SKIN"]["url"])
        if r.status_code == 200:
            self.skinTextures[uuid] = base64.b64encode(r.content)
            return py_str(self.skinTextures[uuid], self.encoding)
        else:
            self.log.warning("Could not fetch skin texture! "
                             "(status code %d)", r.status_code)
            return False
