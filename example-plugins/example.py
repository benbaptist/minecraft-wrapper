# -*- coding: utf-8 -*-

# Any missing item will use it's DEFAULT, which is "", unless otherwise noted

AUTHOR = "Ben Baptist"  # the creator/developer of the plugin
WEBSITE = "http://wrapper.benbaptist.com/"  # the developer or plugin's website

# the version number, with commas in place of periods.
VERSION = (0, 1, 0)  # DEFAULT (0, 1)

SUMMARY = "This plugin documents the suggested plugin structure"  # a short summary of the plugin seen in /plugins
DESCRIPTION = """This is a longer, more in-depth description about the plugin.
While summaries are for quick descriptions of the plugin, the DESCRIPTION
field will be used for a more in-depth explanation.
Descriptions will be used in some parts of Wrapper.py, such as when you
hover over a plugin name when you run /plugins, or in the web interface. """

# The items from this point down are optional items.  ID and NAME will default to the file name for simplicity.
#
# the ID of the plugin, used for identifying the plugin for storage objects and more
ID = "com.benbaptist.plugins.example"  # DEFAULT = the filename (without the '.py' extension)
# the visible name of the plugin, seen in /plugins and whatnot
NAME = "Sample Plugin"  # DEFAULT = the filename (without the '.py' extension)
#
# disables this plugin (for instance, if this *.py file were only a module for another file/plugin)
DISABLED = False  # DEFAULT = False
#
# even if there is only 1 dependency, it must be a 'list' type (enclosed in '[]').
# NOTE - this plugin will not get imported because wrapper will not find these dependencies (except for 'home.py')
DEPENDENCIES = ["home.py", "vault.py", "economy.py", "etc..."]  # DEFAULT = False


# the Wrapper 1.0.0 rc release will maintain backwards compatibility with the pre-release plugin API except for:
# - Storages require a close() method to save their contents to disk. save() still works, but the storage can remain
#   open after the plugin disables, resulting in memory leakages and inconsistent disk storage content.  close() also
#   performs a save().
# - items outside the formal API (accessing wrapper/server/proxy/etc methods directly) are not supported.  Wrapper's own
#   internal classes and methods have been fully re-written and refactored with no support for the prior code.
#
# desiring to maintain backwards-compatibility in wrapper's API means maintaining the camelCase tradition for the API.
# This reasoning is considered by PEP-8 to be a valid reason for non-compliance with the PEP.
# noinspection PyPep8Naming
class Main:
    """
    class 'Main' is what wrapper imports.  The normal steps are:
    1) Wrapper loads the plugin and reads the CONSTANTS above to determine the plugin's ID and any dependencies.
    2) If there are dependencies, it loads those first.
    3) It then instantiates this class Main. (the dependencies are now __init__'ed and onEnable'd at this point...)
    4) It stores the plugin metadata in wrapper's Plugin's dictionary.
    5) Lastly, it runs the Main.onEnable() code.
    """

    def __init__(self, api, log):
        self.api = api
        self.log = log

        # the following getPluginContext is safe to run here because the Main class for any dependency will
        # be instantiated before this Main is, providing you have listed the plugin as a 'DEPENDENCIES'
        # Storages and other plugin contexts can be defined here or in onEnable().  It is generally
        # considered better style to define them here.

        # to access another plugin's data (or methods):
        self.home_plugin = self.api.getPluginContext("net.version6.minecraft.plugins.home")

        # sample Storage
        # setting True causes the data to be stored in the server/world/plugins folder.  otherwise,
        #  the data is stored in wrapper's /wrapper-data/plugins folder.
        self.data = self.api.getStorage("someFilename", True)

    # onEnable is a REQUIRED method and is run immediately when the plugin is imported.
    def onEnable(self):

        # Sample register commands
        self.api.registerCommand("/topic1", self._command1, "permission.node")
        self.api.registerCommand(("/topic2", "top2", "topic_2"), self._command2, "another.permission")
        self.api.registerCommand("/topic3", self._command3, "third.permission")

        # Sample register help
        self.api.registerHelp("Topic", "description of Topic plugin", [
                        ("/topic1 <argument>", "how to use topic1", "permission.node"),
                        ("/topic2 <arg1> <arg2>", "talk about topic2", "another.permission"),
                        ("/topic3", "...", "third.permission")
                ])

        self.api.registerPermission("third.permission", True)  # Everyone can use '/topic3'!

        # Sample registered events
        self.api.registerEvent("player.login", self.playerLogin)
        self.api.registerEvent("player.logout", self.playerLogout)

        self.log.info("example.py is loaded!")
        self.log.error("This is an error test.")
        self.log.debug("This'll only show up if you have debug mode on.")

    def onDisable(self):  # onDisable is not required, but highly suggested, especially if you have to save Storages.
        # this code must terminate before wrapper will stop.
        self.data.close()  # save Storage to disk and close the Storage's periodicsave() thread.

    # Commands section
    def _command1(self, player, args):
        pass

    def _command2(self, player, args):
        pass

    def _command3(self, player, args):
        player.message("You ran /topic3")
        player.message({"text": "Congratulations!", "color": "aqua"})
        self.api.minecraft.broadcast("%s ran /topic3; congratulate them!" % player.username)

    # Events section
    def playerLogin(self, payload):
        playerObj = payload["player"]
        playername = str(playerObj.username)
        self.api.minecraft.broadcast("&a&lEverybody, introduce %s to the server!" % playername)

    def playerLogout(self, payload):
        playerObj = payload["player"]
        playername = str(playerObj.username)
        self.api.minecraft.broadcast("&7&oYou will be dearly missed, %s." % playername)
