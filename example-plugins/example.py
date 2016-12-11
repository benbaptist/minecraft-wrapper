# -*- coding: utf-8 -*-

# Any missing item will use it's DEFAULT, which is "", unless otherwise noted

# the visible name of the plugin, seen in /plugins and whatnot
NAME = "Example Plugin"  # DEFAULT = the filename (without the '.py' extension)
AUTHOR = "Ben Baptist"  # the creator/developer of the plugin
WEBSITE = "http://wrapper.benbaptist.com/"  # the developer or plugin's website

# the ID of the plugin, used for identifying the plugin for storage objects and more
ID = "com.benbaptist.plugins.example"  # DEFAULT = the filename with out '.py' extention (in this case, 'example')

# the version number, with commas in place of periods.
VERSION = (1, 1)  # DEFAULT (0, 1)

# a short summary of the plugin seen in /plugins
SUMMARY = "This plugin helps demonstrate functions in Wrapper.py. :D"
DESCRIPTION = """The longer description of how this plugin helps demonstrate functions in Wrapper.py. :D"""

# The following are optional and affect the plugin import process (for versions after builds circa 107-110).
# Either do not include them or set them to = False if not used:

# disables plugin (for instance, if this *.py file is really only a module for another file/plugin)
DISABLED = False
# even if there is only 1 dependency, it must be a 'list' type (enclosed in '[]').
DEPENDENCIES = False


class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log

    def onEnable(self):
        self.log.info("example.py is loaded!")
        self.log.error("This is an error test.")
        self.log.debug("This'll only show up if you have debug mode on.")

        self.api.registerEvent("player.login", self.playerLogin)
        self.api.registerEvent("player.logout", self.playerLogout)

    def playerLogin(self, payload):
        playerObj = payload["player"]
        playername = str(playerObj.username)
        self.api.minecraft.broadcast("&a&lEverybody, introduce %s to the server!" % playername)

    def playerLogout(self, payload):
        playerObj = payload["player"]
        playername = str(playerObj.username)
        self.api.minecraft.broadcast("&7&oYou will be dearly missed, %s." % playername)

    def onDisable(self):
        pass
