# -*- coding: utf-8 -*-

import time
import fnmatch
import json
import threading

import proxy.mcpacket as mcpacket
from core.storage import Storage
from utils.helpers import processoldcolorcodes, processcolorcodes, getjsonfile, getfileaslines


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
class Player:
    """
    Player objects contains methods and data of a currently logged-in player. This object is destroyed
    upon logging off.
    """

    def __init__(self, username, wrapper):

        self.wrapper = wrapper
        self.javaserver = wrapper.javaserver
        self.permissions = wrapper.permissions
        self.log = wrapper.log

        self.username = username
        self.loggedIn = time.time()
        self.abort = False

        # these are all MCUUID objects.. I have separated out various uses of uuid to clarify for later refractoring
        # ---------------
        # Mojang uuid - the bought and paid Mojand UUID.  Never changes- our one constant point of reference per player.
        # offline uuid - created as a MD5 hash of "OfflinePlayer:%s" % username
        # client uuid - what the client stores as the uuid (should be the same as Mojang?) The player.uuid used by
        #     old api (and internally here).
        # server uuid = the local server uuid... used to reference the player on the local server.  Could be same as
        #     Mojang UUID if server is in online mode or same as offline if server is in offline mode (proxy mode).

        # This can be False if cache (and requests) Fail... bad name or bad Mojang service connection.
        self.mojangUuid = self.wrapper.getuuidbyusername(username)
        # IF False error carries forward, this is not a valid player, for whatever reason...
        self.clientUuid = self.mojangUuid
        # These two are offline by default.
        self.offlineUuid = self.wrapper.getuuidfromname(self.username)
        self.serverUuid = self.offlineUuid  # Start out as the Offline - change it to Mojang if local server is Online

        self.ipaddress = "127.0.0.0"
        self.operatordict = self._read_ops_file()

        self.client = None
        self.clientboundPackets = mcpacket.Client18
        self.serverboundPackets = mcpacket.Server18
        self.clientgameversion = self.javaserver.protocolVersion
        self.playereid = None

        # some player properties associated with abilities
        self.field_of_view = float(1)  # default is 1.  Should normally be congruent with speed.
        self.godmode = 0x00  # Client set godmode is 0x01
        self.creative = 0x00  # Client set creative is 0x08
        self.fly_speed = float(1)  # default is 1

        if self.wrapper.proxy:
            gotclient = False
            for client in self.wrapper.proxy.clients:
                if client.username == self.username:
                    self.client = client
                    self.clientUuid = client.uuid  # Both MCUUID objects
                    self.serverUuid = client.serveruuid
                    self.ipaddress = client.ip
                    self.clientboundPackets = self.client.pktCB
                    self.serverboundPackets = self.client.pktSB
                    self.clientgameversion = self.client.clientversion
                    gotclient = True
                    break
            if not gotclient:
                self.log.error("Proxy is on, but this client is not listed in wrapper.proxy.clients!")
        self.data = Storage(self.clientUuid.string, root="wrapper-data/players")

        if "users" not in self.permissions:  # top -level dict item should be just checked once here (not over and over)
            self.permissions["users"] = {}
        if self.mojangUuid.string not in self.permissions["users"]:  # no reason not to do this here too
            self.permissions["users"][self.mojangUuid.string] = {"groups": [], "permissions": {}}
        if "firstLoggedIn" not in self.data:
            self.data["firstLoggedIn"] = (time.time(), time.tzname)
        if "logins" not in self.data:
            self.data["logins"] = {}
        self.data["lastLoggedIn"] = (self.loggedIn, time.tzname)
        self.data.save()

        t = threading.Thread(target=self._track, args=())
        t.daemon = True
        t.start()

    def __str__(self):
        return self.username

    def __del__(self):
        self.data.save()

    @property
    def name(self):
        return self.username

    @property
    def uuid(self):
        return self.mojangUuid

    def _track(self):
        """
        internal tracking that updates a player's server play time. Not intended as a part of the public
        player object API
        """
        self.data["logins"][int(self.loggedIn)] = time.time()
        while not self.abort:
            self.data["logins"][int(self.loggedIn)] = int(time.time())
            time.sleep(60)
        self.data.save()

    def _read_ops_file(self):
        """
        Internal private method - Not intended as a part of the public player object API
        Returns: contents of ops.json as a dict
        """
        ops = False
        if self.javaserver.protocolVersion > mcpacket.PROTOCOL_1_7:  # 1.7.6 or greater use ops.json
            ops = getjsonfile("ops")
        if not ops:
            # try for an old "ops.txt" file instead.
            ops = {}
            opstext = getfileaslines("ops.txt")
            if not opstext:
                return False
            for x in range(len(opstext)):
                # create a 'fake' ops dictionary from the old pre-1.8 text line name list
                # notice that the level (an option not the old list) is set to 1
                #   This will pass as true, but if the plugin is also checking op-levels, it
                #   may not pass truth.
                ops[opstext[x]] = {"uuid": opstext[x],
                                   "name": opstext[x],
                                   "level": 1}

        return ops

    def execute(self, string):
        """
        Run a command as this player. If proxy mode is not enabled,
        it simply falls back to using the 1.8 'execute' command. To be clear, this
        does NOT work with any Wrapper.py or plugin commands.  The command
        does not pass through the wrapper.

        Args:
            string: full command string send on player's behalf to server.

        Returns: Nothing; passes the server or the console as an "execute" command.

        """
        try:
            self.client.message("/%s" % string)
        except AttributeError:
            if self.javaserver.protocolVersion > mcpacket.PROTOCOL_1_7_9:
                self.wrapper.javaserver.console("execute %s ~ ~ ~ %s" % (self.username, string))
            else:
                self.log.warning("could not run player.execute - wrapper not in proxy mode and minecraft version "
                                 "is less than 1.8 (when /execute was implemented).")

    def sendCommand(self, command, args):
        """
        Sends a command to the wrapper interface as the player instance.
        This would find a nice application with a '\sudo' plugin command.

        Sample usage:
            ```
            player=getPlayer("username")
            player.sendCommand("perms", ("users", "SurestTexas00", "info"))
            ```
        Args:
            command: The wrapper (or plugin) command to execute; no slash prefix
            args: list of arguments (I think it is a list, not a tuple or dict!)

        Returns: Nothing; passes command through commands.py function 'playercommand()'

        """
        pay = {"player": self, "command": command, "args": args}
        self.wrapper.api.callEvent("player.runCommand", pay)

    def say(self, string):
        """
        :param string: message/command sent to the server as the player.
        Send a message as a player.

        Beware: in proxy mode, the message string is sent directly to the server
        without wrapper filtering,so it could be used to execute minecraft
        commands as the player if the string is prefixed with a slash.
        """
        try:
            self.client.message(string)
        except AttributeError:  # pre-1.8
            self.wrapper.javaserver.console("say @a <%s> %s" % (self.username, string))

    def getClient(self):
        """
        :returns: player client object
        """
        if self.client is None:
            for client in self.wrapper.proxy.clients:
                try:
                    if client.username == self.username:
                        self.client = client
                        return self.client
                except Exception as e:
                    self.log.warning("getClient could not return a client for:%s \nException:%s",
                                     (self.username, e))
        else:
            return self.client

    def getBedPostion(self):
        """
        Returns: returns a tuple of the player's last sleeping place (position x, y, z)

        IMPORTANT: wrapper does not store this permanently. It is up to the plugin to record a
            "player.usebed" event and then store the data in their own Storage objects!
        """
        return self.getClient().bedposition

    def getPosition(self):
        """:returns: a tuple of the player's current position x, y, z, and yaw, pitch of head.
        Notes:
        The player's position is obtained by parsing client packets, which are not sent until the
        client logs in to the server.  Allow some time after server login to verify the wrapper has had
        the oppportunity to parse a suitable packet to get the information!
        """
        return self.getClient().position + self.getClient().head

    def getGamemode(self):
        """:returns:  the player's current gamemode.
        Notes:
        The player's gammode may be obtained by parsing server packets, which are not sent until the
        client logs in to the server.  Allow some time after server login to verify the wrapper has had
        the oppportunity to parse a suitable packet to get the information!
        """
        return self.getClient().gamemode

    def getDimension(self):
        """:returns: the player's current dimension.
        -1 for Nether,
         0 for Overworld
         1 for End.
        Notes:
        The player's position is obtained by parsing server/client packets, which are not sent until the
        client logs in to the server.  Allow some time after server login to verify the wrapper has had
        the oppportunity to parse a suitable packet to get the information!
        """
        return self.getClient().dimension

    def setGamemode(self, gm=0):
        """
        :param gm: desired gamemode, as a value 0-3
        Sets the user's gamemode.
        """
        if gm in (0, 1, 2, 3):
            self.client.gamemode = gm
            self.wrapper.javaserver.console("gamemode %d %s" % (gm, self.username))

    def setResourcePack(self, url, hashrp=""):
        """
        :param url: URL of resource pack
        :param hashrp: resource pack hash
        Sets the player's resource pack to a different URL. If the user hasn't already allowed
        resource packs, the user will be prompted to change to the specified resource pack.
        Probably broken right now.
        """
        if self.getClient().version < mcpacket.PROTOCOL_1_8START:
            self.client.packet.sendpkt(0x3f, [_STRING, _BYTEARRAY], ("MC|RPack", url))  # "string|bytearray"
        else:
            self.client.packet.sendpkt(self.clientboundPackets.RESOURCE_PACK_SEND,
                                       [_STRING, _STRING], (url, hashrp))

    def isOp(self, strict=False):
        """
        Args:
            strict: True - use ONLY the UUID as verification

        returns:  A 1-4 op level if the player is currently a server operator.
                can be treated, as before, like a boolean - `if player.isOp():`, but now
                also adds ability to granularize with the OP level

        Accepts player as OP based on either the username OR server UUID.
        This should NOT be used in a recursive loop (like a protection plugin, etc)
        or a very frequently run function because it accesses the disk file
        (ops.json) at each call!  Use of isOP_fast() is recommended instead.
        """

        operators = self._read_ops_file()
        for ops in operators:
            if ops["uuid"] == self.serverUuid.string:
                return ops["level"]
            if ops["name"] == self.username and not strict:
                return ops["level"]
        return False

    def isOp_fast(self, strict=False):
        """
        Args:
            strict: True - use ONLY the UUID as verification

        returns:  A 1-4 op level if the player is currently a server operator.
                can be treated, as before, like a boolean - `if player.isOp():`, but now
                also adds ability to granularize with the OP level

        Works like isOp(), but uses an oplist cached from the __init__ of the player.py api for this player.
        Suitable for quick fast lookup without accessing disk, but someone who is deopped after the
        player logs in will still show as OP.
        """
        for ops in self.operatordict:
            if ops["uuid"] == self.serverUuid.string:
                return ops["level"]
            if ops["name"] == self.username and not strict:
                return ops["level"]
        return False

    def refreshOps(self):
        self.operatordict = self._read_ops_file()

    # region Visual notifications
    def message(self, message=""):
        if isinstance(message, dict):
            self.wrapper.javaserver.console("tellraw %s %s" % (self.username, json.dumps(message)))
        else:
            self.wrapper.javaserver.console("tellraw %s %s" % (self.username, processcolorcodes(message)))

    def actionMessage(self, message=""):
        if self.getClient().version < mcpacket.PROTOCOL_1_8START:
            parsing = [_STRING, _NULL]  # "string|null (nothing sent)"
            data = [message]
        else:
            parsing = [_STRING, _BYTE]  # "string|byte"
            data = (json.dumps({"text": processoldcolorcodes(message)}), 2)
        self.getClient().packet.sendpkt(self.clientboundPackets.CHAT_MESSAGE, parsing,  # "string|byte"
                                        data)

    def setVisualXP(self, progress, level, total):
        """
         Change the XP bar on the client's side only. Does not affect actual XP levels.

        Args:
            progress:  Float between Between 0 and 1
            level:  Integer (short in older versions) of EXP level
            total: Total EXP.

        Returns:

        """
        if self.getClient().version > mcpacket.PROTOCOL_1_8START:
            self.getClient().packet.sendpkt(self.clientboundPackets.SET_EXPERIENCE, [_FLOAT, _VARINT, _VARINT],
                                            (progress, level, total))
        else:
            self.getClient().packet.sendpkt(self.clientboundPackets.SET_EXPERIENCE, [_FLOAT, _SHORT, _SHORT],
                                            (progress, level, total))

    def openWindow(self, windowtype, title, slots):
        """
        Opens an inventory window on the client side.  EntityHorse is not supported due to further
        EID requirement.  1.8 experimental only.

        Args:
            windowtype:  Window Type (text string). See below or applicable wiki entry
                        (for version specific info)
            title: Window title - wiki says chat object (could be string too?)
            slots:

        Returns: None

        Type names (1.9)
            minecraft:chest	Chest, large chest, or minecart with chest
            minecraft:crafting_table	Crafting table
            minecraft:furnace	Furnace
            minecraft:dispenser	Dispenser
            minecraft:enchanting_table	Enchantment table
            minecraft:brewing_stand	Brewing stand
            minecraft:villager	Villager
            minecraft:beacon	Beacon
            minecraft:anvil	Anvil
            minecraft:hopper	Hopper or minecart with hopper
            minecraft:dropper	Dropper
            EntityHorse	Horse, donkey, or mule


        """

        self.getClient().windowCounter += 1
        if self.getClient().windowCounter > 200:
            self.getClient().windowCounter = 2
        # TODO Test what kind of field title is (json or text)
        if self.getClient().version > mcpacket.PROTOCOL_1_8START:
            self.getClient().packet.send(
                self.clientboundPackets.OPEN_WINDOW, [_UBYTE, _STRING, _JSON, _UBYTE], (
                    self.getClient().windowCounter, windowtype, {"text": title}, slots))
        return None  # return a Window object soon
    # endregion Visual notifications

    # region Abilities & Client-Side Stuff
    def setPlayerAbilities(self, fly):
        # based on old playerSetFly (which was an unfinished function)
        """
        this will set 'is flying' and 'can fly' to true for the player.
        these flags/settings will be applied as well:

        getPlayer().godmode  (defaults are all 0x00 - unset, or float of 1.0, as applicable)
        getPlayer().creative
        getPlayer().field_of_view
        getPlayer().fly_speed

        Args:
            fly: Booolean - Fly is true, (else False to unset fly mode)

        Returns: Nothing

        Bitflags used (for all versions): (so 'flying' and 'is flying' is 0x06)
            Invulnerable	0x01
            Flying	        0x02
            Allow Flying	0x04
            Creative Mode	0x08

        """
        # TODO later add and keep track of godmode and creative- code will currently unset them.
        if fly:
            setfly = 0x06  # for set fly
        else:
            setfly = 0x00
        bitfield = self.godmode | self.creative | setfly
        # Note in versions before 1.8, field of view is the walking speed for client (still a float)
        #   Server field of view is still walking speed
        self.getClient().packet.sendpkt(self.clientboundPackets.PLAYER_ABILITIES, [_BYTE, _FLOAT, _FLOAT],
                                        (bitfield, self.fly_speed, self.field_of_view))
        self.getClient().server.packet.sendpkt(self.serverboundPackets.PLAYER_ABILITIES, [_BYTE, _FLOAT, _FLOAT],
                                               (bitfield, self.fly_speed, self.field_of_view))

    def sendBlock(self, position, blockid, blockdata, sendblock=True, numparticles=1, partdata=1):
        """
            Used to make phantom blocks visible ONLY to the client.  Sends either a particle or a block to
            the minecraft player's client. for blocks iddata is just block id - No need to bitwise the
            blockdata; just pass the additional block data.  The particle sender is only a basic version
            and is not intended to do anything more than send something like a barrier particle to
            temporarily highlight something for the player.  Fancy particle operations should be custom
            done by the plugin or someone can write a nicer particle-renderer.

        :param position - players position as tuple.  The coordinates must be in the player's render distance
            or the block will appear at odd places.
        :param blockid - usually block id, but could be particle id too.  If sending pre-1.8 particles this is a
            string not a number... the valid values are found here:
                        ->http://wayback.archive.org/web/20151023030926/https://gist.github.com/thinkofdeath/5110835
        :param blockdata - additional block meta (a number specifying a subtype).
        :param sendblock - True for sending a block.
        :param numparticles - if particles, their numeric count.
        :param partdata - if particles; particle data.  Particles with additional ID cannot be used ("Ironcrack").

        """

        pkt_particle = self.clientboundPackets.PARTICLE
        pkt_blockchange = self.clientboundPackets.BLOCK_CHANGE

        x = (position[0])
        y = (position[1])
        z = (position[2])
        if self.clientgameversion > mcpacket.PROTOCOL_1_7_9:
            if sendblock:
                iddata = blockid << 4 | blockdata
                self.getClient().packet.sendpkt(pkt_blockchange, [_POSITION, _VARINT], (position, iddata))
            else:
                self.getClient().packet.sendpkt(
                    pkt_particle, [_INT, _BOOL, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _INT],
                    (blockid, True, x + .5, y + .5, z + .5, 0, 0, 0, partdata, numparticles))
        if self.clientgameversion < mcpacket.PROTOCOL_1_8START:
            if sendblock:
                self.getClient().packet.sendpkt(pkt_blockchange, [_INT, _UBYTE, _INT, _VARINT, _UBYTE],
                                                (x, y, x, blockid, blockdata))
            else:
                self.getClient().packet.sendpkt(
                    pkt_particle, [_STRING, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _FLOAT, _INT],
                    (blockid, x + .5, y + .5, z + .5, 0, 0, 0, partdata, numparticles))

    # Inventory-related actions. These will probably be split into a specific
    # Inventory class.
    def getItemInSlot(self, slot):
        return self.getClient().inventory[slot]

    def getHeldItem(self):
        """ Returns the item object of an item currently being held. """
        return self.getClient().inventory[36 + self.getClient().slot]

    # Permissions-related

    def hasPermission(self, node, another_player=False):
        """
        If the player has the specified permission node (either directly, or inherited from a group that
        the player is in), it will return the value (usually True) of the node. Otherwise, it returns False.

        Args:
            node: Permission node (string)
            another_player: sending a string name of another player will check THAT PLAYER's permission
                instead! Useful for checking a player's permission for someone who is not logged in and
                has no player object.

        Returns:  Boolean of whether player has permission or not.

        """

        # this might be a useful thing to implement into all permissions methods
        uuid_to_check = self.mojangUuid.string
        if node is None:
            return True
        if another_player:
            other_uuid = self.wrapper.getuuidbyusername(another_player)  # get other player mojang uuid
            if other_uuid:  # make sure other player permission is initialized.
                if self.mojangUuid.string not in self.permissions["users"]:  # no reason not to do this here too
                    self.permissions["users"][self.mojangUuid.string] = {"groups": [], "permissions": {}}
            else:
                return False  # probably a bad name provided.. No further check needed.

        if uuid_to_check in self.permissions["users"]:  # was self.clientUuid.string
            for perm in self.permissions["users"][uuid_to_check]["permissions"]:
                if node in fnmatch.filter([node], perm):
                    return self.permissions["users"][uuid_to_check]["permissions"][perm]
        if uuid_to_check not in self.permissions["users"]:
            return False
        allgroups = []  # summary of groups included children groups
        # get the parent groups
        for group in self.permissions["users"][uuid_to_check]["groups"]:
            if group not in allgroups:
                allgroups.append(group)
        itemstoprocess = allgroups[:]  # process and find child groups
        while len(itemstoprocess) > 0:
            parseparent = itemstoprocess.pop(0)
            for groupPerm in self.permissions["groups"][parseparent]["permissions"]:
                if (groupPerm in self.permissions["groups"]) and \
                        self.permissions["groups"][parseparent]["permissions"][groupPerm] and \
                        (groupPerm not in allgroups):
                    allgroups.append(groupPerm)
                    itemstoprocess.append(groupPerm)
        for group in allgroups:
            for perm in self.permissions["groups"][group]["permissions"]:
                if node in fnmatch.filter([node], perm):
                    return self.permissions["groups"][group]["permissions"][perm]
        for perm in self.permissions["groups"]["Default"]["permissions"]:
            if node in fnmatch.filter([node], perm):
                return self.permissions["groups"]["Default"]["permissions"][perm]
        for pid in self.wrapper.permission:
            if node in self.wrapper.permission[pid]:
                return self.wrapper.permission[pid][node]
        return False

    def setPermission(self, node, value=True):
        """
        Adds the specified permission node and optionally a value to the player.

        Args:
            node: Permission node (string)
            value: defaults to True, but can be set to False to explicitly revoke a particular permission
                from the player, or to any arbitrary value.
        Returns: Nothing

        """
        for uuid in self.permissions["users"]:
            if uuid == self.mojangUuid.string:  # was self.clientUuid.string
                self.permissions["users"][uuid]["permissions"][node] = value
                return

    def removePermission(self, node):
        """ Completely removes a permission node from the player. They will inherit this permission from their
         groups or from plugin defaults.

        If the player does not have the specific permission, an IndexError is raised. Note that this method
        has no effect on nodes inherited from groups or plugin defaults.

        Args:
            node: Permission node (string)

        Returns:  Boolean; True if operation succeeds, False if it fails (set debug mode to see/log error).
    """

        for uuid in self.permissions["users"]:
            if uuid == self.mojangUuid.string:  # was self.clientUuid.string
                if node in self.permissions["users"][uuid]["permissions"]:
                    del self.permissions["users"][uuid]["permissions"][node]
                    return True
                else:
                    self.log.debug("%s does not have permission node '%s'", (self.username, node))
                    return False
        self.log.debug("Player %s uuid:%s does not have permission node '%s'",
                       (self.username, self.mojangUuid.string, node))
        return False

    def hasGroup(self, group):
        """ Returns a boolean of whether or not the player is in the specified permission group.

        Args:
            group: Group node (string)

        Returns:  Boolean of whether player has permission or not.
        """
        for uuid in self.permissions["users"]:
            if uuid == self.mojangUuid.string:  # was self.clientUuid.string
                return group in self.permissions["users"][uuid]["groups"]
        return False

    def getGroups(self):
        """ Returns a list of permission groups that the player is in.

        Returns:  list of groups
        """
        for uuid in self.permissions["users"]:
            if uuid == self.mojangUuid.string:  # was self.clientUuid.string
                return self.permissions["users"][uuid]["groups"]
        return []  # If the user is not in the permission database, return this

    def setGroup(self, group):
        """
        Adds the player to a specified group.  Returns False if group does not exist (set debiug to see error).
        Args:
            group: Group node (string)

        Returns:  Boolean; True if operation succeeds, False if it fails (set debug mode to see/log error).
        """
        if group not in self.permissions["groups"]:
            self.log.debug("No group with the name '%s' exists", group)
            return False
        for uuid in self.permissions["users"]:
            if uuid == self.mojangUuid.string:  # was self.clientUuid.string
                self.permissions["users"][uuid]["groups"].append(group)
                return True
        self.log.debug("Player %s uuid:%s: Could not be added to group '%s'",
                       (self.username, self.mojangUuid.string, group))
        return False

    def removeGroup(self, group):
        """ Removes the player to a specified group. If they are not part of the specified
        group, an IndexError is raised.

        Args:
            group: Group node (string)

        Returns:
            """
        for uuid in self.permissions["users"]:
            if uuid == self.mojangUuid.string:  # was self.clientUuid.string:
                if group in self.permissions["users"][uuid]["groups"]:
                    self.permissions["users"][uuid]["groups"].remove(group)
                else:
                    # TODO DO something about this other than raise exception??
                    raise IndexError("%s is not part of the group '%s'" % (self.username, group))

    # Player Information

    def getFirstLogin(self):
        """ Returns a tuple containing the timestamp of when the user first logged in for the first time,
        and the timezone (same as time.tzname). """
        return self.data["firstLoggedIn"]
    # Cross-server commands

    def connect(self, address, port):
        """
        Upon calling, the player object will become defunct and the client will be transferred to another
         server (provided it has online-mode turned off).

        Args:
            address: server address (local address)
            port: server port (local port)

        Returns: Nothing
        """
        self.client.connect(address, port)
