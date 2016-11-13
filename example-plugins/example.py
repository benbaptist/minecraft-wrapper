NAME = "Example Plugin"  # the visible name of the plugin, seen in /plugins and whatnot
AUTHOR = "Ben Baptist"  # the creator/developer of the plugin
ID = "com.benbaptist.plugins.example"  # the ID of the plugin, used for identifying the plugin for storage objects and more
VERSION = (1, 1) # the version number, with commas in place of periods. add more commas if needed
SUMMARY = "This plugin helps demonstrate functions in Wrapper.py. :D"  # a quick, short summary of the plugin seen in /plugins
WEBSITE = "http://wrapper.benbaptist.com/" # the developer or plugin's website
DESCRIPTION = """The longer description of how this plugin helps demonstrate functions in Wrapper.py. :D"""

# The following are optional and affect the plugin import process (for versions after builds circa 107-110).
# Either do not include them or set them to = False if not used:
DISABLED = False  # disables this plugin (for instance, if this *.py file is really only a module for another file/plugin)
DEPENDENCIES = False  # even if there is only 1 dependency, it must be a 'list' type (enclosed in '[]').


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
