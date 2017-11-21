# -*- coding: utf-8 -*-

# These must be specified to prevent wrapper import errors
AUTHOR = "SurestTexas00"
WEBSITE = ""
VERSION = (0, 1, 0)  # DEFAULT (0, 1)

SUMMARY = "Permission Group Manager for Wrapper plugins"
DESCRIPTION = "Permission Manager allows for group permission management. " \
              "Creates permissions using information from  user-created " \
              "configuration files.  Easily create groups with specified " \
              "permissions.  Will create the following structure and files to " \
              "use: \n'<wrapperfolder>/plugins/groupsmanager/groups.txt'  \n\n" \
              "Each line of groups.txt is a permission group's name.  '#' " \
              "can be used as a comment line.\n" \
              "\nEach group name in groups.txt must has a corresponding " \
              "<name>.txt file in the subfolder: \n" \
              "<wrapperfolder>/plugins/groupsmanager/groups"

NAME = "groupsmanager"
ID = "com.suresttexas00.plugins.groupsmanager"


# If you need another plugin to load first, add the plugin(s) to this list
# DEPENDENCIES = [...]  # DEFAULT = False

# camelCase of the plugin API is the historical standard


# noinspection PyPep8Naming,PyClassicStyleClass
class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log

    def onEnable(self):
        self.api.registerHelp("GroupsManager", "plugin group permission manager",
                              [  # help items
                                  ("/loadgr", "Load permission groups",
                                   "groupsmanager.op"),
                                  ("/delgr", "delete permission group data",
                                   "groupsmanager.op"),
                              ]
                              )

        # registered events
        self.api.registerEvent("player.login", self.playerLogin)

        # registered commands
        self.api.registerCommand("loadgr", self._load_gr, "groupsmanager.op")
        self.api.registerCommand("delgr", self._delete_groups, "groupsmanager.op")

    def onDisable(self):
        pass

    def _delete_groups(self, player, args):
        self.api.resetGroups()
        player.message("&6All groups should be deleted now.")

    # Commands section
    def _load_gr(self, player, args):
        helpers = self.api.helpers
        groups = helpers.getfileaslines("groups.txt", "./plugins/groupsmanager")
        group = {}
        if not groups:
            player.message("&cgroups.txt file is missing")
            return
        for eachgr in groups:
            if eachgr == "" or eachgr[0] == "#":  # ignore blank/comment lines
                continue
            group[eachgr] = helpers.getfileaslines(
                "%s.txt" % eachgr, "./plugins/groupsmanager/groups")
            if not group[eachgr]:
                player.message("&c%s.txt group data is missing" % eachgr)
                return
        player.message("&6Group structure passed...")
        #
        for eachgroup in group:
            self.api.createGroup(eachgroup)
            for eachperm in group[eachgroup]:
                if eachperm == "" or eachperm[0] == "#":  # ignore blank lines
                    continue
                permtext = eachperm.lower().split("=f")
                permval = len(permtext) < 2
                permname = permtext[0]
                self.api.addGroupPerm(eachgroup, permname, permval)
                self.log.debug("added %s to group %s" % (permname, eachgroup))
        player.message("&6Group permission data added!")

    # Events section

    # Give OPs or "groupsmanager.auth" persons permission to use
    def playerLogin(self, payload):
        player_obj = payload["player"]
        if player_obj.isOp() > 0:
            if not player_obj.hasPermission("groupsmanager.op"):
                player_obj.setPermission("groupsmanager.op")
        else:
            if player_obj.hasPermission("groupsmanager.op"):
                player_obj.removePermission("groupsmanager.op")
        if player_obj.hasPermission("groupsmanager.auth"):
            player_obj.setPermission("groupsmanager.op")
