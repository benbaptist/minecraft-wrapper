
**class Minecraft**

    This class contains functions related to in-game features
    directly. These methods are accessed using 'self.api.minecraft'

    

**def configWrapper(self, section, config_item, new_value, reload_file=False)**

        *New feature starting in version 0.8.12*

        Edits the Wrapper.Properties.json file

        :Args:
            :section:

            :config_item:

            :new_value:

            :reload_file: True to reload the config

        :returns: True or False, indicating Success or Failure

        

**def isServerStarted(self)**

        Return a boolean indicating if the server is
        fully booted or not.

        

**def getTimeofDay(self, dttmformat=0)**

        get the "virtual" world time of day on the server.

        :arg dttmformat: 0 = ticks, 1 = Military, (else = civilian AM/PM).

            :ticks: are useful for timebased- events (like spawing
             your own mobs at night, etc).
            :Miliary/civilian: is useful for player displays.

        :returns: The appropriately formatted time string

        

**def giveStatusEffect(self, player, effect, duration=30, amplifier=30)**

        Gives the specified status effect to the specified target.

        :Args: (self explanatory? -see official Minecraft Wiki)

            :player: A player name or any valid string target
             selector (@p/e/a) with arguments ([r=...], etc)
            :effect:
            :duration:
            :amplifier:

        :returns: Nothing; runs in console

        

**def getAllPlayers(self)**

        Returns a dict containing the uuids and associated
        login data of all players ever connected to the server.

        

**def getPlayers(self)**

        Returns a list of the currently connected players.

        

**def getEntityControl(self)**

        Returns the server's entity controls context.  Will be None if
        the server is not up.

        Supported variables and methods:

        :These variables affect entity processing:
            :Property: Config Location

            :self.entityControl:
             config["Entities"]["enable-entity-controls"]

            :self.entityProcessorFrequency:
             config["Entities"]["entity-update-frequency"]

            :self.thiningFrequency:
             config["Entities"]["thinning-frequency"]

            :self.serverStartThinningThreshshold:
             config["Entities"]["thinning-activation-threshhold"]

        :See api.entity for more about these methods:

                def killEntityByEID(self, eid, dropitems=False, count=1)

                def existsEntityByEID(self, eid)

                def getEntityInfo(self, eid)

                def countEntitiesInPlayer(self, playername)

                def countActiveEntities(self)

                def getEntityByEID(self, eid)


        

**def getPlayer(self, username="")**

        Returns the player object of the specified logged-in player.
        Will raise an exception if the player is not logged in.

        :arg username: playername

        :returns: The Player Class object for "playername".

        

**def getOfflineUUID(self, name)**


        :arg name: gets UUID object based on "OfflinePlayer:<name>"

        :returns: a MCUUID object based on the name

        

**def lookupUUID(self, uuid)**

        Returns a dictionary of {"uuid: the-uuid-of-the-player,
        "name": playername}. legacy function from the old 0.7.7 API.

        lookupbyUUID() is a better and more direct way to get the
        name from a uuid.

        :arg uuid:  player uuid

        :returns: a dictionary of two items, {"uuid: <player-uuid>,
         "name": <playername>}

        

**def lookupbyUUID(self, uuid)**

        Returns the username from the specified UUID.
        If the player has never logged in before and isn't in the user
        cache, it will poll Mojang's API.  The function will return
        False if the UUID is invalid.

        :arg uuid: string uuid with dashes

        :returns: username

        

**def lookupbyName(self, name)**

        Returns the UUID from the specified username.
        If the player has never logged in before and isn't in the
        user cache, it will poll Mojang's API.  The function will
        return False if the name is invalid.

        :arg name:  player name

        :returns: a UUID object (wrapper type MCUUID)

        

**def setLocalName(self, MojangUUID, desired_name, kick=True)**

        Set the local name on the server.  Understand that this
        may cause a vanilla server UUID change and loss of player
        data from the old name's offline uuid.

        

**def console(self, string)**

        Run a command in the Minecraft server's console.

        :argstring: Full command text(without slash)

        :returns: Nothing

        

**def message(self, destination="", jsonmessage="")**

        Used to message some specific target.

        :Args:
            :destination: playername or target
             selector '@a', 'suresttexas00' etc
            :jsonmessage: strict json chat message

        :returns: Nothing; succeeds or fails with no programmatic indication.

        

**def broadcast(self, message="", irc=False)**

        Broadcasts the specified message to all clients connected.
        message can be a JSON chat object, or a string with formatting
        codes using the & as a prefix. Setting irc=True will also
        broadcast the specified message on IRC channels that Wrapper.py
        is connected to. Formatting might not work properly.

        :Args:
            :message:  The message
            :irc: Also broadcast to IRC if set to True.

        :returns:  Nothing

        

