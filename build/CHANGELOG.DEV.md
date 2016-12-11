Build 162 Version [0.9.3]
- BugFix: Added getEntityControl() to Minecraft API so plugins can actually access the new entity control methods (gasp!)
- Added getServerPath() to minecraft API (since server can be in other folders now and some plugins need to know this)
- Added utils.py Utils class to API.  These wrap some useful functions from utils.helpers.
- moved backup code out of server instance and put it in the main wrapper instance.
- removed getHelpers from api.base (added in build 121).  Being replaced by Utils class.

Build 161
- clean up example plugins.
- fix player death event death message (mcserver.py)
- Fix /playerstats command (bug in getAllPlayers)

Build 160 Version [0.9.2]
- More wrapper imports improvements to dependency import process
- Including more plugin documentation in example-plugins/example.py.
- Strip down example-plugins/template.py to the bare minimums for a plugin shell.
- Strip old 'Global' plugin dependency back out of teleport.py
- Wrapper now requires requests.  It is no longer optional based on usages (proxy-mode, etc).

Build 159
- Bugfix: - core.wrapper - renamed _shutdown() back to shutdown()

Build 158 Version [0.9.1]
refactor core.plugins module:
- Move some setup code to the init where it belongs.
- delete old plugin modules from sys.modules so they can be reloaded.  Fix issue #365.
- make import process cleaner, more elegant, give user better messages about missing dependencies.

Build 157 Version [0.9.0]
- refactor uuid and username methods out of core.wrapper and into new class UUIDS in core.mcuuid.py
- refactor commands and wrapper console commands section (make it easier to read)
- started updating master CHANGELOG.MD.
- fix update script and error in build script.  Justifies version 0.9.0

Build 156
- generate warnings on wrapper start for python versions below 2.7.
- move chattocolorcodes out of mcserver.py to utils/helpers.py where it can be properly debugged and refactored
- refactored and debugged mcserver broadcast()

Build 155
- third - fix clientconnection import errors when proxy is not used and pycrypto is not installed.

Build 154
- second (typo) - fix proxy errors when proxy is not used and pycrypto is not installed.

Build 152 - 153
- remove remaining pre-1.7 mode code.  Wrapper detects server version and adjusts accordingly.
- fix proxy errors when proxy is not used and pycrypto is not installed.

Build 151
- Minor PEP-8 and bugfix of utils/version.py
- Bugfixes to console parsing
- Modify the vanilla server's message to console about hackers connecting.

build 150
- changed server console parsing to be more independent of server versions
- refactored parsing of server output
- ... therefore, there is no "pre-1.7-mode" anymore and...
- Proxy mode automatically configures the server port to use from server output
- Proxy mode shuts off if version is pre-1.7.

