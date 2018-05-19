# -*- coding: utf-8 -*-

# Any missing item will use it's DEFAULT, which is "", unless otherwise noted

AUTHOR = "Ben Baptist"  # the creator/developer of the plugin
WEBSITE = "http://wrapper.benbaptist.com/"  # the developer or plugin's website

# the version number, with commas in place of periods.
VERSION = (0, 1, 0)  # DEFAULT (0, 1)

# a short summary of the plugin seen in /plugins
SUMMARY = "This plugin documents the suggested plugin structure"
DESCRIPTION = """
This is a longer, more in-depth description about the plugin.
While summaries are for quick descriptions of the plugin, the DESCRIPTION
field will be used for a more in-depth explanation.
Descriptions will be used in some parts of Wrapper.py, such as when you
hover over a plugin name when you run /plugins, or in the web interface. 
"""

# The items from this point down are optional items.
# ID and NAME will default to the file name (without the '.py' extension)
#  for simplicity.
#
# the ID of the plugin, used for identifying the plugin.
ID = "com.benbaptist.plugins.example"
# the visible name of the plugin, seen in /plugins and whatnot
NAME = "Sample Plugin"
#
# disables this plugin (for instance, if this *.py file were
# only a module for another file/plugin)
# TODO this plugin is Disabled to run it change this line:
DISABLED = True  # DEFAULT = False
#
# even if there is only 1 dependency, it must be a 'list' type.
# NOTE - this plugin will not get imported because wrapper will
# not find these dependencies (except for 'home.py')
DEPENDENCIES = ["home.py", "teleport.py", ]
# DEPENDENCIES = False

# The specific errors and acceptable deviations from Pep-8 we
# accept in the plugin API:
# -------------------
# PEP-8 Naming conventions:
#  - javascript/java style camelCase of the plugin API is the historical norm.
# Unused arguments in methods:
#  - Wrapper passes these arguments (player, args) whether we use them of not..
# defining *.self attributes outside of __init__:
#  - Getting Storages and defining them to a self should be done on onEnable(),
#    otherwise, a storage could get closed, but not restarted during a
#    plugin reload.
# Use of classic style classes:
#  - plugin `Main` is not tested for new classes.
# Using non static methods where a static method amy be used
# and LIMITED broad exception try-except usages are permitted.


# noinspection PyPep8Naming,PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyClassicStyleClass,PyAttributeOutsideInit
class Main:
    """
    class 'Main' is what wrapper imports.  The normal steps are:
    1) Wrapper loads the plugin and reads the CONSTANTS above to determine
       the plugin's ID and any dependencies.
    2) If there are dependencies, it loads those first.
    3) It then instantiates this class Main. (the dependencies are now
        __init__'ed and onEnable'd at this point...)
    4) It stores the plugin metadata in wrapper's Plugin's dictionary.
    5) Lastly, it runs the Main.onEnable() code.
    """

    def __init__(self, api, log):
        self.api = api
        self.log = log

        # the following getPluginContext is safe to run here because the
        # Main class for any dependency will be instantiated before this
        # Main is, providing you have listed the plugin as a 'DEPENDENCIES'
        # Storages and other plugin contexts can be defined here or in
        # onEnable().  althought it is generally considered better style
        # to define them here, keeping them in onEnable() ensures proper
        # operation of the plugins during reloads (since onDisable() will
        # close any open Storages!).

        # to access another plugin's data (or methods):
        self.home_plugin = self.api.getPluginContext(
            "net.version6.minecraft.plugins.home"
        )

    # onEnable is a REQUIRED method and is run immediately
    # when the plugin is imported.
    def onEnable(self):
        # you can disable the plugin by returning False!

        # sample Storage
        # setting True causes the data to be stored in the
        # server/world/plugins folder.  otherwise, the data is
        #  stored in wrapper's /wrapper-data/plugins folder.
        self.data = self.api.getStorage("someFilename", True)

        # Sample register commands
        self.api.registerCommand("topic1", self._command1, "permission.node")
        self.api.registerCommand(
            ("topic2", "top2", "topic_2"), self._command2, "another.permission"
        )
        self.api.registerCommand("topic3", self._command3, "third.permission")

        # Sample register help
        self.api.registerHelp(
            "Example", "description of Topic plugin", [
                ("/topic1 <argument>", "how to use topic1", "permission.node"),
                ("/topic2 <arg1> <arg2>", "talk about topic2",
                 "another.permission"),
                ("/topic3", "...", "third.permission")
            ]
        )

        # Everyone can use '/topic3'!
        self.api.registerPermission("third.permission", True)

        # Sample registered events
        self.api.registerEvent("player.login", self.playerLogin)
        self.api.registerEvent("player.logout", self.playerLogout)

        # Due to our self-implemented colorization of logs, text formatting
        # must use old-stye ("variable = %s" % variable) formatting and not the
        # newer ("variable = ", variable) style formatting.
        self.log.info("example.py is loaded!")
        self.log.error("This is an error test.")
        self.log.debug("This'll only show up if you have debug mode on.")

    # onDisable is not required, but highly suggested, especially if
    #  you have to save Storages.
    def onDisable(self):
        # this code must terminate before wrapper will stop.

        # save Storage to disk and close the Storage's periodicsave() thread.
        self.data.close()

    # Commands section
    def _command1(self, player, args):
        pass

    def _command2(self, player, args):
        pass

    def _command3(self, player, args):
        self.data.Data["message"] = "You ran /topic3"
        player.message(self.data.Data["message"])
        player.message({"text": "Congratulations!", "color": "aqua"})
        self.api.minecraft.broadcast(
            "%s ran /topic3; congratulate them!" % player.username
        )

    # Events section
    def playerLogin(self, payload):
        playerObj = payload["player"]
        playername = str(playerObj.username)
        self.api.minecraft.broadcast(
            "&a&lEverybody, introduce %s to the server!" % playername
        )

    def playerLogout(self, payload):
        playerObj = payload["player"]
        playername = str(playerObj.username)
        self.api.minecraft.broadcast(
            "&7&oYou will be dearly missed, %s." % playername
        )
