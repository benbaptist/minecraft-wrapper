#Changelog#

<h4>To-do List</h4>
- Web interface for server management
- Multi-server mode
- Proxy system (like Bungeecord, perhaps)
-- Maybe add some in-game Wrapper.py commands such as /halt
-- Block/Action Logging
- Ability to halt server without shutting down wrapper - for fine server control
- Potentially implement region fixer in wrapper.py
- Update version of Minecraft server automatically
- Clean up & organize code... it's a tad cluttery right now!

<h4>0.4.0</h4>
Small update, but brings one much-needed change: the new configuration file system. Change your settings in wrapper.properties now. Much nicer and update-friendly.
- Achivements are announced in IRC
- IRC bridge can be turned off so Wrapper.py can be used as a backup-only script
- New configuration file
- Obstruct usernames in IRC to refrain from pinging (currently doesn't work with colored names, known bug)
- Bug fixes:
-- Save-off during backup
-- Various crashes, such as when it can't connect to IRC
-- Other small fixes
