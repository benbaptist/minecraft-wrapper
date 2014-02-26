#Changelog#

<h4>To-do List</h4>
- Web interface for server management
- Multi-server mode
- Proxy system (like Bungeecord, perhaps)
<ul>
<li> Maybe add some custom in-game Wrapper.py commands such as /halt</li>
<li> Log player actions such as block manipulation, etc.</li>
</ul>
- Ability to halt server without shutting down wrapper - for fine server control
- Potentially implement region fixer in wrapper.py
- Update version of Minecraft server automatically
- First-run setup wizard for new setups
- Potentially implement a way to reload the config - but that might be too difficult/bug prone
- UHC-style timer
- Clean up & organize code... it's a tad cluttery right now! (this is only semi-true now, I've cleaned it up quite a bit)

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
