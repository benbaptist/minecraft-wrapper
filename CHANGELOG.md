#Changelog#
<h4>1.0.17 rc 22</h4>
-bugfix for non-proxy setups.  See Dev changelogs (on development branch).

<h4>1.0.15 rc 20</h4>
Primary reasons for update:
- Regular update prior to further new Wrapper development

Api improvements:
- Updates to NBT.py for various parts of Mincraft 1.12 and upcoming 1.13.
- version checking added to proxy/utils/encryption.py cryptography import.
- Make the packet flush times configurable since different computers and setups may have different ideal flushing intervals.
- allow different IP's for hubs (able to use 192.168.x.x, for instance).
- adds DiscordRelay plugin by @PurePi
- api.helpers.get_int - accepts possible booleans
- add Regions suite to stable plugins.
- Add base API property `wrapper_version` to allow plugins to inspect Wrapper's version.
- improved name changes to include offline hubs being able to update names too!
  : whitelist warning : Names are still whitelisted by offline name. An
   automatic name change will cause player to not be whitelisted (you will
   have to `whitelist add` the new name).
- Make wrapper current through snapshot 18w14b:
    - add protocol 368 as PROTOCOL_PRE_RELEASE
    - add PROTOCOL_PRE_RELEASE packets for CB and SB.
    - Fix slot parsing, which has changed with new snapshots.
    **TEMPORARILY BROKE / not implemented yet** - server.autoCompletes
     (parse_cb.py) event is not compliant for sending/modding the new packet.

Bugfixes:
- name changes were not actually working (old name persisted).
- Fixed wrapper's player.interact use_item event that has been broken
 ever since wrapper stopped using the old string-keys packet read() format.
