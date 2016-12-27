
**class Player**

    This class is accessed either as a passed argument, or can be called using getPlayer(username).

    Player objects contains methods and data of a currently logged-in player. This object is destroyed
    upon logging off.
    

**def execute(self, string)**

        Run a command as this player. If proxy mode is not enabled,
        it simply falls back to using the 1.8 'execute' command. To be clear, this
        does NOT work with any Wrapper.py or plugin commands.  The command
        does not pass through the wrapper.

        Args:
            string: full command string send on player's behalf to server.

        Returns: Nothing; passes the server or the console as an "execute" command.

        

**def sendCommand(self, command, args)**

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

        

**def say(self, string)**

        :param string: message/command sent to the server as the player.
        Send a message as a player.

        Beware: in proxy mode, the message string is sent directly to the server
        without wrapper filtering,so it could be used to execute minecraft
        commands as the player if the string is prefixed with a slash.
        

**def getClient(self)**

        :returns: player client object
        

**def getPosition(self)**
:returns: a tuple of the player's current position x, y, z, and yaw, pitch of head.
        Notes:
        The player's position is obtained by parsing client packets, which are not sent until the
        client logs in to the server.  Allow some time after server login to verify the wrapper has had
        the oppportunity to parse a suitable packet to get the information!
        

**def getGamemode(self)**
:returns:  the player's current gamemode.
        Notes:
        The player's gammode may be obtained by parsing server packets, which are not sent until the
        client logs in to the server.  Allow some time after server login to verify the wrapper has had
        the oppportunity to parse a suitable packet to get the information!
        

**def getDimension(self)**
:returns: the player's current dimension.
        -1 for Nether,
         0 for Overworld
         1 for End.
        Notes:
        The player's position is obtained by parsing server/client packets, which are not sent until the
        client logs in to the server.  Allow some time after server login to verify the wrapper has had
        the oppportunity to parse a suitable packet to get the information!
        

**def setGamemode(self, gm=0)**

        :param gm: desired gamemode, as a value 0-3
        Sets the user's gamemode.
        

**def setResourcePack(self, url, hashrp="")**

        :param url: URL of resource pack
        :param hashrp: resource pack hash
        Sets the player's resource pack to a different URL. If the user hasn't already allowed
        resource packs, the user will be prompted to change to the specified resource pack.
        Probably broken right now.
        

**def refreshOpsList(self)**
 OPs list is read from disk at startup.  Use this method to refresh the in-memory list from disk.

**def isOp(self, strict=False)**

        Args:
            strict: True - use ONLY the UUID as verification

        returns:  A 1-4 op level if the player is currently a server operator.
                can be treated, as before, like a boolean - `if player.isOp():`, but now
                also adds ability to granularize with the OP level

        Accepts player as OP based on either the username OR server UUID.

        If a player has been opped since the last server start, ensure that you run refreshOpsList() to
        ensure that wrapper will acknowlege them as OP.

        

**def setVisualXP(self, progress, level, total)**

         Change the XP bar on the client's side only. Does not affect actual XP levels.

        Args:
            progress:  Float between Between 0 and 1
            level:  Integer (short in older versions) of EXP level
            total: Total EXP.

        Returns:

        

**def openWindow(self, windowtype, title, slots)**

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


        

**def setPlayerAbilities(self, fly)**

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

        

**def sendBlock(self, position, blockid, blockdata, sendblock=True, numparticles=1, partdata=1)**

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

        

**def getHeldItem(self)**
 Returns the item object of an item currently being held. 

**def hasPermission(self, node, another_player=False)**

        If the player has the specified permission node (either directly, or inherited from a group that
        the player is in), it will return the value (usually True) of the node. Otherwise, it returns False.

        Args:
            node: Permission node (string)
            another_player: sending a string name of another player will check THAT PLAYER's permission
                instead! Useful for checking a player's permission for someone who is not logged in and
                has no player object.

        Returns:  Boolean of whether player has permission or not.

        

**def setPermission(self, node, value=True)**

        Adds the specified permission node and optionally a value to the player.

        Args:
            node: Permission node (string)
            value: defaults to True, but can be set to False to explicitly revoke a particular permission
                from the player, or to any arbitrary value.
        Returns: Nothing

        

**def removePermission(self, node)**
 Completely removes a permission node from the player. They will inherit this permission from their
         groups or from plugin defaults.

        If the player does not have the specific permission, an IndexError is raised. Note that this method
        has no effect on nodes inherited from groups or plugin defaults.

        Args:
            node: Permission node (string)

        Returns:  Boolean; True if operation succeeds, False if it fails (set debug mode to see/log error).
    

**def hasGroup(self, group)**
 Returns a boolean of whether or not the player is in the specified permission group.

        Args:
            group: Group node (string)

        Returns:  Boolean of whether player has permission or not.
        

**def getGroups(self)**
 Returns a list of permission groups that the player is in.

        Returns:  list of groups
        

**def setGroup(self, group)**

        Adds the player to a specified group.  Returns False if group does not exist (set debiug to see error).
        Args:
            group: Group node (string)

        Returns:  Boolean; True if operation succeeds, False if it fails (set debug mode to see/log error).
        

**def removeGroup(self, group)**
 Removes the player to a specified group. If they are not part of the specified
        group, an IndexError is raised.

        Args:
            group: Group node (string)

        Returns:
            

**def getFirstLogin(self)**
 Returns a tuple containing the timestamp of when the user first logged in for the first time,
        and the timezone (same as time.tzname). 

**def connect(self, address, port)**

        Upon calling, the player object will become defunct and the client will be transferred to another
         server (provided it has online-mode turned off).

        Args:
            address: server address (local address)
            port: server port (local port)

        Returns: Nothing
        
