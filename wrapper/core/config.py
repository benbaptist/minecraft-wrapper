# -*- coding: utf-8 -*-

import os
import sys
import logging
from utils.helpers import getjsonfile, putjsonfile

"""[General]
server-name = Minecraft Server
server-directory = "."
command = java -jar minecraft_server.1.9.2.jar nogui
auto-restart = True
auto-update-wrapper = False
auto-update-dev-build = False
pre-1.7-mode = False
timed-reboot = False
timed-reboot-seconds = 86400
timed-reboot-warning-minutes = 5
shell-scripts = False
encoding = UTF-8

[Backups]
;; Automatic backups with automatic backup pruning. Interval is in seconds. ;;
enabled = False
backup-folders = ['server.properties', 'world']
backup-interval = 3600
backup-notification = True
backup-location = backup-directory
backup-compression = False
backups-keep = 10

[IRC]
;; This allows your users to communicate to and from the server via IRC and vise versa. ;;
irc-enabled = False
server = benbaptist.com
port = 6667
nick = MinecraftWrap
password = None
channels = ['#wrapper']
command-character = .
autorun-irc-commands = ['COMMAND 1', 'COMMAND 2']
obstruct-nicknames = False
control-from-irc = False
control-irc-pass = password
show-channel-server = True
show-irc-join-part = True

[Proxy]
;; This is a man-in-the-middle proxy similar to BungeeCord, which is used for extra plugin functionality. ;;
;; online-mode must be set to False in server.properties. Make sure that the server is inaccessible directly
;; from the outside world. ;;
;; Note: the online-mode option here refers to the proxy only, not to the server's offline mode. ;;
;; It is recommended that you turn network-compression-threshold to -1 in server.properties for less issues. ;;
proxy-enabled = False
proxy-port = 25565
proxy-bind = 0.0.0.0
server-port = 25564
online-mode = True
max-players = 1024
spigot-mode = False
convert-player-files = False

[Web]
;; This is a web UI. ;;
web-enabled = False
web-bind = 0.0.0.0
web-port = 8070
web-password = password
web-allow-file-management = True
public-stats = True
"""

# Default Configuration File
NEWCONFIG = {
    "Backups": {
        "backup-compression": False,
        "backup-folders": [
            "server.properties",
            "world"
        ],
        "backup-interval": 3600,
        "backup-location": "backup-directory",
        "backup-notification": True,
        "backups-keep": 10,
        "enabled": False
    },
    "General": {
        "auto-restart": True,
        "auto-update-dev-build": False,
        "auto-update-wrapper": False,
        "command": "java -jar minecraft_server.1.9.2.jar nogui",
        "encoding": "UTF-8",
        "pre-1.7-mode": False,
        "server-directory": ".",
        "server-name": "Minecraft Server",
        "shell-scripts": False,
        "timed-reboot": False,
        "timed-reboot-seconds": "86400",
        "timed-reboot-warning-minutes": 5
    },
    "IRC": {
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
        "convert-player-files": False,
        "max-players": 1024,
        "online-mode": True,
        "proxy-bind": "0.0.0.0",
        "proxy-enabled": False,
        "proxy-port": 25565,
        "server-port": 25564,
        "spigot-mode": False
    },
    "Web": {
        "public-stats": True,
        "web-allow-file-management": True,
        "web-bind": "0.0.0.0",
        "web-enabled": False,
        "web-password": "password",
        "web-port": 8070
    }
}


class Config:
    def __init__(self):
        self.log = logging.getLogger('Config')
        self.config = {}
        self.exit = False

    def loadconfig(self):
        # creates new wrapper.properties. The reason I do this is so the
        # ordering isn't random and is a bit prettier
        if os.path.exists("wrapper.properties"):
            with open("wrapper.properties", "r") as f:
                oldconfig = f.read()
            oldconfig = "Deprecated File!  Use the 'wrapper.properties.json' instead!\n\n%s" % oldconfig
            with open("_wrapper.properties", "w") as f:
                f.write(oldconfig)
            os.remove("wrapper.properties")

        if not os.path.exists("wrapper.properties.json"):
            putjsonfile(NEWCONFIG, "wrapper.properties", sort=True, encodedas="UTF-8")
            self.exit = True

        self.config = getjsonfile("wrapper.properties")  # the only data file that must be UTF-8
        if self.config is None:
            self.log.error("I think you messed up the Json formatting of your "
                           "wrapper.properties.json file. "
                           "Take your file and have it checked at: \n"
                           "http://jsonlint.com/")
            self.exit = True

        changesmade = False
        for section in NEWCONFIG:
            if section not in self.config:
                self.log.debug("Adding section [%s] to configuration", section)
                self.config[section] = {}
                changesmade = True
            for configitem in NEWCONFIG[section]:
                if configitem not in self.config[section]:
                    self.log.debug("Key %s in section %s not in wrapper.properties - adding", configitem, section)
                    self.config[section][configitem] = NEWCONFIG[section][configitem]
                    changesmade = True
        if changesmade:
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
        putjsonfile(self.config, "wrapper.properties", sort=True, encodedas="UTF-8")
