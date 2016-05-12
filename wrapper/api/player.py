# -*- coding: utf-8 -*-

# p2 and py3 compliant (no PyCharm IDE-flagged warnings or errors)

import time
import fnmatch
import json
import threading

import proxy.mcpacket as mcpacket
from core.storage import Storage
from api.base import API

class Player:
    """
    Player objects contains methods and data of a currently logged-in player. This object is destroyed
    upon logging off. """

    def __init__(self, username, wrapper):
        """
        UUID terminologies:
        Mojang uuid - the bought and paid Mojand UUID.
        offline uuid - created as a MD5 hash of "OfflinePlayer:%s" % username
        server uuid = the local server uuid... used to reference the player on the local server.  Could be same as
            Mojang UUID if server is in online mode or same as offline if server is in offline mode (proxy mode).
        client uuid - what the client stores as the uuid (should be the same as Mojang?)
        """

        self.wrapper = wrapper
        self.server = wrapper.server
        self.permissions = wrapper.permissions
        self.log = wrapper.log

        self.username = username
        self.loggedIn = time.time()
        self.abort = False

        # these are all MCUUID objects.. I have separated out various uses of uuid to clarify for later refractoring
        self.mojangUuid = self.wrapper.getUUIDByUsername(username)
        self.offlineUuid = self.wrapper.getUUIDFromName("OfflinePlayer:%s" % self.username)
        self.clientUuid = self.wrapper.getUUID(username)  # - The player.uuid used by old api (and internally here).
        self.serverUuid = self.wrapper.getUUIDByUsername(username)

        self.ipaddress =  "127.0.0.0"
        self.operatordict = self._read_ops_file()

        self.client = None
        self.clientPackets = mcpacket.ClientBound18
        self.serverPackets = mcpacket.ServerBound18

        # some player properties associated with abilities
        self.field_of_view = float(1) # default is 1.  Should normally be congruent with speed.
        self.godmode = 0x00  # Client set godmode is 0x01
        self.creative = 0x00  # Client set creative is 0x08
        self.fly_speed = float(1)  # default is 1

        if self.server.version > mcpacket.PROTOCOL_1_9START:
            self.serverPackets = mcpacket.ServerBound19

        if self.wrapper.proxy:
            for client in self.wrapper.proxy.clients:
                if client.username == username:
                    self.client = client
                    self.clientUuid = client.uuid # Both MCUUID objects
                    self.serverUuid = client.serverUuid
                    self.ipaddress = client.ip
                    if self.getClient().version > 49:  # packet numbers fluctuated  wildly between 48 and 107
                        self.clientPackets = mcpacket.ClientBound19
                    break

        self.data = Storage(self.clientUuid.string, root="wrapper-data/players")

        if "users" not in self.permissions: # top -level dict item should be just checked once here (not over and over)
            self.permissions["users"] = {}
        if self.mojangUuid.string not in self.permissions["users"]:  # no reason not to do this here too
            self.permissions["users"][self.mojangUuid.string] = {"groups": [], "permissions": {}}
        if "firstLoggedIn" not in self.data:
            self.data["firstLoggedIn"] = (time.time(), time.tzname)
        if "logins" not in self.data:
            self.data["logins"] = {}
        t = threading.Thread(target=self._track, args=())
        t.daemon = True
        t.start()

    def __str__(self):
        return self.username

    @property
    def name(self):
        return self.username

    @property
    def uuid(self):
        return self.mojangUuid

    def _track(self):
        """
        internal tracking that updates a players last login time. Not intended as a part of the public player object API
        """
        self.data["logins"][int(self.loggedIn)] = time.time()
        while not self.abort:
            self.data["logins"][int(self.loggedIn)] = int(time.time())
            time.sleep(60)

    @staticmethod
    def _processOldColorCodes(message):
        """
        Internal private method - Not intended as a part of the public player object API

         message: message text containing '&' to represent the chat formatting codes
        :return: mofified text containing the section sign (§) and the formatting code.
        """
        for i in API.colorCodes:
            message = message.replace("&" + i, "\xc2\xa7" + i)
        return message

    @staticmethod
    def _read_ops_file():
        """
        Internal private method - Not intended as a part of the public player object API
        Returns: contents of ops.json as a dict
        """
        with open("ops.json", "r") as f:
            ops = json.loads(f.read())
        return ops

    def console(self, string):
        """
        :param string: command to execute (no preceding slash) in the console
        Run a command in the Minecraft server's console.
        """
        self.wrapper.server.console(string)

    def execute(self, string):
        """
        :param string: command to execute (no preceding slash)
         Run a command as this player. To be clear, this does NOT work with
         any Wrapper.py or commands.  The command is sent straight to the
         server console without going through the wrapper.
        """
        self.console("execute %s ~ ~ ~ %s" % (self.name, string))

    def say(self, string):
        """
        :param string: message/command sent to the server as the player.
        Send a message as a player.

        Beware: the message string is sent directly to the server
        without wrapper filtering,so it could be used to execute minecraft
        commands as the player if the string is prefixed with a slash.
        * Only works in proxy mode. """
        self.client.message(string)

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
                    self.log.warning("getClient could not return a client for:%s \nException:%s", (self.username, e))
        else:
            return self.client

    def getPosition(self):
        """:returns: a tuple of the player's current position x, y, z, and yaw, pitch of head. """
        return self.getClient().position + self.getClient().head

    def getGamemode(self):
        """:returns:  the player's current gamemode. """
        return self.getClient().gamemode

    def getDimension(self):
        """:returns: the player's current dimension.
        -1 for Nether,
         0 for Overworld
         1 for End.
         """
        return self.getClient().dimension

    def setGamemode(self, gm=0):
        """
        :param gm: desired gamemode, as a value 0-3
        Sets the user's gamemode.
        """
        if gm in (0, 1, 2, 3):
            self.client.gamemode = gm
            self.console("gamemode %d %s" % (gm, self.username))

    def setResourcePack(self, url, hashrp=""):
        """
        :param url: URL of resource pack
        :param hashrp: resource pack hash
        Sets the player's resource pack to a different URL. If the user hasn't already allowed
        resource packs, the user will be prompted to change to the specified resource pack.
        Probably broken right now.
        """
        if self.getClient().version < mcpacket.PROTOCOL_1_8START:
            self.client.packet.send(0x3f, "string|bytearray", ("MC|RPack", url))
        else:
            self.client.packet.send(self.clientPackets.RESOURCE_PACK_SEND,
                             "string|string", (url, hashrp))

    def isOp(self):
        """
        :returns: whether or not the player is currently a server operator.
        Accepts player as OP based on either the username OR server UUID.
        This should NOT be used in a recursive loop (like a protection plugin, etc)
        or a very frequently run function because it accesses the disk file
        (ops.json) at each call!  Use of isOP_fast() is recommended instead.
        """

        operators = self._read_ops_file()
        for ops in operators:
            if ops["uuid"] == self.serverUuid.string or ops["name"] == self.username:
                return True
        return False

    def isOp_fast(self):
        """
        :returns: whether or not the player is currently a server operator.
        Works like isOp(), but uses an oplist cached from the __init__ of the player.py api for this player.
        Suitable for quick fast lookup without accessing disk, but someone who is deopped after the
        player logs in will still show as OP.
        """
        for ops in self.operatordict:
            if ops["uuid"] == self.serverUuid.string or ops["name"] == self.username:
                return True
        return False

    # region Visual notifications
    def message(self, message=""):
        if isinstance(message, dict):
            self.wrapper.server.console("tellraw %s %s" % (self.username, json.dumps(message)))
        else:
            self.wrapper.server.console("tellraw %s %s" % (self.username, self.wrapper.server.processColorCodes(message)))

    def actionMessage(self, message=""):
        if self.getClient().version > mcpacket.PROTOCOL_1_8START:
            self.getClient().packet.send(self.clientPackets.CHAT_MESSAGE, "string|byte",
                                         (json.dumps({"text": self._processOldColorCodes(message)}), 2))

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
            self.getClient().packet.send(self.clientPackets.SET_EXPERIENCE, "float|varint|varint", (progress, level, total))
        else:
            self.getClient().packet.send(self.clientPackets.SET_EXPERIENCE, "float|short|short", (progress, level, total))

    def openWindow(self, windowtype, title, slots):
        """
        Opens an inventory window on the client side.  EntityHorse is not supported due to further EID requirement.

        Args:
            windowtype:  Window Type (text string). See below or applicable wiki entry (for version specific info)
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
                self.clientPackets.OPEN_WINDOW, "ubyte|string|json|ubyte", (
                    self.getClient().windowCounter, windowtype, {"text": title}, slots))
        return None  # return a Window object soon
    # endregion Visual notifications

    # region Abilities & Client-Side Stuff
    def getClientPacketList(self):
        """
        Allow plugins to get the players client plugin list per their client version
        e.g.:
        packets = player.getClientPacketList()
        player.client.packet.send(packets.PLAYER_ABILITIES, "byte|float|float", (0x0F, 1, 1))
        """
        return self.clientPackets


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
        self.getClient().packet.send(self.clientPackets.PLAYER_ABILITIES, "byte|float|float",
                              (bitfield, self.fly_speed, self.field_of_view))
        self.getClient().server.packet.send(self.serverPackets.PLAYER_ABILITIES, "byte|float|float",
                                     (bitfield, self.fly_speed, self.field_of_view))


    # Unfinished function, will be used to make phantom blocks visible ONLY to the client
    def setBlock(self, position):
        pass
    # endregion

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

        #this might be a useful thing to implement into all permissions methods
        uuid_to_check = self.mojangUuid.string
        if node is None:
            return True
        if another_player:
            other_uuid = self.wrapper.getUUIDByUsername(another_player)  # get other player mojang uuid
            if other_uuid: # make sure other player permission is initialized.
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
        itemsToProcess = allgroups[:]  # process and find child groups
        while len(itemsToProcess) > 0:
            parseparent = itemsToProcess.pop(0)
            for groupPerm in self.permissions["groups"][parseparent]["permissions"]:
                if (groupPerm in self.permissions["groups"]) and \
                        self.permissions["groups"][parseparent]["permissions"][groupPerm] and (groupPerm not in allgroups):
                    allgroups.append(groupPerm)
                    itemsToProcess.append(groupPerm)
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

        If the player does not have the specific permission, an IndexError is raised. Note that this method has no
        effect on nodes inherited from groups or plugin defaults.

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
        self.log.debug("Player %s uuid:%s does not have permission node '%s'", (self.username, self.mojangUuid.string, node))
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
        self.log.debug("Player %s uuid:%s: Could not be added to group '%s'", (self.username, self.mojangUuid.string, group))
        return False

    def removeGroup(self, group):
        """ Removes the player to a specified group. If they are not part of the specified group, an IndexError is raised.
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

