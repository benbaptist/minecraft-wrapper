Build 28, 1.0.19 RC 28
- Bugfix commands.py line 784 where player message is used with no argument.

Build 27
- increment version to 1.0.18 RC 27
- fix player to player teleport ValueError bug caused by trying to read coordinates
 where only a player name was given ("[lukeeexd: Teleported lukeeexd to Nyaii]")
- create PR to development.

Build 26
- Fix Chat.py plugin (all player's were sharing the same chat configuration).
- Fix Chat.py breaking on /reload.
- bugfix message from offline wrapper that is a hub in mcserver.py.
- changed deop to allow any vanilla level 4 OP to run it.
- add Geode plugin that prints each player's IP and country code at login.

Build 25
- Explicitly `close()` sockets that were shutdown.
- substitute 'localhost' for code occurences of '127.0.0.1'.

Build 24
Version number bumps to match Master  1.0.17 RC 24

Build 23
- Bugfixes:
  - at player logout (mcserver.py), server would attempt to run
   proxy method removestaleclients(), even if proxy mode was not running.
  - mcserver.py getplayer() not returning a player object in non-proxy mode.

Build 22
- Implement the proxy host as a ProcessPoolExecutor multiprocessor (only on Python3)

Build 21 (In-process Dev build) [1.0.16 RC 21]
- Refractor proxy and remove external "ServerVitals" class and integrate wrapper into proxy again.

Build 21 [1.0.16 RC 21]  (Patch to Master)
- Bugfix - at player logout (mcserver.py), server would attempt to run
 proxy method removestaleclients(), even if proxy mode was not running.

Starting with:
Build 20 [1.0.15 RC 20] - Development branch update
- includes first version of vanilla claims plugin.