- Fix error that causes wrapper to think snapshots are pre-netty.
- Fix old Py3 Errors in NBT things
- Harden up wrapper's handling of disconnected players.
- Patch resource imports that may not work on Windows.
- Fix wrapper client inventory bugs (inconsistent use of None versus {"id" = -1}
 in code.
- Various regions plugin bugfixes and improvements.
- Fix bug in api.backups.enableBackups.
- fix bug in portals.py
- fix bug clientconnection.py line 1074 (not enough args for log formatting).
- fix bug in parse_sb.py and parse_cb.py player objects, usually caused by player disconnection.
- Possibly fixed bug where we may not be shutting down client sockets when they abort,
 causing the os system file limits to be exceeded after a certain amount of time.
- fix error in backups.py.  It still referenced the "payload" argument from
 the original 'timer.second' event that used to drive it.
- bug fix packet.py line 645 that calls close_server method (which did not
 formerly exist for clientconnection.py).  added a `close_server` method to
 clientconnection.py to wrap cleintconnection's `_close_server_instance` method.
- Bugfix remove Python3 style function annotations.  Use comment style annoations instead.
- fix errors with occasional problems in playerposition and look type packets that kill the client connection.
- Fix documentation errors in block placement, digging, and interaction events.
- removed debug print statements in parse_sb.py
- Restore interact event's ability to parse the placement coords of buckets.

Refactors and code improvements:
- Change proxy.base.pollserver() to return values instead of modding wrapper's
 values directly.  This makes it a truly public function, not an internal method.
 Provides for future ability to poll other servers besides the locally wrapped one.
- Tie entitycontrol abort signal to wrapper/proxy abort signals, eliminate its' personal abort signal.
- refactor wrapper halt signal from halt to haltsig.
- Cleanup disconnection code some.
- Mark blockForEvent code as deprecated for removal by wrapper 1.0 final or
 1.1 rc.
- Only call Wrapper Alerts if enabled.- Possibly fixed bug where we may not be shutting down client sockets when they abort,
 causing the os system file limits to be exceeded after a certain amount of time.
- Remove on-second timer from backups.
- Change event coding to use a single thread for processing non-blocking events, utilizing a queue.
- Backups timer uses wrapper storage to store it's backup timer between restarts.
- Changed existing plugins that use timer.second to implement their own timers.
- Remove player.interact event out of the block placement code because there
 really is no way to tell if the client is interacting or not based on inventory.
 clicking on a chest with no item or clicking on a chest with a block in hand still
 opens the chest, for example.
- added a player object "player" to event payloads that did not have it.  This is
 only a cosmetic change in the API (and a speed optimization) because the event
 code already added "player" objects to payloads missing the player object,  This
 also corrects the documentation that did not list player as a payload.  Retained
 the "playername" payload in these events, for backwards compatibility.
- optimize the event processor thread timer.
- Improve plugin event code some.
- use collections.deque to decrease pop TimeComplexity from O(k) to O(1) in
 event handling code and packet.py processing (https://wiki.python.org/moin/TimeComplexity).

KNOWN BUG (which exists in previous release version too):
- does not work with compression disabled.

<h4>1.0.2 rc 4</h4>
Primary reasons for update:
- critical bug fix for name changes.
- Fixed a UUID error in API:
    - Turns out that plugins can call api.minecraft.lookupbyUUID and if a MCUUID
      object gets passed, you fry the wrapper cache with a non-json-serializable
      MCUUID(xx-xx--x--x--) object as the uuid index.

Changes also added:
- implement PARSER for player digging (internal refactor).
- remove some more test code (tracer branch leftovers).
- give plugins ability to return a False for onEnable().
- start adding some type-hinting to wrapper functions.
- clean up stable plugins
- made the UUID lookups for getuuidbyusername case in-sensitive.  This was
 causing un-necessary mojang API lookups during certain operations just because
 a name was not capitalized properly.  Usernames are unique regardless of
 capitalization, making this an un-needed check.
- Fix bug allowing a group to be assigned to a player more than once.
- upgrade player permission items to operate with optional uuid=<MCUUID> to
 operate upon another player (logged on or not).
- add plugins "groupsmanager" and "portals" to stable plugins.

KNOWN BUG (which exists in previous release version too):
- does not work with compression disabled.


<h4>1.0.0 rc 0</h4>
- Finished player.connect() function.
- Include sample hubworlds plugin in examples and Stable plugins.
- Implement /hub as a full featured command if ["Proxy"]["built-in-hub"] is enabled. Allows full use of hub worlds
 without requiring any plugins.
- Make player respawn to hub if destination connection fails
- Implemented "max-players" into proxy (a separate thing from the server's max players).
- wrapper uses extra LOGIN arguments and minecraft plugin chanels to communicate UUID and IP between wrapper instances.
- These plugin messages will help wrapper determine it's role (HUB or subworld),
    pass server information, manage login/logouts, pass proper online UUIDs to
    plugins even if the plugin's (local) wrapper is offline.
- Continued improvements to UUID reliability
- create a player.uuid property that reliably returns the very best (online)
 UUID it can find.  This uuid is used to positively ID a player for purposes
 of uniquely identifying that player no matter what name they have.
 - Clarify that the only uuid that is a string and not MCUUID is player
 property 'uuid'.
- kick rogue players that inadvertently join a proxy world directly to the server's port.  
- Fix bugs in Event code.  Standardize event process:
        Plugin returns   ==   event returns
        False            ==   False
        None/True        ==   True
        Payload          ==   Payload
        Multiple plugins can modify the final event return:
        Any plugin can permanently Abort the Event.  Any False is permanent.
        Any plugin can None/True, but a subsequent event can False or payload it (mod it)
        Any plugin can return a payload _if_ it has not been `False`d..
- Refactored all packet constants to a standard format:
    CONSTANT = [PACKET, [PARSING]], where PACKET = 0xNN packet number and parsing
     is a list of constants like [VARINT, BOOL, STRING].
- Corrected Entities config items listing old names (i.e. - 'Sheep' was changed to 'sheep' in 11.1)
- Added internal wrapper event 'server.autoCompletes' to process (future) autocompletions.
- Removed "player.runCommand" event from public API.  It is now private event.  Also
 changed the behaviour to not be "abortable".. I.e. any command _will_ abort and get
 processed directly by _either_ wrapper or the server.
- All registered commands and non-abortable events run on their own thread, so
  wrapper plugin and commands do not pause proxy!
- scrub out old packet.send methods that are now deprecated.
- Improved name change handling.  Name changes are now automatic.  If you don't want automatic
 name change handling, set config `["Proxy"]["auto-name-changes"] = False` and wrapper will use the
 old "falling back to..." name behavior.  If you are supporting (vanilla server) local aliases via
 a plugin, you should set this to False.
- Improve proxy to only use compression once (while reading a packet).  If a packet
 is not going to be changed, the original unmolested packet is resent, eliminating
 the need to re-compress.
- correct compression bugs where client and server could be at different compression numbers.
 _They must be operating at the same compression level now_ because of the "once-only compression"
 used by proxymode now.
- whitelist add/remove both also 'reload'... because everybody forgets that part!
- whitelist adds players using offline uuids while in proxy mode.
- install vanilla whitelist commands into 'commands.py' -off, on, add, remove, list, reload
- two new commands added:
    - /whitelist online - convert all whitelist names to online uuids (to set server to online mode)
    - /whitelist offline -  convert all whitelist names to offline uuids (to set server to offline/proxy mode)
- Whitelist online/offline also converts player data uuid files to their correct type, so converting
   the server between online and offline will not hurt players inventory (provided you restart promptly).
- [#519](https://github.com/benbaptist/minecraft-wrapper/issues/519) - delay server backups during idle periods.
- upgrade consoleuser.py for use with new player.message()
- add its 'execute()' method.
- create support for alternate output streams besides the console.
- Manually Save server before a restart (spigot plugins mess with save states).
- Ensure server auto-restarts don't happen during a backup cycle.
- added some API.backups functions to test backup status.
- Fix [#521](https://github.com/benbaptist/minecraft-wrapper/issues/521)
   using a config item in Misc: "trap-ctrl-z"
- removed option to disable wrapper passphrase.
- Player.message takes second argument for position of message (0,1,2)
- restage version.py and make buildscript.py comply with 5 part format.
- build numbers are now unique only to major version and release type (X.x.x, 'a','b', 'rc', 'final')
- remove PyCrypto dependency!  PyCrypto is no longer maintained.
- wrapper dependencies are only `requests`, `cryptography` and `bcrypt`:
- added file "requirements.txt" to be useful for `pip install -r requirements.txt`
- Fixed numerous Web module bugs plus new features:
    - Fixed bug that prevented browsing into directories with periods (like com.banbaptist.some.plugin)
    - Added a feature for only allowing connections from 'safe-ips'.
    - Server properties - can be saved and reloaded.
    - plugins - can be disabled.  If all plugins are disabled, all disabled plugins can be reloaded.
    - Py3 fixes for Web mode.
    - Add Wrapper memory usage items to Web.
    - Web console commands pass through wrappers console parsing, so that wrapper
       commands can be run in Web.
    - Allow login page to capture a unique username for the WebAdmin.

- Add api.base items to api:
  - sendAlerts(self, message, group="wrapper")
  - sendEmail( message, recipients, subject, group="wrapper")
- Built-in alerts for wrapper startup, shutdown, and crashes.  Alerts allow wrapper to send emails:
    - api.base - 
    - New wrapper.properties.json section: "Alerts".
- Warning messages in wrapper startup.
- Warning messages in Login.html.
- Add countdown timers of 45, 30, 15 and then 5-1 seconds to the reboot timers broadcasts
- Add a backups summary text.
- fix spigot bug where nicknamed players producing chat results in
 an invalid playerobject being generated with a player.message event
 because the nickname is not a logged on player.
- A few documentation updates/corrections.
- update change logs (not done properly since 0.7.7)
- Fixed #354 "Relogging as Spectator disables noclip"
- slight API change in getStorage().  Third argument for pickle (a new API addition anyway) changed slightly.


<h4>0.15.0</h4>
Build 254 [0.15.0] - Master branch update - Wrapper now implements password encryption

- added module `wrapper/utils/crypt.py` with full featured password encryption schemas:
```
    <Class Crypt>
    - `bcrypt_make_hash(password_string)` - hash a password
    - `bcrypt_check_pw(password_string, hashed_pw_str,)` check password against hash
    - `check_pw(password_string, hashed_pw_str)` Fernet password checker
    - `encrypt(data)` - do a Fernet encrypt of data.
    - `decrypt(encrypted_str_data)` - Fernet decryption of data
```
- implement a wrapper password to be used internally by wrapper to
 create the Fernet cipher used by the Crypt class.
- implement encryption hashing of all stored passwords to disk
 (web, IRC, so forth.. ).
- add config items to allow entering plaintext passwords that
 get digested and re-saved with Fernet encryption.
- Added /password command to wrapper to allow setting of encrypted
 passwords in the wrapper.config.json file.
- added plugin API (base.py) non-Fernet password handler functions:
  ```
      def hash_password(self, password):
         """ Bcrypt-based password encryption.  Takes a raw string password
         returns a string representation of the binary hash."""

      def check_password(self, password, hashed_password):
         """ Bcrypt-based password checker.  Takes a raw string password and
         compares it to the hash of a previously hashed password, returning
         True if the passwords match, or False if not.
  ```

- Bug fix [issue 492](https://github.com/benbaptist/minecraft-wrapper/issues/492):
    - Fix timer loops for reboots
    - Fix custom messages in Misc section and add new message "halt-message"
     for when wrapper is halted.
- Correct Python 3 errors in IRC (IRC now works in Python 2 and 3)
- Add explanatory comments about player object usage in strings
- Add warning log about web mode being presently broken
- fix error in core/wrapper.py that caused spamming of "Disabling proxy
 mode because ..." to the console.
- added text to the vanilla message to tell console user not only the
 port of the minecraft server, but the proxy too (if proxy is enabled).
- Few spigot fixes.


<h4>0.14.1</h4>
[0.14.1] - master branch (stable)

Build 245 [0.14.1] - Master branch update
- fix spigot login position (due to spigot pre-pending the world name to
 the player coordinates).
- Improve the non-proxy event section some.
    - Add IP address to player object from login text (so that
     non-proxy wrapper's have the player IP address).
    - Add player.teleport event (core/mcserver.py)
    - API for getPosition and getDimension given non-proxy functionality:
        -getPosition(): will return whatever position was last returned when
         a player was teleported.
        -getDimension just returns the overworld (versus returning nothing)
    - Upgraded the homes plugin to a more robust version that can work without
      proxy mode and has administrative functions to list and manage homes on
      a server.


<h4>0.13.5</h4>
[0.13.5] - master branch (stable)

- Fix minecraft.rst document header caused by module containind the name
  "class". renamed proxy/entityclasses to entitybasics.
- more touch ups to documentation.
- improve /perms:
    - reimplement RESET command
    - add individual, all user, and groups reset methods to the API
- some refactoring of command processing portions of wrapper.py, commands.py.
- various bugfixes to bugs I created.
- move pickling methods to the helpers API


<h4>0.13.4</h4>
[0.13.4] - master branch (stable)

Mostly updates to newer minecraft versions as well as lots of work with Proxy package

Dev versions [0.13.1] to [0.13.4]
- Bugfixes only

Dev version changes [0.13.0]
- Update for Minecraft 1.12.1 packets
- API was missing permission group management commands.  Added them
 to the base API:
    - createGroup(groupname)
    - deleteGroup(groupname)
    - addGroupPerm(group, node, value=True)
    - deleteGroupPerm(group, node)
    - resetGroups()  - deletes all group data
- added groupsmanager plugin an a "stable" plugins repo
- found a new 1.12 metadata data type.. cant parse it yet ('13' - nbt tag)

Dev version changes [0.12.1]
- update packet information to minecraft version 1.12
- Proxy is an independent system, save for some api.helpers dependencies.
 Proxy can now, in theory, be used without Wrapper as a stand-alone
 component for other uses.
- proxy is entirely refactored, separated proxy into several groups:
    - base.py file for main Proxy class
    - client, server, packets, utils, entity groups.
- Entity control moved to Proxy, where it belongs
- All wrapper and javaserver references finally removed.
- proxy passes information back to wrapper (or whatever system) via
 the shared data (for server and player data) or by calling events.
 The templates for these shared structures and API's are included as
 small classes in wrapper/proxy/base.py.
- Another goal of separation is to make the player api less confusing,
 since the documentation is not clear on what player API methods are
 available with/without proxy mode.  Hopefully, movement can be made
 to offer similar functionality for non-proxy mode (versus just
 generating errors when an attempt is made to access player
 data from the proxy).


<h4>0.7.8 - 0.11.x</h4>
The scope of this update has been __enormous__.  It is a completely new refactor of the old Wrapper.
It has been our intent to keep the original API intact, but some minor changes were made.  LOTS of _NEW_
features, configurations, bugfixes, and new events have been added!

**Features** *(by no means a complete list)*
- Upgraded to Python 3 (versions after 0.9.13)
- Console interface is completely revamped.
    - added ban commands (ban-ip, ban, pardon, pardon-ip)
    - colorized the menus/helps (does not use log statements for display)
    - minimal console player class added to wrapper.  Console has a fake "player" class that mimicks player methods and variables.  Presently, this allows the in-game wrapper menus and the console commands to share common methods, so that separate code is not needed to do things like...
    - Add /perms to console commands!  Add /playerstats also.. (the player.message() components of the in-game commands are passed to the console as colored print statements).
    - Added console mute (/cm) function to mute a spammy server or while running wrapper commands.
- console supports and uses colorized text.
- Old log.py removed in favor of newer one using the built-in logging module. With this overhaul,
 the logging configuration settings were stripped out of wrapper.properties and an extended
 version now resides in logging.json.
- Server and Console parsing is completely new and includes optional anti-scroll-away mode to keep your typing at the last line.
- Ability to mute server output temporarily while you work at the console.
- New console commands for modifying the config file, tracking entities, and proxy ban functions.
- Console can now run in-game wrapper commands, like "/permissions"!
- Entity tracking implemented:
    - Entities are parsed/tracked (added and removed) in wrapper's memory.
    - Entity limits/ mob controls can now be set in each players loaded chunks.
    - Api items for entities in API.entity
- Proxy mode refactored and supports newer minecraft versions with less effort.
- Proxy mode bans system functional (that operate from Mojang uuid service) in API.Minecraft.
- Tons of new API.minecraft methods, like "getGameRules()", which returns a dictionary of the server gamerules.
- More reliable permissions code in API.player.
- More fun stuff in the player API, like "setPlayerAbilities", "sendBlock", "getBedPostion" methods, and better hand/window items tracking.
- Tons of performance updates to make wrapper cycle the disks less and decrease memory leaks.
- Class API.Backups added to allow plugins to control backups.
- Improved (hopefully) event processing to allow multiple plugins to rationally use the same events.
- Fixed the pesky UUID None/False issues experienced by proxy mode.
- the server folder and wrapper folder can be truly divorced from one another with all server files in one
folder and all the wrapper files in another (making the plugin-developers decision to use world-based storages
more meaningful/consequential).
- Wrapper auto-detects the server port (removed 'server-port' from proxy config)
- Wrapper parses console output for pre-1.7 and spigot/bukkit/etc servers without using special config items.
- Wrapper config files are now in 'logging.json' and 'wrapper.properties.json' (in json format, of course)
- Speaking of which, wrapper writes all json files and storages with human-readable spacing and indents.
- wrapper handles all it's own ban code for the server (mostly for proxy mode).
- temporary bans are available (uses the "expires" field in the ban files!)
- wrapper fully handles keepalives between client and server. technically, we are moving towards the separation of client and server that could allow future functions like server restarts that don't kick players, cleaner transfers to other server instances, and a "pre-login" lobby where player can interact with wrapper before wrapper logs the player onto the server...
- custom startup/restart messages (#319)
- Add "server.lagged" event which returns payload - "ticks": (number of ticks server skipped).
- Wrapper now requires requests.  It is no longer optional based on usages (proxy-mode, etc).
- Storages are now pickled by default (avoids problems with non-text keys and other Json bugs/annoyances)
- Created new permissions code.
- Implement SuperOPs system of permissions above OP 4.

API changes:
    [Minecraft]

    - lookupName (uuid) Get name of player with UUID "uuid"
    - lookupUUID (name) Get UUID of player "name" - both will poll Mojang or the wrapper cache and return _online_ versions
    - ban code methods added (bannUUID, banName, banIp, pardonName, pardonUUID, pardonIp, isUUIDBanned, isIpBanned)
    - when using the proxy mode banning system, be aware that the server has it's own version in memory that was loaded on startup... if you run a minecarft ban or pardon, it will overwrite the disk with _its_ version!  Once the server restarts, the wrapper proxy changes on disk are safe and permanent.
    - Added def getGameRules(self) - returns: a dictionary of gamerules.
    - Added getServerPath() - since server can be in other folders now and some plugins may need to know this.
    - Added two API minecraft items to makeOP() and deOp()
    - console and in-game command connections all use wrapper's
      op/deop API.  See documention in api minecraft.

    [Player]

    - Added a "lastLoggedIn" item to player data.
    - Implemented sendBlock (the unfinished function "setBlock") to place phantom client side only blocks.
    - Added "player.usebed" event.  Payload - {"playername": self.client.username, "position": data[1]} Position is the head of the bed (x,y,z).
    - new player method getBedPostion() can get the location where the player slept.  Wrapper does not store this between client restarts!
    - ".name" and ".uuid" are deprecated properties that reference ".username" and ".mojangUuid" respectively.
    - added player .offlineUuid (offline server UUID) and .ipaddress (the actual IP from proxy) self variables.
    - quicker isOp_fast() - similar to .isOP(), but does not read ops.json file each time.  For use in iterative loops where re-reading a file is a performance issue.  Refreshes at each player login.
    - refreshOps() - refresh isOp_fast dictionary.
    - sendCommand(self, command, args) -Sends a command to the wrapper interface as the player.  Similar to execute, but will execute wrapper commands.  Example: `player.sendCommand("perms", ("users", "SurestTexas00", "info"))`
    - self.clientboundPackets / serverboundPackets - contain the packet class constants being used by wrapper.  Usage example: `player.getClient().packet.send(player.clientboundPackets.PLAYER_ABILITIES,
    "byte|float|float", (bitfield, self.fly_speed, self.field_of_view))` renaming these in the plugin code is fine:
        ```
        pktcb = player.clientboundPackets
        player.getClient().packet.send(pktcb.PLAYER_ABILITIES ...)
        ```
    - setPlayerAbilities(self, fly) - pass True to set player in flying mode.
    - added event "player.Spawn" - occurs after "player.login"; when the player actually spawns (i.e., when the player actaully sees something other than the "login, building terrain..").  This is a good place for plugins to start gathering information like player.position and such because it gives the proxy time to bather those items.  The "player.login" happens too soon for proxy to gather information on many player variables...
    - Methods in the client/server (like sending packets) are different.  Plugins doing this will need to be modified. Using the wrapper permissions or other wrapper components directly (self.wrapper.permissions, etc) by plugins will be broken with this version.

    [Entity]
    - added entity controls which are configurable.
      ```
        "Entities": {
                "enable-entity-controls": False,  # enable entity controls.
                "thinning-frequency": 10,  # how often thinning of mobs runs, in seconds
                "thinning-activation-threshhold": 100,  # when TOTAL mobs are below this number, thinning is skipped entirely
                "thin-any-mob": 50,  # any mob count above this number gets thinned.
                "thin-Cow": 30,  # Example, keeps Cows < 30.  Name must match exactly.  Overrides 'thin-any-mob'.
                "thin-Sheep": 30,
                "thin-Chicken": 30 },
      ```

    - New entity API (api.world):

      ```
            def countActiveEntities(self):
                """ return a count of all entities. """
            def getEntityInfo(self, eid):
                """ get dictionary of info on the specified EID.  Returns None if fails
            def existsEntityByEID(self, eid):
                """ A way to test whether the specified eid is valid """
            def killEntityByEID(self, eid, dropitems=False, finishstateof_domobloot=True, count=1):
                """ takes the entity by eid and kills the entity [...] "
            plus original: def getEntityByEID(self, eid):
                """ Returns the entity context or False if the specified entity ID doesn't exist."""
      ```

    [Backups]
    - create api.backups.py as a publicly accessible `self.api.backups` backup interface for plugins:
    ```
        def verifyTarInstalled(self):
            """checks for tar on users system."""
        def performBackup(self):
            """Perform an immediate backup"""
        def pruneBackups(self):
            """prune backups according to wrapper properties settings."""
        def disableBackups(self):
            """Allow plugin to temporarily shut off backups (only during this wrapper session)."""
        def enableBackups(self):
            """Allow plugin to re-enable disabled backups or enable backups during this wrapper session."""
        def adjustBackupInterval(self, desired_interval):
            """Adjust the backup interval for automatic backups."""
        def adjustBackupsKept(self, desired_number):
            """Adjust the number of backups kept."""
    ```
- [pull request #247] Bookmarks plugin by Cougar
- [pull request #248] Storage.py fixes, NBT slot reading/sending

**Developer Changes**
- __MOST IMPORTANT__ - Plugins using Storages _must_ invoke `self.<storageObject>.close()` in their `onDisable(self):` method
to ensure their data is saved on wrapper shutdown.
- If you wrote or edited wrapper code before, forget everything you learned.  It's that different.  Only the API
was (mostly) maintained for plugin compatibility. The previously documented API: http://wrapper.benbaptist.com/docs/api.html
- If your plugins accessed server or wrapper methods (maybe even via api.minecraft.getServer!), those methods are
certainly broken.  If you were using self.wrapper.someWrapperFunction, it is likely broken.  Look over the API and see
if a method was added to do what you want.  If not, please submit an issue or PR for that feature :)
- release wrapper from BBL license to GPL version 3 or later

**Bug Fixes**
- [pull request #269] Bug fixes by sasszem
- Old bugs were fixed
- TONS of new ones were added
- The code was almost broken, repaired again, and new bugs fixed.. all too
numerous to detail!
- At least a year's work of adding new bugs and fixing them!



<h4>0.7.7</h4>
This update contains an important patch regarding username changes. It is important that you update immediately if you use proxy mode, or else any players who've changed their names will be treated as new players upon logging in.

**Features**
- Added password support to IRC
- Added `show-irc-join-part` IRC config option for hiding join/part messages from IRC in-game to wrapper.properties
- Added Spigot support! Make sure your jar file is named "spigot" if it's a Spigot jar, to ensure Wrapper.py goes into Spigot-compatibility mode
  - Proxy mode should work with Spigot as well. Only tested on 1.8 Spigot
  - `/reload` command in-game warns about how it's only reloading the Wrapper's plugins and not the server's plugins
  - New proxy mode option 'spigot-mode' for handling UUIDs and IP addresses offline
- Improvements to the /playerstats command
- Added proxy option 'convert-player-files' for migrating regular servers over to proxy mode
  - Renames player files and whitelists. Will not convert bans, so banned players may become unbanned when switching to proxy mode until you manually re-ban them
- Added log rotation, and logs are now stored in logs/wrapper directory
- Added support for Minecraft protocol 54/snapshot 15w32c
- [pull request #247] New Bookmarks plugin by Cougar

**Developer Changes**
- Events which return a payload other than True/False will be passed onto the event caller
  - e.g. you can read an event such as player.rawMessage, and then `return "Different message!"` to change the message (this includes commands!)
- [pull request #178] Fixed player.setResourcePack
- [*pull request #193/#194] player.getPosition() now returns the following tuple format: (x, y, z, yaw, pitch) [MAY BREAK EXISTING PLUGINS]
- [issue #199] Added new methods for modifying player permissions:
    - player.setGroup(group)
    - player.setPermission(node, value=True) (value argument is optional, default is True)
    - player.removePermission(node)
    - player.removeGroup(group) 
- [issue #164] Implemented timer.tick event (event is called 20 times per second, like a game tick)
- [pull request #222] Added player.createsign event when player writes to a sign 

*Pull request was modified from original to better fit the API.  

**Bug Fixes/Regular**
- CRITICAL BUG FIX: Players who changeed usernames would be treated as a new user (Temporarily fixed by not allowing name changes - it'll continue to use their old usernames even after changing until we implement a workaround)
- Fixed IRC bug where unicode crashes.... AGAIN. UGH. HOW MANY TIMES DO I HAVE TO FIX THIS?
- Fixed proxy not binding when server-port is misconfigured/unable to connect to the destination server
- [issue #214] Fixed slot packet not being parsed properly and causing random disconnections
- [issue #221] api.minecraft getAllplayers filelock issue on Wind0ze
- Potentially fixed permission UUIDs being stored inconsistently (some with dashes, some without)
- Fixed issues that broke Spigot with Wrapper.py
- Fixed issues with Minecraft 1.7.10 proxy mode
- Fixed spectator teleportation while using proxy mode

- Fixed `/wrapper halt` command in-game
- Web mode fixes:
  - Escaped <>'s in the Chat tab
  - Joins and parts now show up in the Chat tab
  - "remember me" when logging in actually makes it remember you
  - "Lost Connection" page now works again 
- Fixed some proxy instabibility
- Help command page fixes
- Cross-server improvements:
  - Fixed skins and duplicating players on tab list when traversing between Wrapper.py servers
  - Weather is now accurate

**Bug Fixes/Developer**
- Fixed "KeyError: 'users'" error with .hasPermission()
- Potentially fixed issues with UUIDs being set as "None" or "False" in the Player object. If this bug persists, the console will print a message related to it. Please file a bug report containing this message.
- Fixed self.log not printing anything in console
- Better cross-server handling (i.e. player.connect() works better now)
- Better error handling for Storage objects

<h4>0.7.6</h4>
**Bug Fixes**
- Security fixes
- Fixed all players being kicked when one user logs out
- Banned players now disconnect with the reason as intended
- Changed time in backup filename from : to . for Windows compatibility
- Fixed 'enabled' configuration option for IRC and Backups by renaming IRC's enabled to irc-enabled

<h4>0.7.5</h4>
**Features**
- Web interface improvements:
  - Increased console scrollback from 200 lines to 1000 lines 
  - Added 'Server' tab with sub-tabs:
    - Moved the server console into the Server tab
    - Chat tab for chatting with both the server and IRC simutaniously
    - File manager for viewing, renaming, and deleting, in the server folder
    - Settings tab for changing server.properties and other settings
  - Other slight design improvements
- `/raw` console command

- Server MOTD can now be formatted with &codes
- Player login count, and player login and logout times are now recorded. More features to come out of this soon.

**Bug Fixes**
- Fixed error message when backups.json was corrupt with IRC turned on
- Potentially fixed CPU leak with web/proxy mode. I'm still not 100% sure what caused it and if it is actually fixed yet, though.
- Fixed crash if 'resource' module isn't installed (usually on non-POSIX systems)

**Developer Changes**
- api.registerHelp(groupName, summary, commands): Register new help menus to be displayed in the /help command. See documentation for more info
- "AUTHOR" and "WEBSITE" plugin metadata variables added (see template.py for example)
- player.say(message): Say something through the player. Proxy mode only.
- player.execute(command): Execute a command as the player. Works best in proxy mode, but will fallback to using the 1.8 'execute' command if proxy mode is not available.
- Fixed minecraft.getPlayer(username) so that it actually worked
- server.getStorageAvailable(): Returns the amount of bytes free on the disk of the working directory
- minecraft.getAllPlayers(): Returns a dict with the UUID as the key for each player that has ever joined the server, and inside each UUID is their offline player object containing stats such as first login time, player activity, and more soon. The player list is not world-specific.
- Removed event 'server.start' (redundant)

<h4>0.7.4</h4>
Just a small little update, to fix a few things, and improve upon some existing features.

**Features**
- `/wrapper halt` in-game command for killing Wrapper.py
- Improvements to the web interface:
  - Bootstrap design! Looks way nicer, but still not the final design
  - Manage plugins (list plugins and their info, reload all plugins)
    - Disabling plugins will be implemented in a future update
  - Give/take operator through player list
  - Increased server console scrollback and
  - See the faces of the players in the player list
  - Check server memory usage
    - Featuring a pretty memory graph, as well!
  - Check the filesize of the currently-loaded world
  - Other minor improvements
- Proxy mode now reads server MOTD and max player count from server.properties
- 'server-name' in wrapper.properties for naming servers (used in web interface)
- Warn users of tar not being installed when a backup begins
- Warn users of a scheduled reboot (timed-reboot-warning-minutes)
  - timed-reboot-warning-minutes actually adds extra minutes to the reboot, so if you have it setup to reboot every hour, and timed-reboot-warning-minutes is set to 5 minutes, it will reboot once every hour+five minutes.
- Check memory usage of server in IRC, console, and in-game with /wrapper mem
- Wrapper.py shuts down cleanly when it receives SIGTERM signal
- Wrapper.py remembers server state upon exit - i.e. if you `/stop` the server from the console, it will remain stopped until you `/start` it again

**Bug Fixes**
- Fixed error when player dies
- Fixed "Request Too Long" error in IRC when messages exceed the 512-byte limit
- Fixed packet error when player was kicked from server with proxy mode
- Fixed login rate-limit system
- Fixed issues with compressed backups not being pruned
- Fixed arrow key support (pull request #46)
- Fixed https:// links not being clickable from IRC->Game
- Fixed other players being invisible and not showing up in tab menu when using proxy mode offline (issue #47)
- Fixed URL-unsafe characters not working in the web interface (e.g. typing a question mark in the server console would cause issues) 

**Developer Changes**
- New events: 
  - wrapper.backupFailure(reasonCode, reasonText): Called when a backup fails for some reason.
    - reasonCode: The error code of the failure
    - reasonText: Text explaining the error
    - reasonCode types: 1: tar is not installed | 2: backup file didn't exist after backup finished | 3: one or more of the files slated to backup didn't exist, so backup was cancelled
    
Remove memory graph, unless I can fix it, because it (or something else) is making the page freeze/lag. Undefined UUID for player when nobody logged in. Ghost plugin when no plugins are installed. Server version is not always showing up.

<h4>0.7.3</h4>
At last, Wrapper.py 0.7.3 release! This is a relatively big update, and will fix a bunch of random inconsistencies in the APIs. It also adds a ton of new APIs, some big new features, and a bunch of bug fixes.

**Features**
- Web admin panel for controlling the wrapper & the server from a browser
  - It is extremely ugly, and primitive. Don't expect much yet.
- Optional backup compression (tar.gz)

- Optional auto-update system (turned off by default)
  - If auto-update-wrapper is turned on in wrapper.properties, the Wrapper will check for updates every 24 hours
  - If you are on a stable build, and a new version exists, it will download the update and will be applied when you start Wrapper.py next time
  - If you are on a development build, it won't automatically update unless auto-update-dev-build is on - it will just tell you that an update is available and you can do /update-wrapper to allow it to update
  - You can also use /update-wrapper to force check for new updates, and apply them. This works even if you turned off auto-update-wrapper.
  - If you want to jump from a stable build to the latest dev build, run /wrapper-update dev
  - If you want to jump from a dev build to the latest stable (if a newer stable version exists), run /wrapper-update stable
  - Updates can be performed in-game with the `/wrapper update` command
  - Updates can be performed from the IRC remote control interface with the 'wrapper-update' command
- IRC Remote & Web Remote will now be disabled if the password is set to 'password'

**Bug Fixes**
- Fixed "Backup file '%s' does not exist - will not backup" when conducting a backup
- Fixed "AttributeError: 'bool' object has no attribute 'clients'" when not using proxy mode
- Fixed users doing /me or /action in IRC displaying inappropriately on server
- Fixed quit messages from IRC not displaying in-game (FINALLY!)
- IRC will attempt different nicknames if the nick is already taken now
  - The first two attempts will just tack two underscores to the end of the name
  - Any futher attempts will randomize three different characters in the nickname
- Links posted inside of IRC will be clickable in-game
- Players can now leave boats/minecarts again
- Proxy mode should work with 1.7.10 now
- Fixed 'stop' in IRC remote not keeping the server off
- Fixed player position not changing while riding an entity
- Fixed backup paths with spaces not working right
  
**Developer Changes**
- New formatting code: &@ for opening URLs when clicked in game chat
  - Anything sandwiched between two &@ codes will be clickable. i.e. `&@http://benbaptist.com/&@`
- Big rewrites and internal code organization:
  - Complete rewrite of the Server class, and partial rewrite of the IRC class
  - Backup code has now been separated into the Backups class of backups.py
  - api.py is now a folder with four individual files:
    - __init__.py contains API class
    - minecraft.py contains Minecraft class
    - player.py contains Player class
    - entity.py contains Entity class and list
- New events:
  - server.starting: Called just before the server begins to boot
  - server.started: Once the server reports Done in the console and is ready for players
  - server.stopping: Called as the server starts to shutdown
  - server.stopped: Once the server has completely shutdown, and is safe to modify the world files
  - server.state(state): All of the above events consolidated into one event
  - irc.action(nick, channel, message): User doing /me or /action in an IRC channel
  - irc.quit(nick, channel, message): User quitting from IRC. 'channel' returns None currently. 'message' is their QUIT message
  - player.mount(player, vehicle_id, leash): Called when a player enters a vehicle, such as a boat, minecart, or horse.
  - player.unmount(player): Called when a player leaves a vehicle that they previously entered.
  - player.preLogin(player, online_uuid, offline_uuid, ip): Called after a client authorizees, but hasn't connected to the server yet. Can be use to prevent logins
- Changed events:
  - wrapper.backupBegin(file): file argument added
  - wrapper.backupEnd(file, status): backupFile argument renamed to file
  - wrapper.backupDelete(file): backupFile argument renamed to file
- Renamed events:
  - irc.message(nick, channel, message) from irc.channelMessage
  - irc.join(nick, channel) from irc.channelJoin
  - irc.part(nick, channel) from irc.channelPart
  - player.interact from player.action (player.action from right clicking blocks, not from /me)
- New Server class methods (accessable with api.minecraft.getServer()):
  - server.start(): Start the server (if it isn't already started)
  - server.restart(reason): Restart the server, and kick users with an optional reason (default: "Restarting server...")
  - server.stop(reason): Stop the server, kick users with a reason (default: "Stopping server..."), don't automatically start back up, but keep Wrapper.py running.
- New World class methods (accessable with api.minecraft.getWorld()):
  - world.setBlock(x, y, z, tilename, damage=0, mode="replace", data={})
  - world.fill(position1, position2, tilename, damage=0, mode="destroy", data={}): Fills the area between two coordinates with the specified block
  - world.replace(position1, position2, tilename1, damage1, tilename2, damage2=0): Replaces the blocks within two coordinates from a specific block to the specified block
  - world.getEntityByEID(eid)
- Cleaned up MORE inconsistencies in these events:
  - player.achievement
- New method: self.log.warn
- All irc.* events use "nick" instead of "user" for the payload now
- server.status renamed to server.state (from api.minecraft.getServer())
- Entity tracking system being implemented
  - Very early, buggy junk
  - Doesn't handle despawning very well quite yet, or multiple players
- player.getDimension() now properly updates when switching dimensions.

<h4>0.7.2</h4>
Server jumping still seems super buggy and weird. It only works in my test environment, but fails in other environments. I have no clue why.
- Fixed Wrapper.py not ignoring hidden files wrapper-plugins (files prefixed with a period)
- Fixed players not disappearing from tab menu with proxy mode enabled
- Wrapper.py now logs when a player joined the server for the first time
- Added APIs for checking group information about a player (player.getGroups, player.hasGroup)
- Cleaned up inconsistencies in the following events (events returning the player's name instead of the player object)
  - player.message
  - player.action
  - player.death
  - player.join
  - player.leave
- New events: 
  - server.say(message): When /say is used in the console or by a player.
  - player.chatbox(player, json): Anything that appears in a player's chatbox. Can be aborted by returning False.
- Added max-players option to proxy mode (thanks Melair!)

<h4>0.7.1</h4>
- Fixed /wrapper not working in-game
- Fixed /plugins not working in the console
- player.connect() now works as intended
- Players connected to another server via proxy (using player.connect) will now be properly booted back to the main server when disconnected
- Other extremely minor improvements 

<h4>0.7.0</h4>
- Huge Improvements to APIs
  - self.api.registerCommand() for making real /commands in-game
  - self.api.minecraft.changeResourcePack() for changing resource packs on the fly
  - Events containing the player's username should now contain the Player class
- Added a proxy mode - this is necessary for additional features of the API such as /commands and other special features
  - If you've used BungeeCord before - proxy mode should make sense. The only difference is that you don't need to make the server in offline mode.
  - Built-in commands such as /reload, /wrapper, /pl(ugins), etc.
  - Extremely experimental, near-useless server-jumping mode (doesn't work quite yet)
- Write date to log files as well as a timestamp
- Added /plugins command - was removed in the last update by mistake
- Removed IRC -> Server Line-Wrapping (each message was divided automatically every 80 characters - it was annoying)
- Fixed bug where serious plugin errors resulted in that plugin not being reloadable
- Fixed quit messages not being displayed in IRC (finally!)
- Added new shell scripting setting where you can execute certain shell scripts on specific events (NIX-only systems)
  - The schell scripts' are pregenerated with content, and has a short description of when each script is executed, and what arguments are passed to the script, if any 
  - Shell scripts are in wrapper-data/scripts

<h4>0.6.0</h4>
- Added an in-development plugin system! Super early, but it works great, it seems.
<ul>
    <li>Plugins are hosted in the 'wrapper-plugins' folder as single .py files or Python package folders</li>
    <li>Type '/plugins' in the console to see a list of loaded Wrapper.py plugins</li>
    <li>Type '/reloadplugins' to reload plugins</li>
    <li>More documentation for writing plugins will be released soon</li>
</ul> 
- Fixed crash when typing 'list' command in console (I thought I fixed this crash long ago, but apparently not!)
- Added .about command in IRC to see Wrapper.py version

I had more planned for this update, but I got busy, haven't really been able to work much on Wrapper.py as much. 
I've written part of the code for a web panel, but the code is not even close to being finished. I released 0.6 earlier
because some people really wanted the plugin functionality ASAP.

As a note, the plugin API is still very *extremely* early in development. I have a lot more planned for it, but it's still
pretty powerful as is.

<h4>0.5.0</h4>
- Fixed non-UTF-8 characters crashing Wrapper.py
- Fixed backups failing due to non-existant backup files (and changed defaults for configuration to be vanilla-friendly)
- Fixed server + console + IRC lag when the console was spammed
- Server can be started and stopped while Wrapper is running
- Wrapper.py console messages are now logged to wrapper.log
- Reorganized code a bit - split more tasks into individual threads (Wrapper seems more stable now)
<ul><li>Codebase will be split into multiple files in development, but compiled into a single package for users (it's technically a zip file disguised as a .py that Python can execute)</li></ul>

<h4>0.4.1</h4>
- Fixed m's being stripped from messages
- Fixed /halt not shutting down Wrapper.py

<h4>0.4.0</h4>
Small update, but brings one much-needed change: the new configuration file system. Change your settings in wrapper.properties now. Much nicer and update-friendly.
- Achivements are announced in IRC
- IRC bridge can be turned off so Wrapper.py can be used as a backup-only script
- New configuration file
- Obstruct usernames in IRC to refrain from pinging (currently doesn't work with colored names, known bug)
- Bug fixes:
<ul>
<li> Save-off during backup</li>
<li> Various crashes, such as when it can't connect to IRC</li>
<li> Other small fixes</li>
</ul>

#To-do List#
- Web interface improvements:
  - Add buttons to update the wrapper from it
  - Changing all settings on wrapper.properties and server.properties from it
  - Rolling back world file from backups
  - Show server ports (proxy and internal, unless proxy is disabled, then just internal.)
  - Show chat as an individual tab (without any console messages)
  - Add "remember me" checkmark, make all current sessions last 30 days instead of the default week, and then extend lifetime of session when accessed
  - Make it stream information rather than polling for the sake of bandwidth efficiency and speed
  - Change password from web panel
  - Perhaps move to Flask?
  - Implement a logged notification system - useful for critical errors that happened in the past, etc. 
- Multi-server mode (This might actually become a separate project for managing multiple servers and accounts, rather than being a Wrapper.py feature)
  - If I make it a separate project, it might use Wrapper.py as a backend for booting servers for extra features, for the sake of not duplicating code across projects
- First-run setup wizard for new setups
- Import bans from the vanilla server when using proxy mode for the first time
  - Something with whitelists too. Whitelisting and stuff is super broken with proxy mode being enabled.
- Allow fake !commands to be made with api.registerCommand() (for non-proxy mode setups)
- Hibernation mode: Wrapper.py will be able to stop the server, but listen for incoming connections and will fire the server up when someone connects. It will make logging into the server slower if the server is hibernated, but otherwise it will reduce the average load of a server box running multiple servers.
- Update code:
  - Allow auto-updating from dev build to stable, if it's the latest
  - Jumping from stable to dev manually, if the dev build is newer than the stable build
  - Create a difference between "checking for updates" and "auto-updating"
- Stop backups from happening unless server is running. Handle running out of disk space by freezing java process. Upon every boot, check level.dat and player files. If corrupted, replace from backup.