**def setBlock(self, x, y, z, tilename, datavalue=0, oldblockhandling="replace", datatag=None)**

        Sets a block at the specified coordinates with the specific
        details. Will fail if the chunk is not loaded.

        :Args:  See the minecraft command wiki for these setblock arguments:

                :x:
                :y:
                :z:
                :tilename:
                :datavalue:
                :datatag:
                :oldblockhandling:

         :returns: Nothing.

        

**def summonEntity(self, entity, x=0, y=0, z=0, datatag=None)**

        Summons an entity at the specified coordinates with the
        specified data tag.

        :Args:

                :entity: string entity name type (capitalized correctly!)
                :x: coords
                :y:
                :z:
                :datatag: strict json text datatag


        :returns: Nothing - console executes command.

        

**def teleportAllEntities(self, entity, x, y, z)**

        Teleports all of the specific entity type to the specified coordinates.

        :Args:
                :entity: string entity name type (capitalized correctly!)
                :x: coords
                :y:
                :z:

        :returns: Nothing - console executes command.

        

**def getLevelInfo(self, worldname=False)**

        Get the world level.dat.

        :arg worldname:
            optional world name.  If not
            specified, Wrapper looks up the server worldname.

        :returns: Return an NBT object of the world's level.dat.

        

**def getGameRules(self)**

        Get the server gamerules.

        :returns: a dictionary of the gamerules.

        

**def getSpawnPoint(self)**

        Get the spawn point of the current world.

        :returns: Returns the spawn point of the current world.

        

**def getTime(self)**

        Gets the world time in ticks.  This is total ticks since
        the server started! modulus the value by 24000 to get the time.

        :returns: Returns the time of the world in ticks.

        

**def getServer(self)**

        Returns the server context.  Use at own risk - items
        in server are generally private or subject to change (you are
        working with an undefined API!)... what works in this wrapper
        version may not work in the next.

        :returns: The server context that this wrapper is running.

        

**def getServerPath(self)**

        Gets the server's path.

        

**def getWorld(self)**

        Get the world context

        :returns: Returns the world context of 'api.world, class World'
         for the running server instance

        

**def getWorldName(self)**

        Returns the world's name.

        

**def getUuidCache(self)**

        Gets the wrapper uuid cache.  This is as far as the API goes.
        The format of the cache's contents are undefined by this API.

        

**def banUUID(self, playeruuid, reason="by wrapper api.", source="minecraft.api", expires=False)**

        Ban a player using the wrapper proxy system.

        :args:

                :playeruuid: Player's uuid... specify the mojangUuid
                 for online ban and offlineUuid for offline bans.

                :reason: Optional text reason.

                :source: Source (author/op) of ban.

                :expires: Optional expiration in time.time() format.
                 Expirations only work when wrapper handles the login
                 (proxy mode).. and only for online bans.

        :returns: String describing the operation's outcome.

        

**def banName(self, playername, reason="by wrapper api.", source="minecraft.api", expires=False)**

        Ban a player using the wrapper proxy system.  Will attempt to
        poll or read cache for name. If no valid name is found, does a
        name-only ban with offline-hashed uuid

        :args:

                :playername: Player's name... specify the mojangUuid for online
                 ban and offlineUuid for offline bans.

                :reason: Optional text reason.

                :source: Source (author/op) of ban.

                :expires: Optional expiration in time.time() format.
                 Expirations only work when wrapper handles the login
                 (proxy mode).. and only for online bans.

        :returns: String describing the operation's outcome.

        

**def banIp(self, ipaddress, reason="by wrapper api.", source="minecraft.api", expires=False)**

        Ban an ip address using the wrapper proxy system. Messages
        generated by process can be directed to a particular player's
        client or to the Console (default). Ban will fail if it is not
        a valid ip4 address.

        :args:

                :ipaddress: IP address to ban
                :reason: Optional text reason
                :source: Source (author/op) of ban.
                :expires: Optional expiration in time.time() format.

        :returns: String describing the operation's outcome.

        

**def pardonName(self, playername)**

        Pardon a player.

        :arg playername:  Name to pardon.

        :returns: String describing the operation's outcome.

        

**def pardonUUID(self, playeruuid)**

        Pardon a player by UUID.

        :arg playeruuid:  UUID to pardon

        :returns: String describing the operation's outcome.

        

**def pardonIp(self, ipaddress)**

        Pardon an IP.

        :arg ipaddress: a valid IPV4 address to pardon.

        :returns:  String describing the operation's outcome.

        

**def isUUIDBanned(self, uuid)**

        Check if a uuid is banned.  Using this method also refreshes
        any expired bans and unbans them.

        :arg uuid: Check if the UUID of the user is banned

        :returns: True or False (banned or not banned)

        

**def isIpBanned(self, ipaddress)**

        Check if a ipaddress is banned.  Using this method also
        refreshes any expired bans and unbans them.

        :arg ipaddress: Check if an ipaddress is banned

        :returns: True or False (banned or not banned)

        
