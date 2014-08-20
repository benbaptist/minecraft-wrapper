#Changelog#

<h4>To-do List</h4>
- Web interface for server management
- Multi-server mode
- Proxy system (like Bungeecord, perhaps)
<ul>
<strike>
<li> Maybe add some custom in-game Wrapper.py commands such as /halt</li>
<li> Log player actions such as block manipulation, etc.</li>
</strike>
<li>The above is possible now with the proxy mode, using plugins.</li>
</ul>
- Ability to halt server without shutting down wrapper - for fine server control
- Potentially implement region-fixer in Wrapper.py
- Update version of Minecraft server automatically
- Update Wrapper.py automatically or with a one-click update
- First-run setup wizard for new setups
- Potentially implement a way to reload the config - but that might be too difficult/bug prone
- UHC-style timer mode
- Clean up & organize code... it's a tad cluttery right now! (this is only semi-true now, I've cleaned it up quite a bit)
<ul>
<li> Move backup code into a new class, backup.py</li>
<li> Redo function names and general cleanup in in server.py - names are very confusing at the moment (fix start & stop functions, console functions)</li>
</ul>
- Fix messages not sending from IRC to server with show-channel off

<h4>0.7.0</h4>
- Huge Improvements to APIs
<ul>
<li>self.api.registerCommand() for making real /commands in-game</li>
<li>self.api.minecraft.changeResourcePack() for changing resource packs on the fly</li>
</ul> 
- Added a proxy mode - this is necessary for additional features of the API
<ul>
<li>If you've used BungeeCord before - proxy mode should make sense. The only difference is that you don't need to make the server in offline mode.</li>
</ul> 
- Write date to log files as well as a timestamp
- Added /plugins command - was removed in the last update by mistake
- Removed IRC -> Server Line-Wrapping (each message was divided automatically every 80 characters - it was annoying)
- Fixed bug where serious plugin errors resulted in that plugin not being reloadable


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
