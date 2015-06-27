Build #104:
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
