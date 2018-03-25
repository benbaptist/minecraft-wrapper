
**< class Player(object) >**

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

    -  Config file items and layout

'''

*wrapperconfig.py is the default config file.  Changes made
here are inserted or deleted from the the wrapper config
each time wrapper starts.*

*The wrapper.config.json file contents will look like this,
but without all the comment lines.*

'''

CONFIG = {

# Backups - Automatic backups with pruning. Intervals are specified in seconds.

    "Backups":

            "backup-compression": False,

         # Specify server files and folders you want backed up.  Items must be in your server folder (see 'General' section)

            "backup-folders":

                [
                    "server.properties",

                    "world",

                    "wrapper-data",

                ],

         # backup interval in seconds: 3600 = hourly, 86400 = Daily, 604800 = weekly

            "backup-interval": 3600,

         # backup location is inside wrapper's directory, unless you use an absolute path (such as /home/otherdirectory/backups)

            "backup-location": "backup-directory",

            "backup-notification": True,

            "backups-keep": 10,

            "enabled": False


# Alerts - provide email or other notification of wrapper problems (server down, etc).

    "Alerts":


         # with some modern email providers, you may need to "allow less secure apps” on your account..

         # You should use a dedicated email with a password that is different from your other accounts for this purpose.

            "enabled": False,

         # enable a server item by setting login name to something other than "False".  Use your email address for login-name and the associated password (encrypt it first).

            "servers": [

                {

         # built in alerts use "wrapper" group.

                    "group": "wrapper",

                    "subject": "Wrapper.py Alert",

                    "type": "email",

                    "address": "smtp.gmail.com",

                    "port": 587,

                    "login-name": False,

                    "encrypted-password": "Copy and Paste from 'password' after wrapper encrypts it.",

                    "recipients": ["email1@provider.com", "email2@provider.com"]

                }
            ],


         # -plaintext items are converted to hashed items by wrapper

            "password-plaintext": False,

            "password": "use `/password -s Alerts password <your password>` to set this (or enter a password-plaintext).",


# Gameplay - miscellaneous configuration items.

    "Gameplay":

         # Use of timer-tick is not recommended.  1/20th of a second timer option for plugin use. May impact wrapper performance negatively.

            "use-timer-tick-event": False,


# Entity processing - This is somewhat superfluous now that minecraft has more built-in entity management gamerules now.  Must be turned on to use player.mount / unmount events.

    "Entities":

         # whether to use the wrapper entity controls.  With new minecraft versions, these are largely unnecessary and better done with the Gamerules.

            "enable-entity-controls": False,

         # how often the entity processor updates world entity counts

            "entity-update-frequency": 4,

         # how often thinning of mobs runs, in seconds.  a large difference between this and the entity update frequency will ensure no 'overkill" occurs.

            "thinning-frequency": 30,

         # when mobs < this threshhold, thinning is inactive (server or player)

            "thinning-activation-threshhold": 100,

         # The following items thin specific mobs over the stated count.  This only happens after the total mob count threshold above is met first.  For example, 'thin-Cow: 40` starts thinning cows > 40.  Entity names must match minecraft naming exactly as they would appear in the game.

         # Check /wrapper-data/json/entities.json

         # there are some surprising changes after 1.11, like "PigZombie" is now zombie_pigman and EntityHorse is horse, etc.  Sheep, Cow, anc Chicken are now lower case: sheep, cow, chicken.. etc.

            "thin-cow": 40,

            "thin-zombie_pigman": 40,

            "thin-sheep": 40,

            "thin-chicken": 30


# Updates - Control wrapper update behaviour.

    "Updates":

         # Use one of the names listed herein (i.e. 'stable-branch')

            "auto-update-branch": None,

         # If True, an "auto-update-branch" must be specified.

            "auto-update-wrapper": False,

         # You can point these to another branch, if desired.

            "stable-branch": "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master",

            "dev-branch": "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development",


# Misc - look 'n' feel type customizations

    "Misc":

         # Reboot message occurs with automatic timed server restarts ["General"]["timed-reboot"]

            "reboot-message": "Server is conducting a scheduled reboot. The server will be back momentarily!",

         # Restart message occurs when console command "/restart" is run.

            "default-restart-message": "Server restarting...",

         # Stop message is generated from wrapper "/stop" command.

            "stop-message": "Stopping The Minecraft Server",

         # message when wrapper halt is called.

            "halt-message": "Halting Wrapper...",

         # Specify if wrapper should trap control-z and shutdown in a controlled manner (similar to ctrl-c).  If false, follows the behavior permitted by your system (and that might not end well!)  - Discussion: https://github.com/benbaptist/minecraft-wrapper/issues/521

            "trap-ctrl-z": True,

         # Use-betterconsole replaces "use-readline" for clarity about what this option does.  The default is False because use-betterconsole may not be fully cross-platform.  Better Console makes it easier for the console operator too see what they are typing, even while the server or wrapper my be writing output at the same time, essentially produces jline-like functionality to the wrapper console...

            "use-betterconsole": False,


# General wrapper and server startup options

    "General":

         # restart server automatically if it stops (unless you explicity used the "/stop" command within the console).

            "auto-restart": True,

         # You will need to update this to your particular server start command line.

            "command": "java -jar -Xmx2G -Xms1G server.jar nogui",

         # If not uft-8, specify your system's encoding here.

            "encoding": "utf-8",

         # Using the default '.' roots the server in the same folder with wrapper. Change this to another folder to keep the wrapper and server folders separate.  Do not use a trailing slash...  e.g. - '/full/pathto/the/server'.  relative paths are ok too, as long as there is no trailing slash.  For instance, to use a sister directory, use `../server`.

            "server-directory": ".",


            "shell-scripts": False,

            "timed-reboot": False,

         # salt is used internally for wrapper encryption.  Do not edit this; Wrapper will create the salt.  It does not matter much that it is on disk here, as the user must create a passphrase also.  This just prevents the need for a hardcoded salt and ensures each wrapper installation will use a different one.

            "salt": False,

            "timed-reboot-minutes": 1440,

            "timed-reboot-warning-minutes": 5,


# IRC - This allows your users to communicate to and from the server via IRC and vice versa.

    "IRC":

            "autorun-irc-commands":

                [
                    "COMMAND 1",

                    "COMMAND 2"

                ],

            "channels":

                [
                    "#wrapper"

                ],

            "command-character": ".",

            "control-from-irc": False,

         # enter a password here and wrapper will convert it to a hashed password

            "control-irc-pass-plaintext": False,

            "control-irc-pass": "from console use `/password IRC control-irc-pass <your password>`",

            "irc-enabled": False,

            "nick": "MinecraftWrap",

            "obstruct-nicknames": False,

         # enter a password here and wrapper will convert it to a hashed password

            "password-plaintext": False,

            "password": "from console use `/password IRC password <your password>`",

            "port": 6667,

            "server": "benbaptist.com",

            "show-channel-server": True,

            "show-irc-join-part": True

# Proxy settings -

# This is a man-in-the-middle proxy similar to BungeeCord, which is used for extra plugin functionality. Online-mode must be set to False in server.properties. Make sure that the server port is not accessible directly from the outside world.

# Note: the online-mode option here refers to the proxy only, not to the server's offline mode.  Each server's online mode will depend on its setting in server.properties.  If you experience issues, you might try turning network-compression-threshold to -1 (off) in server.properties.

    "Proxy":

         # Must be a single character.

            "command-prefix": "/",

         # This will kick players that are not in the playerlist (because they entered the server port directly).

            "disconnect-nonproxy-connections": True,

         # The number of players the proxy will hold.  This includes connected players from all hub worlds

            "max-players": 1024,

         # Auto name changes causes wrapper to automatically change the player's server name.  Enabling this makes name change handling automatic, but will prevent setting your own custom names on the server.

            "auto-name-changes": True,

         # the wrapper's online mode, NOT the server.

            "online-mode": True,

            "proxy-bind": "0.0.0.0",

            "proxy-enabled": False,

         # the wrapper's proxy port that accepts client connections from the internet. This port is exposed to the internet via your port forwards.

            "proxy-port": 25565,

         # silent bans cause your server to ignore sockets from that IP (for IP bans). This will cause your server to appear offline and avoid possible confrontations.

            "silent-ipban": True,

            "hidden-ops":

             # these players do not appear in the sample server player list pings.

                [

                    "SurestTexas00",

                    "BenBaptist"

                ],

         # set to True to use the wrapper built in Hub system (you must specify all your "worlds").

            "built-in-hub": False,

         # Define your worlds here to give players access to multiple worlds (with no plugin required).

            "worlds":

             # "world"= the name used in the hub/ command.  "port" = its value, corresponding to the local port. "desc" is the world's meta description that fits this sentence: ` Go to "".`.  `worlds` and `help` are reserved (do not use them for world names).  These names can also be used to drive the world change confirmation message, even if you are using your own player.connect() plugin.

                {

                    "world": {"port": 25565, "desc": "a world description"},

                },

# Web - Web mode allows you to control and monitor the server.  This is not a https connection.  Be mindful of that and don't use the same password you use anywhere else.  It is also advised that this be open only to the localhost.

    "Web":

            "web-allow-file-management": True,

            "web-bind": "0.0.0.0",

            "web-enabled": False,

         # enter a password here and wrapper will convert it to a hashed password

            "web-password-plaintext": False,

            "web-password": "to set this, from console use `/password Web web-password <your password>`",

            "web-port": 8070,

         # By default, wrapper only accepts connections from "safe" IP addresses.  Disable (set 'safe-ips-use' ot false) or add the IP address of computers you may use to access web mode.

            "safe-ips": ["127.0.0.1"],

            "safe-ips-use": True,

            "server-name": "Minecraft Server",

# 
-  addGroupPerm(self, groupname, permissionnode, value=True)

        Used to add a permission node to a group.

        :Args:
            :groupname: The name of the permission group.

            :permissionnode: The permission node to add to the group.
             The node can be another group!  Nested permissions must be
             enabled (see player api "hasPermission").

            :value: value of the node.  normally True to allow the
             permission, but can be false to deny the permission. For
             instance, you want a "badplayer" group to be denied some
             command that would normally be permitted.

        :returns:  string message indicating the outcome

        
-  banIp(self, ipaddress, reason="by wrapper api.", source="minecraft.api", expires=False)

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
         If there is no proxy instance, nothing is returned.

        
-  banName(self, playername, reason="by wrapper api.", source="minecraft.api", expires=False)

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
         If there is no proxy instance, nothing is returned.

        
-  banUUID(self, playeruuid, reason="by wrapper api.", source="minecraft.api", expires=False)

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
         If there is no proxy instance, nothing is returned.

        
-  blockForEvent(self, eventtype)

        Blocks until the specified event is called.
        
-  broadcast(self, message="", irc=False)

        Broadcasts the specified message to all clients connected.
        message can be a JSON chat object, or a string with formatting
        codes using the & as a prefix. Setting irc=True will also
        broadcast the specified message on IRC channels that Wrapper.py
        is connected to. Formatting might not work properly.

        :Args:
            :message:  The message
            :irc: Also broadcast to IRC if set to True.

        :returns:  Nothing

        
-  callEvent(self, event, payload, abortable=False)

        Invokes the specific event. Payload is extra information
        relating to the event. Errors may occur if you don't specify
        the right payload information.

        The only use it seems to have is internal (it is used by
        player.sendCommand().

        
-  changeServerProps(self, config_item, new_value, reload_server=False)

        *New feature starting in version 1.0*

        Edits the server.properties file

        :Args:
            :item: item, like "online-mode"

            :new_value: applicable value

            :reload_server: True to restart the server.

        Items are changed in the config, but a server restart is required to
         make the changes persist.

        
-  checkPassword(self, password, hashed_password)

        Bcrypt-based password checker.  Takes a raw string password and
        compares it to the hash of a previously hashed password, returning True
        if the passwords match, or False if not.

        Bcrypt functions are to be used where ever you are storing a user's
        password, but do not ever want to be able to "know" their password
        directly.  We only need to know if the password they supplied is
        correct or not.

        :Args:
            :password: The raw string password to be checked.
            :hashed_password: a previously stored hash.

        :returns: Boolean result of the comparison.  Returns
         False if bcrypt is not installed on the system.
        
-  configWrapper(self, section, config_item, new_value, reload_file=False)

        *New feature starting in version 0.8.12*

        Edits the Wrapper.Properties.json file

        :Args:
            :section:

            :config_item:

            :new_value:

            :reload_file: True to reload the config

        :returns: True or False, indicating Success or Failure

        
-  console(self, string)

        Run a command in the Minecraft server's console.

        :arg string: Full command text(without slash)

        :returns: Nothing

        
-  createGroup(self, groupname)

        Used to create a permission group.

        :Args:
            :groupname: The name of the permission group.


        :returns:  string message indicating the outcome

        
-  deOp(self, name_to_deop, playerObj=None,)

        De-ops player 'name_to_deop'.  If he is a super-op, the
        name is removed from superops.txt also.  Case sensitive!

        :Requires: Running server instance.

        :Args:
            :playerObj: This is the player that receives the command's
             output.  Setting 'None' uses the console operator (and
             permissions!). This player object must have OP level 10
             permission.
            :name_to_deop: The player to de-op.  Must match what is
             in superops.txt to remove superOP perms, but may deop
             the server ops.json file without case-sensitivity.

        :returns: True if success, a text message on failure.

        
-  deleteGroup(self, groupname)

        Used to delete a permission group.

        :Args:
            :groupname: The name of the permission group.


        :returns:  string message indicating the outcome

        
-  deleteGroupPerm(self, groupname, permissionnode)

        Used to remove a permission node to a group.

        :Args:
            :groupname: The name of the permission group.

            :permissionnode: The permission node to remove.

        :returns:  string message indicating the outcome

        
-  getAllPlayers(self)

        Returns a dict containing the uuids and associated
        login data of all players ever connected to the server.

        
-  getEntityControl(self)

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

            :self.startThinningThreshshold:
             config["Entities"]["thinning-activation-threshhold"]

        :See api.entity for more about these methods:

                def killEntityByEID(self, eid, dropitems=False, count=1)

                def existsEntityByEID(self, eid)

                def getEntityInfo(self, eid)

                def countEntitiesInPlayer(self, playername)

                def countActiveEntities(self)

                def getEntityByEID(self, eid)


        
-  getGameRules(self)

        Get the server gamerules.

        :returns: a dictionary of the gamerules.

        
-  getLevelInfo(self, worldname=False)

        Get the world level.dat.

        :arg worldname:
            optional world name.  If not
            specified, Wrapper looks up the server worldname.

        :returns: Return an NBT object of the world's level.dat.

        
-  getOfflineUUID(self, name)


        :arg name: gets UUID object based on "OfflinePlayer:<name>"

        :returns: a MCUUID object based on the name

        
-  getPlayer(self, username="")

        Returns the player object of the specified logged-in player.
        Will raise an exception if the player is not logged in.

        This includes players who are transferred to another server. If
        you need to test whether a player is on this server; test if
        player.client and player.client.local == True

        :arg username: playername

        :returns: The Player Class object for "playername".

        
-  getPlayers(self)

        Returns a list of the currently connected players.

        
-  getPluginContext(self, plugin_id)

        Returns the instance (content) of another running wrapper
        plugin with the specified ID.

        :arg plugin_id:  The `ID` of the plugin from the plugin's header.
         if no `ID` was specified by the plugin, then the file name
         (without the .py extension) is used as the `ID`.

        :sample usage:

            .. code:: python

                essentials_id = "com.benbaptist.plugins.essentials"
                running_essentials = api.getPluginContext(essentials_id)
                warps = running_essentials.data["warps"]
                print("Warps data currently being used by essentials: \n %s" %
                      warps)
            ..

        :returns:  Raises exception if the specified plugin does not exist.

        
-  getServer(self)

        Returns the server context.  Use at own risk - items
        in server are generally private or subject to change (you are
        working with an undefined API!)... what works in this wrapper
        version may not work in the next.

        :returns: The server context that this wrapper is running.

        
-  getServerPackets(self, packetset="CB")

        Get the current proxy packet set.  Packet use will also
        require the following import at the begining of your
        plugin:
        .. code:: python

        from proxy.utils.constants import *
        # this line is needed to access constants for packet sending/parsing.

        ..

        :packets are also available from the player.api:
            player.cbpkt
            player.sbpkt

        :Args:
           :packetset: type(string)= "CB" or "SB". Argument is optional.
            If not specified, the client-bound packetset is returned.  If
            packetset is actually anything except "CB", the server-bound
            set is returned.

        :returns: The desired packet set.

       
-  getServerPath(self)

        Gets the server's path.

        
-  getSpawnPoint(self)

        Get the spawn point of the current world.

        :returns: Returns the spawn point of the current world.

        
-  getStorage(self, name, world=False, pickle=True)

        Returns a storage object manager for saving data between reboots.

        :Args:
            :name:  The name of the storage (on disk).
            :world:  THe location of the storage on disk -
                :False: '/wrapper-data/plugins'.
                :True: '<serverpath>/<worldname>/plugins'.
            :Pickle:  Whether wrapper should pickle or save as json.

            Pickle formatting is the default. pickling is
             less strict than json formats and leverages binary storage.
             Use of json can result in errors if your keys or data do not
             conform to json standards (like use of string keys).  However,
             pickle is not generally human-readable, whereas json is human
             readable.

        :Returns: A storage object manager.  The manager contains a
         storage dictionary called 'Data'. 'Data' contains the
         data your plugin will remember across reboots.
        ___

        :NOTE: This method is somewhat different from previous Wrapper
         versions prior to 0.10.1 (build 182).  The storage object is
         no longer a data object itself; It is a manager used for
         controlling the saving of the object data.  The actual data
         is contained in the property/dictionary variable 'Data'

        ___

        :sample methods:

            The new method:

            .. code:: python

                # to start a storage:
                self.homes = self.api.getStorage("homes", True)

                # access the data:
                for player in self.homes.Data:  # note upper case `D`
                    print("player %s has a home at: %s" % (
                        player, self.homes.Data[player]))

                # to save (storages also do periodic saves every minute):
                self.homes.save()

                # to close (and save):
                def onDisable(self):
                    self.homes.close()
            ..

            the key difference is here (under the old Storage API):

            .. code:: python

                # This used to work under the former API
                # however, this will produce an exception
                # because "self.homes" is no longer an
                # iterable data set:
                for player in self.homes:  <= Exception!
                    print("player %s has a home at: %s" % (
                        player, self.homes[player]))
            ..

            **tip**
            *to make the transition easier for existing code, redefine
            your the storage statements above like this to re-write as
            few lines as possible (and avoid problems with other
            plugins that might link to your plugin's data)*:

            .. code:: python

                # change your storage setup from:
                self.homes = self.api.getStorage("homes", True)

                # to:
                self.homestorage = self.api.getStorage("homes", True)
                self.homes = homestorage.Data

                # Now the only other change you need to make is to any
                # .save() or .close() statements:
                def onDisable(self):
                    # self.homes.close()  # change to -
                    self.homestorage.close()
            ..

        
-  getTime(self)

        Gets the world time in ticks.  This is total ticks since
        the server started! modulus the value by 24000 to get the time.

        :returns: Returns the time of the world in ticks.

        
-  getTimeofDay(self, dttmformat=0)

        get the "virtual" world time of day on the server.

        :arg dttmformat: 0 = ticks, 1 = Military, (else = civilian AM/PM).

            :ticks: are useful for timebased- events (like spawing
             your own mobs at night, etc).
            :Miliary/civilian: is useful for player displays.

        :returns: The appropriately formatted time string

        
-  getUuidCache(self)

        Gets the wrapper uuid cache.  This is as far as the API goes.
        The format of the cache's contents are undefined by this API.

        
-  getWorld(self)

        Get the world context

        :returns: Returns the world context of 'api.world, class World'
         for the running server instance

        
-  getWorldName(self)

        Returns the world's name.  If worldname does not exist (server
         not started), it returns `None`.  If a server was stopped and a
         new server instance not started, it will return the old world name.

        
-  getplayerby_eid(self, eid)

        Returns the player object of the specified logged-in player.
        Will raise an exception if the player is not logged in.

        :arg eid: EID of the player

        :returns: The Player Class object for the specified EID.
         If the EID is not a player or is not found, returns False
        
-  giveStatusEffect(self, player, effect, duration=30, amplifier=30)

        Gives the specified status effect to the specified target.

        :Args: (self explanatory? -see official Minecraft Wiki)

            :player: A player name or any valid string target
             selector (@p/e/a) with arguments ([r=...], etc)
            :effect:
            :duration:
            :amplifier:

        :returns: Nothing; runs in console

        
-  hashPassword(self, password)

        Bcrypt-based password encryption.  Takes a raw string password
        returns a string representation of the binary hash.

        Bcrypt functions are to be used where ever you are storing a user's
        password, but do not ever want to be able to "know" their password
        directly.  We only need to know if the password they supplied is
        correct or not.

        :Args:
            :password: The raw string password to be encrypted.

        :returns: a string representation of the encrypted data.  Returns
         False if bcrypt is not installed on the system.

        
-  isIpBanned(self, ipaddress)

        Check if a ipaddress is banned.  Using this method also
        refreshes any expired bans and unbans them.

        :arg ipaddress: Check if an ipaddress is banned

        :returns: True or False (banned or not banned).
         If there is no proxy instance, nothing is returned.

        
-  isServerStarted(self)

        Return a boolean indicating if the server is
        fully booted or not.
        
-  isUUIDBanned(self, uuid)

        Check if a uuid is banned.  Using this method also refreshes
        any expired bans and unbans them.

        :arg uuid: Check if the UUID of the user is banned

        :returns: True or False (banned or not banned)
         If there is no proxy instance, None is returned.

        
-  lookupUUID(self, uuid)

        Returns a dictionary of {"uuid: the-uuid-of-the-player,
        "name": playername}. legacy function from the old 0.7.7 API.

        lookupbyUUID() is a better and more direct way to get the
        name from a uuid.

        :arg uuid:  player uuid

        :returns: a dictionary of two items, {"uuid: <player-uuid>,
         "name": <playername>}

        
-  lookupbyName(self, name)

        Returns the UUID from the specified username.
        If the player has never logged in before and isn't in the
        user cache, it will poll Mojang's API.  The function will
        return False if the name is invalid.

        :arg name:  player name

        :returns: a UUID object (wrapper type MCUUID)

        
-  lookupbyUUID(self, uuid)

        Returns the username from the specified UUID.
        If the player has never logged in before and isn't in the user
        cache, it will poll Mojang's API.  The function will return
        False if the UUID is invalid.

        :arg uuid: string uuid with dashes

        :returns: username

        
-  makeOp(self, nametoOP, argslist, playerObj=None)

        Ops player 'nametoOP'.  Case sensitivity and other
        bahaviors of the command vary with server status and
        the arguments to 'argslist'

        :nametoOP: Name of player to OP.

        :playerObj: This is the player that receives the command's
         output.  Setting 'None' uses the console operator (and
         permissions!). This player object must have OP level 10
         permission.

        :Valid args for argslist:
            :-s: make player superop.txt entry.  Player will still
             not be superOP unless given appropriate level.
            :-o: use offline name and uuid.  This option only
             works if the server is not running!  Otherwise,
             the server uses its' default (depending on server
             mode).
            :-l: Flag for next argument to be a number
             corresponding to the desired level.  If the server is
             running, this argument only superops.txt is updated.
             if server is not running, the json.ops is also
             updated (to a maximum level of 4).
            :<number>: A number corresponding to the desired
             '-l' level.  These are two separate arguments and
             this number must be the next argument after -l in
             the list.

        :Notes:
            - Json.ops controls minecraft server permissions.
              This command CAN alter json.ops if the server is
              not running.
            - superops.txt controls wrapper commands, INCLUDING
              proxy ban commands.

        :returns: Nothing.  All output is directed to playerObj.

        
-  message(self, destination="", jsonmessage="")

        Used to message some specific target.

        :Args:
            :destination: playername or target
             selector '@a', 'suresttexas00' etc
            :jsonmessage: strict json chat message

        :returns: Nothing; succeeds or fails with no programmatic indication.

        
-  pardonIp(self, ipaddress)

        Pardon an IP.

        :arg ipaddress: a valid IPV4 address to pardon.

        :returns:  String describing the operation's outcome.
         If there is no proxy instance, nothing is returned.

        
-  pardonName(self, playername)

        Pardon a player.

        :arg playername:  Name to pardon.

        :returns: String describing the operation's outcome.
         If there is no proxy instance, nothing is returned.

        
-  pardonUUID(self, playeruuid)

        Pardon a player by UUID.

        :arg playeruuid:  UUID to pardon

        :returns: String describing the operation's outcome.
         If there is no proxy instance, nothing is returned.

        
-  refreshOpsList(self)

        OPs list is read from disk at startup.  Use this method
        to refresh the in-memory list from disk.

        
-  registerCommand(self, command, callback, permission=None)

        This registers a command that, when entered by the Minecraft
        client, will execute `callback(player, args)`. permission is
        an optional attribute if you want your command to only be
        executable if the player has a specified permission node.

        :Args:
            :command:  The command the client enters (without the
             slash).  using a slash will mean two slashes will have
             to be typed (e.g. "/region" means the user must type "//region".

            :callback:  The plugin method you want to call when the
             command is typed. Expected arguments that will be returned
             to your function will be: 1) the player  object, 2) a list
             of the arguments (words after the command, stripped of
             whitespace).

            :permission:  A string item of your choosing, such as
             "essentials.home".  Can be (type) None to require no
             permission.  (See also `api.registerPermission` for another
             way to set permission defaults.)

        :sample usage:

            .. code:: python

                self.api.registerCommand("home", self._home, None)
            ..

        :returns:  None/Nothing

        
