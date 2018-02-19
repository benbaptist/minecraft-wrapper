# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2018 - BenBaptist and Wrapper.py developer(s).
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

Lines ending in '# NODOC' (no trailing whitespace!) are removed from the rst
 document.

'''

# def Config file items and layout:
# """
'''

*wrapperconfig.py is the default config file.  Changes made
here are inserted or deleted from the the wrapper config
each time wrapper starts.*

*Items marked as "deprecated" get removed from the wrapper  # NODOC
config when wrapper starts.  These are are not valid items.  # NODOC
they only exist so that they will get removed from older  # NODOC
wrapper versions.  This is intended to keep the actual  # NODOC
wrapper.config.json file from getting cluttered with old  # NODOC
unused items.*  # NODOC
  # NODOC
*The wrapper.config.json file contents will look like this,
but without all the comment lines.*

'''

CONFIG = {

# Backups - Automatic backups with pruning. Intervals are specified in seconds.

    "Backups":

        {  # NODOC
            # NODOC
            "backup-compression": False,

         # Specify server files and folders you want backed up.  Items must be in your server folder (see 'General' section)

            "backup-folders":

                [
                    "server.properties",

                    "world"

                ],

         # backup interval in seconds: 3600 = hourly, 86400 = Daily, 604800 = weekly

            "backup-interval": 3600,

         # backup location is inside wrapper's directory, unless you use an absolute path (such as /home/otherdirectory/backups)

            "backup-location": "backup-directory",

            "backup-notification": True,

            "backups-keep": 10,

            "enabled": False

        },  # NODOC

# Alerts - provide email or other notification of wrapper problems (server down, etc).

    "Alerts":

        {  # NODOC

         # with some modern email providers, you may need to "allow less secure apps” on your account..

         # You should use a dedicated email with a password that is different from your other accounts for this purpose.

         # deprecated items were incorprated into the servers dictionary.  # NODOC
            # NODOC
            "send-method": "deprecated",  # NODOC
            # NODOC
            "server-addr": "deprecated",  # NODOC
            # NODOC
            "server-port": "deprecated",  # NODOC
            # NODOC
            "login-name": "deprecated",  # NODOC
            # NODOC
            "enabled": False,

         # enable a server item by setting login name to something other than "False".  Use your email address for login-name and the associated password (encrypt it first).

            "servers": [

                {

         # built in alerts use "wrapper" group.

                    "group": "wrapper",

                    "subject": "Wrapper.py Alert",

                    "type": "email",

                    "address": "smtp.gmail.com",

                    "port": 587,

                    "login-name": False,

                    "encrypted-password": "Copy and Paste from 'password' after wrapper encrypts it.",

                    "recipients": ["email1@provider.com", "email2@provider.com"]

                }
            ],


         # -plaintext items are converted to hashed items by wrapper

            "password-plaintext": False,

            "password": "use `/password -s Alerts password <your password>` to set this (or enter a password-plaintext)."

        },  # NODOC

# Gameplay - miscellaneous configuration items.

    "Gameplay":

        {  # NODOC
            # NODOC
         # Use of timer-tick is not recommended.  1/20th of a second timer option for plugin use. May impact wrapper performance negatively.

            "use-timer-tick-event": False,

        },  # NODOC

# Entity processing - This is somewhat superfluous now that minecraft has more built-in entity management gamerules now.  Must be turned on to use player.mount / unmount events.

    "Entities":

        {  # NODOC
            # NODOC
         # whether to use the wrapper entity controls.  With new minecraft versions, these are largely unnecessary and better done with the Gamerules.

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

        },  # NODOC

# Updates - Control wrapper update behaviour.

    "Updates":

        {  # NODOC
            # NODOC
         # Use one of the names listed herein (i.e. 'stable-branch')

            "auto-update-branch": None,

         # If True, an "auto-update-branch" must be specified.

            "auto-update-wrapper": False,

         # You can point these to another branch, if desired.

            "stable-branch": "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master",

            "dev-branch": "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development",

        },  # NODOC

# Misc - look 'n' feel type customizations

    "Misc":

        {  # NODOC
            # NODOC
         # if you change the command-prefix, no minecraft command will work because minecraft itself only recognizes "/" commands... TODO - Bug or feature? -not sure.

            "command-prefix": "/",

         # Reboot message occurs with automatic timed server restarts ["General"]["timed-reboot"]

            "reboot-message": "Server is conducting a scheduled reboot. The server will be back momentarily!",

         # Restart message occurs when console command "/restart" is run.

            "default-restart-message": "Server restarting...",

         # Stop message is generated from wrapper "/stop" command.

            "stop-message": "Stopping The Minecraft Server",

         # message when wrapper halt is called.

            "halt-message": "Halting Wrapper...",

         # Speficy if wrapper should trap control-z and shutdown in a controlled manner (similar to ctrl-c).  If false, follows the behavior permitted by your system (and that might not end well!)  - Discussion: https://github.com/benbaptist/minecraft-wrapper/issues/521

            "trap-ctrl-z": True,

         # readline is likely to be more-cross platform, but does not use wrapper's ability to keep console keystroke entries visually intact while server produces output.  # NODOC
            # NODOC
            "use-readline": "deprecated",  # NODOC
            # NODOC
         # Use-betterconsole replaces "use-readline" for clarity about what this option does.  The default is False because use-betterconsole may not be fully cross-platform.  Better Console makes it easier for the console operator too see what they are typing, even while the server or wrapper my be writing output at the same time, essentially produces jline-like functionality to the wrapper console...

            "use-betterconsole": False

        },  # NODOC

# General wrapper and server startup options

    "General":

        {  # NODOC
            # NODOC
         # restart server automatically if it stops (unless you explicity used the "/stop" command within the console).

            "auto-restart": True,

         # You will need to update this to your particular server start command line.

            "command": "java -jar -Xmx2G -Xms1G server.jar nogui",

         # If not uft-8, specify your system's encoding here.

            "encoding": "utf-8",

         # Using the default '.' roots the server in the same folder with wrapper. Change this to another folder to keep the wrapper and server folders separate.  Do not use a trailing slash...  e.g. - '/full/pathto/the/server'

            "server-directory": ".",

         # server-name was moved to Web (it is used only by web module in code)  # NODOC
            # NODOC
            "server-name": "deprecated",  # NODOC
            # NODOC
            "shell-scripts": False,

            "timed-reboot": False,

         # salt is used internally for wrapper encryption.  Do not edit this; Wrapper will create the salt.  It does not matter much that it is on disk here, as the user must create a passphrase also.  This just prevents the need for a hardcoded salt and ensures each wrapper installation will use a different one.

            "salt": False,

            "timed-reboot-minutes": 1440,

            "timed-reboot-warning-minutes": 5,

         # wrapper detects server version and adjusts accordingly now.  # NODOC
            # NODOC
            "pre-1.7-mode": "deprecated",  # NODOC
            # NODOC
         # Deprecated for consistency with timed reboot "warning" being in "minutes", not seconds  # NODOC
            # NODOC
            "timed-reboot-seconds": "deprecated",  # NODOC
            # NODOC
         # The remaining items and functionality were moved to group "Updates" and deprecated from this section.  # NODOC
            # NODOC
            "auto-update-branch": "deprecated",  # NODOC
            # NODOC
            "auto-update-dev-build": "deprecated",  # NODOC
            # NODOC
            "auto-update-wrapper": "deprecated",  # NODOC
            # NODOC
            "stable-branch":  "deprecated",  # NODOC
            # NODOC
            "dev-branch":  "deprecated",  # NODOC
            # NODOC
        },  # NODOC

# IRC - This allows your users to communicate to and from the server via IRC and vice versa.

    "IRC":

        {  # NODOC
            # NODOC
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

         # enter a password here and wrapper will convert it to a hashed password

            "control-irc-pass-plaintext": False,

            "control-irc-pass": "from console use `/password IRC control-irc-pass <your password>`",

            "irc-enabled": False,

            "nick": "MinecraftWrap",

            "obstruct-nicknames": False,

         # enter a password here and wrapper will convert it to a hashed password

            "password-plaintext": False,

            "password": "from console use `/password IRC password <your password>`",

            "port": 6667,

            "server": "benbaptist.com",

            "show-channel-server": True,

            "show-irc-join-part": True

        },  # NODOC
# Proxy settings -

# This is a man-in-the-middle proxy similar to BungeeCord, which is used for extra plugin functionality. Online-mode must be set to False in server.properties. Make sure that the server port is not accessible directly from the outside world.

# Note: the online-mode option here refers to the proxy only, not to the server's offline mode.  Each server's online mode will depend on its setting in server.properties.  If you experience issues, you might try turning network-compression-threshold to -1 (off) in server.properties.

    "Proxy":

        {  # NODOC
            # NODOC
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

         # Server port is deprecated - This port is autoconfigured from server console output now.  # NODOC
            # NODOC
            "server-port": "deprecated",  # NODOC
            # NODOC
         # spigot mode has some slightly "off" bytes in the login sequence.

            "spigot-mode": False,

         # silent bans cause your server to ignore sockets from that IP (for IP bans). This will cause your server to appear offline and avoid possible confrontations.

            "silent-ipban": True,

            "hidden-ops":

             # these players do not appear in the sample server player list pings.

                [

                    "SurestTexas00",

                    "BenBaptist"

                ]

        },  # NODOC
        # NODOC
# Web - Web mode allows you to control and monitor the server.  This is not a https connection.  Be mindful of that and don't use the same password you use anywhere else.  It is also advised that this be open only to the localhost.

    "Web":

        {  # NODOC
            # NODOC
            "public-stats": "deprecated",  # NODOC
            # NODOC
            "web-allow-file-management": True,

            "web-bind": "0.0.0.0",

            "web-enabled": False,

         # enter a password here and wrapper will convert it to a hashed password

            "web-password-plaintext": False,

            "web-password": "to set this, from console use `/password Web web-password <your password>`",

            "web-port": 8070,

         # By default, wrapper only accepts connections from "safe" IP addresses.  Disable (set 'safe-ips-use' ot false) or add the IP address of computers you may use to access web mode.

            "safe-ips": ["127.0.0.1"],

            "safe-ips-use": True,

            "server-name": "Minecraft Server",

        }  # NODOC
    # NODOC
    }  # NODOC

# """
