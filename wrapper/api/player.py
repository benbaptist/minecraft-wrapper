# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import time
import json
import threading

from proxy.mcpackets_cb import Packets as Packets_cb
from proxy.mcpackets_sb import Packets as Packets_sb

from proxy.constants import *
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
    logged-in player. This object is destroyed
    upon logging off.  Most features are tied heavily to
    proxy mode implementations and the proxy client instance.

    """

    def __init__(self, username, wrapper):

        self.wrapper = wrapper
        self.javaserver = wrapper.javaserver
        self.log = wrapper.log

        self.username = username
        self.loggedIn = time.time()

        # mcserver will set this to false later to close the thread.
        # meanwhile, it still needs to respect wrapper halts
        # TODO - clean this out.  let player objects GC with their client
        self.abort = self.wrapper.halt

        # these are all MCUUID objects.. I have separated out various
        #  uses of uuid to clarify for later refractoring
        # ---------------
        # Mojang uuid - the bought and paid Mojand UUID.  Never
        # changes- our one constant point of reference per player.
        # offline uuid - created as a MD5 hash of "OfflinePlayer:%s" % username
        # client uuid - what the client stores as the uuid (should be
        # the same as Mojang?) The player.uuid used by old api (and
        # internally here).
        # server uuid = the local server uuid... used to reference
        # the player on the local server.  Could be same as Mojang UUID
        # if server is in online mode or same as offline if server is
        # in offline mode (proxy mode).
        # *******************

        # This can be False if cache (and requests) Fail... bad name or
        # bad Mojang service connection.
        self.mojangUuid = self.wrapper.uuids.getuuidbyusername(username)

        # IF False error carries forward, this is not a valid player,
        # for whatever reason...
        self.clientUuid = self.mojangUuid

        # These two are offline by default.
        self.offlineUuid = self.wrapper.uuids.getuuidfromname(self.username)
        # Start out as the Offline -
        # change it to Mojang if local server is Online
        self.serverUuid = self.offlineUuid

        self.ipaddress = "127.0.0.0"
        self.loginposition = [0, 0, 0]

        self.client = None
        self.clientboundPackets = Packets_cb(self.javaserver.protocolVersion)
        self.serverboundPackets = Packets_sb(self.javaserver.protocolVersion)
        self.clientgameversion = self.javaserver.protocolVersion

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
            for client in self.wrapper.proxy.clients:
                if client.username == self.username:
                    self.client = client
                    # Both MCUUID objects
                    self.clientUuid = client.uuid
                    self.serverUuid = client.serveruuid

                    self.ipaddress = client.ip

                    # pktSB already set to javaserver.protocolVerion
                    self.clientboundPackets = self.client.pktCB
                    self.clientgameversion = self.client.clientversion
                    gotclient = True
                    break
            if not gotclient:
                self.log.error("Proxy is on, but this client is not "
                               "listed in wrapper.proxy.clients!")
                self.log.error("The usual cause of this would be that"
                               " someone is connecting directly to"
                               " your server port and not the wrapper"
                               " proxy port!")

        # Process login data
        self.data = Storage(
            self.clientUuid.string, root="wrapper-data/players")
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
        self.data.close()

    @property
    def name(self):
        return self.username

    @property
    def uuid(self):
        return self.mojangUuid

    def _track(self):
        """
        internal tracking that updates a player's server play time.
        Not a part of the public player object API.

        Sample ReST formattings -

        # emphasized notes
        Note: *You do not need to run this function unless you want*
         *certain permission nodes to be granted by default.*
         *i.e., 'essentials.list' should be on by default, so players*
         *can run /list without having any permissions*

        # code samples
            :sample usage:

                .. code:: python

                    < code here >

                ..

        """
        self.data.Data["logins"][int(self.loggedIn)] = time.time()
        while not self.abort:
            timeupdate = time.time()
            if timeupdate % 60:  # Just update every 60 seconds
                self.data.Data["logins"][int(self.loggedIn)] = int(time.time())
            # this needs a fast response to ensure the storage closes 
            # immediately on player logoff
            time.sleep(.5)
        self.data.close()

    def execute(self, string):
        """
        Run a command as this player. If proxy mode is not enabled,
        it simply falls back to using the 1.8 'execute' command. To 
        be clear, this does NOT work with any Wrapper.py or plugin 
        commands.  The command does not pass through the wrapper.  
        It is only sent to the server console.

        :arg string: full command string send on player's behalf to server.

        :returns: Nothing; passes the server or the console as an
         "execute" command.

        """
        try:
            self.client.chat_to_server("/%s" % string)
        except AttributeError:
            if self.javaserver.protocolVersion > PROTOCOL_1_7_9:
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
            :args: list of arguments (I think it is a list, not a
             tuple or dict!)

        :returns: Nothing; passes command through commands.py function
         'playercommand()'

        """
        pay = {"player": self, "command": command, "args": args}
        self.wrapper.api.callEvent("player.runCommand", pay)

    def say(self, string):
        """
        Send a message as a player.

        :arg string: message/command sent to the server as the player.

        Beware: *in proxy mode, the message string is sent directly to*
        *the server without wrapper filtering,so it could be used to*
        *execute minecraft commands as the player if the string is*
        *prefixed with a slash.*

        """
        try:
            self.client.chat_to_server(string)
        except AttributeError:
            # pre-1.8
            self.wrapper.javaserver.console(
                "say @a <%s> %s" % (self.username, string))

    def getClient(self):
        """
        Returns the player client context.  Use at your own risk - items
        in client are generally private or subject to change (you are
        working with an undefined API!)... what works in this wrapper
        version may not work in the next.

        :returns: player client object

        """
        if self.client is None:
            for client in self.wrapper.proxy.clients:
                try:
                    if client.username == self.username:
                        self.client = client
                        return self.client
                except Exception as e:
                    self.log.warning(
                        "getClient could not return a client for:%s"
                        " \nException:%s", (self.username, e))
        else:
            return self.client

    def getPosition(self):
        """
        Get the players position
        
        :Note:  The player's position is obtained by parsing client
         packets, which are not sent until the client logs in to 
         the server.  Allow some time after server login to verify 
         the wrapper has had the oppportunity to parse a suitable 
         packet to get the information!
        
        :returns: a tuple of the player's current position x, y, z, 
         and yaw, pitch of head.
        
        """
        return self.getClient().position + self.getClient().head

    def getGamemode(self):
        """
        Get the player's current gamemode.
        
        :Note:  The player's Gamemode is obtained by parsing client
         packets, which are not sent until the client logs in to 
         the server.  Allow some time after server login to verify 
         the wrapper has had the oppportunity to parse a suitable 
         packet to get the information!
         
        :returns:  An Integer of the the player's current gamemode.

        """
        return self.getClient().gamemode

    def getDimension(self):
        """
        Get the player's current dimension.

        :Note:  The player's Dimension is obtained by parsing client
         packets, which are not sent until the client logs in to 
         the server.  Allow some time after server login to verify 
         the wrapper has had the oppportunity to parse a suitable 
         packet to get the information!
         
         :returns: the player's current dimension.

             :Nether: -1
             :Overworld: 0
             :End: 1

        """
        return self.getClient().dimension

    def setGamemode(self, gamemode=0):
        """
        Sets the user's gamemode.

        :arg gamemode: desired gamemode, as a value 0-3

        """
        if gamemode in (0, 1, 2, 3):
            self.client.gamemode = gamemode
            self.wrapper.javaserver.console(
                "gamemode %d %s" % (gamemode, self.username))

    def setResourcePack(self, url, hashrp=""):
        """
        Sets the player's resource pack to a different URL. If the
        user hasn't already allowed resource packs, the user will
        be prompted to change to the specified resource pack.
        Probably broken right now.

        :Args:
            :url: URL of resource pack
            :hashrp: resource pack hash

        """
        if self.getClient().version < PROTOCOL_1_8START:
            self.client.packet.sendpkt(
                0x3f,
                [_STRING, _BYTEARRAY],
                ("MC|RPack", url))
        else:
            self.client.packet.sendpkt(
                self.clientboundPackets.RESOURCE_PACK_SEND,
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

        if self.javaserver.operator_list in (False, None):
            return False  # no ops in file
        # each op item is a dictionary
        for ops in self.javaserver.operator_list:
            if ops["uuid"] == self.serverUuid.string:
                return ops["level"]
            if ops["name"] == self.username and not strict:
                return ops["level"]
        return False

    def message(self, message=""):
        """
        Sends a message to the player.

        :arg message: Can be text, colorcoded text, or json chat

        """
        if self.javaserver:
            self.javaserver.broadcast(message, who=self.username)
        else:
            # TODO message client directly
            pass

    def actionMessage(self, message=""):
        if self.getClient().version < PROTOCOL_1_8START:
            parsing = [_STRING, _NULL]
            data = [message]
        else:
            parsing = [_STRING, _BYTE]
            data = (json.dumps({"text": processoldcolorcodes(message)}), 2)

        self.getClient().packet.sendpkt(
            self.clientboundPackets.CHAT_MESSAGE,
            parsing,  # "string|byte"
            data)

    def setVisualXP(self, progress, level, total):
        """
         Change the XP bar on the client's side only. Does not
         affect actual XP levels.

        :Args:
            :progress:  Float between Between 0 and 1
            :level:  Integer (short in older versions) of EXP level
            :total: Total EXP.

        :returns: Nothing

        """
        if self.getClient().version > PROTOCOL_1_8START:
            parsing = [_FLOAT, _VARINT, _VARINT]
        else:
            parsing = [_FLOAT, _SHORT, _SHORT]

        self.getClient().packet.sendpkt(
            self.clientboundPackets.SET_EXPERIENCE,
            parsing,
            (progress, level, total))

    def openWindow(self, windowtype, title, slots):
        """
        Opens an inventory window on the client side.  EntityHorse
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

        self.getClient().windowCounter += 1
        if self.getClient().windowCounter > 200:
            self.getClient().windowCounter = 2

        # TODO Test what kind of field title is (json or text)

        if not self.getClient().version > PROTOCOL_1_8START:
            return False

        self.getClient().packet.sendpkt(
            self.clientboundPackets.OPEN_WINDOW,
            [_UBYTE, _STRING, _JSON, _UBYTE],
            (self.getClient().windowCounter, windowtype, {"text": title},
             slots))

        return None  # return a Window object soon

    def setPlayerAbilities(self, fly):
        """
        *based on old playerSetFly (which was an unfinished function)*

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
        self.getClient().packet.sendpkt(
            self.clientboundPackets.PLAYER_ABILITIES,
            [_BYTE, _FLOAT, _FLOAT],
            (bitfield, self.fly_speed, self.field_of_view))

        self.getClient().server.packet.sendpkt(
            self.serverboundPackets.PLAYER_ABILITIES,
            [_BYTE, _FLOAT, _FLOAT],
            (bitfield, self.fly_speed, self.field_of_view))

    def sendBlock(self, position, blockid, blockdata, sendblock=True,
                  numparticles=1, partdata=1):
        """
        Used to make phantom blocks visible ONLY to the client.  Sends
        either a particle or a block to the minecraft player's client.
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
            self.getClient().packet.sendpkt(
                self.clientboundPackets.BLOCK_CHANGE,
                blockparser,
                (posx, y, x, iddata, blockdata))
        else:
            self.getClient().packet.sendpkt(
                self.clientboundPackets.PARTICLE,
                particleparser,
                (blockid, True, x + .5, y + .5, z + .5, 0, 0, 0,
                 partdata, numparticles))

    # Inventory-related actions.
    def getItemInSlot(self, slot):
        """
        Returns the item object of an item currently being held.

        """
        return self.getClient().inventory[slot]

    def getHeldItem(self):
        """
        Returns the item object of an item currently being held.

        """
        return self.getClient().inventory[36 + self.getClient().slot]

    # Permissions-related
    def hasPermission(self, node, another_player=False, group_match=True, find_child_groups=True):
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
        uuid_to_check = self.mojangUuid.string
        if another_player:
            # get other player mojang uuid
            uuid_to_check = str(
                self.wrapper.uuids.getuuidbyusername(another_player))
            if not uuid_to_check:
                # probably a bad name provided.. No further check needed.
                return False

        return self.wrapper.perms.has_permission(
            uuid_to_check, node, group_match, find_child_groups)

    def setPermission(self, node, value=True):
        """
        Adds the specified permission node and optionally a value
        to the player.

        :Args:
            :node: Permission node (string)
            :value: defaults to True, but can be set to False to
             explicitly revoke a particular permission from the
             player, or to any arbitrary value.

        :returns: Nothing

        """
        self.wrapper.perms.set_permission(self.mojangUuid.string, node, value)

    def removePermission(self, node):
        """
        Completely removes a permission node from the player. They
        will inherit this permission from their groups or from
        plugin defaults.

        If the player does not have the specific permission, an
        IndexError is raised. Note that this method has no effect
        on nodes inherited from groups or plugin defaults.

        :arg node: Permission node (string)

        :returns:  Boolean; True if operation succeeds, False if
         it fails (set debug mode to see/log error).

        """
        return self.wrapper.perms.remove_permission(
            self.mojangUuid.string, node)

    def hasGroup(self, group):
        """
        Returns a boolean of whether or not the player is in
        the specified permission group.

        :arg group: Group node (string)

        :returns:  Boolean of whether player has permission or not.

        """
        return self.wrapper.perms.has_group(self.mojangUuid.string, group)

    def getGroups(self):
        """
        Returns a list of permission groups that the player is in.

        :returns:  list of groups

        """
        return self.wrapper.perms.get_groups(self.mojangUuid.string)

    def setGroup(self, group, creategroup=True):
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

        :returns:  Boolean; True if operation succeeds, False
         if it fails (set debug mode to see/log error).

        """
        return self.wrapper.perms.set_group(
            self.mojangUuid.string, group, creategroup)

    def removeGroup(self, group):
        """
        Removes the player to a specified group.

        :arg group: Group node (string)

        :returns:  (use debug logging to see any errors)

            :True: Group was found and .remove operation performed
             (assume success if no exception raised).
            :None: User not in group
            :False: player uuid not found!

        """
        return self.wrapper.perms.remove_group(
            self.mojangUuid.string, group)

    # Player Information
    def getFirstLogin(self):
        """
        Returns a tuple containing the timestamp of when the user
        first logged in for the first time, and the timezone (same
        as time.tzname).

        """
        return self.data.Data["firstLoggedIn"]

    # Cross-server commands
    def connect(self, address, port):
        """
        Upon calling, the player object will become defunct and
        the client will be transferred to another server or wrapper
        instance (provided it has online-mode turned off).

        :Args:
            :address: server address (local address)
            :port: server port (local port)

        :returns: Nothing

        """
        self.client.change_servers(address, port)
