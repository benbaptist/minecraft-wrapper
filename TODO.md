# Major To-Do #

- [DONE] Wrapper shuts down on first start, to allow user to edit generated config file
    - Eventually, interactive first-time setup

- [PARTIAL] Implement backup system
    - [DONE] Support various containers (zip, tar, 7z, etc.) and compression methods (gzip, etc.)
    - [DONE] Don't backup if server has been in stopped state
    - [DONE] Option to stop backup if no players have logged in
    - Automatic world rollback through dashboard
- [DONE] Implement shell script calls
- Implement dashboard using Flask
    - Multi-user support with multiple access levels (or permissions)
- Implement locales, potentially
- Implement plugin API
    - Server object
        - World object
        - Player object
        - (if proxy mode is implemented) Entity object
- Implement server.properties hijacking (temporarily replace server.properties with custom values before starting server, and putting original one back after server booted)
- [Very Low Priority] Implement Proxy mode

# Minor To-Do List #
- [DONE] Auto-accept EULA
- [DONE] Automatically turn on gamerule to hide command runs from ops, to prevent chat spam
- Server
    - Respect arguments
    - Respect auto-restart
- log_manager
    - [PARTIAL] Rotate logs
    - [DONE] Compress old logs using gzip
    - [DONE] Respect debug-mode settings
- Backups
    - Purge old backups
    - Respect ingame-notification settings
