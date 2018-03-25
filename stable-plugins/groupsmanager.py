# -*- coding: utf-8 -*-

AUTHOR = "SurestTexas00"
WEBSITE = ""
VERSION = (1, 0, 0)
SUMMARY = "Permission Group Manager for Wrapper plugins"
DESCRIPTION = """
Permission Manager allows for group permission management.  
Creates permissions using information from  user-created  
configuration files.  Easily create groups with specified  
permissions.

Will create the following directory structure on startup:
`./wrapper-data/plugins/groupsmanager/`

First, create a text file called "groups.txt" inside the groupsmanager folder.
second, create a text file for each group you wish to create, <group>.txt.

Each line of groups.txt is a permission group's name.  Comments using '#' 
and blank lines are permitted. 

Each group name in groups.txt must has a corresponding <group>.txt file 
in `/wrapper-data/plugins/groupsmanager/`
"""

NAME = "groupsmanager"
ID = "com.suresttexas00.plugins.groupsmanager"

SAMPLE_GROUPS_TEXT = """admin
moderator
patron
"""

SAMPLE_ADMIN = """
#region commands
region.delete
region.define
region.protect
region.adjust

# own more than one region
region.multiple
# set any region's owner
region.setowner

# vanilla claims
vclaims.admin

# homes
home.admin.super
home.admin.visit
home.admin.homes

# inherit mod
moderator
"""

SAMPLE_MOD = """
# home
home.admin

# inherit trusted
patron
"""

SAMPLE_PATRON = """
teleport.tpa
teleport.tpahere
bookmarks
"""


# noinspection PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyPep8Naming,PyClassicStyleClass
class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log

    def onEnable(self):
        self.api.registerHelp(
            "GroupsManager", "plugin group permission manager",
            [
                ("/loadgr", "Load permission groups", "groupsmanager.op"),
                ("/delgr", "delete permission group data", "groupsmanager.op"),
                ("/summgr <gr>", "list players in <gr>", "groupsmanager.op"),
                ("/summperm <perm>",
                 "list players that have permission <perm>",
                 "groupsmanager.op"),
                ("/sample", "create sample files to edit", "groupsmanager.op"),
            ]
        )

        # registered events
        self.api.registerEvent("player.login", self.playerLogin)

        # registered commands
        self.api.registerCommand(
            "sample", self._sample, "groupsmanager.op"
        )
        self.api.registerCommand(
            "loadgr", self._load_gr, "groupsmanager.op"
        )
        self.api.registerCommand(
            "delgr", self._delete_groups, "groupsmanager.op"
        )
        self.api.registerCommand(
            "summgr", self._summarize_groups, "groupsmanager.op"
        )
        self.api.registerCommand(
            "summperm", self._summarize_perms, "groupsmanager.op"
        )

        # This just creates the file struture, if it does not yet exist
        self.api.helpers.getfileaslines(
            "groups.txt", "./wrapper-data/plugins/groupsmanager"
        )

    def onDisable(self):
        pass

    # Commands section

    def _sample(self, player, args):
        with open("wrapper-data/plugins/groupsmanager/groups.txt", 'w') as f:
            f.write(SAMPLE_GROUPS_TEXT)
        with open("wrapper-data/plugins/groupsmanager/admin.txt", 'w') as f:
            f.write(SAMPLE_ADMIN)
        with open("wrapper-data/plugins/groupsmanager/moderator.txt", 'w') as f:
            f.write(SAMPLE_MOD)
        with open("wrapper-data/plugins/groupsmanager/patron.txt", 'w') as f:
            f.write(SAMPLE_PATRON)
        player.message("&2Files written.")

    def _delete_groups(self, player, args):
        self.api.resetGroups()
        player.message("&6All groups should be deleted now.")

    def _summarize_groups(self, player, args):
        groupname = self.api.helpers.getargs(args, 0)
        if groupname == "":
            player.message("&cYou did not specify a group!.")
            return
        players = []
        player.message("&ePlease wait while I process that request.", 2)
        all_players = self.api.minecraft.getUuidCache()
        for playeruuid in all_players:
            playername = self.api.minecraft.lookupbyUUID(playeruuid)
            if player.hasGroup(groupname, uuid=playeruuid):
                players.append(playername)
        if len(players) > 0:
            player.message("&2" + " ".join(players))
        else:
            player.message("&eNo players have group %s" % groupname)

    def _summarize_perms(self, player, args):
        perm = self.api.helpers.getargs(args, 0)
        if perm == "":
            player.message("&cYou did not specify a permission!.")
            return
        players = []
        player.message("&ePlease wait while I process that request.", 2)
        all_players = self.api.minecraft.getUuidCache()
        for playeruuid in all_players:
            playername = self.api.minecraft.lookupbyUUID(playeruuid)
            if player.hasPermission(perm, another_player=playername):
                players.append(playername)
        if len(players) > 0:
            player.message("&2" + " ".join(players))
        else:
            player.message("&eNo players have permission %s" % perm)

    def _load_gr(self, player, args):
        helpers = self.api.helpers
        groups = helpers.getfileaslines(
            "groups.txt", "./wrapper-data/plugins/groupsmanager"
        )
        group = {}
        if not groups:
            player.message("&cgroups.txt file is missing")
            return
        for eachgr in groups:
            if eachgr == "" or eachgr[0] == "#":  # ignore blank/comment lines
                continue
            group[eachgr] = helpers.getfileaslines(
                "%s.txt" % eachgr, "./wrapper-data/plugins/groupsmanager/"
            )
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
    # Give Super OPs or "groupsmanager.auth" persons permission to use
    def playerLogin(self, payload):
        player_obj = payload["player"]
        if player_obj.isOp() > 9:
            if not player_obj.hasPermission("groupsmanager.op"):
                player_obj.setPermission("groupsmanager.op")
        else:
            if player_obj.hasPermission("groupsmanager.op"):
                player_obj.removePermission("groupsmanager.op")
        if player_obj.hasPermission("groupsmanager.auth"):
            player_obj.setPermission("groupsmanager.op")
