# Major To-Do #

- [x] Wrapper shuts down on first start, to allow user to edit generated config file
    - Eventually, interactive first-time setup

- [PARTIAL] Implement backup system
    - [x] Support various containers (zip, tar, 7z, etc.) and compression methods (gzip, etc.)
    - [x] Don't backup if server has been in stopped state
    - [x] Option to stop backup if no players have logged in
    - [ ] Automatic world rollback through dashboard
- [x] Implement shell script calls
- [ ] Implement dashboard using Flask
    - [ ] Multi-user support with permissions
- [ ] Implement locales, potentially
- [ ] Implement plugin API
    - [ ] Server object
        - [ ] World object
        - [ ] Player object
        - [ ] (if proxy mode is implemented) Entity object
- [ ] Implement server.properties hijacking (temporarily replace server.properties with custom values before starting server, and putting original one back after server booted)
- [ ] (Very Low Priority) Implement Proxy mode

# Minor To-Do List #
- [x] Auto-accept EULA
- [x] Automatically turn on gamerule to hide command runs from ops, to prevent chat spam
- [ ] Server
    - [ ] Throttle server start attempts if failing to start (i.e. invalid CLI arguments, wrong server jar name, etc.)
    - [ ] Respect arguments
    - [ ] Respect auto-restart
- [ ] log_manager
    - [PARTIAL] Rotate logs
    - [x] Compress old logs using gzip
    - [x] Respect debug-mode settings
- [ ] Backups
    - [ ] Purge old backups
    - [ ] Respect ingame-notification settings
    - [x] Console commands for controlling backups
    - [x] Cancel ongoing backup
- [ ] Dashboard
    - [ ] Localize MaterializeCSS dependencies (don't use CDN)

# Plugin Ideas #
- [ ] IRC bridge plugin
- [ ] Essentials Clone
