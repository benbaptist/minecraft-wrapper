#Changelog#

<h4>0.7.3</h4>
Before I release 0.7.3, I'd like to add support for pre-1.7 back again, and fix #38. Maybe I should add the auto-updater too.
Make sure to add dimension client updating thingy player.getDimension()

Pre-1.7 support is mostly there, but Python gives errors on stdin.write() due to the color codes causing encoding errors. I hate Python 2.x's string encoding bullcrap.

I might need to re-implement the auto-server-restarter. People with colored names don't appear in /say on IRC, apparently.

**Features**
- Optional backup compression (tar.gz)
- Optional auto-update system (turned off by default)
  - If auto-update-wrapper is turned on in wrapper.properties, the Wrapper will check for updates every 24 hours
  - If you are on a stable build, and a new version exists, it will download the update and will be applied when you start Wrapper.py next time
  - If you are on a development build, it won't automatically update - it will just tell you that an update is available and you can do /update-wrapper to allow it to update
  - You can also use /update-wrapper to force check for new updates, and apply them. This works even if you turned off auto-update-wrapper.

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
  - server.stopped: Once the server is completely shutdown, and is safe to modify the world files
  - server.state(state): All of the above events consolidated into one event
  - irc.action(nick, channel, message): User doing /me or /action in an IRC channel
  - irc.quit(nick, channel, message): User quitting from IRC. 'channel' returns None currently. 'message' is their QUIT message
  - player.mount(player, vehicle_id, leash): Called when a player enters a vehicle, such as a boat, minecart, or horse.
  - player.unmount(player): Called when a player leaves a vehicle that they previously entered.
  - player.preLogin(player, online_uuid, offline_uuid, ip): 
- Renamed events:
  - irc.message(nick, channel, message) from irc.channelMessage
  - irc.join(nick, channel) from irc.channelJoin
  - irc.part(nick, channel) from irc.channelPart
  - player.interact from player.action (player.action from right clicking blocks, not from /me)
- New Server class methods (accessable with api.minecraft.getServer()):
  - server.start(): Start the server (if it isn't already started)
  - server.restart(reason): Restart the server, and kick users with an optional reason (default: "Restarting server...")
  - server.stop(reason): Stop the server, kick users with a reason (default: "Stopping server..."), don't automatically start back up, but keep Wrapper.py running. 
- Cleaned up MORE incosistencies in these events:
  - player.achievement
- New method: self.log.warn
- All irc.* events use "nick" instead of "user" for the payload
- server.status renamed to server.state (from api.minecraft.getServer())
- Entity tracking system being implemented
  - Very early, buggy junk
  - Doesn't handle despawning very well quite yet, or multiple players

This update is relatively big and definitely makes some API methods cleaner. 

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
<ul>
<li>self.api.registerCommand() for making real /commands in-game</li>
<li>self.api.minecraft.changeResourcePack() for changing resource packs on the fly</li>
<li>Events containing the player's username should now contain the Player class</li>
</ul> 
- Added a proxy mode - this is necessary for additional features of the API such as /commands and other special features
<ul>
<li>If you've used BungeeCord before - proxy mode should make sense. The only difference is that you don't need to make the server in offline mode.</li>
<li>Built-in commands such as /reload, /wrapper, /pl(ugins), etc.</li>
<li>Extremely experimental, near-useless server-jumping mode (doesn't work quite yet)</li>
</ul> 
- Write date to log files as well as a timestamp
- Added /plugins command - was removed in the last update by mistake
- Removed IRC -> Server Line-Wrapping (each message was divided automatically every 80 characters - it was annoying)
- Fixed bug where serious plugin errors resulted in that plugin not being reloadable
- Fixed quit messages not being displayed in IRC (finally!)
- Added new shell scripting setting where you can execute certain shell scripts on specific events (NIX-only systems)
<ul>
<li> The schell scripts' are pregenerated with content, and has a short description of when each script is executed, and what arguments are passed to the script, if any </li>
<li> Shell scripts are in wrapper-data/scripts </li>
</ul>

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
- Web interface for server management (partially implemented, not sure when it'll be done)
- Multi-server mode (This might actually become a separate project for managing multiple servers and accounts, rather than being a Wrapper.py feature)
  - If I make it a separate project, it might use Wrapper.py as a backend for booting servers for extra features, for the sake of not duping code across projects</li>
- Ability to halt server without shutting down wrapper - for fine server control
- Update version of Minecraft server automatically
- Update Wrapper.py automatically or with a one-click update
- First-run setup wizard for new setups
- Potentially implement a way to reload the config - but that might be too difficult/bug prone
- Improve configuration system/redo from scratch
  - Add support for comments
  - Allow manual ordering of the options, to make configuration files a bit easier on the eyes
- Import bans from the vanilla server when using proxy mode for the first time
- Finish adding all block IDs, item IDs and their respective damage values to items.py
  - Might be better just to use some sort of pre-existing JSON list
- Allow fake !commands to be made with api.registerCommand() (for non-proxy mode setups)
- Hibernation mode: Wrapper.py will be able to stop the server, but listen for incoming connections and will fire the server up when someone connects. It will make logging into the server slower if the server is hibernated, but otherwise it will reduce the average load of a server box running multiple servers.
- Add custom /help command (the current /help command is the vanilla help command, and it doesn't show any Wrapper.py commands)
- Move permissions code, plugin loading code, and command code into separate files for more organized code
- Split proxy.py into three files: __init__.py for the main proxy class, client.py for client class, server.py for server class, and network.py for core networking code (Packet class)
- "Request too long" in IRC due to certain messages being too big