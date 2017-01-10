# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

import os
import sys
import logging
from api.helpers import getjsonfile, putjsonfile


# Default Configuration File
# Config items with values of "deprecated" get removed if they exist in an active config file
NEWCONFIG = {
    "Backups": {
        # Automatic backups with automatic backup pruning. Interval is in seconds.
        "backup-compression": False,
        # Specify files and folders you want backed up.  Items must be in your server folder (see 'General' section)
        "backup-folders": [
            "server.properties",
            "world"
        ],
        "backup-interval": 3600,
        "backup-location": "backup-directory",  # this location will be inside wrapper's directory
        "backup-notification": True,
        "backups-keep": 10,
        "enabled": False
    },
    "Gameplay": {
        "use-timer-tick-event": False,  # not recommended.  1/20th of a second timer option for plugin use. May
                                        # impact wrapper performance negatively.
    },
    "Entities": {
        "enable-entity-controls": False,  # enable entity controls.
        "entity-update-frequency": 4,  # how often the entity processor updates world entity counts
        "thinning-frequency": 30,  # how often thinning of mobs runs, in seconds.  a large difference between this and
                                   # the entity update frequency will ensure no 'overkill" occurs.
        "thinning-activation-threshhold": 100,  # when mobs < this number, thinning is inactive (server or player)
        "thin-Cow": 40,  # Example, starts thinning Cow > 40.  Name must match exactly.
        "thin-Sheep": 40,  # another example
        "thin-Chicken": 30  # because they are especially annoying
    },
    "Updates": {
        "auto-update-branch": None,  # Use one of the names listed herein (i.e. 'stable-branch')
        "auto-update-wrapper": False,  # If True, an "auto-update-branch" must be specified.
        # You can point these to another branch, if desired.
        "stable-branch": "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/build/version.json",
        "dev-branch": "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/build/version.json",
    },
    "Misc": {  # look 'n' feel type customizations
        "command-prefix": "/",  # if you change this, no minecraft command will work. Bug or feature? TODO not sure.
        "reboot-message": "Server is conducting a scheduled reboot. The server will be back momentarily!",
        "default-restart-message": "Server restarting...",
        "stop-message": "Stopping The Minecraft Server",
        "use-readline": True  # using readline is likely to be more-cross platform, but does not use wrapper's ability
                              # to keep console keystroke entries visually intact while server produces output.
    },
    "General": {
        "auto-restart": True,
        # You will need to update this to your particular server start command line.
        "command": "java -jar -Xmx2G -Xms1G server.jar nogui",
        "encoding": "UTF-8",
        "pre-1.7-mode": "deprecated",  # wrapper detects server version and adjusts accordingly now
        "server-directory": ".",  # Using the default '.' roots the server in the same folder with wrapper. Change
                                  # this to another folder to keep the wrapper and server folders separate.
                                  # Do not use a trailing slash.
                                  # '/full/pathto/the/server'
        "server-name": "deprecated",  # moved to Web (used only by web module in code)
        "shell-scripts": False,
        "timed-reboot": False,
        "timed-reboot-seconds": "deprecated",  # deprecated for consistency with timed reboot warning 'minutes'
        "timed-reboot-minutes": 1440,
        "timed-reboot-warning-minutes": 5,
        "auto-update-branch": "deprecated",  # moved to group "Updates"
        "auto-update-dev-build": "deprecated",  # no separate item for wrapper/dev-build.
        "auto-update-wrapper": "deprecated",  # moved to group "Updates"
        "stable-branch":  "deprecated",  # moved to group "Updates"
        "dev-branch":  "deprecated",  # moved to group "Updates"
    },
    "IRC": {
        # This allows your users to communicate to and from the server via IRC and vise versa.
        # _________________________________
        "autorun-irc-commands": [
            "COMMAND 1",
            "COMMAND 2"
        ],
        "channels": [
            "#wrapper"
        ],
        "command-character": ".",
        "control-from-irc": False,
        "control-irc-pass": "password",
        "irc-enabled": False,
        "nick": "MinecraftWrap",
        "obstruct-nicknames": False,
        "password": None,
        "port": 6667,
        "server": "benbaptist.com",
        "show-channel-server": True,
        "show-irc-join-part": True
    },
    "Proxy": {
        # This is a man-in-the-middle proxy similar to BungeeCord, which is used for extra plugin functionality.
        # online-mode must be set to False in server.properties. Make sure that the server is not accessible directly
        # from the outside world.
        # _________________________________
        # Note: the online-mode option here refers to the proxy only, not to the server's offline mode.  Each server's
        # online mode will depend on its setting in server.properties
        # _________________________________
        # It is recommended that you turn network-compression-threshold to -1 (off) in server.properties
        # for fewer issues.
        # _________________________________
        "convert-player-files": False,
        "max-players": 1024,  # todo - re-implement this somewhere? perhaps in the server JSON response?
        "online-mode": True,  # the wrapper's online mode, NOT the server.
        "proxy-bind": "0.0.0.0",
        "proxy-enabled": False,
        "proxy-sub-world": False,  # this wrapper is a sub world (wrapper needs to do extra work to spawn the player).
        "proxy-port": 25565,  # the wrapper's proxy port that accepts client connections from the internet. This
                              # port is exposed to the internet via your port forwards.
        "server-port": "deprecated",  # This port is autoconfigured from server console output now.
        "spigot-mode": False,
        "silent-ipban": True,  # silent bans cause your server to ignore sockets from that IP (for IP bans)
                              #  The idea is to cause your server to appear offline and avoid possible confrontations.
        "hidden-ops": [         # these players do no appear in the sample server player list pings.
            "SurestTexas00",
            "BenBaptist"
        ]
    },
    "Web": {
        "public-stats": True,
        "web-allow-file-management": True,
        "web-bind": "0.0.0.0",
        "web-enabled": False,
        "web-password": "password",
        "web-port": 8070,
        "server-name": "Minecraft Server",
    }
}