-  registerEvent(self, eventname, callback)

        Register an event and a callback function. See
         https://github.com/benbaptist/minecraft-wrapper/blob/development/documentation/events.rst
         for a list of events.

        :Args:
            :eventname:  A text name from the list of built-in events,
             for example, "player.place".
            :callback: the plugin method you want to be called when the
             event occurs. The contents of the payload that is passed
             back to your method varies between events.

        :returns:  None/Nothing

        
-  registerHelp(self, groupname, summary, commands)

        Used to create a help group for the /help command.

        :Args:
            :groupname: The name of the help group (usually the plugin
             name). The groupname is the name you'll see in the list
             when you run '/help'.

            :summary: The text that you'll see next next to the help
             group's name.

            :commands: a list of tuples in the following example format;

                .. code:: python

                    [("/command <argument>, [optional_argument]", "description", "permission.node"),
                    ("/summon <EntityName> [x] [y] [z]", "Summons an entity", None),
                    ("/suicide", "Kills you - beware of losing your stuff!", "essentials.suicide")]
                ..

        :returns:  None/Nothing

        
-  registerPermission(self, permission=None, value=False)

        Used to set a default for a specific permission node.

        Note: *You do not need to run this function unless you want*
        *certain permission nodes to be granted by default.*
        *i.e., 'essentials.list' should be on by default, so players*
        *can run /list without having any permissions*

        :Args:
            :permission:  String argument for the permission node; e.g.
             "essentials.list"
            :value:  Set to True to make a permission default to True.

        :returns:  None/Nothing

        