Build 149  Version [0.8.18]
- BugFix broken "entity" command.
- neaten up server console parsing area.
- wrapper.py - separate the console input reading function out of the command parsing (add function getconsoleinput())
- Add "server.lagged" event which returns payload - "ticks": (number of ticks server skipped).
- Made entity processor speed configurable.
- toned down thinner code to kill less aggresively.  Merely "thins" half of any detected excess at each cycle.
- "kills" are actually "tp"'s, making the code cleaner and more reliable (server does not have to cycle doMobLoot gamerules)
- removed option to limit all mobs (it was killing item stacks and innocent mobs under certain circumstances.

Build 148
- make wrapper's output (logger.logging() and utils.helpers.readout() ) reserve the last line for user input as well.

Build 147 version [0.8.17]
- Added console mute (/cm) function to mute a spammy server or while running wrapper commands.
- More and more refactors and tweaks, like making 'ban' a server command again (versus wrapper proxy '.ban')
- add /perms to console help (the command already existed, but was not documented in help)
- OPs processing (make checking OPs less disk-intense):
    - removed operator file reads from the player object API and moved to the server object
    - OPs file is read ONCE by default, when server is instantiated, and at any starts and restarts.
    - a mcserver.py MCServer class method added to be able to refresh OPs list when changes are made.
    - The refresh_ops() will be wrapped in the player API as `refreshOpsList()` for convenience, but will obviously
     now refresh the list for ALL players.
    - isOp_fast() is removed due to not being needed (and no one probably EVER wrote a plugin dependent upon it).
- fix issue with wrapper's getuuidbyusername that could cause the person's local name on the server to revert unexpectedly.
- added neater way to read server properties and have them included in mcserver.py self.properties as a dictionary.
- add set_item() to utils.helpers.  This will allow wrapper to easily write new server.properties values to disk.
- add other nice helper functions.
- Added readchar package to utils and...
- Optional console input processing to read keystrokes (instead of waiting for /n readline) so that:
    - I can fix issue #326 https://github.com/benbaptist/minecraft-wrapper/issues/326
    - make console input even fancier.
    - staged wrapper self variables to allow up/down arrow key command history.
- removed trace-level logging.
- staged some things to start work on the ability to restart a server and keep players connected in proxy mode.

Build 146
- custom startup/restart messages (#319)

Build #145 version [0.8.16]
- Implement 'Solutions for multiple plugins using a single wrapper event' #277
- Implement "player.rawMessage" payload needs consistency of return values #340
- Pulled update items out of General config and made them their own group.
- added config item to change command prefix to something other than a '/' slash (#319)

Build #144 
- refactor API's world and entity:
    * api.entity (class EntityControl) is now the actual Entity api versus the internal tracking methods, which are now
    moved to the core.entities module.
    * removed entity api methods from api.world to api.entity.
- Added:
```
    def getGameRules(self):
        """

        returns: a dictionary of gamerules.

        """
```

Build #143
Bugfix: forgot to change api/world references to "Gameplay"/"Entities" section.

Build #142
- spammy console solution started.
- quick and dirty build to move Entity config items to it's own group:
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

Build #141
- added entity controls which are configurable.

Build #140
- Fix error in serverconnection.py:
new entities that have been added to MC version 1.11 are not yet listed in the grahamedgecombe resource.  This
results in the parse referencing an entity type ID number that does not exist in the entity type dictionary. Adjusted
code to skip such non-conforming entries.

Build #139
- Fix backups for other-folder servers.
- correct error in config that was not removing deprecated entries.
- Give the console player its own __str__ method to display "CONSOLE OPERATOR" versus <object...> stuff in wrapper.infos

Build #138  [0.8.15]
- fix the player.logout (def logout in mcserver.py) to pass a player-type object for parsing of the 'player.username'
upon exiting for the example.py plugin.  No idea what other items from player payload are in use, but they can be added
later to the MiniPlayer class.  The actual player object becomes defunct before it reaches the plugin event.
- fixed redundant logic in clientconnection.py.  Verified wrapper still functions in Proxymode for 1.11 pre-1.

Build #137  [0.8.14]
- Fix build 135's problem with sys.stdin.readline()... it needs additional .strip() to be equivalent to raw_input.
- updated the Cougar teleports.py plugin for the new wrapper logic (whichs returns None for non-existing getPlayer()'s.

Build #136
- core config.py:
    * add config items for updates.
    * correct potential for dictionary changes during iteration while detecting changes.
    * added code to remove deprecated items from the config
    * added more comments to the new default config dictionary.
- finish out updates and versioning that was in an intermediate state (switching things like "build" to "__build__")
- implement SurestTexas00 #25 by JasonBristol to add wrapper update URLs to wrapper config
- continuing refactor of core/wrapper.py
- restore timer.tick event, but it is only enabled by a new config item in new section "Gameplay".
- Fix gameplay proxy server issues caused by build 133-134

Build #135
- refactor core.wrapper.py.  Reorganize wrapper imports for readability, grouping by function.
- make console display the ConsolePlayer.message() using the passed color codes (&_) or json "color": item.
- make utils.helpers.readout() even more generic and configurable.
- refactor to remove various camelCase in various non-API places.
- remove old raw_input (py2) and input (py3) in favor of sys.stdin.readline().  It's cleaner and works well for all
    python versions (at least after 2.6).

Build 133 - 134
- Starting attempts to fix player.connect() and lobby functions.
- 134 build works with these known problems:
    1) wrapper hub can connect player to second server, but Server does not send player packets to
    position (clear "download terrain") or "respawn".  The player must die to spawn into the world.
    2) After that, it works great, until the player leaves and tries to rejoin. The second joining seems to
    "remember" toom much about the last connection
The purpose of these builds is to progressively work towards full functionality.  Each build will be better
than the last until player.connect() is fully functional.

Build #132 [0.8.13]
- Fix circular-referencing Client() class- the final argument to Client() was the client's own instance (from proxy)
- some minor refractors and edits here and there

Build #131 [0.8.12]
- Fix some broken help functionality

Build #130 [0.8.12]
- Added /kill command to console and improved error checking some more.
- Added api.minecraft function "configWrapper" to allow plugin control of wrapper configuration
- Added /config command to console (and in-game OPs) to modify the wrapper properties configuration.
- improved the readout display for console operators on some help items that use the console player.message function.
- made helpers.format_bytes more generic for future use in other modules (like web or IRC).

Build #129 [0.8.11]
- Added feature to display memory in both raw bytes and a shortened, more readable, version using appropriate
 units (KiB, MiB, GiB).

Build #128 [0.8.11]
- Refactor core.plugins.py, modularizing the various portions of the 'eachsecond' method for external use.
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

Build #127 [0.8.10]
- This was a previous snake_case build of build 128's Backups API.
```
Wrapper's orginal convention throughtout the codebase has been camelCase from the begining.  The internal code
should be converted (going forward) to snake_case per PEP-8.
However, PEP-8 also acknowledges that:

'mixedCase is allowed only in contexts where that's already the prevailing style (e.g. threading.py), to retain
backwards compatibility.'

This is certainly the case with the wrapper plugin API.  Converting the entire plugin API to snake_case will
break all existing plugins.  Creating the backups API with snake_case will create an inconsitent `look 'n feel` within
the API.  The only other alternative would be to create excessive wrappers between oldFunctions and new_functions
(and does not serve to remove the oldFunctions anyway!)
```

Build #126 [0.8.9]
- Fixed problems with last serverState not being saved properly.
- Renamed serverState to ServerStarted for clarity with regards to its boolean values.
- Fixed lots of other bugs in the start/stop functions, especially an error that could start the server twice.
- Added error checks to prevent /start/stop/restart where not appropriate (starting an already running server, etc).

Build #125 [0.8.9]
- Ensure ban commands are only handled by wrapper in proxy mode.
- Fix broken build script that was not zipping the files properly.

Build #121 [0.8.7]
- storages have a close() method, which also saves the storage. This is to be called on plugin unload.
- corrected the example plugins from save() to close().
- Added 'def getHelpers(self, attribute, yourname="callingPlugin")' to api.base.  Allow plugin API access to functions in utils.helpers.
- completed the basic entity API (api.world):
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
- Fix various errors and improved the entity processing.
- Added (more) entity management commands to console.
- improve and debug Storage.py.
- Optimizations and improvements to all of proxy. Notably:
    --better, smoother cleanup of player logouts.
    --made the 10 second delay ONLY apply when proxy could NOT bind (player logins were delayed 10 seconds previously).
    --improved the packet flushes using pop() instead of cycling through the packetlist and then setting it to [] (and hope new packets did nto arrive while going throught list!)
    --fixed disconnect messages and standardized to ALL use string text. color and bold options exist for disconnect()
    --server and client don't fight to try and shut each other down in circular manner when connections are lost.
- Fixed a few parsing bugs in serverconnection.py.
- removed proprietary/copyrighted Django code (six and termcolors).

Build #120 [0.8.6]

- lots of  internal refactoring.
- Fix smallbrother.py plugin #284 and #240
- restore api.minecraft.lookupUUID(uuid) to it's former 0.7.x behavior that returns a dictionary of the "uuid": and "name":.
- renamed the newer lookupUUID(name) and lookupName(uuid) to lookupbyName(name) and lookupbyUUID(uuid) respectively.

Build #119 [0.8.5]

- Separate path for server outside the wrapper folder supported.  Wrapper folder remains unchanged and by default, the server uses the wrapper folder too, as it always has.
    - there is no need to modify the start command in wrapper.properties.json; wrapper automatically prefixes the server path.
    - getStorage() method still takes the second (world=True) argument to put a storage object in the world (server) folder, so data can stay server-specific.
    - This also means you should not attempt to run a server as wrapper startup arguments (like `python /home/surest/MyServer/wrapper java -jar minecraft_server.1.9.2.jar nogui`).  Wrapper needs to parse the server command from wrapper.properties.json.

Build #118 [0.8.4]
- Fixed serious bug fix for wrapper.getusernamebyuuid() that will prevent new players from joining.
- Refactored config.py to use pure json (updates wrapper.properties to wrapper.properties.json).

Build #117 [0.8.3.1]
- bug fix # [SurestTexas00 #183 - 'Unable to launch'](https://github.com/suresttexas00/minecraft-wrapper/issues/183) caused by invalid PY2 argument 'exist_ok=' for os.makedirs().
- centralize the mkdir_p function to utils.helpers.
- make wrapper a little more verbose about why it can't start.
- prevent infinite loop server re-starts when wrapper cannot start a server.
- allow a few restarts to try setting EULA and server.properties

Build #116 [0.8.3]:

- [Capturing bed sleeping / right click #146](https://github.com/benbaptist/minecraft-wrapper/issues/146)
_____________________________________
- Added "player.usebed" event.  It has no payload other than the player object.  Functions purely to notify plugins that... 
- new player method getBedPostion() can get the location where the player slept.  Wrapper does not store this between client restarts!
______________________________________
- Eliminate some unneeded packet parsing.
- Add entity destroy packet to mcpacket (for future entity work)
- Proxy mode will now work with all (unmodded) minecraft versions from 1.7.2 - 1.9.4
- Fixed isOp to function in pre-1.7.6 (reads ops.json or ops.txt, depending on server version).
- Fix wrapper inventory by parsing client CLICK_WINDOW packets
- Immediately populate a logged on players EID and location (for proxy client) from the mcserver.py console parse.
- Fix lots of packet parsing problems, most of which were due to not parsing correctly for a given version.   This fixes a __lot__ of random disconnect issues.
- Implemented packet sets for mcpacket.py for ALL versions 1.7 to 1.9
- Added a (maybe temporary) slot parsing read_slot_nbtless() for cases where our parsing of the nbt slot data is not working (1.7 minecrafts).
- Added a "lastLoggedIn" item to player data.
- Implemented sendBlock (the unfinished function "setBlock") to place phantom client side only blocks.
- Removed the threaded periodicsave from Storage.  Plugin periodic saves (if desired) should be run on "ontimer".  Every plugin should already be using save() somewhere in the code anyway (like during "onDisable"). 
- added \_\_Del__ saves to various modules to implement Storage object save()'s.
- Removed deprecated proxy-storage.  Bans are stored in the server files and wrapper uses usercache for username caches.
- Add error checking to alert for player object that cannot get a client in proxy mode.
- Entities dynamically updated from http://minecraft-ids.grahamedgecombe.com on a monthly basis, if available.
- block tiles for minecraft.py are also fetched from grahamedgecombe.com.
- Destroyed entities are parsed and removed from world entities collection to await garbage collection.
- new file core.entities.py replaces items from api.entity and core.items.
- Add getOfflineUUID to player api to get an offline (local server) uuid.
- Implemented a full Entity manager with blocking locks.
- Completed kill entity by eid methods
- added the /entity command to the console and wrapper in-game commands.
- added Objects class (non-living entities that behave as blocks too). No dynamic source (yet), but primed to do so.
- fixed problems with getuuidfromname usage/implementations
- added and improved several Entity-related api.Minecraft and api.world methods.



##### update Packet read and send methods: #####
_____________________________________
read and send are now abstraction wrappers for readpkt and sendpkt.

readpkt and sendpkt are lower-level methods that eliminate the use of
string arguments like "double:xposition|double:yposition|double:zposition|bool:on_ground".

Arguments for read (like the example cited) are reduced simply to number codes (constants)
for the desired data types to be returned (i.e., 8 for "double").  Instead, in the example
cited, the readpkt argument would simply be '[8, 8, 8, 10]'.  Of course, the numbers can be
abstracted with constants for readability.  readpkt() returns a __list__ of the results in the
same order as the numbers/constants were passed.  The reading function can decide what variable names
to assign based on their list position:

```
# as used in the server or client: 
data = ["server.."].packet.readpkt([_DOUBLE, _DOUBLE, _DOUBLE, _BOOL])  # even for single arguments the [] take care of typing it as list
x, y, z, on_ground = data
# or
x = data[0]  # even if this were a single element, you must still use the index because a list gets returned.
```

similarly, packet.sendpkt() is a bit like the original send()/packet.send(), except that the
field types are abstracted numbers too and don't need the slicing operations to get the
arguments (the payload portion does not change, but must be a list or tuple).

The primary aim of these changes is to remove un-needed string operations while preserving
readability in the code.  This code is run in high frequency on a packet stream.. The
unneeded string parsing operations and the overly fancy use of slower dictionary methods
needs to be limited in this high-use code to improve wrapper's speed.


Build #114 [0.8.1]:
- A completely new rewrite.  Fully compatible with x.7.x version plugins _if_ they do not dip into wrapper's internal methods and stick strictly to the previously documented API:
http://wrapper.benbaptist.com/docs/api.html
- Methods in the client/server (like sending packets) are different.  Plugins doing this will need to be modified. Using the wrapper permissions or other wrapper components directly (self.wrapper.permissions, etc) by plugins will be broken with this version.
- I take that back about packet sending... there is a wrapper that will still allow client.send() (instead of the new client.packet.sendpkt(); However, if you have debug set to true, expect the console to get spammed with 'deprecated server.send()...' messages!

API changes Summary:

[Minecraft]

- lookupName (uuid) Get name of player with UUID "uuid"
- lookupUUID (name) Get UUID of player "name" - both will poll Mojang or the wrapper cache and return _online_ versions
- ban code methods added (bannUUID, banName, banIp, pardonName, pardonUUID, pardonIp, isUUIDBanned, isIpBanned)
- when using the proxy mode banning system, be aware that the server has it's own version in memory that was loaded on startup... if you run a minecarft ban or pardon, it will overwrite the disk with _its_ version!  Once the server restarts, the wrapper proxy changes on disk are safe and permanent.
[Player]

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

Broad-spectrum summary of changes:

[Re-vamped console interface]

- added ban commands (ban-ip, ban, pardon, pardon-ip)
- colorized the menus/helps (does not use log statements for display)
- minimal console player class added to wrapper.  Console has a fake "player" class that mimicks player methods and variables.  Presently, this allows the in-game wrapper menus and the console commands to share common methods, so that separate code is not needed to do things like... 
- Add /perms to console commands!  Add /playerstats also.. (the player.message() components of the in-game commands are passed to the console as colored print statements).

[wrapper structure in general]

- Wrapper was split into 5 modules and is prepped for packaging.
- Dashboard files were placed in a Management module.
- New utility classes were added (/utils): 
 -- encryption.py
 -- log.py
 -- termcolors.py (colored console logging!)
 -- six.py (PY3 <=> PY2 compatibility code)
 -- helpers.py (centralized high use code snippets).
 
- The logging system utilized in wrapper was overhauled and is now thread safe and features an additional level TRACE for packet tracing and other low level information. With this overhaul, the logging configuration settings were stripped out of wrapper.properties and an extended version now resides in logging.json.
- The proxy was split into individual modules instead of one large one.
 -- base.py - General functions, including various ban methods.
 -- mcpacket.py - contains general packet abstraction classes.  Defines critical-change version-to-protocol number references, start and stop points to define a given packet set, etc. Contains packet sets for all wrapper-supported minecraft versions.
 -- packet.py - old packet class; send/receive packets.
 -- clientconnection.py - old Client class.
 -- serverconnection.py - old proxy Server class (not the console server.py!)
 
- Creation of /core group where most core wrapper items reside.  Base wrapper source folder just has `__init__.py` and `__main__.py`.
- Old log.py removed in favor of newer one using the built-in logging module
- trace level logging of packet parsing is available

features/other changes:

- wrapper handles all it's own ban code for the server.
- temporary bans are available (uses the "expires" field in the ban files!)
- wrapper fully handles keepalives between client and server. technically, we are moving towards the separation of client and server that could allow future functions like server restarts that don't kick players, cleaner transfers to other server instances, and a "pre-login" lobby where player can interact with wrapper before wrapper logs the player onto the server...

ISSUES ADDRESSED:

Progresses towards:
- [Refactor Wrapper Version and Release Pipeline #299](https://github.com/benbaptist/minecraft-wrapper/issues/299)

Addresses in part:
- [Performance Updates #295](https://github.com/benbaptist/minecraft-wrapper/issues/295)
- [Python 3 #301](https://github.com/benbaptist/minecraft-wrapper/issues/301)
- [Python CPU usage creeps up over time #276](https://github.com/benbaptist/minecraft-wrapper/issues/276)

Fixes:
- [Fresh install of Wrapper.py in certain conditions does this thing #262](https://github.com/benbaptist/minecraft-wrapper/issues/262)
- [Proxy.py Rewrite #244](https://github.com/benbaptist/minecraft-wrapper/issues/244)
- [UUID set to False #227](https://github.com/benbaptist/minecraft-wrapper/issues/227)
- [Strange client.properties issue that disconnected all people #190](https://github.com/benbaptist/minecraft-wrapper/issues/190)
- [Web.py Client.runaction Action=Admin_stats dictionary problem #188](https://github.com/benbaptist/minecraft-wrapper/issues/188)
- [UUID-related error in console. #133](https://github.com/benbaptist/minecraft-wrapper/issues/133)

 
Builds - 112 - 113:
- experimental pre-releases of build #114

Build #111:
- Added dashboard.py - beginning work on Dashboard rewrite using Flask + SocketIO

Build #110:
- [pull request #269] Bug fixes by sasszem
- based on build 109 with all current pull requests as of 1/30/2016
- updated md5 to hashlib in a few places (md5 is deprecated)
- Updated the Player.chatbox event to allow the chat to modified.  Also upgraded it to handle UTF-8 and special
		characters in chat.
- added to api.minecraft: getTimeofDay(self, format=0)
		# 0 = ticks, 1 = Military, else = civilian AM/PM, return -1 if no one on or server not started
		returns actual world time of day  (changes in server.py and API/minecraft.py)
- Added Chat.py plugin example...
- ..that utilizes the new abilty of "player.chatbox" event to accept plugin changes to chat.
- Added clock.py example for getTimeofDay()
- Lots of changes to proxy.py... Added mcpkt.py file for packet number references.  Packets are now referenced (in the
		play mode sections) by names, not hardcoded packet numbers.
- Added file mcpkt.py, where packet definitions are stored for reference by proxy.py.
- Beefed up player.interact event some to allow blocking of "interaction events" like lava and water placement, shooting, etc

Build #109:
- [pull request #247] Bookmarks plugin by Cougar
- [pull request #248] Storage.py fixes, NBT slot reading/sending

Build #108:
- Disabled slot parsing for 0x30 until fixes can be made to NBT things

Build #107:
 Screw the release canidates. Just another regular build.
- [pull request #218/issue #210] Another, hopefully final fix for Wind0ze log issue
- [pull request #222] Add player.createsign event (signedit 0x12 packet)
- [pull request #219] Allow disabling plugins via plugin metadata
- [issue #221] api.minecraft getAllplayers filelock issue on Wind0ze
- Fixed spectator teleportation while using proxy mode
- Added support for Minecraft protocol 54/15w32c
- Fixed offline mode being broken

Build #106 [0.7.7 RC3]:
- [issue #210] More possible fixes for log-rotation issue on Windows
- [issue #214] Fixed slot packet not being parsed properly and causing random disconnectionss
- [issue #80] server-icon.png is now read with rb, to fix Windows compatibility
- [pull request #209/issue #131] - Make groups inherit other groups

- Plugin changes:
	- WorldEdit:
		- Fixed wand not functioning properly

Build #105 [0.7.7 RC2]:
I added a new ROADMAP.md file for keeping a nice, organized file on the future of Wrapper.py updates.

- [issue #80] server-icon.png is now loaded once prior to starting the server, to prevent file conflicts on Windows
- [issue #210] Experimental fix for log-rotation issue on Windows
- Disabled editing server.properties until fixed
- Fixed indentation inconsistencies in proxy.py

- Plugin changes:
	- WorldEdit:
		- Re-fixed double-click issue thingy or something [not entirely sure what the issue was]
		- No longer using player.execute - doesn't require op AND permission node

Build #104 [0.7.7 RC1]:
- Fixed Control+D crash
- Removed most debug printing stuff as it's mostly ready for primetime
- Fixed issue with new permissions methods not working at all

- Plugin changes:
	- WorldEdit:
		- Added //replacenear command
		- Added //extinguish command
		- Added /help entry for all WorldEdit commands

Build #103:
- SERIOUS bug fix: Wrapper.py spams "day changed, rotating logs..." and creates new log file every second
- Traversing cross-server is now far more efficient (uses respawn to different dimension, then switches to actual dimension)

Build #102:
- Added log rotation, and logs are now stored in logs/wrapper directory
- Default server jar is now set to 1.8.7 for wrapper.properties
- Fixed support for Minecraft 1.7.10 in proxy mode
- Fixed `/wrapper halt` command in-game
- API changes:
	- [issue #199] Added new methods for modifying player permissions [untested]:
		- player.setGroup(group)
		- player.setPermission(node, value=True) (value argument is optional, default is True)
		- player.removePermission(node)
		- player.removeGroup(group)
	- [issue #164] Implemented timer.tick event (finally!)

Build #101:
- Fixed crashes relating to packets 0x1a (again!) and 0x1e
- player.getPosition() now returns the following tuple format: (x, y, z, yaw, pitch) (removed onGround)

Build #100:
- Proxy mode improvements:
	- Fixed 1.7.10 servers not working due to changes in #98 (packet 0x2b being sent on a non-1.8 server)
	- Fixed skin settings not persisting when changing servers
	- Fixed status effects not disappearing when connected to a secondary server
	- Fixed client disconnecting from 0x1a packet
	- [issue #200] Fixed crash/chunks not loading in Nether and End
- API changes:
 - [*pull request #193/#194] player.getPosition() now returns the following tuple format: (x, y, z, onGround, yaw, pitch) [MAY BREAK EXISTING PLUGINS]

*Pull request was modified from original to better fit the API.  

Build #99:
- Added /lobby command for cross-servers
- [pull request #178] Fix player.setResourcePack
- Removed trace amounts of try:except statements in proxy code in an effort to reduce random issues that aren't being detected
	- I've also done some little fixes, and I think the proxy mode is a bit more stable now.
	- Translating more packets that involve entity IDs when cross-server to fix weird issues
		- Clothes can be changed, beds work properly, animations might work better, etc.

Build #98:
- Added new example plugins `teleport` and `home` by Cougar [pull requests #155 and #154 respectively]
- Removed Top 10 Players until lag can be fixed
- [issue #160] Fixed new players without a skin breaking parts of the Wrapper
- Cross-server improvements:
	- Fixed skins and duplicating players on tab list when traversing between Wrapper.py servers
	- Weather is now accurate
- [pull request #176] Parse PID 0x30 (Window Items)
- [pull request #174/#173] Fix issue #172

- Plugin changes:
	- Essentials:
		- [pull request #162] Assign default MOTD during login if it does not exist like /motd does

Build #97:
- Split plugin, command, and event code into separate respectively-named files/classes for cleaner code
- Fixed nobody being able to connect via proxy with oddly-formatted whitelist.json
- `/permissions groups [group] info` now shows usernames alongside UUID [surresttexas00/#145]
- `/permissions users [username] remove` sub-command added [surresttexas00/#148]
- Fixed `player.hasGroup` always returning None [issue #144]
- Fixed `/help` command showing two pages when only four items are listed [issue #141]
- Passing a list or tuple as the command name to api.registerCommand for easily registering multiple aliases for a command [issue #135]
- Commands are no longer case-sensitive [issue #135]
- Removed bolding on `/help` command groups [issue #121]
- Proxy config option `convert-player-files` is now False by default until fixed
