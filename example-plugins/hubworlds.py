# the visible name of the plugin, seen in /plugins and whatnot
NAME = "hubworlds"
# the creator/developer of the plugin
AUTHOR = "SurestTexas00"
# the ID of the plugin, used for identifying the plugin internally
ID = "wrapper.plugin.surest.hubworlds"
# the version number, with commas in place of periods. add more commas if needed
VERSION = (1, 0)
# a quick, short summary of the plugin seen in /plugins
SUMMARY = "A sample Hub with four worlds that can be modded for your use."
# the developer or plugin's website
WEBSITE = "http://wrapper.benbaptist.com/"
# long description desplayed in Web pluging descriptions, etc.
DESCRIPTION = "The hubworlds plugin is a sample plugin that demonstrates " \
              "wrapper hubs and can be modified for use in your own " \
              "server(s).  This sample setup assumes 4 worlds:\n" \
              "1) The main online mode wrapper and it's wrapped server, on " \
              "whichever ports you prefer...\n" \
              "2) 'world1p' is another offline wrapper running on port " \
              "25611.  'world1 directly connects to world1p's server running " \
              "on 26510, by-passing it's proxy mode.  This is just for demo " \
              "purposes - you probably don't want to do this; it will " \
              "confuse wrapper since it will not be able to see the player" \
              " objects!\n" \
              "3) world2 - an unwrapped server.\n" \
              "4) Another server with no wrapper.\n\n" \
              "You can replace worlds 2 and 3 with any server or wrapper you " \
              "like.  The actual world names on disk can be whatever you like." \
              "\n\nSometimes, you don't spawn correctly.  This can usually be" \
              "corrected by running /hub and trying again."
# The following are optional and affect the plugin import process.
# Either do not include them or set them to = False if not used:

# Disables this plugin (for instance, if this *.py file is really only
#  a module for another file/plugin)
DISABLED = False
# Dependencies is a `list` (enclosed in '[]', even if there is only one item).
DEPENDENCIES = False


class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log

    def onEnable(self):
        self.log.info("Hubworlds is loaded!")

        self.api.registerHelp(
            "hubworlds", SUMMARY,
            [("/hub", "Returns you to this server.", None),  # /hub is built-in
             ("/world1", "visit vanilla world1.", None),
             ("/world1p", "visit vanilla world1's proxy (and use its plugins)", None),
             ("/world2", "visit world2.", None),
             ("/world3", "visit world3.", None),
             ]
        )

        self.api.registerEvent("player.login", self.playerLogin)
        self.api.registerCommand("world1", self._s1)
        self.api.registerCommand("world1p", self._s1p)
        self.api.registerCommand("world2", self._s2)
        self.api.registerCommand("world3", self._s3)

    def playerLogin(self, payload):
        playerObj = payload["player"]
        playername = str(playerObj.username)
        self.api.minecraft.broadcast(
            "&a&lEverybody, welcome %s and tell them what "
            "hub worlds you have visited!" % playername
        )

    def onDisable(self):
        pass

    def _s1(self, player, args):
        player.connect(25610)

    def _s1p(self, player, args):
        player.connect(25611)

    def _s2(self, player, args):
        player.connect(25612)

    def _s3(self, player, args):
        player.connect(25614)