class Config:
    def __init__(self):
        self.log = logging.getLogger('Config')
        self.config = {}
        self.exit = False

    def loadconfig(self):
        # load older versions of wrapper.properties to preserve prior settings.
        if os.path.exists("wrapper.properties"):
            with open("wrapper.properties", "r") as f:
                oldconfig = f.read()
            oldconfig = "Deprecated File!  Use the 'wrapper.properties.json' instead!\n\n%s" % oldconfig
            with open("_wrapper.properties", "w") as f:
                f.write(oldconfig)
            os.remove("wrapper.properties")

        # Create new config if none exists
        if not os.path.exists("wrapper.properties.json"):
            putjsonfile(NEWCONFIG, "wrapper.properties", sort=True)
            self.exit = True

        # Read existing configuration
        self.config = getjsonfile("wrapper.properties")  # the only data file that must be UTF-8
        if self.config is None:
            self.log.error("I think you messed up the Json formatting of your "
                           "wrapper.properties.json file. "
                           "Take your file and have it checked at: \n"
                           "http://jsonlint.com/")
            self.exit = True

        # detection and addition must be separated to prevent changing dictionary while iterating over it.
        # detect changes
        changesmade = False
        deprecated_entries = []
        new_sections = []
        new_entries = []
        for section in NEWCONFIG:
            if section not in self.config:
                self.log.debug("Adding section [%s] to configuration", section)
                new_sections.append(section)
                changesmade = True

            for configitem in NEWCONFIG[section]:
                if section in self.config:
                    # mark deprecated items for deletion
                    if configitem in self.config[section]:
                        if NEWCONFIG[section][configitem] == "deprecated":
                            self.log.debug("Deprecated item '%s' in section '%s'. - removing it from"
                                           " wrapper properties", configitem, section)
                            deprecated_entries.append([section, configitem])
                            changesmade = True
                    # mark new items for addition
                    else:
                        # handle new items in an existing section
                        if NEWCONFIG[section][configitem] != "deprecated":  # avoid re-adding deprecated items
                            self.log.debug("Item '%s' in section '%s' not in wrapper properties - adding it!",
                                           configitem, section)
                            new_entries.append([section, configitem])
                            changesmade = True
                else:
                    # handle new items in a (new) section
                    self.log.debug("Item '%s' in new section '%s' not in wrapper properties - adding it!",
                                   configitem, section)
                    new_entries.append([section, configitem])
                    changesmade = True

        # Apply changes and save.
        if changesmade:
            # add new section
            if len(new_sections) > 0:
                for added_section in new_sections:
                    self.config[added_section] = {}

            # Removed deprecated entries
            if len(deprecated_entries) > 0:
                for removed in deprecated_entries:
                    del self.config[removed[0]][removed[1]]

            # Add new entries
            if len(new_entries) > 0:
                for added in new_entries:
                    self.config[added[0]][added[1]] = NEWCONFIG[added[0]][added[1]]

            self.save()
            self.exit = True

        if self.exit:
            self.log.warning(
                "Updated wrapper.properties.json file - check and edit configuration if needed and start again.")
            sys.exit()

    def change_item(self, section, item, desired_value):
        if section in self.config:
            if item in self.config[section]:
                self.config[section][item] = desired_value
                return True
            else:
                self.log.error("Item '%s' not found in section '%s' of the wrapper.properties.json" % (item, section))
                return False
        else:
            self.log.error("Section '%s' does not exist in the wrapper.properties.json" % section)
            return False

    def save(self):
        putjsonfile(self.config, "wrapper.properties", sort=True)