-  resetGroups(self)

        resets group data (removes all permission groups).

        :returns:  nothing

        
-  resetUsers(self)

        resets all user data (removes all permissions from all users).

        :returns:  nothing

        
-  sendAlerts(self, message, group="wrapper", blocking=False)

        Used to send alerts outside of wrapper (email, for instance).

        :Args:
            :message: The message to be sent to the servers configured
             and listed in the wrapper.propertues ["Alerts"]["servers"]
             list.
            :group: message will be sent to each of the emails/servers
             listed that have the matching "group" in
             wrapper.properties.json["Alerts"]["servers"][<serverindex>]["group"]
            :blocking: if True, runs non-daemonized and holds up continued
             wrapper execution until sending is complete.  You would want this
             set to False normally when dealing with players.  However, at an
             'onDisable' plugin event, or anywhere else wrapper execution may end
             abruptly, blocking may be advisble to ensure the emails finish.

        :returns:  None/Nothing

        
-  sendEmail(self, message, recipients, subject, group="wrapper", blocking=False)

        Use group email server settings to email a specified set of recipients
        (independent of alerts settings or enablement).

        :Args:
            :message: The message content to be emailed (text/string).
            :recipients: list of email addresses, type=list (even if only one)
            :subject: plain text
            :group: message will be sent using the settings in the matching
             "group" in wrapper.properties.json["Alerts"]["servers"][<serverindex>]["group"]
            :blocking: if True, runs non-daemonized and holds up continued
             wrapper execution until sending is complete.  You would want this
             set to False normally when dealing with players.  However, at an
             'onDisable' plugin event, or anywhere else wrapper execution may end
             abruptly, blocking may be advisble to ensure the emails finish.

        :returns:  None/Nothing

        
