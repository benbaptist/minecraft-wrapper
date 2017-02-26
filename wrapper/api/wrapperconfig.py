# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# noinspection PySingleQuotedDocstring
'''
This file format is a bit non-pythonic, but is intended to produce a nicer
ReST file for the documentation. Three `'` quotes are disregarded by
our document production methods.  Lines are also greater than 79 characters...
In fact, they are whatever length should get grouped together as a single
sentence or paragraph.  Double CR's are treated as a single CR by ReST
parsers.
'''

# def Config file items and layout:
# """
'''

*wrapperconfig.py is the default config file.  Changes made
here are inserted or deleted from the the wrapper config
each time wrapper starts.*

*Items marked as "deprecated" get removed from the wrapper
config when wrapper starts.  These are are not valid items.
they only exist so that they will get removed from older
wrapper versions.  This is intended to keep the actual
wrapper.config.json file from getting cluttered with old
unused items.*

*The wrapper.config.json file contents will look like this,
but without all the comment lines.*

'''

CONFIG = {

# Automatic backups with pruning. Intervals are specified in seconds.

    "Backups":

        {

            "backup-compression": False,

         # Specify files and folders you want backed up.  Items must be in your server folder (see 'General' section)

            "backup-folders":

                [
                    "server.properties",

                    "world"

                ],

            "backup-interval": 3600,

         # backup location is inside wrapper's directory

            "backup-location": "backup-directory",

            "backup-notification": True,

            "backups-keep": 10,

            "enabled": False

    },

    "Gameplay":

        {

        # Use of timer-tick is not recommended.  1/20th of a second timer option for plugin use. May impact wrapper performance negatively.

            "use-timer-tick-event": False,

        },

    "Entities":

        {

         # whether to use the wrapper entity controls.

            "enable-entity-controls": False,

         # how often the entity processor updates world entity counts

            "entity-update-frequency": 4,

         # how often thinning of mobs runs, in seconds.  a large difference between this and the entity update frequency will ensure no 'overkill" occurs.

            "thinning-frequency": 30,

         # when mobs < this threshhold, thinning is inactive (server or player)

            "thinning-activation-threshhold": 100,

         # The following items thin specific mobs over the stated count.  This only happens after the total mob count threshold above is met first.  For example, 'thin-Cow: 40` starts thinning cows > 40.  Entity names must match minecraft naming exactly as they would appear in the game.

            "thin-Cow": 40,

         # 1.11 naming!  Check /wrapper-date/json/entities.json

         # there are some surprising changes, like "PigZombie" is now zombie_pigman and EntityHorse is horse, etc

            "thin-cow": 40,

            "thin-zombie_pigman": 200,

            "thin-Sheep": 40,

            "thin-Chicken": 30

        },

    "Updates":

        {

         # Use one of the names listed herein (i.e. 'stable-branch')

            "auto-update-branch": None,

         # If True, an "auto-update-branch" must be specified.

            "auto-update-wrapper": False,

         # You can point these to another branch, if desired.

            "stable-branch":

                "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/build/version.json",

            "dev-branch":

                "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/build/version.json",

        },

# look 'n' feel type customizations

    "Misc":

        {

         # if you change command-prefix, no minecraft command will work. Bug or feature? -TODO not sure.

            "command-prefix": "/",

            "reboot-message": "Server is conducting a scheduled reboot. The server will be back momentarily!",

            "default-restart-message": "Server restarting...",

            "stop-message": "Stopping The Minecraft Server",

         # readline is likely to be more-cross platform, but does not use wrapper's ability to keep console keystroke entries visually intact while server produces output.

            "use-readline": True

        },

    "General":

        {

            "auto-restart": True,

         # You will need to update this to your particular server start command line.

            "command": "java -jar -Xmx2G -Xms1G server.jar nogui",

            "encoding": "UTF-8",

         # wrapper detects server version and adjusts accordingly now

            "pre-1.7-mode": "deprecated",

         # Using the default '.' roots the server in the same folder with wrapper. Change this to another folder to keep the wrapper and server folders separate.  Do not use a trailing slash...  e.g. - '/full/pathto/the/server'

            "server-directory": ".",

         # server-name was moved to Web (it is used only by web module in code)

            "server-name": "deprecated",

            "shell-scripts": False,

            "timed-reboot": False,

         # Deprecated for consistency with timed reboot warning 'minutes'

            "timed-reboot-seconds": "deprecated",

            "timed-reboot-minutes": 1440,

            "timed-reboot-warning-minutes": 5,

         # The remaining items and functionality were moved to group "Updates" and deprecated from this section.

            "auto-update-branch": "deprecated",

            "auto-update-dev-build": "deprecated",

            "auto-update-wrapper": "deprecated",

            "stable-branch":  "deprecated",

            "dev-branch":  "deprecated",

        },

# This allows your users to communicate to and from the server via IRC and vice versa.

    "IRC":

        {

            "autorun-irc-commands":

                [
                    "COMMAND 1",

                    "COMMAND 2"

                ],

            "channels":

                [
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



    "Proxy":

    # This is a man-in-the-middle proxy similar to BungeeCord, which is used for extra plugin functionality. online-mode must be set to False in server.properties. Make sure that the server is not accessible directly from the outside world.

    # Note: the online-mode option here refers to the proxy only, not to the server's offline mode.  Each server's online mode will depend on its setting in server.properties.  It is recommended that you turn network-compression-threshold to -1 (off) in server.properties for fewer issues.

        {

                "convert-player-files": False,

            # This actually does nothing in the code. TODO - re-implement this somewhere? perhaps in the server JSON response?

                "max-players": 1024,

            # the wrapper's online mode, NOT the server.

                "online-mode": True,

                "proxy-bind": "0.0.0.0",

                "proxy-enabled": False,

            # if wrapper is a sub world (wrapper needs to do extra work to spawn the player).

                "proxy-sub-world": False,

            # the wrapper's proxy port that accepts client connections from the internet. This port is exposed to the internet via your port forwards.

                "proxy-port": 25565,

            # Deprecated - This port is autoconfigured from server console output now.

                "server-port": "deprecated",

                "spigot-mode": False,

            # silent bans cause your server to ignore sockets from that IP (for IP bans). This will cause your server to appear offline and avoid possible confrontations.

                "silent-ipban": True,

                "hidden-ops":

                # these players do not appear in the sample server player list pings.

                    [

                        "SurestTexas00",

                        "BenBaptist"

                    ]

            },

        "Web":

            {

                "public-stats": True,

                "web-allow-file-management": True,

                "web-bind": "0.0.0.0",

                "web-enabled": False,

                "web-password": "password",

                "web-port": 8070,

                "server-name": "Minecraft Server",

            }

    }

# """
