#Changelog#
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
  - Renames player files and whitelists. Will not convert bans, so banned players may remain unbanned until you manually re-ban them 
  - This is turned on by default
- Top 10 active players can be viewed from the web mode
  
**Developer Changes**
- Events which return a payload other than True/False will be passed onto the event caller
  - e.g. you can read an event such as player.rawMessage, and then `return "Different message!"` to change the message (this includes commands!)
- [pull request #178] Fix player.setResourcePack

**Bug Fixes/Regular**
- CRITICAL BUG FIX: Players who changeed usernames would be treated as a new user (Temporarily fixed by not allowing name changes - it'll continue to use their old usernames even after changing until we implement a workaround)
- Fixed IRC bug where unicode crashes.... AGAIN. UGH. HOW MANY TIMES DO I HAVE TO FIX THIS?
- Fixed proxy not binding when server-port is misconfigured/unable to connect to the destination server
- Potentially fixed permission UUIDs being stored inconsistently (some with dashes, some without)
- Fixed issues that broke Spigot with Wrapper.py
- Web mode fixes:
  - Escaped <>'s in the Chat tab
  - Joins and parts now show up in the Chat tab
  - "remember me" when logging in actually makes it remember you
  - "Lost Connection" page now works again 
- Fixed proxy instabibility
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
  - It is extremely ugly, and primitive. Don't except much yet.
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
- player.getDimension() now properly updates when switching dimensions

This update definitely makes some API methods cleaner. 

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
  - Halting the wrapper
  - IRC control
  - Changing all settings on wrapper.properties and server.properties from it
  - Rolling back world file from backups
  - Show server ports (proxy and internal, unless proxy is disabled, then just internal.)
  - Show chat as an individual tab (without any console messages)
  - Add "remember me" checkmark, make all current sessions last 30 days instead of the default week, and then extend lifetime of session when accessed
  - Make it stream information rather than polling for the sake of bandwidth efficiency and speed
  - Change password from web panel
  - Move password from the config file to a hashed password in web.py's data object
  - Perhaps move to Flask?
  - Implement a logged notification system - useful for critical errors that happened in the past, etc. 
- Fix backups happening upon start (potentially an issue, not 100% sure)
- Fix packet error when teleporting long distances
- Multi-server mode (This might actually become a separate project for managing multiple servers and accounts, rather than being a Wrapper.py feature)
  - If I make it a separate project, it might use Wrapper.py as a backend for booting servers for extra features, for the sake of not duplicating code across projects
- Update version of Minecraft server automatically
- First-run setup wizard for new setups
- Potentially implement a way to reload the config - but that might be too difficult/bug prone
- Improve configuration system/redo from scratch
  - Add support for comments
  - Allow manual ordering of the options, to make configuration files a bit easier on the eyes
- Import bans from the vanilla server when using proxy mode for the first time
  - Something with whitelists too. Whitelisting and stuff is super broken with proxy mode being enabled.
- Finish adding all block IDs, item IDs and their respective damage values to items.py
  - Might be better just to use some sort of pre-existing JSON list
- Allow fake !commands to be made with api.registerCommand() (for non-proxy mode setups)
- Hibernation mode: Wrapper.py will be able to stop the server, but listen for incoming connections and will fire the server up when someone connects. It will make logging into the server slower if the server is hibernated, but otherwise it will reduce the average load of a server box running multiple servers.
- Add custom /help command (the current /help command is the vanilla help command, and it doesn't show any Wrapper.py commands)
- Move permissions code, plugin loading code, and command code into separate files for more organized code
- Split proxy.py into three files: __init__.py for the main proxy class, client.py for client class, server.py for server class, and network.py for core networking code (Packet class)
- Update code:
  - Allow auto-updating from dev build to stable, if it's the latest
  - Jumping from stable to dev manually, if the dev build is newer than the stable build
  - Create a difference between "checking for updates" and "auto-updating"
- Stop backups from happening unless server is running. Handle running out of disk space by freezing java process. Upon every boot, check level.dat and player files. If corrupted, replace from backup.