-  setBlock(self, x, y, z, tilename, datavalue=0, oldblockhandling="replace", datatag=None)

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

        
-  setLocalName(self, MojangUUID, desired_name, kick=True)

        Set the local name on the server.  Understand that this
        may cause a vanilla server UUID change and loss of player
        data from the old name's offline uuid.

        
-  summonEntity(self, entity, x=0, y=0, z=0, datatag=None)

        Summons an entity at the specified coordinates with the
        specified data tag.

        :Args:

                :entity: string entity name type (capitalized correctly!)
                :x: coords
                :y:
                :z:
                :datatag: strict json text datatag


        :returns: Nothing - console executes command.

        
-  teleportAllEntities(self, entity, x, y, z)

        Teleports all of the specific entity type to the specified coordinates.

        :Args:
                :entity: string entity name type (capitalized correctly!)
                :x: coords
                :y:
                :z:

        :returns: Nothing - console executes command.

        
-  wrapperHalt(self)

        Shuts wrapper down entirely.  To use this as a wrapper-restart
        method, use some code like this in a shell file to start
        wrapper (Linux example).  This code will restart wrapper
        after every shutdown until the console user ends it with CTRL-C.

        .. caution::
            (using CTRL-C will allow Wrapper.py to close gracefully,
            saving it's Storages, and shutting down plugins. Don't use
            CTRL-Z unless absolutely necessary!)
        ..

        :./start.sh:


            .. code:: bash

                    #! bin/bash
                    function finish() {
                      echo "Stopped startup script!"
                      read -p "Press [Enter] key to continue..."
                      exit
                    }

                    trap finish SIGINT SIGTERM SIGQUIT

                    while true; do
                      cd "/home/wrapper/"
                      python Wrapper.py
                      sleep 1
                    done
            ..

        
