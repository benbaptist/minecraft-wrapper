#Changelog#

<h4>0.7.3</h4>
- Fixed "Backup file '%s' does not exist - will not backup" when conducting a backup
- Fixed "AttributeError: 'bool' object has no attribute 'clients'" when not using proxy mode
- Fixed users doing /me or /action in IRC displaying inappropriately on server
- Complete rewrite of the Server class, and partial rewrite of the IRC class
  - Backup code has now been separated into the Backups class of backups.py
- New events:
  - server.starting: Called just before the server begins to boot
  - server.started: Once the server reports Done in the console and is ready for players
  - server.stopping: Called as the server starts to shutdown
  - server.stopped: Once the server is completely shutdown, and is safe to modify the world files
  - server.state(state): All of the above events consolidated into one event
  - irc.action(nick, channel, message): User doing /me or /action in an IRC channel
  - irc.quit(nick, channel, message): User quitting from IRC. 'channel' returns None currently. 'message' is their QUIT message
- Renamed events:
  - irc.message(nick, channel, message) from irc.channelMessage
  - irc.join(nick, channel) from irc.channelJoin
  - irc.part(nick, channel) from irc.channelPart
- New Server class methods (accessable with api.minecraft.getServer):
  - server.start(): Start the server (if it isn't already started)
  - server.restart(reason): Restart the server, and kick users with an optional reason (default: "Restarting server...")
  - server.stop(reason): Stop the server, kick users with a reason (default: "Stopping server..."), don't automatically start back up, but keep Wrapper.py running. 
- Cleaned up MORE incosistencies in these events:
  - player.achievement
- New method: self.log.warn
- All irc.* events use "nick" instead of "user" for the payload
 
This update is relatively big and definitely makes some methods cleaner and more straight forward.
Backups are currently broken on this particular dev build of 0.7.3, since I removed all of the server code and redid it from scratch. Will re-enable backups soon.
IRC is also partially broken (IRC->Server) for the same reason. In fact, a lot of stuff will probably be broken. But it's for the best!

<h4>0.7.2</h4>
Server jumping still seems super buggy and weird. It only works in my test environment, but fails in other environments. I have no clue why.
- Fixed Wrapper.py not ignoring hidden files wrapper-plugins (files prefixed with a period)
- Fixed players not disappearing from tab menu with proxy mode enabled
- Wrapper.py now logs when a player joined the server for the first time
- Added APIs for checking group information about a player (player.getGroups, player.hasGroup)
- Cleaned up inconsistencies in the following events (events returning the player's name instead of the player object)
<ul>
<li> player.message </li>
<li> player.action </li>
<li> player.death </li>
<li> player.join </li>
<li> player.leave </li>
</ul>
- New events: 
  - server.say(message): When /say is used in the console or by a player.
  - player.chatbox(player, json): Anything that appears in a player's chatbox. Can be aborted by returning False.
- Added max-players option to proxy mode (thanks melair!)

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
<ul>
<li>If I make it a separate project, it might use Wrapper.py as a backend for booting servers for extra features, for the sake of not duping code across projects</li>
</ul>
- Ability to halt server without shutting down wrapper - for fine server control
- Potentially implement region-fixer in Wrapper.py
- Update version of Minecraft server automatically
- Update Wrapper.py automatically or with a one-click update
- First-run setup wizard for new setups
- Potentially implement a way to reload the config - but that might be too difficult/bug prone
- Improve configuration system/redo from scratch
<ul>
<li>Add support for comments</li>
<li>Allow manual ordering of the options, to make configuration files a bit easier on the eyes</li>
</ul>
- Fix ban system for proxy-based setups
- Clean up & organize code... it's a tad cluttery right now! (this is only semi-true now, I've cleaned it up quite a bit)
<ul>
<li> Move backup code into a new class, backup.py</li>
<li> Redo function names and general cleanup in in server.py - names are very confusing at the moment (fix start & stop functions, console functions)</li>
</ul>
- Fix messages not sending from IRC to server with show-channel off
- Finish adding all block IDs, item IDs and their respective damage values to items.py
- Proxy mode error: Error -3 while decompressing data: incorrect header check
- Proxy mode error: Error -5 while decompressing data: incomplete or truncated stream
- The server.py and irc.py code SERIOUSLY needs a total rewrite. (I noticed this while fixing pre-1.7 support)
- Duplicate IRC messages (possibily fixed)
- Make URLs posted in IRC clickable inside of Minecraft
- Allow fake !commands to be made with api.registerCommand()
- Hibernation mode: Wrapper.py will be able to stop the server, but listen for incoming connections and will fire the server up when someone connects. It will make logging into the server slower if the server is hibernated, but otherwise it will reduce the average load of a server box running multiple servers.
- Add custom /help command (the current /help command is the vanilla help command, and it doesn't show any Wrapper.py commands)
- Move backup code, permissions code, plugin loading code, and command code into separate files for more organized code
- Split proxy.py into three files: __init__.py for the main proxy class, client.py for client class, server.py for server class, and network.py for core networking code (Packet class)
- "Request too long" in IRC due to certain messages being too big
