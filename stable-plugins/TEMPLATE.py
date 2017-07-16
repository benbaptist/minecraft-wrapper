# -*- coding: utf-8 -*-

# These must be specified to prevent wrapper import errors
AUTHOR = ""
WEBSITE = ""
VERSION = (0, 1, 0)  # DEFAULT (0, 1)
# NAME = "Template"
# ID = "com.benbaptist.plugins.template"

SUMMARY = "a short summary of the plugin seen in /plugins"
DESCRIPTION = """This is a longer, more in-depth description about the plugin.
While summaries are for quick descriptions of the plugin, the DESCRIPTION
field will be used for a more in-depth explanation.
Descriptions will be used in some parts of Wrapper.py, such as when you 
hover over a plugin name when you run /plugins, or in the web interface. """

# totally optional items
#
# Disables plugin
# DISABLED = True  # DEFAULT = False
#
# If you need another plugin to load first, add the plugin(s) to this list
# DEPENDENCIES = [...]  # DEFAULT = False


# camelCase of the plugin API is the historical standard
# noinspection PyPep8Naming
class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log
        self.data = self.api.getStorage("someFilename", False)  # use wrapper-data/plugins folder

    def onEnable(self):
        self.api.registerCommand("", self._command, "permission.node")

        self.api.registerHelp("template", "description of plugin 'template'",
                              [  # help items
                                  ("/command <argument>", "how to use command", "permission.node"),
                              ]
                              )

        self.api.registerPermission("permission.node", True)  # Everyone can use '/topic3'!

        # Sample registered events
        self.api.registerEvent("player.login", self.playerLogin)

        self.log.info("example.py is loaded!")
        self.log.error("This is an error test.")
        self.log.debug("This'll only show up if you have debug mode on.")

    def onDisable(self):
        self.data.close()  # save Storage to disk and close the Storage's periodicsave() thread.

    # Commands section
    def _command(self, player, args):
        pass

    # Events section
    def playerLogin(self, payload):
        player_obj = payload["player"]
        playername = str(player_obj.username)
        self.api.minecraft.broadcast("&a&lEverybody, introduce %s to the server!" % playername)
