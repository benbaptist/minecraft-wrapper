# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import time
import threading
import pprint

from proxy.packets.mcpackets_cb import Packets as Packets_cb
from proxy.packets.mcpackets_sb import Packets as Packets_sb

from proxy.utils.constants import *
from core.storage import Storage
from api.helpers import processoldcolorcodes


# region Constants
# ------------------------------------------------

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


# noinspection PyPep8Naming
class Player(object):
    """
    .. code:: python

        def __init__(self, username, wrapper)

    ..

    This class is normally passed as an argument to an event
    callback, but can be also be called using getPlayer(username):

    .. code:: python

        player = self.api.getPlayer(<username>)

    ..

    Player objects contains methods and data of a currently
    logged-in player. Most features are tied heavily to
    proxy mode implementations and the proxy client instance.
    Player creation happens at one of two points:
     1) Proxy - at the player.preLogin event when the client first joins
     the wrapper proxy.  It is created by core.events.py in response to
     player.pre-Login's missing player argument.
     2) Non-proxy - Created at the player.login event when they join the
     local server.

    The player object has a self.__str___ representation that returns the
    player.username.  Therefore, plugins do not need to attempt string
    conversion or do explicit references to player.username in their code
    (str(player) or player.username in plugin code). There is also an
    additional property for getting the username: `name`

    When using events, events in the "proxy" (Group 'Proxy') section are only
    available in proxy mode.  "server" events (Group 'core/mcserver.py')
    are available even without proxy mode, as long as the server is running.


    Supported properties of the player:
    
    .. code:: python

        self.username  # client username on this server.
        self.loggedIn  # time the player object logged on.

        self.name  # property that returns the username
        self.uuid  # property that returns the very best UUID available.
        # self.uuid polls for the first UUID it finds in the list below.
        # self.uuid is also the only uuid that is a string type

        # These UUIDs are a MCUUID object.  Warning: they will not json
        #  serialize unless you convert them to a string!
        # To specifically get a certain uuid:
        self.mojangUuid
        self.clientUuid  # usually = self.mojangUuid (proxy mode only)
        self.offlineUuid
        self.serverUuid  # usually = self.offlineUuid in proxy mode.

        # These are available to non-proxy mode wrappers:
        self.loginposition
        self.playereid
        self.ipaddress

        # proxy only
        #-----------
        # player.client is the player client instance.  See the
        #  mincraft.api for getting packet constants for use with
        self.client
        self.clientUuid
        self.clientgameversion
        self.clientboundPackets = Packets_cb(self.clientgameversion)
        self.serverboundPackets = Packets_sb(self.clientgameversion)

        # some player properties associated with abilities (proxy)
        # default is 1.  Should normally be congruent with speed.
        self.field_of_view = float(1)
        # Client set godmode is 0x01
        self.godmode = 0x00
        # Client set creative is 0x08
        self.creative = 0x00
        # default is 1
        self.fly_speed = float(1)

    ..

    """

    def __init__(self, username, wrapper):
        """
        :UUIDS:
            All uuids are wrapper's MCUUID objects.  If being used in a string
            context, they must be used with the *.string property (or str()
            explicitly):
                player.mojangUuid.string
                player.mojangUuis.__str__
                str(player.mojangUuid)

            The only exception to this is the `uuid` property, which is always
             a string.

            :uuid (property, string): This will pull the best uuid
             available in this order-
            :1) mojangUuid: The bought and paid Mojand UUID.  Never changes and
             is the prefered way to ID player keys.
            :2) offlineUuid: A MD5 hash of "OfflinePlayer:%s" % username
            :3) clientUuid: What the client believes is the uuid.  If
             Wrapper is online, this should be the same as mojangUuid.
            :4) serverUuid: The player's local uuid on the server,
             usually the same as offline uuid.

        :param username:
        :param wrapper:
        """

        self.wrapper = wrapper
        self.javaserver = wrapper.javaserver
        self.log = wrapper.log
        self.username = username
        self.loggedIn = time.time()

        # mcserver will set this to false later to close the thread.
        self.abort = False
        self.data = None
        # meanwhile, it still needs to respect wrapper halts
        self.wrapper_signal = self.wrapper.halt
        self.kick_nonproxy_connects = self.wrapper.config["Proxy"][
            "disconnect-nonproxy-connections"]

        self.mojangUuid = False
        self.clientUuid = False
        # These two are offline by default.
        self.offlineUuid = self.wrapper.uuids.getuuidfromname(self.username)
        self.serverUuid = self.offlineUuid

        self.ipaddress = "127.0.0.0"
        self.loginposition = [0, 0, 0]
        self._position = [0, 0, 0, 0, 0]  # internally used for non-proxy mode

        self.client = None
        self.clientgameversion = self.wrapper.servervitals.protocolVersion
        self.cbpkt = Packets_cb(self.clientgameversion)
        self.sbpkt = Packets_sb(self.clientgameversion)

        self.playereid = None

        # some player properties associated with abilities
        #
        # default is 1.  Should normally be congruent with speed.
        self.field_of_view = float(1)
        # Client set godmode is 0x01
        self.godmode = 0x00
        # Client set creative is 0x08
        self.creative = 0x00
        # default is 1
        self.fly_speed = float(1)

        if self.wrapper.proxy:
            gotclient = False
            for client in self.wrapper.servervitals.clients:
                if client.username == self.username:
                    self.client = client
                    self.clientUuid = client.wrapper_uuid
                    self.serverUuid = client.local_uuid
                    self.mojangUuid = client.mojanguuid
                    self.ipaddress = client.ip

                    # pktSB already set to self.wrapper.servervitals.protocolVersion  # noqa
                    self.clientboundPackets = self.client.pktCB
                    self.clientgameversion = self.client.clientversion
                    gotclient = True
                    break
            if not gotclient:
                pprint.pprint(self.wrapper.servervitals.clients)
                self.log.error("Proxy is on, but this client is not "
                               "listed in proxy.clients!")
                self.log.error("The usual cause of this would be that"
                               " someone attempted to connect directly to"
                               " your server port and not the wrapper"
                               " proxy port, but can also be the result of"
                               " a player that has abruptly disconnected.")
                if self.kick_nonproxy_connects:
                    port = self.wrapper.proxy.proxy_port
                    self.log.info("API.player Kicked %s" % self.name)
                    self.abort = True
                    self.wrapper.javaserver.console(
                        "kick %s %s" % (
                            self.name,
                            "Access Denied!  Use port %s instead!" % port
                        )
                    )

                    return
        if not self.mojangUuid:
            # poll cache/mojang for proper uuid
            self.mojangUuid = self.wrapper.uuids.getuuidbyusername(username)

        # Process login data
        self.data = Storage(
            self.mojangUuid.string, root="wrapper-data/players")
        if "firstLoggedIn" not in self.data.Data:
            self.data.Data["firstLoggedIn"] = (time.time(), time.tzname)
        if "logins" not in self.data.Data:
            self.data.Data["logins"] = {}
        self.data.Data["lastLoggedIn"] = (self.loggedIn, time.tzname)
        self.data.save()

        # start player logged in time tracking thread
        t = threading.Thread(target=self._track, args=())
        t.daemon = True
        t.start()

    def __str__(self):
        return self.username

    def __del__(self):
        if self.data:
            self.data.close()

    @property
    def name(self):
        return self.username

    @property
    def uuid(self):
        """
        @property
        Return the very best UUID available as a string, with
        the goal of never returning improper things like False and None.
        """
        if self.mojangUuid:
            return self.mojangUuid.string
        if self.client and self.client.info["realuuid"] != "":
            return self.client.info["realuuid"]
        if self.clientUuid:
            return self.clientUuid.string
        if self.serverUuid:
            return self.serverUuid.string
        return self.offlineUuid.string

    def _track(self):
        """
        internal tracking that updates a player's server play time.
        Not a part of the public player object API.
        """
        self.data.Data["logins"][int(self.loggedIn)] = time.time()
        while not (self.abort or self.wrapper_signal.halt):
            timeupdate = time.time()
            if timeupdate % 60:  # Just update every 60 seconds
                self.data.Data["logins"][int(self.loggedIn)] = int(time.time())
            # this needs a fast response to ensure the storage closes 
            # immediately on player logoff
            time.sleep(.5)
        self.data.close()

    def kick(self, reason):
        """
        Kick a player with 'reason'.  Using this interface (versus the
        console command) ensures the player receives the proper disconnect
        messages based on whether they are in proxy mode or not.  This will
        also allow hub players to respawn in the main wrapper server.

        """
        self.wrapper.javaserver.kick_player(self, self.username, reason)

    def execute(self, string):
        """
        Run a command as this player. If proxy mode is not enabled,
        it simply falls back to using the 1.8 'execute' command. To 
        be clear, this does NOT work with any Wrapper.py or plugin 
        commands.  The command does not pass through the wrapper.  
        It is only sent to the server console (or the actual server in
        proxy mode).

        :arg string: full command string send on player's behalf to server.

        :returns: Nothing; passes the server or the console as an
         "execute" command.

        """
        if string[0] in (self.wrapper.servervitals.command_prefix, "/"):
            string = string[1:]
        try:
            self.client.chat_to_server("/%s" % string)
        except AttributeError:
            if self.wrapper.servervitals.protocolVersion > PROTOCOL_1_7_9:
                self.wrapper.javaserver.console(
                    "execute %s ~ ~ ~ %s" % (self.username, string))
            else:
                self.log.warning("could not run player.execute - wrapper not"
                                 " in proxy mode and minecraft version is less"
                                 " than 1.8 (when /execute was implemented).")

    def sendCommand(self, command, args):
        """
        Sends a command to the wrapper interface as the player instance.
        This would find a nice application with a '\sudo' plugin command.

        :sample usage:

            .. code:: python

                player=getPlayer("username")
                player.sendCommand("perms", ("users", "SurestTexas00", "info"))

            ..

        :Args:
            :command: The wrapper (or plugin) command to execute; no
             slash prefix
            :args: tuple/list of arguments.

        :returns: Nothing; passes command through commands.py function
         'playercommand()'.  The player will receive any player.message()
         the command generates, if any.  Console commands in particular
         may only show their output at the console.

        """
        pay = {"player": self, "command": command, "args": args}
        self.wrapper.api.callEvent("player.runCommand", pay, abortable=False)

    def say(self, string):
        """
        Send a message as a player.

        :arg string: message/command sent to the server as the player.

        Beware: *in proxy mode, the message string is sent directly to*
        *the server without wrapper filtering,so it could be used to*
        *execute minecraft commands as the player if the string is*
        *prefixed with a slash (assuming the player has the permission).*

        """
        try:
            self.client.chat_to_server(string)
        except AttributeError:
            # pre-1.8
            self.wrapper.javaserver.console(
                "say @a <%s> %s" % (self.username, string))

    def getClient(self):
        """
        Deprecated - use `player.client` to Access the proxy client...

        Returns the player client context. Retained for older plugins
        which still use it.

        TODO - Deprecate by wrapper version 1.5 final.

        :returns: player client object.

        """
        if self.client is None:
            for client in self.wrapper.servervitals.clients:
                if client.username == self.username:
                    self.client = client
                    return client
            self.log.warning("getClient could not return a client for:%s"
                             " \nThe usual cause of this condition"
                             " is that no client instance exists because"
                             " proxy is not enabled.", self.username)
            return None
        else:
            return self.client

    def getPosition(self):
        """
        Get the players position
        
        :Proxymode Note:  The player's position is obtained by parsing client
         packets, which are not sent until the client logs in to 
         the server.  Allow some time after server login to verify 
         the wrapper has had the oppportunity to parse a suitable 
         packet to get the information!

        :Non-proxymode note: will still work, but the returned position will
         be either the player's login position or where he last teleported
         to...
        
        :returns: a tuple of the player's current position x, y, z, 
         and yaw, pitch of head.
        
        """
        if self.wrapper.proxy:
            return self.client.position + self.client.head
        else:
            # Non-proxy mode:
            return self._position

    def getGamemode(self):
        """
        Get the player's current gamemode.
        
        :Proxymode Note:  The player's Gamemode is obtained by parsing client
         packets, which are not sent until the client logs in to 
         the server.  Allow some time after server login to verify 
         the wrapper has had the oppportunity to parse a suitable 
         packet to get the information!
         
        :returns:  An Integer of the the player's current gamemode.

        """
        try:
            return self.client.gamemode
        except AttributeError:
            # Non-proxy mode:
            return 0

    def getDimension(self):
        """
        Get the player's current dimension.

        :Proxymode Note:  The player's Dimension is obtained by parsing client
         packets, which are not sent until the client logs in to 
         the server.  Allow some time after server login to verify 
         the wrapper has had the oppportunity to parse a suitable 
         packet to get the information!
         
         :returns: the player's current dimension.

             :Nether: -1
             :Overworld: 0
             :End: 1

        """
        try:
            return self.client.dimension
        except AttributeError:
            # Non-proxy mode:
            return 0

    def setGamemode(self, gamemode=0):
        """
        Sets the user's gamemode.

        :arg gamemode: desired gamemode, as a value 0-3

        """
        if gamemode in (0, 1, 2, 3):
            try:
                self.client.gamemode = gamemode
            except AttributeError:
                # Non-proxy mode:
                pass
            self.wrapper.javaserver.console(
                "gamemode %d %s" % (gamemode, self.username))

    def setResourcePack(self, url, hashrp=""):
        """
        :Proxymode: Sets the player's resource pack to a different URL. If the
         user hasn't already allowed resource packs, the user will
         be prompted to change to the specified resource pack.
         Probably broken right now.

        :Args:
            :url: URL of resource pack
            :hashrp: resource pack hash
        :return: False if not in proxy mode.
        
        """
        try:
            version = self.wrapper.proxy.srv_data.protocolVersion
        except AttributeError:
            # Non proxy mode
            return False
        if version < PROTOCOL_1_8START:
            self.client.packet.sendpkt(
                self.clientboundPackets.PLUGIN_MESSAGE[PKT],
                [_STRING, _BYTEARRAY],
                ("MC|RPack", url))
        else:
            self.client.packet.sendpkt(
                self.clientboundPackets.RESOURCE_PACK_SEND[PKT],
                [_STRING, _STRING],
                (url, hashrp))

    def isOp(self, strict=False):
        """
        Check if player has Operator status. Accepts player as OP
        based on either the username OR server UUID (unless 'strict'
        is set).

        Note: *If a player has been opped since the last server start,*
        *make sure that you run refreshOpsList() to ensure that*
        *wrapper will acknowlege them as OP.*

        :arg strict: True - use ONLY the UUID as verification

        :returns:  A 1-10 (or more?) op level if the player is currently
         a server operator.

        Can be treated, as before, like a
        boolean - 'if player.isOp():', but now also adds ability
        to granularize with the OP level.  Levels above 4 are
        reserved for wrapper.  10 indicates owner. 5-9 are
        reserved for future minecraft or wrapper levels.  pre-1.8
        servers return 1.  levels above 4 are based on name only
        from the file "superops.txt" in the wrapper folder.
        To assign levels, change the lines of <PlayerName>=<oplevel>
        to your desired names.  Player must be an actual OP before
        the superops.txt will have any effect.  Op level of 10 is
        be required to operate permissions commands.

        """

        if self.wrapper.servervitals.operator_list in (False, None):
            return False  # no ops in file
        # each op item is a dictionary
        for ops in self.wrapper.servervitals.operator_list:
            if ops["uuid"] == self.serverUuid.string:
                return ops["level"]
            if ops["name"] == self.username and not strict:
                return ops["level"]
        return False

    def message(self, message="", position=0):
        """
        Sends a message to the player.

        :Args:
            :message: Can be text, colorcoded text, or chat dictionary of json.
            :position:  an integer 0-2.  2 will place it above XP bar.
             1 or 0 will place it in the chat. Using position 2 will
             only display any text component (or can be used to display
             standard minecraft translates, such as
             "{'translate': 'commands.generic.notFound', 'color': 'red'}" and
             "{'translate': 'tile.bed.noSleep'}")


        :returns: Nothing


        """

        if self.wrapper.proxy:
            if isinstance(message, dict):
                sentitem = message
            else:
                sentitem = processoldcolorcodes(message)

            self.client.chat_to_client(sentitem, position)
        else:
            self.javaserver.broadcast(message, who=self.username)

    def setVisualXP(self, progress, level, total):
        """
        :Proxymode: Change the XP bar on the client's side only. Does not
         affect actual XP levels.

        :Args:
            :progress:  Float between Between 0 and 1
            :level:  Integer (short in older versions) of EXP level
            :total: Total EXP.

        :returns: Nothing

        """
        try:
            version = self.wrapper.proxy.srv_data.protocolVersion
        except AttributeError:
            # Non proxy mode
            return False

        if version > PROTOCOL_1_8START:
            parsing = [_FLOAT, _VARINT, _VARINT]
        else:
            parsing = [_FLOAT, _SHORT, _SHORT]

        self.client.packet.sendpkt(
            self.clientboundPackets.SET_EXPERIENCE[PKT],
            parsing,
            (progress, level, total))

    def openWindow(self, windowtype, title, slots):
        """
        :Proxymode: Opens an inventory window on the client side.  EntityHorse
         is not supported due to further EID requirement.  *1.8*
         *experimental only.*

        :Args:
            :windowtype:  Window Type (text string). See below
             or applicable wiki entry (for version specific info)
            :title: Window title - wiki says chat object (could
             be string too?)
            :slots:

        :returns: None (False if client is less than 1.8 version)


        Valid window names (1.9)

        :minecraft\:chest: Chest, large chest, or minecart with chest

        :minecraft\:crafting_table: Crafting table

        :minecraft\:furnace: Furnace

        :minecraft\:dispenser: Dispenser

        :minecraft\:enchanting_table: Enchantment table

        :minecraft\:brewing_stand: Brewing stand

        :minecraft\:villager: Villager

        :minecraft\:beacon: Beacon

        :minecraft\:anvil: Anvil

        :minecraft\:hopper: Hopper or minecart with hopper

        :minecraft\:dropper: Dropper

        :EntityHorse: Horse, donkey, or mule

        """
        try:
            version = self.wrapper.proxy.srv_data.protocolVersion
        except AttributeError:
            # Non proxy mode
            return False
        client = self.client
        client.windowCounter += 1
        if client.windowCounter > 200:
            client.windowCounter = 2

        # TODO Test what kind of field title is (json or text)

        if not version > PROTOCOL_1_8START:
            return False

        client.packet.sendpkt(
            self.clientboundPackets.OPEN_WINDOW[PKT],
            [_UBYTE, _STRING, _JSON, _UBYTE],
            (client.windowCounter, windowtype, {"text": title},
             slots))

        return None  # return a Window object soon

    def setPlayerAbilities(self, fly):
        """
        :Proxymode: *based on old playerSetFly (which was an unfinished
         function)*

        NOTE - You are implementing these abilities on the client
         side only.. if the player is in survival mode, the server
         may think the client is hacking!

        this will set 'is flying' and 'can fly' to true for the player.
        these flags/settings will be set according to the players
        properties, which you can set just prior to calling this
        method:

            :getPlayer().godmode:  Hex or integer (see chart below)

            :getPlayer().creative: Hex or integer (see chart below)

            :getPlayer().field_of_view: Float - default is 1.0

            :getPlayer().fly_speed: Float - default is 1.0

        :arg fly: Boolean

            :True: set fly mode.
            :False: to unset fly mode

        :Bitflags used (for all versions): These can be added to
         produce combination effects.   This function sets
         0x02 and 0x04 together (0x06).

            :Invulnerable: 0x01
            :Flying: 0x02
            :Allow Flying: 0x04
            :Creative Mode: 0x08

        :returns: Nothing

        """
        try:
            sendclient = self.client.packet.sendpkt
            sendserver = self.client.server.packet.sendpkt
        except AttributeError:
            # Non proxy mode
            return False

        # TODO later add and keep track of godmode and creative- code
        # will currently unset them.

        if fly:
            setfly = 0x06  # for set fly
        else:
            setfly = 0x00

        bitfield = self.godmode | self.creative | setfly

        # Note in versions before 1.8, field of view is the
        # walking speed for client (still a float) Server
        # field of view is still walking speed
        sendclient(self.clientboundPackets.PLAYER_ABILITIES[PKT],
                   [_BYTE, _FLOAT, _FLOAT],
                   (bitfield, self.fly_speed, self.field_of_view))

        sendserver(self.sbpkt.PLAYER_ABILITIES[PKT],
                   [_BYTE, _FLOAT, _FLOAT],
                   (bitfield, self.fly_speed, self.field_of_view))

    def sendBlock(self, position, blockid, blockdata, sendblock=True,
                  numparticles=1, partdata=1):
        """
        :Proxymode: Used to make phantom blocks visible ONLY to the client.
         Sends either a particle or a block to the minecraft player's client.
         For blocks iddata is just block id - No need to bitwise the
         blockdata; just pass the additional block data.  The particle
         sender is only a basic version and is not intended to do
         anything more than send something like a barrier particle to
         temporarily highlight something for the player.  Fancy particle
         operations should be custom done by the plugin or someone can
         write a nicer particle-renderer.

        :Args:

            :position: players position as tuple.  The coordinates must
             be in the player's render distance or the block will appear
             at odd places.

            :blockid: usually block id, but could be particle id too.  If
             sending pre-1.8 particles this is a string not a number...
             the valid values are found here

            :blockdata: additional block meta (a number specifying a subtype).

            :sendblock: True for sending a block.

            :numparticles: if particles, their numeric count.

            :partdata: if particles; particle data.  Particles with
             additional ID cannot be used ("Ironcrack").

        :Valid 'blockid' values:
         http://wayback.archive.org/web/20151023030926/https://gist.github.com/thinkofdeath/5110835

        """
        try:
            sendclient = self.client.packet.sendpkt
        except AttributeError:
            # Non proxy
            return False

        posx = position
        x = (position[0])
        y = (position[1])
        z = (position[2])
        if self.clientgameversion > PROTOCOL_1_7_9:
            # 1.8 +
            iddata = blockid << 4 | blockdata

            # [1.8pos/1.7x | 1.7y | 1.7z | 1.7BlockID/1.8iddata | 1.7blockdata]
            # these are whitespaced this way to line up visually
            blockparser = [_POSITION, _NULL, _NULL, _VARINT,  _NULL]

            particleparser = [_INT,    _BOOL, _FLOAT, _FLOAT, _FLOAT, _FLOAT,
                              _FLOAT, _FLOAT, _FLOAT, _INT]
        else:
            # 1.7
            posx = x
            iddata = blockid

            blockparser = [_INT,      _UBYTE, _INT, _VARINT, _UBYTE]

            particleparser = [_STRING, _NULL, _FLOAT, _FLOAT, _FLOAT, _FLOAT,
                              _FLOAT, _FLOAT, _FLOAT, _INT]

        if sendblock:
            sendclient(self.clientboundPackets.BLOCK_CHANGE[PKT],
                       blockparser,
                       (posx, y, x, iddata, blockdata))
        else:
            sendclient(self.clientboundPackets.PARTICLE[PKT],
                       particleparser,
                       (blockid, True, x + .5, y + .5, z + .5, 0, 0, 0,
                        partdata, numparticles))

    # Inventory-related actions.
    def getItemInSlot(self, slot):
        """
        :Proxymode: Returns the item object of an item currently being held.

        """
        try:
            return self.client.inventory[slot]
        except AttributeError:
            # Non proxy
            return False

    def getHeldItem(self):
        """
        Returns the item object of an item currently being held.

        """
        try:
            return self.client.inventory[36 + self.client.slot]
        except AttributeError:
            # Non proxy
            return False

    # Permissions-related
    def hasPermission(self, node, another_player=False, group_match=True, find_child_groups=True):  # noqa
        """
        If the player has the specified permission node (either
        directly, or inherited from a group that the player is in),
        it will return the value (usually True) of the node.
        Otherwise, it returns False.  Using group_match and
        find_child_groups are enabled by default.  Permissions
        can be sped up by disabling child inheritance or even
        group matching entirely (for high speed loops, for
        instance).  Normally, permissions are related to
        commands the player typed, so the 'cost' of child
        inheritance is not a concern.

        :Args:
            :node: Permission node (string)
            :another_player: sending a string name of another player
             will check THAT PLAYER's permission instead! Useful for
             checking a player's permission for someone who is not
             logged in and has no player object.
            :group_match: return a permission for any group the player
             is a member of.  If False, will only return permissions
             player has directly.
            :find_child_groups: If group matching, this will
             additionally locate matches when a group contains
             a permission that is another group's name.  So if group
             'admin' contains a permission called 'moderator', anyone
             with group admin will also have group moderator's
             permissions as well.

        :returns:  Boolean indicating whether player has permission or not.

        """
        uuid_to_check = self.uuid
        if another_player:
            # get other player mojang uuid
            uuid_to_check = str(
                self.wrapper.uuids.getuuidbyusername(another_player))
            if not uuid_to_check:
                # probably a bad name provided.. No further check needed.
                return False

        return self.wrapper.perms.has_permission(
            uuid_to_check, node, group_match, find_child_groups)

    def setPermission(self, node, value=True, uuid=None):
        """
        Adds the specified permission node and optionally a value
        to the player.

        :Args:
            :node: Permission node (string)
            :value: defaults to True, but can be set to False to
             explicitly revoke a particular permission from the
             player, or to any arbitrary value.
            :uuid: Optional MCUUID/string UUID of a (different) player.

        :returns: Nothing

        """
        try:
            uuid = uuid.string
        except AttributeError:
            pass

        if uuid:
            self.wrapper.perms.set_permission(uuid, node, value)
        else:
            self.wrapper.perms.set_permission(self.uuid, node, value)

    def removePermission(self, node, uuid=None):
        """
        Completely removes a permission node from the player. They
        will inherit this permission from their groups or from
        plugin defaults.

        If the player does not have the specific permission, an
        IndexError is raised. Note that this method has no effect
        on nodes inherited from groups or plugin defaults.

        :arg node: Permission node (string)
        :arg uuid: Optional MCUUID/string UUID of a (different) player.

        :returns:  Boolean; True if operation succeeds, False if
         it fails (set debug mode to see/log error).

        """
        try:
            uuid = uuid.string
        except AttributeError:
            pass

        if uuid:
            return self.wrapper.perms.remove_permission(uuid, node)
        else:
            return self.wrapper.perms.remove_permission(self.uuid, node)

    def resetPerms(self, uuid=None):
        """

        resets all user data (removes all permissions).

        :arg uuid: Optional MCUUID/string UUID of a (different) player.

        :returns:  nothing

        """
        try:
            uuid = uuid.string
        except AttributeError:
            pass

        if uuid:
            return self.wrapper.perms.fill_user(uuid)
        else:
            return self.wrapper.perms.fill_user(self.uuid)

    def hasGroup(self, group, uuid=None):
        """
        Returns a boolean of whether or not the player is in
        the specified permission group.

        :arg group: Group node (string)
        :arg uuid: Optional MCUUID/string UUID of a (different) player.

        :returns:  Boolean of whether player has permission or not.

        """
        try:
            uuid = uuid.string
        except AttributeError:
            pass
        if uuid:
            return self.wrapper.perms.has_group(uuid, group)
        else:
            return self.wrapper.perms.has_group(self.uuid, group)

    def getGroups(self, uuid=None):
        """
        Returns a list of permission groups that the player is in.

        :arg uuid: Optional MCUUID/string UUID of a (different) player.

        :returns:  list of groups

        """
        try:
            uuid = uuid.string
        except AttributeError:
            pass

        if uuid:
            return self.wrapper.perms.get_groups(uuid)
        else:
            return self.wrapper.perms.get_groups(self.uuid)

    def setGroup(self, group, creategroup=True, uuid=None):
        """
        Adds the player to a specified group.  Returns False if
        the command fails (set debiug to see error).  Failure
        is only normally expected if the group does not exist
        and creategroup is False.

        :Args:
            :group: Group node (string)
            :creategroup: If True (by default), will create the
             group if it does not exist already.  This WILL
             generate a warning log since it is not an expected
             condition.
            :uuid: Optional MCUUID/string UUID of a (different) player.

        :returns:  Boolean; True if operation succeeds, False
         if it fails (set debug mode to see/log error).

        """
        try:
            uuid = uuid.string
        except AttributeError:
            pass

        if uuid:
            return self.wrapper.perms.set_group(
                uuid, group, creategroup
            )
        else:
            return self.wrapper.perms.set_group(
                self.uuid, group, creategroup
            )

    def removeGroup(self, group, uuid=None):
        """
        Removes the player to a specified group.

        :arg group: Group node (string)
        :arg uuid: Optional MCUUID/string UUID of a (different) player.

        :returns:  (use debug logging to see any errors)

            :True: Group was found and .remove operation performed
             (assume success if no exception raised).
            :None: User not in group
            :False: player uuid not found!

        """
        try:
            uuid = uuid.string
        except AttributeError:
            pass

        if uuid:
            return self.wrapper.perms.remove_group(
                uuid, group)
        else:
            return self.wrapper.perms.remove_group(
                self.uuid, group)

    # Player Information
    def getFirstLogin(self):
        """
        Returns a tuple containing the timestamp of when the user
        first logged in for the first time, and the timezone (same
        as time.tzname).

        """
        return self.data.Data["firstLoggedIn"]

    # Cross-server commands
    def connect(self, ip="127.0.0.1", port=25600):
        """
        Connect to another server.  Upon calling, the client's current
         server instance will be closed and a new server connection made
         to the target port of another server or wrapper instance.

        Any such target must be in offline-mode.
        The player object remains valid, but is largely ignored by this
         server.
        The player may respawn back to this server by typing `/hub`.

        :Args:
            :port: server or wrapper port you are connecting to.
            :ip:  the destination server ip.  Should be on your own
             network and inaccessible to outside port forwards.

        :returns: Nothing

        """
        if not self.wrapper.proxymode:
            self.log.warning("Can't use player.connect() without proxy mode.")
            return

        self.client.change_servers(ip, port)
