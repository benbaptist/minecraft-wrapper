# -*- coding: utf-8 -*-

import SurestLib
import time
from copy import deepcopy

NAME = "VanillaClaims"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.vanillaclaims"
VERSION = (0, 1)
SUMMARY = "Simple player-administered land claim system"
WEBSITE = ""
DESCRIPTION = "Requires SurestLib.py and regions.py"
DEPENDENCIES = ["regions.py", ]

BEDROCK = 7
GOLDBLOCK = 41
DIAMONDBLOCK = 57
LITREDSTONEORE = 74


class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log
        self.regions = self.api.getPluginContext("com.suresttexas00.plugins.regions")
        self.defaultclaimblocks = 1024

        # sets the rate of block accumulation
        self.actionsperblock = 100

        self.maxclaimblocks = 200000
        self.maxclaims = 5
        self.minclaimsize = 81
        self.minclaimwidth = 6

        # whether player must make their own gold spade
        self.earnspade = False

        self.data_storageobject = self.api.getStorage("claimdata", True)
        self.data = self.data_storageobject.Data

    def onEnable(self):

        # init data
        if "player" not in self.data:
            self.data["player"] = {}

        self.api.registerEvent("player.place", self.action_place)
        self.api.registerEvent("player.spawned", self.playerSpawned)
        self.api.registerEvent("timer.second", self.onSecond)
        self.api.registerEvent("player.dig", self.action_dig)

        # Whether users can use the system by default or need vclaims permission
        vclaimsperms = None
        # vclaimsperms = "vclaims.use"

        self.api.registerHelp("VanillaClaims", "Claim based grief prevention system.", [
            ("/abandonclaim", "Abandon the claim you are standing in.", vclaimsperms),
            ("/abandonallclaims", "Abandon all claims you own.", vclaimsperms),
            ("/adjustclaimblocks <player> <add/sub/set/info> <amount>", "Adjust player claim blocks.", "vclaims.admin"),
            ("/transferclaim <newusername>", "re-creates the same claim in another's name", "vclaims.admin"),
            ("/claimblocks", "View your claims blocks information.", vclaimsperms),
            ("/trust <player>", "Allow player full access to your claim.", vclaimsperms),
            ("/breaktrust <player>", "Allow player to break blocks on your claim.", vclaimsperms),
            ("/placetrust <player>", "Allow player to place blocks / operate things.", vclaimsperms),
            ("/accesstrust <player>", "Allow player interaction (place lava, eat, throw pearls, etc)", vclaimsperms),
            ("/untrust <player>", "remove a player from your claim.", vclaimsperms),
            ("XX/trustlist", "Display the claim's player information.", vclaimsperms),
            ("/deleteclaim", "Delete the claim you are standing in", "vclaims.admin"),
            ("/deleteallclaims <player>", "Delete all a players claims.", "vclaims.admin"),
            ("/show", "Show the claim you are standing in.", vclaimsperms),
            ("/spade", "Gives the land claim gold shovel", vclaimsperms)])

        self.api.registerCommand("show", self._show_comm, vclaimsperms)
        self.api.registerCommand(("spade", "wand", "shovel"), self._spade, vclaimsperms)
        self.api.registerCommand(("abandonclaim", "abandonclaims"), self._abandonclaim_comm, vclaimsperms)
        self.api.registerCommand("abandonallclaims", self._abandonallclaims_comm, vclaimsperms)
        self.api.registerCommand("deleteclaim", self._deleteclaim_comm, "vclaims.admin")
        self.api.registerCommand("deleteallclaims", self._deleteallclaims_comm, "vclaims.admin")
        self.api.registerCommand("adjustclaimblocks", self._adjustclaimblocks_comm, "vclaims.admin")
        self.api.registerCommand("transferclaim", self._transferclaim_comm, "vclaims.admin")
        self.api.registerCommand(("claimblocks", "claimblock", "claimsblock", "claimsblocks"), self._claimblocks_comm,
                                 vclaimsperms)
        self.api.registerCommand("trust", self._trust_comm, vclaimsperms)
        self.api.registerCommand("breaktrust", self._breaktrust_comm, vclaimsperms)
        self.api.registerCommand("placetrust", self._placetrust_comm, vclaimsperms)
        self.api.registerCommand("accesstrust", self._accesstrust_comm, vclaimsperms)
        self.api.registerCommand("untrust", self._untrust_comm, vclaimsperms)
        # self.api.registerCommand("trustlist", self._trustlist_comm, vclaimsperms)

    def onDisable(self):
        self.data_storageobject.close()

    def playerSpawned(self, payload):
        # try:  # wrapper bullet-proofing
        playerobj = payload["player"]
        playername = str(playerobj.username)
        onlineuuid = str(playerobj.mojangUuid)
        if onlineuuid not in self.data["player"]:
            self._init_player_record(onlineuuid, playername)

    def onSecond(*args):  # Change back to (self, payload)?
        self = args[0]
        for players in self.api.minecraft.getPlayers():
            player = self.api.minecraft.getPlayer(players)
            try:
                playeruuid = str(player.mojangUuid)
            except TypeError:
                continue  # probably a bad player object

            if playeruuid not in self.data["player"]:
                self._init_player_record(playeruuid, player.username)
            try:
                item = player.getHeldItem()
            except AttributeError:
                self.api.minecraft.console("kick %s bad connection -restart your game?" % player.username)
                continue

            try:
                itemid = item["id"]
            except TypeError:
                itemid = "none"

            if "selectionmode" not in self.data["player"][playeruuid]:
                self.data["player"][playeruuid]["selectionmode"] = "idle"
            mode = self.data["player"][playeruuid]["selectionmode"]
            if itemid != 284 and mode != "none":
                player.message("&2Shovel put away... Switching out of claims selection mode")
                self._finishwithselectionmode(playeruuid)
            if itemid == 284 and mode == "none":
                # This just exists to notify player they can use gold shovel now for claims
                player.message("&2Claims shovel active... Click and area to edit or to claim.")
                self.data["player"][playeruuid]["selectionmode"] = "idle"

    def action_dig(self, payload):
        player = self.api.minecraft.getPlayer(payload["player"])
        position = payload["position"]
        item = player.getHeldItem()
        playeruuid = str(player.mojangUuid)
        dim = player.getDimension()
        action = payload["action"]

        try:
            itemid = item["id"]
        except TypeError:
            itemid = "none"

        if itemid == 284 and action == "end_break":
            player.sendBlock(position, BEDROCK, 0)
            player.message("&5Easy slick.. just a light click will do!")
            return False
        if itemid == 284 and action == "begin_break":
            self.wand_use(player, playeruuid, position, dim)
            return False

        # block increaser
        self.data["player"][playeruuid]["activitycount"] += 1
        activities = self.data["player"][playeruuid]["activitycount"]
        if activities % self.actionsperblock != 0:
            return
        self.data["player"][playeruuid]["activitycount"] = 0
        idleclaimblocks = self.data["player"][playeruuid]["claimblocks"]
        inuseblocks = self.data["player"][playeruuid]["claimblocksused"]
        if (idleclaimblocks + inuseblocks) < self.maxclaimblocks:
            self.data["player"][playeruuid]["claimblocks"] += 1

    def action_place(self, payload):
        player = self.api.minecraft.getPlayer(payload["player"])
        dim = int(player.getDimension())
        clickposition = (payload["clickposition"][0], payload["clickposition"][1], payload["clickposition"][2])
        item = player.getHeldItem()
        onlineuuid = str(player.mojangUuid)

        try:
            itemid = item["id"]
        except TypeError:
            itemid = "none"

        if itemid == 284:
            self.wand_use(player, onlineuuid, clickposition, dim)
            return False  # never allow gold shovel use - reserved for claims

        # block increaser
        self.data["player"][onlineuuid]["activitycount"] += 1
        activities = self.data["player"][onlineuuid]["activitycount"]
        if activities % self.actionsperblock != 0:
            return
        self.data["player"][onlineuuid]["activitycount"] = 0
        idleclaimblocks = self.data["player"][onlineuuid]["claimblocks"]
        inuseblocks = self.data["player"][onlineuuid]["claimblocksused"]
        if (idleclaimblocks + inuseblocks) < self.maxclaimblocks:
            self.data["player"][onlineuuid]["claimblocks"] += 1
        return

    def wand_use(self, player, playeruuid, position, dim):
        """redefines things a bit.
        Point parameters are now: point1 now means goal is point one selection,
        point2 means goal is point2 selection.  Error means error occurred with
        selection (too small, ovelapping region, etc, etc...). """
        # "none", "point1" "point2", "error"
        # "none, "new", "edit", "idle"
        point = self.data["player"][playeruuid]["selectionpoint"]
        mode = self.data["player"][playeruuid]["selectionmode"]
        anyregion = self.regions.regionname(position, dim)
        if mode == "new":
            # entering new mode should have point set to point1.
            if point == "error":
                #
                # Only clicking a previously selected corner will restore to point selection
                if position == self.data["player"][playeruuid]["point2"]:
                    # Contine point 2 selection
                    self.data["player"][playeruuid]["selectionpoint"] = "point2"
                    return
                if position == self.data["player"][playeruuid]["point1"]:
                    #
                    # move point 2 data to point one (including marking)
                    pt1 = deepcopy(self.data["player"][playeruuid]["point1"])
                    pt1dim = deepcopy(self.data["player"][playeruuid]["dim1"])
                    pt2 = deepcopy(self.data["player"][playeruuid]["point2"])
                    pt2dim = deepcopy(self.data["player"][playeruuid]["dim2"])
                    self.data["player"][playeruuid]["point1"] = pt2
                    self.data["player"][playeruuid]["dim1"] = pt2dim
                    self.data["player"][playeruuid]["point2"] = pt1
                    self.data["player"][playeruuid]["dim2"] = pt1dim
                    #
                    # re-draw new point1 as point1 color (diamond)
                    player.sendBlock(self.data["player"][playeruuid]["point1"],
                                     DIAMONDBLOCK, 0)
                    #
                    # Continue with point 2 (new point2) selection
                    self.data["player"][playeruuid]["selectionpoint"] = "point2"
                    return
                # error assumes two points selected - redraw those points and remind player what to do.
                player.sendBlock(self.data["player"][playeruuid]["point1"],
                                 LITREDSTONEORE, 0)
                player.sendBlock(self.data["player"][playeruuid]["point2"],
                                 LITREDSTONEORE, 0)
                player.message("&eChange or edit selection area by clicking on a restone")
                player.message("&e corner and then selecting a new spot.")
                player.message("&e(to cancel, put shovel away)")
                return

            if point == "point2":
                if position == self.data["player"][playeruuid]["point1"]:
                    player.sendBlock(position, DIAMONDBLOCK, 0)
                    return  # ignore double selection/clicking
                if self.data["player"][playeruuid]["dim1"] != dim:
                    self.data["player"][playeruuid]["selectionpoint"] = "point1"  # restart claim in new dimension
                    self.data["player"][playeruuid]["selectionmode"] = "new"
                    player.message("&cSelection dimension changed...")
                    return
                # input point 2
                self.data["player"][playeruuid]["point2"] = position
                # Normalize selection (set to standard pt1 low and pt2 high coords)
                low, high = self.regions.normalizeSelection(
                    self.data["player"][playeruuid]["point1"],
                    self.data["player"][playeruuid]["point2"]
                )
                highcorner = (high[0], position[1] + 5, high[2])
                lowcorner = (low[0], position[1] + 1, low[2])
                self.data["player"][playeruuid]["point3"] = lowcorner
                self.data["player"][playeruuid]["point4"] = highcorner
                # attempt claim
                newclaim = self._claim(player, playeruuid)
                if newclaim:
                    player.sendBlock(position, GOLDBLOCK, 0)
                    player.message("&6Second Corner selected.")
                    player.message("&6Claim action successful.")
                    SurestLib.client_show_cube(player, lowcorner, highcorner, sendblock=False)
                    player.sendBlock(self.data["player"][playeruuid]["claiminfo"][newclaim]["handle1"],
                                     DIAMONDBLOCK, 0)
                    player.sendBlock(self.data["player"][playeruuid]["claiminfo"][newclaim]["handle2"],
                                     GOLDBLOCK, 0)
                    self.data["player"][playeruuid]["selectionmode"] = "none"
                    self.data["player"][playeruuid]["selectionpoint"] = "none"
                    return
                if newclaim is False:
                    player.message("&cClaim action failed.  &eChange or edit selection area")
                    player.message("&eby right-clicking on a restone corner and then right-")
                    player.message("&eclick on a new spot")
                    player.sendBlock(self.data["player"][playeruuid]["point1"],
                                     LITREDSTONEORE, 0)
                    player.sendBlock(self.data["player"][playeruuid]["point2"],
                                     LITREDSTONEORE, 0)
                    self.data["player"][playeruuid]["selectionpoint"] = "error"
                    return

            if point == "point1":  # select point 1
                self.data["player"][playeruuid]["point3"] = (0, 0, 0)
                self.data["player"][playeruuid]["point4"] = (0, 0, 0)
                self.data["player"][playeruuid]["point1"] = position
                self.data["player"][playeruuid]["dim1"] = dim
                self.data["player"][playeruuid]["selectionpoint"] = "point2"
                player.sendBlock(position, DIAMONDBLOCK, 0)
                player.message("&6First Corner selected. &e(to cancel, put shovel away)")
                return

        if mode == "edit":
            # entering edit mode requires the input of points 1 and 2 from whatever is the edited selection.
            # and point set to "none"
            if point in ("error", "none"):
                #
                # Only clicking a previously selected corner will restore to point selection
                # clicklowXZ = position[0], position[2]
                if position == self.data["player"][playeruuid]["point1"]:
                    # Contine point 2 selection
                    self.data["player"][playeruuid]["selectionpoint"] = "point1"
                    player.sendBlock(self.data["player"][playeruuid]["point1"],
                                     BEDROCK, 0)
                    return  # Only clicking a previously selected corner will restore to point selection
                if position == self.data["player"][playeruuid]["point2"]:
                    # Contine point 2 selection
                    self.data["player"][playeruuid]["selectionpoint"] = "point2"
                    player.sendBlock(self.data["player"][playeruuid]["point2"],
                                     BEDROCK, 0)
                    return

                # render - clicking outside of points
                if anyregion is False:
                    self.data["player"][playeruuid]["selectionmode"] = "none"
                    self.data["player"][playeruuid]["selectionpoint"] = "none"
                    return
                handle1 = self.data["player"][playeruuid]["claiminfo"][anyregion]["handle1"]
                handle2 = self.data["player"][playeruuid]["claiminfo"][anyregion]["handle2"]
                player.sendBlock(handle1, DIAMONDBLOCK, 0)
                player.sendBlock(handle2, GOLDBLOCK, 0)
                normpos1, normpos2 = self.regions.normalizeSelection(handle1, handle2)
                correcty = normpos2[1] + 4
                normpos_tocorrected = (normpos2[0], correcty, normpos2[2])
                SurestLib.client_show_cube(player, normpos1, normpos_tocorrected, sendblock=False)

            if point in ("point2", "point1"):
                if point == "point2":
                    self.data["player"][playeruuid]["dim2"] = dim
                if point == "point1":
                    self.data["player"][playeruuid]["dim1"] = dim
                if self.data["player"][playeruuid]["dim2"] != self.data["player"][playeruuid]["dim1"]:
                    self.data["player"][playeruuid]["selectionpoint"] = "none"  # abort editing mode
                    self.data["player"][playeruuid]["selectionmode"] = "none"
                    player.message("&cSelection dimension does not match...")
                    player.message("&cExiting claim edit mode...")
                    return
                # input the new point
                self.data["player"][playeruuid][point] = position
                # Normalize selection (set to standard pt1 low and pt2 high coords)
                low, high = self.regions.normalizeSelection(
                    self.data["player"][playeruuid]["point1"],
                    self.data["player"][playeruuid]["point2"]
                )
                highcorner = (high[0], position[1] + 5, high[2])
                lowcorner = (low[0], position[1] + 1, low[2])
                self.data["player"][playeruuid]["point3"] = lowcorner
                self.data["player"][playeruuid]["point4"] = highcorner
                if point == "point1":
                    player.sendBlock(position, DIAMONDBLOCK, 0)
                if point == "point2":
                    player.sendBlock(position, GOLDBLOCK, 0)
                player.message("&6Corner selected.")
                # thisclaimname = self.data["player"][playeruuid]["selectiontarget"]
                thisclaimname = anyregion
                newclaim = self._editclaim(player, playeruuid, thisclaimname)

                if newclaim:
                    player.message("&6Claim action successful.")
                    SurestLib.client_show_cube(player, lowcorner, highcorner, sendblock=False)
                    player.sendBlock(self.data["player"][playeruuid]["claiminfo"][newclaim]["handle1"],
                                     DIAMONDBLOCK, 0)
                    player.sendBlock(self.data["player"][playeruuid]["claiminfo"][newclaim]["handle2"],
                                     GOLDBLOCK, 0)
                    self.data["player"][playeruuid]["selectionmode"] = "none"
                    self.data["player"][playeruuid]["selectionpoint"] = "none"
                    return
                if newclaim is False:
                    player.message("&cClaim action failed.  &eChange or edit selection area")
                    player.message("&eby right-clicking on a restone corner and then right-")
                    player.message("&eclick on a new spot")
                    player.sendBlock(self.data["player"][playeruuid]["point1"],
                                     LITREDSTONEORE, 0)
                    player.sendBlock(self.data["player"][playeruuid]["point2"],
                                     LITREDSTONEORE, 0)
                    self.data["player"][playeruuid]["selectionpoint"] = "error"
                    return

        # modes of "idle/none"
        if anyregion is False:
            self.data["player"][playeruuid]["selectionpoint"] = "point1"
            self.data["player"][playeruuid]["selectionmode"] = "new"
            player.message("&eSelect two opposite corners...")
            return
        owneruuid = self.regions.getregioninfo(anyregion, "ownerUuid")

        # determine if this region is a claim
        if anyregion not in self.data["player"][owneruuid]["claimlist"]:
            player.message("&5This is a region-guarded area (%s), not a claim..." % anyregion)
            return

        if owneruuid == playeruuid:
            # pull up handles.  If no handles exist, exit (error).
            if anyregion not in self.data["player"][owneruuid]["claiminfo"]:
                player.message("&4Could not pull up claiminfo for this claim...")
                player.message("&4You may need to /abandonclaim and re-do it.")
                return
            if ("handle1" and "handle2") not in self.data["player"][owneruuid]["claiminfo"][anyregion]:
                player.message("&4Could not pull up handle adjustment points for this claim...")
                player.message("&4You may need to /abandonclaim and re-do it.")
                return
            handle1 = self.data["player"][owneruuid]["claiminfo"][anyregion]["handle1"]
            handle2 = self.data["player"][owneruuid]["claiminfo"][anyregion]["handle2"]
            self.data["player"][playeruuid]["point1"] = handle1
            self.data["player"][playeruuid]["point2"] = handle2
            self.data["player"][playeruuid]["selectionmode"] = "edit"
            self.data["player"][playeruuid]["selectionpoint"] = "none"
            return

    def _trust_comm(self, *args):
        player = args[0]
        argspassed = args[1]
        if len(argspassed) < 1:
            player.message("&cUsage: /trust <username>")
            return
        targetuuid = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=True))
        targetname = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=False))
        if targetname == "[]":
            player.message("&cinvalid username.")
            return
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            owner = self.regions.getregioninfo(regionname, "ownerUuid")
            playeruuid = str(player.mojangUuid)
            if playeruuid != owner:
                player.message("&cThis is not your claim.")
                return
            self.regions.rgedit(regionname, playername=targetname, addbreak_uuid=targetuuid)
            self.regions.rgedit(regionname, playername=targetname, addplace_uuid=targetuuid)
            self.regions.rgedit(regionname, playername=targetname, addaccess_uuid=targetuuid)
            player.message("&e%s has been granted full access to this claim." % targetname)

    def _untrust_comm(self, *args):
        player = args[0]
        argspassed = args[1]
        if len(argspassed) < 1:
            player.message("&cUsage: /untrust <username>")
            return
        targetuuid = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=True))
        targetname = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=False))
        if targetname == "[]":
            player.message("&cinvalid username.")
            return
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            owner = self.regions.getregioninfo(regionname, "ownerUuid")
            playeruuid = str(player.mojangUuid)
            if playeruuid != owner:
                player.message("&cThis is not your claim.")
                return
            self.regions.rgedit(regionname, playername=targetname, remove_uuid=targetuuid)
            player.message("&e%s has been removed from this claim." % targetname)

    def _breaktrust_comm(self, *args):
        player = args[0]
        argspassed = args[1]
        if len(argspassed) < 1:
            player.message("&cUsage: /breaktrust <username>")
            return
        targetuuid = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=True))
        targetname = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=False))
        if targetname == "[]":
            player.message("&cinvalid username.")
            return
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            owner = self.regions.getregioninfo(regionname, "ownerUuid")
            playeruuid = str(player.mojangUuid)
            if playeruuid != owner:
                player.message("&cThis is not your claim.")
                return
            self.regions.rgedit(regionname, playername=targetname, addbreak_uuid=targetuuid)
            player.message("&e%s added to this claim. Player can now break items here." % targetname)

    def _placetrust_comm(self, *args):
        player = args[0]
        argspassed = args[1]
        if len(argspassed) < 1:
            player.message("&cUsage: /placetrust <username>")
            return
        targetuuid = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=True))
        targetname = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=False))
        if targetname == "[]":
            player.message("&cinvalid username.")
            return
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            owner = self.regions.getregioninfo(regionname, "ownerUuid")
            playeruuid = str(player.mojangUuid)
            if playeruuid != owner:
                player.message("&cThis is not your claim.")
                return
            self.regions.rgedit(regionname, playername=targetname, addplace_uuid=targetuuid)
            player.message("&e%s added to this claim. Player can now access/place items here." % targetname)

    def _accesstrust_comm(self, *args):
        player = args[0]
        argspassed = args[1]
        if len(argspassed) < 1:
            player.message("&cUsage: /accesstrust <username>")
            return
        targetuuid = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=True))
        targetname = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=False))
        if targetname == "[]":
            player.message("&cinvalid username.")
            return
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            owner = self.regions.getregioninfo(regionname, "ownerUuid")
            playeruuid = str(player.mojangUuid)
            if playeruuid != owner:
                player.message("&cThis is not your claim.")
                return
            self.regions.rgedit(regionname, playername=targetname, addaccess_uuid=targetuuid)
            player.message("&e%s added to this claim. Player can now access/place items here." % targetname)

    def _claimblocks_comm(self, *args):
        player = args[0]
        playerid = str(player.mojangUuid)
        playername = player.username
        self._claimblocks(player, playerid, playername)

    def _adjustclaimblocks_comm(self, player, args):
        if len(args) < 3:
            amount = 0
        else:
            amount = int(args[2])
        if len(args) < 2:
            player.message("&cUsage: /adjustclaimblocks <username> <add/sub/set/info> <amount>")
        targetrname = str(SurestLib.makenamevalid(self, args[0], online=False, return_uuid=False))
        targetuuid = str(SurestLib.makenamevalid(self, args[0], online=False, return_uuid=True))
        if targetrname == "[]":
            player.message("invalid name: %s" % args[0])
            return
        subcommmand = str(args[1]).lower()
        blocksinuse = self.data["player"][targetuuid]["claimblocksused"]
        if subcommmand == "add":
            self.data["player"][targetuuid]["claimblocks"] += amount
            player.message("&eAdded %s blocks to player %s" % (amount, targetrname))
        if subcommmand == "sub":
            self.data["player"][targetuuid]["claimblocks"] -= amount
            player.message("&eremoved %s blocks from player %s" % (amount, targetrname))
        if subcommmand == "set":
            self.data["player"][targetuuid]["claimblocks"] = amount - self.data["player"][targetuuid]["claimblocksused"]
            player.message("&eset %s's blocks to %s" % (targetrname, amount))
        if subcommmand == "info":
            self._claimblocks(player, targetuuid, targetrname)
            return
        amount = self.data["player"][targetuuid]["claimblocks"] + blocksinuse
        player.message("&2%s has %s blocks." % (targetrname, amount))

    def _spade(self, *args):
        player = args[0]
        if self.earnspade:
            player.message("&aSorry, this server requires you to craft your own gold shovel.")
        else:
            self.api.minecraft.console("give %s minecraft:golden_shovel 1 0" % player.username)
        return

    def _abandonclaim_comm(self, *args):
        player = args[0]
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            owner = self.regions.getregioninfo(regionname, "ownerUuid")
            playeruuid = str(player.mojangUuid)
            if playeruuid != owner:
                player.message("&cThis is not your claim.")
                return
            self._abandonclaim(player, regionname, playeruuid)
        return

    def _deleteclaim_comm(self, *args):
        player = args[0]
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            owneruuid = self.regions.getregioninfo(regionname, "ownerUuid")
            self._abandonclaim(player, regionname, owneruuid)
        return

    def _abandonallclaims_comm(self, *args):
        player = args[0]
        playerid = str(player.mojangUuid)
        claimlist = list(self.data["player"][playerid]["claimlist"])
        for thisclaimname in claimlist:
            self._abandonclaim(player, str(thisclaimname), playerid)
        return

    def _deleteallclaims_comm(self, *args):
        player = args[0]
        argspassed = args[1]
        if len(argspassed) < 1:
            player.message("&cUsage: /deleteallclaims <username>")
            return
        targetuuid = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=True))
        if targetuuid == "[]":
            player.message("&cinvalid username.")
            return
        claimlist = list(self.data["player"][targetuuid]["claimlist"])
        for thisclaimname in claimlist:
            self._abandonclaim(player, str(thisclaimname), targetuuid)
        return

    def _newclaim_comm(self, *args):
        player = args[0]
        self._newclaim(player)

    def _transferclaim_comm(self, *args):
        player = args[0]
        argspassed = args[1]
        if len(argspassed) < 1:
            player.message("&cUsage: /transferclaim <newusername>")
            return
        position = player.getPosition()
        dim = player.getDimension()
        regionname = self.regions.regionname(position, dim)
        if regionname is False:
            player.message("&cYou are not standing in a claim.")
            return
        else:
            newowneruuid = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=True))
            newownername = str(SurestLib.makenamevalid(self, argspassed[0], online=False, return_uuid=False))
            if newowneruuid == "[]":
                player.message("&cinvalid username.")
                return
            oldowneruuid = self.regions.getregioninfo(regionname, "ownerUuid")
            pos1 = self.regions.getregioninfo(regionname, "pos1")
            pos2 = self.regions.getregioninfo(regionname, "pos2")
            if newowneruuid not in self.data["player"]:
                self._init_player_record(newowneruuid, newownername)
            self._abandonclaim(player, regionname, oldowneruuid)
            self._do_claim(player, newowneruuid, dim, pos1, pos2, ycoords_of_feet=player.getPosition()[1])
        return

    def _show_comm(self, *args):
        player = args[0]
        pos5 = player.getPosition()
        pos = (int(pos5[0]), int(pos5[1]), int(pos5[2]))
        dim = player.getDimension()
        regionname = self.regions.regionname(pos, dim)
        if regionname is False:
            player.message("&ethis is unclaimed")
            return
        playeruuid = str(player.mojangUuid)
        self.data["player"][playeruuid]["point3"] = self.regions.getregioninfo(regionname, "pos1")
        self.data["player"][playeruuid]["point4"] = self.regions.getregioninfo(regionname, "pos2")
        x = int(pos[0])
        y = int(pos[1]) - 1
        z = int(pos[2])
        self._show(player, (x, y, z), playeruuid)
        player.message("&eRegion: &5%s" % regionname)

    def _claimblocks(self, playerobjecttomessage, playerid, playername):
        blocksavailable = self.data["player"][playerid]["claimblocks"]
        blocksinuse = self.data["player"][playerid]["claimblocksused"]
        totalblocks = blocksavailable + blocksinuse
        claimlist = self.data["player"][playerid]["claimlist"]
        totalclaims = len(claimlist)
        playerobjecttomessage.message("")
        playerobjecttomessage.message("&6Claims information for &e%s&6:" % playername)
        playerobjecttomessage.message("&6Total claim blocks &5%s&6" % totalblocks)
        playerobjecttomessage.message("&6Blocks used: &5%s &6Blocks available: &5%s" % (blocksinuse, blocksavailable))
        playerobjecttomessage.message("&6Using &5%s&6 claims." % totalclaims)

    def _newclaim(self, player):
        playerid = str(player.mojangUuid)
        self.data["player"][playerid]["selectionmode"] = "new"
        player.message("&2Entering claims selection mode...")
        player.message("&2Use gold shovel to select points (/spade)...")

    def _abandonclaim(self, player, thisclaimname, playerid):
        handle1 = self.data["player"][playerid]["claiminfo"][thisclaimname]["handle1"]
        handle2 = self.data["player"][playerid]["claiminfo"][thisclaimname]["handle2"]
        blocksize, length, width = self._getsizeclaim(handle1, handle2)
        if thisclaimname in self.data["player"][playerid]["claiminfo"]:
            del self.data["player"][playerid]["claiminfo"][thisclaimname]
        if thisclaimname in self.data["player"][playerid]["claimlist"]:
            self.data["player"][playerid]["claimlist"].remove(thisclaimname)
        player.sendBlock(handle1, BEDROCK, 0)
        player.sendBlock(handle2, BEDROCK, 0)
        self.regions.rgdelete(thisclaimname)
        self.data["player"][playerid]["claimblocks"] += blocksize
        self.data["player"][playerid]["claimblocksused"] -= blocksize
        player.message("&eClaim %s deleted!" % thisclaimname)

    def _claim(self, player, playerid):
        #  1) calculate the claim size parameters
        if self.data["player"][playerid]["selectionpoint"] != "point2":
            player.message("&cNothing selected to claim!")
            return False
        lowcoord = self.data["player"][playerid]["point3"]
        highcoord = self.data["player"][playerid]["point4"]
        blocks, length, width = self._getsizeclaim(lowcoord, highcoord)
        playersblocks = self.data["player"][playerid]["claimblocks"]

        if blocks < self.minclaimsize:
            player.message("&cClaim (%d) is not minimum size of at least %d blocks." % (blocks, self.minclaimsize))
            return False
        if length < self.minclaimwidth or width < self.minclaimwidth:
            player.message("&cClaim has to be at least %d blocks wide all around." % self.minclaimwidth)
            return False

        if blocks > playersblocks:
            player.message("&cYou do not have enough blocks to make this claim.")
            player.message("&eYou have: %d" % playersblocks)
            player.message("&eYou need: %d" % blocks)
            return False
        #  2) look for interceptions
        dim = self.data["player"][playerid]["dim1"]
        sel1coords = self.data["player"][playerid]["point3"]
        sel2coords = self.data["player"][playerid]["point4"]
        collisions = self.regions.intersecting_regions(dim, sel1coords, sel2coords, rect=True)
        if collisions is not None:
            player.message("&cArea overlaps region(s):")
            player.message("&5%s" % str(collisions).replace("u'", "'"))
            player.message("claimed areas can be discovered with a wooden stick...")
            return False
        thisclaimname, humanname = self._useclaimname(playerid)  # get a new claims region name
        if not thisclaimname:
            if not player.hasPermission("vclaims.admin"):
                player.message("&cyou have claimed the maximum number of areas (%s)" % self.maxclaims)
                return False
        #  3) inspections passed, claim allowed.
        lowcorner = (sel1coords[0], 5, sel1coords[2])
        highcorner = (sel2coords[0], 255, sel2coords[2])
        handle1 = self.data["player"][playerid]["point1"]
        handle2 = self.data["player"][playerid]["point2"]

        self.regions.rgdefine(thisclaimname, playerid, humanname, dim, lowcorner, highcorner)
        self.regions.protection_on(thisclaimname)
        player.message("&2Region &5%s&2 created and protected." % thisclaimname)
        self.data["player"][playerid]["claimlist"].append(thisclaimname)
        self.data["player"][playerid]["claiminfo"][thisclaimname] = {}
        self.data["player"][playerid]["claiminfo"][thisclaimname]["handle1"] = handle1
        self.data["player"][playerid]["claiminfo"][thisclaimname]["handle2"] = handle2
        self.data["player"][playerid]["claimblocks"] -= blocks
        self.data["player"][playerid]["claimblocksused"] += blocks
        self.data["player"][playerid]["point1"] = (0, 0, 0)
        self.data["player"][playerid]["point2"] = (0, 0, 0)
        self.data["player"][playerid]["point3"] = (0, 0, 0)
        self.data["player"][playerid]["point4"] = (0, 0, 0)
        self.data["player"][playerid]["selectionpoint"] = "none"
        self.data["player"][playerid]["selectionmode"] = "none"
        return str(thisclaimname)

    def _editclaim(self, player, playerid, existingclaimname):
        # get existing claimdata
        pos1 = self.regions.getregioninfo(existingclaimname, "pos1")
        pos2 = self.regions.getregioninfo(existingclaimname, "pos2")
        if pos1 is False:
            player.message("&cClaim %s failed 'locate'!" % existingclaimname)
            return False
        thisclaimblocksbefore, exlength, exwidth = self._getsizeclaim(pos1, pos2)
        #  1) calculate the claim size parameters
        if self.data["player"][playerid]["selectionpoint"] != "point2":
            player.message("&cNothing selected to claim!")
            return False
        lowcoord = self.data["player"][playerid]["point3"]
        highcoord = self.data["player"][playerid]["point4"]
        blocks, length, width = self._getsizeclaim(lowcoord, highcoord)
        playersblocksavail = self.data["player"][playerid]["claimblocks"] + thisclaimblocksbefore
        if blocks < self.minclaimsize:
            player.message("&cClaim (%d) is not minimum size of at least %d blocks." % (blocks, self.minclaimsize))
            return False
        if length < self.minclaimwidth or width < self.minclaimwidth:
            player.message("&cClaim has to be at least %d blocks wide all around." % self.minclaimwidth)
            return False

        if blocks > playersblocksavail:
            player.message("&cYou do not have enough blocks to make this claim.")
            player.message("&eYou have: %d" % playersblocksavail)
            player.message("&eYou need: %d" % blocks)
            return False
        #  2) look for interceptions
        self.regions.protection_off(existingclaimname)  # must turn off protection momentarily to avoid self collision.
        dim = self.data["player"][playerid]["dim1"]
        sel1coords = self.data["player"][playerid]["point3"]
        sel2coords = self.data["player"][playerid]["point4"]
        collisions = self.regions.intersecting_regions(dim, sel1coords, sel2coords, rect=True)
        self.regions.protection_on(existingclaimname)  # restore protection status
        if collisions is not None:
            player.message("&cArea overlaps region(s):")
            player.message("&5%s" % str(collisions).replace("u'", "'"))
            player.message("claimed areas can be discovered with a wooden stick...")
            return False
        #  3) inspections passed, resize allowed.
        # using same claim name
        lowcorner = (sel1coords[0], 5, sel1coords[2])
        highcorner = (sel2coords[0], 255, sel2coords[2])
        handle1 = self.data["player"][playerid]["point1"]
        handle2 = self.data["player"][playerid]["point2"]

        thisclaimname = self.regions.rgedit(existingclaimname, edit_coords=True, low_corner=lowcorner,
                                            high_corner=highcorner, playername=player.username)
        player.message("Region %s edited." % thisclaimname)
        self.data["player"][playerid]["claiminfo"][thisclaimname]["handle1"] = handle1
        self.data["player"][playerid]["claiminfo"][thisclaimname]["handle2"] = handle2
        self.data["player"][playerid]["claimblocks"] = playersblocksavail - blocks
        self.data["player"][playerid]["claimblocksused"] += (blocks - thisclaimblocksbefore)
        self.data["player"][playerid]["point1"] = (0, 0, 0)
        self.data["player"][playerid]["point2"] = (0, 0, 0)
        self.data["player"][playerid]["point3"] = (0, 0, 0)
        self.data["player"][playerid]["point4"] = (0, 0, 0)
        self.data["player"][playerid]["selectionpoint"] = "none"
        self.data["player"][playerid]["selectionmode"] = "none"
        return str(thisclaimname)

    def _useclaimname(self, playerid):
        x = 0
        searching = True
        humanname = self.data["player"][playerid]["playername"]
        claimname = "%s-%d" % (humanname, x)
        while searching:
            if claimname not in self.data["player"][playerid]["claimlist"]:
                searching = False
            else:
                x += 1
                if x > self.maxclaims:
                    return False, False
                claimname = "%s-%d" % (humanname, x)
        return claimname, humanname

    def _show(self, player, position, onlineuuid):
        if self.data["player"][onlineuuid]["point3"] == (0, 0, 0):
            player.message("&cNo seletion to show!")
            return
        low = self.data["player"][onlineuuid]["point3"]
        high = self.data["player"][onlineuuid]["point4"]
        lowcorner = low[0], position[1] + 1, low[2]
        highcorner = (high[0], position[1] + 4, high[2])
        SurestLib.client_show_cube(player, lowcorner, highcorner, sendblock=False)

    def _finishwithselectionmode(self, playeruuid):
        self.data["player"][playeruuid]["point1"] = (0, 0, 0)
        self.data["player"][playeruuid]["point2"] = (0, 0, 0)
        self.data["player"][playeruuid]["point3"] = (0, 0, 0)
        self.data["player"][playeruuid]["point4"] = (0, 0, 0)
        self.data["player"][playeruuid]["selectionpoint"] = "none"
        self.data["player"][playeruuid]["selectionmode"] = "none"
        self.data["player"][playeruuid]["selectiontarget"] = "none"
        self.data_storageobject.save()

    def _init_player_record(self, onlineuuid, playername):
        """ if onlineUuid not in self.data["player"]: self._init_player_record(onlineUuid, playername)"""
        # Initialize new record
        self.data["player"][onlineuuid] = {
            "selectionpoint": "none",
            "selectionmode": "none",
            "selectiontarget": "none",
            "claimblocks": self.defaultclaimblocks,
            "claimblocksused": 0,
            "activitycount": 0,
            "point1": (0, 0, 0),
            "point2": (0, 0, 0),
            "point3": (0, 0, 0),
            "point4": (0, 0, 0),
            "dim1": 0,
            "dim2": 0,
            "playername": playername,
            "claimlist": [],
            "claiminfo": {},
            "laston": time.time(),
        }

    def _do_claim(self, player_msg_object, owneruuid, dim, pos1, pos2, ycoords_of_feet=62):
        self.data["player"][owneruuid]["selectionpoint"] = "point2"
        self.data["player"][owneruuid]["dim1"] = dim
        self.data["player"][owneruuid]["dim2"] = dim
        self.data["player"][owneruuid]["point1"] = pos1
        self.data["player"][owneruuid]["point2"] = pos2
        low, high = self.regions.normalizeSelection(
            self.data["player"][owneruuid]["point1"],
            self.data["player"][owneruuid]["point2"]
        )
        highcorner = high[0], ycoords_of_feet + 1, high[2]
        lowcorner = low[0], ycoords_of_feet + 5, low[2]
        self.data["player"][owneruuid]["point3"] = lowcorner
        self.data["player"][owneruuid]["point4"] = highcorner
        claimed = self._claim(player_msg_object, owneruuid)
        if claimed:
            player_msg_object.message("&6Claim action successful.")
            self.data["player"][owneruuid]["selectionmode"] = "none"

    @staticmethod
    def _getsizeclaim(coord1, coord2):
        width = abs(coord2[0] - coord1[0]) + 1  # size is including boundary
        length = abs(coord2[2] - coord1[2]) + 1
        blocks = length * width
        return blocks, length, width
