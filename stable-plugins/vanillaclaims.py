# -*- coding: utf-8 -*-

import time
from copy import deepcopy
import threading

NAME = "VanillaClaims"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.vanillaclaims"
VERSION = (0, 9, 0)
SUMMARY = "Simple player-friendly land claim system"
WEBSITE = ""
DESCRIPTION = "Uses regions.py as the backend for protecting player claims."
DEPENDENCIES = ["regions.py", ]


DISABLED = False
BEDROCK = 7
GOLDBLOCK = 41
DIAMONDBLOCK = 57
LITREDSTONEORE = 74


# The specific errors we need not worry about in the plugin API:
# noinspection PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyPep8Naming,PyClassicStyleClass,PyAttributeOutsideInit
class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log

        self.userperm = "vclaims.use"  # change to None for anyone to access.

        # claim blocks configuration
        self.defaultclaimblocks = 2048  # the starting number of blocks
        self.actionsperblock = 50  # -    sets the rate of block accumulation
        self.maxclaimblocks = 200000  # - determine max earned claim blocks
        # These prevent claims abuse or spurious annoyance-type claims
        self.maxclaims = 5  # -           max claims per player
        self.minclaimsize = 81  # -       minimum claim size
        self.minclaimwidth = 6  # -       minimum claim width

        # whether player must make their own gold spade
        self.earnspade = False

        # temporary run-time player data
        self.player_dat = {}

    def onEnable(self):
        # get the regions plugin:
        self.regions = self.api.getPluginContext("com.suresttexas00.regions")
        if self.regions.version < 1.3:
            self.log.error(
                "Regions.py is out of date!, Vanilla Claims not enabled."
            )
            return False

        # init storage data
        self.data_storageobject = self.api.getStorage(
            "claimdata", world=False, pickle=False)
        self.data = self.data_storageobject.Data

        self.api.registerEvent("player.place", self.action_place)
        self.api.registerEvent("player.spawned", self.playerSpawned)
        self.api.registerEvent("player.dig", self.action_dig)

        user = self.userperm
        admin = "vclaims.admin"

        self.api.registerHelp(
            "VanillaClaims", "Claim based grief prevention system.", [
                ("/abandonclaim",
                 "Abandon the claim you are standing in.", user),
                ("/abandonallclaims",
                 "Abandon all claims you own.", user),
                ("/claimblocks",
                 "View your claims blocks information.", user),
                ("/trust <player>",
                 "Allow player full access to your claim.", user),
                ("/breaktrust <player>",
                 "Allow player to break blocks on your claim.", user),
                ("/placetrust <player>",
                 "Allow player to place blocks / operate things.", user),
                ("/accesstrust <player>",
                 "Allow player interaction (place lava, eat, throw pearls, etc)",  # noqa
                 user),
                ("/untrust <player>",
                 "remove a player from your claim.", user),
                ("/trustlist",
                 "Display the claim's player information.", user),
                ("/show",
                 "Show the claim you are standing in.", user),
                ("/spade",
                 "Gives the land claim gold shovel", user),
                ("/adjustclaimblocks <player> <add/sub/set/info> <amount>",
                 "Adjust player claim blocks.", admin),
                ("/transferclaim <newusername>",
                 "re-creates the same claim in another's name",
                 admin),
                ("/deleteclaim",
                 "Delete the claim you are standing in", admin),
                ("/deleteallclaims <player>",
                 "Delete all a players claims.", admin)
                ])

        self.api.registerCommand(
            "show", self._show_comm, user)
        self.api.registerCommand(
            ("spade", "wand", "shovel"), self._spade, user)
        self.api.registerCommand(
            ("abandonclaim", "abandonclaims"), self._abandonclaim_comm, user)
        self.api.registerCommand(
            "abandonallclaims", self._abandonallclaims_comm, user)
        self.api.registerCommand(
            "deleteclaim", self._deleteclaim_comm, admin)
        self.api.registerCommand(
            "deleteallclaims", self._deleteallclaims_comm, admin)
        self.api.registerCommand(
            "adjustclaimblocks", self._adjustclaimblocks_comm, admin)
        self.api.registerCommand(
            "transferclaim", self._transferclaim_comm, admin)
        self.api.registerCommand(
            ("claimblocks", "claimblock", "claimsblock", "claimsblocks"), 
            self._claimblocks_comm, user)
        self.api.registerCommand(
            "trust", self._trust_comm, user)
        self.api.registerCommand(
            "breaktrust", self._breaktrust_comm, user)
        self.api.registerCommand(
            "placetrust", self._placetrust_comm, user)
        self.api.registerCommand(
            "accesstrust", self._accesstrust_comm, user)
        self.api.registerCommand(
            "untrust", self._untrust_comm, user)
        # self.api.registerCommand("trustlist", self._trustlist_comm, user)

        self.run = True
        self.action_queue = []
        tr = threading.Thread(target=self._track_activity,
                              name="trackblocks", args=())
        tr.daemon = True
        tr.start()

        ts = threading.Thread(target=self.on_timer,
                              name="inv_timer", args=())
        ts.daemon = True
        ts.start()

    def onDisable(self):
        self.run = False
        self.data_storageobject.close()

    def get_claim_data(self, uuid, playername):
        try:
            return self.data[uuid]
        except KeyError:
            self.data[uuid] = {
                "blocks": self.defaultclaimblocks,
                "blocksused": 0,
                "activity": 0,
                "playername": playername,
                "claimlist": [],
                "claiminfo": {},
                "laston": time.time(),
            }
            return self.player_dat[uuid]

    def get_player_data(self, name):
        """
        Get the player's selection data.  Selection data is not saved
        between reboots.

        :param name: player name.

        :returns:  A dictionary of player selection data.
        {
            "point1" (cubical tuple)
            "point2" (cubical tuple)
            "dim1"
            "dim2"
            "mode"  # selection modes ...
            "point"
            "target"
            }

        """
        try:
            return self.player_dat[name]
        except KeyError:
            self.player_dat[name] = {
                "point1": None, "point2": None,
                "dim1": None, "dim2": None,
                "mode": None,
                "point": None,
                "target": None
            }
            return self.player_dat[name]

    def _track_activity(self):
        """
        Each item is just a playeruuid entry.
        """

        while self.run:
            time.sleep(1)
            while len(self.action_queue) > 0:
                # grab next change
                uuid = self.action_queue.pop(0)
                # block increaser
                self.data[uuid]["activitycount"] += 1
                activities = self.data[uuid]["activitycount"]
                if activities % self.actionsperblock is not 0:
                    continue
                self.data[uuid]["activitycount"] = 0
                idleclaimblocks = self.data[uuid]["claimblocks"]
                inuseblocks = self.data[uuid]["claimblocksused"]
                if (idleclaimblocks + inuseblocks) < self.maxclaimblocks:
                    self.data[uuid]["claimblocks"] += 1

    def on_timer(self):
        while self.run:
            time.sleep(.5)
            for players in self.api.minecraft.getPlayers():
                player = self.api.minecraft.getPlayer(players)
                try:
                    playeruuid = player.uuid
                    item = player.getHeldItem()
                    itemid = item["id"]
                except AttributeError:
                    # probably a bad player object
                    continue

                p = self.get_player_data(player.username)

                try:
                    mode = p["selection"]
                except KeyError:
                    mode = "idle"
                    self.data[playeruuid]["selectionmode"] = "idle"

                if itemid != 284 and mode != "none":
                    player.message(
                        "&2Shovel put away... Switching out of claims "
                        "selection mode"
                    )
                    self._finishwithselectionmode(playeruuid)
                if itemid == 284 and mode == "none":
                    # This just exists to notify player they can use gold
                    # shovel now for claims
                    player.message(
                        "&2Claims shovel active... Click and area to edit "
                        "or to claim."
                    )
                    self.data[playeruuid]["selectionmode"] = "idle"

    def playerSpawned(self, payload):
        try:
            player = payload["player"]
        except AttributeError:
            self.log.error("VanillaClaims player spawn not successful.  "
                           "Payload: %s" % payload)
            return
        p = self.get_claim_data(player.uuid, player.username)
        p["laston"] = time.time()

    def action_dig(self, payload):
        try:
            position = payload["position"]
            player = payload["player"]
            action = payload["action"]
            playeruuid = player.uuid
            itemid = player.getHeldItem()["id"]
            dim = player.getDimension()
        except AttributeError:
            # probably a bad player object
            return False

        if itemid == 284 and action == "end_break":
            player.sendBlock(position, BEDROCK, 0)
            player.message("&5Easy slick.. just a light click will do!")
            return False
        if itemid == 284 and action == "begin_break":
            self.wand_use(player, playeruuid, position, dim)
            return False
        if action == "end_break":
            self.action_queue.append(playeruuid)

    def action_place(self, payload):
        try:
            player = payload["player"]
            dim = int(player.getDimension())
            clickposition = (
                payload["clickposition"][0],
                payload["clickposition"][1],
                payload["clickposition"][2]
            )
            itemid = player.getHeldItem()["id"]
            playeruuid = player.uuid
        except AttributeError:
            return False

        if itemid == 284:
            self.wand_use(player, playeruuid, clickposition, dim)
            # never allow gold shovel use - reserved for claims
            return False
        self.action_queue.append(playeruuid)

    def wand_use(self, player, playeruuid, position, dim):
        """redefines things a bit.
        Point parameters are now: point1 now means goal is point one selection,
        point2 means goal is point2 selection.  Error means error occurred with
        selection (too small, ovelapping region, etc, etc...). """
        # "none", "point1" "point2", "error"
        # "none, "new", "edit", "idle"
        point = self.data[playeruuid]["selectionpoint"]
        mode = self.data[playeruuid]["selectionmode"]
        anyregion = self.regions.regionname(position, dim)
        if mode == "new":
            # entering new mode should have point set to point1.
            if point == "error":
                #
                # Only clicking a previously selected corner 
                # ill restore to point selection
                if position == self.data[playeruuid]["point2"]:
                    # Contine point 2 selection
                    self.data[playeruuid]["selectionpoint"] = "point2"
                    return
                if position == self.data[playeruuid]["point1"]:
                    #
                    # move point 2 data to point one (including marking)
                    pt1 = deepcopy(self.data[playeruuid]["point1"])
                    pt1dim = deepcopy(self.data[playeruuid]["dim1"])
                    pt2 = deepcopy(self.data[playeruuid]["point2"])
                    pt2dim = deepcopy(self.data[playeruuid]["dim2"])
                    self.data[playeruuid]["point1"] = pt2
                    self.data[playeruuid]["dim1"] = pt2dim
                    self.data[playeruuid]["point2"] = pt1
                    self.data[playeruuid]["dim2"] = pt1dim
                    #
                    # re-draw new point1 as point1 color (diamond)
                    player.sendBlock(self.data[playeruuid]["point1"],
                                     DIAMONDBLOCK, 0)
                    #
                    # Continue with point 2 (new point2) selection
                    self.data[playeruuid]["selectionpoint"] = "point2"
                    return
                # error assumes two points selected - redraw those 
                # points and remind player what to do.
                player.sendBlock(self.data[playeruuid]["point1"],
                                 LITREDSTONEORE, 0)
                player.sendBlock(self.data[playeruuid]["point2"],
                                 LITREDSTONEORE, 0)
                player.message(
                    "&eChange or edit selection area by clicking on a restone"
                )
                player.message("&e corner and then selecting a new spot.")
                player.message("&e(to cancel, put shovel away)")
                return

            if point == "point2":
                if position == self.data[playeruuid]["point1"]:
                    player.sendBlock(position, DIAMONDBLOCK, 0)
                    return  # ignore double selection/clicking
                if self.data[playeruuid]["dim1"] != dim:
                    # restart claim in new dimension
                    self.data[playeruuid]["selectionpoint"] = "point1"
                    self.data[playeruuid]["selectionmode"] = "new"
                    player.message("&cSelection dimension changed...")
                    return
                # input point 2
                self.data[playeruuid]["point2"] = position
                # Normalize selection (set to standard pt1 low and 
                # pt2 high coords)
                low, high = self.regions.stat_normalize_selection(
                    self.data[playeruuid]["point1"],
                    self.data[playeruuid]["point2"]
                )
                highcorner = (high[0], position[1] + 5, high[2])
                lowcorner = (low[0], position[1] + 1, low[2])
                self.data[playeruuid]["point3"] = lowcorner
                self.data[playeruuid]["point4"] = highcorner
                # attempt claim
                newclaim = self._claim(player, playeruuid)

                if newclaim:
                    print(newclaim)
                    player.sendBlock(position, GOLDBLOCK, 0)
                    player.message("&6Second Corner selected.")
                    player.message("&6Claim action successful.")
                    self.regions.client_show_cube(
                        player, lowcorner, highcorner, sendblock=False
                    )
                    player.sendBlock(
                        self.data[playeruuid][
                            "claiminfo"][newclaim]["handle1"],
                        DIAMONDBLOCK, 0
                    )
                    player.sendBlock(
                        self.data[playeruuid][
                            "claiminfo"][newclaim]["handle2"],
                        GOLDBLOCK, 0
                    )
                    self.data[playeruuid]["selectionmode"] = "none"
                    self.data[playeruuid]["selectionpoint"] = "none"
                    return
                if newclaim is False:
                    player.message("&cClaim action failed.")
                    player.message(
                        {
                            "text": "Change or edit selection area by selecting"
                                    " a restone corner and then selecting a "
                                    "new spot", "color": "yellow"
                        }
                    )
                    player.sendBlock(
                        self.data[playeruuid]["point1"],
                        LITREDSTONEORE, 0
                    )
                    player.sendBlock(
                        self.data[playeruuid]["point2"],
                        LITREDSTONEORE, 0
                    )
                    self.data[playeruuid]["selectionpoint"] = "error"
                    return

            if point == "point1":  # select point 1
                self.data[playeruuid]["point3"] = (0, 0, 0)
                self.data[playeruuid]["point4"] = (0, 0, 0)
                self.data[playeruuid]["point1"] = position
                self.data[playeruuid]["dim1"] = dim
                self.data[playeruuid]["selectionpoint"] = "point2"
                player.sendBlock(position, DIAMONDBLOCK, 0)
                player.message(
                    "&6First Corner selected. &e(to cancel, put shovel away)"
                )
                return

        if mode == "edit":
            # entering edit mode requires the input of points 1 and 2
            # from whatever is the edited selection.
            #
            # and point set to "none"
            if point in ("error", "none"):
                #
                # Only clicking a previously selected corner will restore
                # to point selection
                # clicklowXZ = position[0], position[2]
                if position == self.data[playeruuid]["point1"]:
                    # Contine point 2 selection
                    self.data[playeruuid]["selectionpoint"] = "point1"
                    player.sendBlock(self.data[playeruuid]["point1"],
                                     BEDROCK, 0)
                    # Only clicking a previously selected corner will restore
                    # to point selection
                    return
                if position == self.data[playeruuid]["point2"]:
                    # Contine point 2 selection
                    self.data[playeruuid]["selectionpoint"] = "point2"
                    player.sendBlock(self.data[playeruuid]["point2"],
                                     BEDROCK, 0)
                    return

                # render - clicking outside of points
                if anyregion is False:
                    self.data[playeruuid]["selectionmode"] = "none"
                    self.data[playeruuid]["selectionpoint"] = "none"
                    return
                handle1 = self.data[playeruuid][
                    "claiminfo"][anyregion]["handle1"]
                handle2 = self.data[playeruuid][
                    "claiminfo"][anyregion]["handle2"]
                player.sendBlock(handle1, DIAMONDBLOCK, 0)
                player.sendBlock(handle2, GOLDBLOCK, 0)
                normpos1, normpos2 = self.regions.stat_normalize_selection(
                    handle1, handle2
                )
                correcty = normpos2[1] + 4
                normpos_tocorrected = (normpos2[0], correcty, normpos2[2])
                self.regions.client_show_cube(
                    player, normpos1, normpos_tocorrected, sendblock=False
                )

            if point in ("point2", "point1"):
                if point == "point2":
                    self.data[playeruuid]["dim2"] = dim
                if point == "point1":
                    self.data[playeruuid]["dim1"] = dim
                if self.data[playeruuid]["dim2"] != self.data[
                        "player"][playeruuid]["dim1"]:
                    # abort editing mode
                    self.data[playeruuid]["selectionpoint"] = "none"
                    self.data[playeruuid]["selectionmode"] = "none"
                    player.message("&cSelection dimension does not match...")
                    player.message("&cExiting claim edit mode...")
                    return
                # input the new point
                self.data[playeruuid][point] = position
                # Normalize selection (set to standard pt1 low and pt2 high coords)  # noqa
                low, high = self.regions.stat_normalize_selection(
                    self.data[playeruuid]["point1"],
                    self.data[playeruuid]["point2"]
                )
                highcorner = (high[0], position[1] + 5, high[2])
                lowcorner = (low[0], position[1] + 1, low[2])
                self.data[playeruuid]["point3"] = lowcorner
                self.data[playeruuid]["point4"] = highcorner
                if point == "point1":
                    player.sendBlock(position, DIAMONDBLOCK, 0)
                if point == "point2":
                    player.sendBlock(position, GOLDBLOCK, 0)
                player.message("&6Corner selected.")
                # thisclaimname = self.data[playeruuid]["selectiontarget"]  # noqa
                thisclaimname = anyregion
                newclaim = self._editclaim(player, playeruuid, thisclaimname)

                if newclaim:
                    player.message("&6Claim action successful.")
                    self.regions.client_show_cube(
                        player, lowcorner, highcorner, sendblock=False
                    )
                    player.sendBlock(self.data[playeruuid][
                                         "claiminfo"][newclaim]["handle1"],
                                     DIAMONDBLOCK, 0)
                    player.sendBlock(self.data[playeruuid][
                                         "claiminfo"][newclaim]["handle2"],
                                     GOLDBLOCK, 0)
                    self.data[playeruuid]["selectionmode"] = "none"
                    self.data[playeruuid]["selectionpoint"] = "none"
                    return
                if newclaim is False:
                    player.message("&cClaim action failed.")
                    player.message(
                        {
                            "text": "Change or edit selection area by selecting"
                                    " a restone corner and then selecting a "
                                    "new spot", "color": "yellow"
                        }
                    )
                    player.sendBlock(self.data[playeruuid]["point1"],
                                     LITREDSTONEORE, 0)
                    player.sendBlock(self.data[playeruuid]["point2"],
                                     LITREDSTONEORE, 0)
                    self.data[playeruuid]["selectionpoint"] = "error"
                    return

        # modes of "idle/none"
        if anyregion is False:
            self.data[playeruuid]["selectionpoint"] = "point1"
            self.data[playeruuid]["selectionmode"] = "new"
            player.message("&eSelect two opposite corners...")
            return
        owneruuid = self.regions.getregioninfo(anyregion, "ownerUuid")

        # determine if this region is a claim
        if anyregion not in self.data[owneruuid]["claimlist"]:
            player.message(
                "&5This is a region-guarded area (%s), not a "
                "claim..." % anyregion
            )
            return

        if owneruuid == playeruuid:
            # pull up handles.  If no handles exist, exit (error).

            # owner and player can be used interchangeably because they are ==
            data = self.data[playeruuid]
            if anyregion not in data["claiminfo"]:
                player.message(
                    "&4Could not pull up claiminfo for this claim..."
                )
                player.message(
                    "&4You may need to /abandonclaim and re-do it."
                )
                return
            try:
                handle1 = data["claiminfo"][anyregion]["handle1"]
                handle2 = data["claiminfo"][anyregion]["handle2"]
            except KeyError:
                player.message(
                    "&4Could not pull up handle adjustment points for "
                    "this claim..."
                )
                player.message("&4You may need to /abandonclaim and re-do it.")
                return
            data["point1"] = handle1
            data["point2"] = handle2
            data["selectionmode"] = "edit"
            data["selectionpoint"] = "none"
            return

    def _check_username(self, playerobj, args, usage_msg, arg_count=1):
        if len(args) < arg_count:
            playerobj.message("&cUsage: %s" % usage_msg)
            return False
        targetuuid = str(self.api.minecraft.lookupbyName(args[0]))
        targetname = self.api.minecraft.lookupbyUUID(targetuuid)
        if not targetuuid or targetname.lower() != args[0].lower():
            playerobj.message("&cinvalid username.")
            return False
        return targetname, targetuuid

    def _check_regionname(self, player):
        try:
            position = player.getPosition()
            dim = player.getDimension()
        except AttributeError:
            return False
        regionname = self.regions.regionname(position, dim)
        if regionname:
            return regionname, position, dim
        else:
            player.message("&cYou are not standing in a claim.")
            return False

    def _trust_comm(self, *args):
        player = args[0]
        try:
            targetname, targetuuid = self._check_username(
                player, args[1], "&/trust <username>")
            regionname, position, dim = self._check_regionname(player)
        except TypeError:
            return

        owner = self.regions.getregioninfo(regionname, "ownerUuid")
        playeruuid = str(player.mojangUuid)
        if playeruuid != owner:
            player.message("&cThis is not your claim.")
            return
        self.regions.rgedit(
            regionname, playername=targetname,
            addbreak=True, addplace=True, addaccess=True
        )
        player.message(
            "&e%s has been granted full access to this claim." % targetname
        )

    def _untrust_comm(self, *args):
        player = args[0]
        try:
            targetname, targetuuid = self._check_username(
                player, args[1], "/untrust <username>")
            regionname, position, dim = self._check_regionname(player)
        except TypeError:
            return

        owner = self.regions.getregioninfo(regionname, "ownerUuid")
        playeruuid = str(player.mojangUuid)
        if playeruuid != owner:
            player.message("&cThis is not your claim.")
            return
        self.regions.rgedit(
            regionname, playername=targetname, remove=True
        )
        player.message("&e%s has been removed from this claim." % targetname)

    def _breaktrust_comm(self, *args):
        player = args[0]
        try:
            targetname, targetuuid = self._check_username(
                player, args[1], "/breaktrust <username>")
            regionname, position, dim = self._check_regionname(player)
        except TypeError:
            return

        owner = self.regions.getregioninfo(regionname, "ownerUuid")
        playeruuid = str(player.mojangUuid)
        if playeruuid != owner:
            player.message("&cThis is not your claim.")
            return
        self.regions.rgedit(
            regionname, playername=targetname, addbreak=True
        )
        player.message(
            "&e%s added to this claim. Player can now break items "
            "here." % targetname
        )

    def _placetrust_comm(self, *args):
        player = args[0]
        try:
            targetname, targetuuid = self._check_username(
                player, args[1], "/placetrust <username>")
            regionname, position, dim = self._check_regionname(player)
        except TypeError:
            return

        owner = self.regions.getregioninfo(regionname, "ownerUuid")
        playeruuid = str(player.mojangUuid)
        if playeruuid != owner:
            player.message("&cThis is not your claim.")
            return
        self.regions.rgedit(
            regionname, playername=targetname, addplace=True
        )
        player.message(
            "&e%s added to this claim. Player can now access/place items"
            " here." % targetname)

    def _accesstrust_comm(self, *args):
        player = args[0]
        try:
            targetname, targetuuid = self._check_username(
                player, args[1], "/accesstrust <username>")
            regionname, position, dim = self._check_regionname(player)
        except TypeError:
            return

        owner = self.regions.getregioninfo(regionname, "ownerUuid")
        playeruuid = str(player.mojangUuid)
        if playeruuid != owner:
            player.message("&cThis is not your claim.")
            return
        self.regions.rgedit(
            regionname, playername=targetname, addaccess=True
        )
        player.message(
            "&e%s added to this claim. Player can now access/place items"
            " here." % targetname
        )

    def _claimblocks_comm(self, *args):
        player = args[0]
        playerid = str(player.mojangUuid)
        playername = player.username
        self._claimblocks(player, playerid, playername)

    def _adjustclaimblocks_comm(self, player, args):
        player = args[0]
        try:
            targetname, targetuuid = self._check_username(
                player, args[1],
                "/adjustclaimblocks <username> <add/sub/set/info> <amount>", 3
            )
        except TypeError:
            return

        amount = int(args[2])
        subcommmand = str(args[1]).lower()
        blocksinuse = self.data[targetuuid]["claimblocksused"]
        if subcommmand == "add":
            self.data[targetuuid]["claimblocks"] += amount
            player.message(
                "&eAdded %s blocks to player %s" % (amount, targetname)
            )
        if subcommmand == "sub":
            self.data[targetuuid]["claimblocks"] -= amount
            player.message(
                "&eremoved %s blocks from player %s" % (amount, targetname)
            )
        if subcommmand == "set":
            self.data[targetuuid]["claimblocks"] = amount - self.data[
                "player"][targetuuid]["claimblocksused"]
            player.message("&eset %s's blocks to %s" % (targetname, amount))
        if subcommmand == "info":
            self._claimblocks(player, targetuuid, targetname)
            return
        amount = self.data[targetuuid]["claimblocks"] + blocksinuse
        player.message("&2%s has %s blocks." % (targetname, amount))

    def _spade(self, *args):
        player = args[0]
        if self.earnspade:
            player.message(
                "&aSorry, this server requires you to craft your own "
                "gold shovel."
            )
        else:
            self.api.minecraft.console(
                "give %s minecraft:golden_shovel 1 30" % player.username
            )
        return

    def _abandonclaim_comm(self, *args):
        player = args[0]
        try:
            regionname, position, dim = self._check_regionname(player)
        except TypeError:
            return

        owner = self.regions.getregioninfo(regionname, "ownerUuid")
        if player.uuid != owner:
            player.message("&cThis is not your claim.")
            return
        self._abandonclaim(player, regionname, player.uuid)

    def _deleteclaim_comm(self, *args):
        player = args[0]
        try:
            regionname, position, dim = self._check_regionname(player)
        except TypeError:
            return
        owneruuid = self.regions.getregioninfo(regionname, "ownerUuid")
        self._abandonclaim(player, regionname, owneruuid)

    def _abandonallclaims_comm(self, *args):
        player = args[0]
        playerid = str(player.mojangUuid)
        claimlist = list(self.data[playerid]["claimlist"])
        for thisclaimname in claimlist:
            self._abandonclaim(player, str(thisclaimname), playerid)
        return

    def _deleteallclaims_comm(self, *args):
        player = args[0]
        try:
            targetname, targetuuid = self._check_username(
                player, args[1], "/deleteallclaims <username>",
            )
        except TypeError:
            return

        claimlist = list(self.data[targetuuid]["claimlist"])
        for thisclaimname in claimlist:
            self._abandonclaim(player, str(thisclaimname), targetuuid)
        return

    def _newclaim_comm(self, *args):
        player = args[0]
        self._newclaim(player)

    def _transferclaim_comm(self, *args):
        player = args[0]
        try:
            regionname, position, dim = self._check_regionname(player)
            targetname, targetuuid = self._check_username(
                player, args[1], "/transferclaim <newusername>"
            )
        except TypeError:
            return

        oldowneruuid = self.regions.getregioninfo(regionname, "ownerUuid")
        pos1 = self.regions.getregioninfo(regionname, "pos1")
        pos2 = self.regions.getregioninfo(regionname, "pos2")
        if targetuuid not in self.data:
            self._init_player_record(targetuuid, targetname)
        self._abandonclaim(player, regionname, oldowneruuid)
        self._do_claim(
            player, targetuuid, dim, pos1, pos2, ycoords_of_feet=position[1]
        )

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
        self.data[playeruuid]["point3"] = self.regions.getregioninfo(
            regionname, "pos1"
        )
        self.data[playeruuid]["point4"] = self.regions.getregioninfo(
            regionname, "pos2"
        )
        x = int(pos[0])
        y = int(pos[1]) - 1
        z = int(pos[2])
        self._show(player, (x, y, z), playeruuid)
        player.message("&eRegion: &5%s" % regionname)

    def _claimblocks(self, playerobject, playerid, playername):
        blocksavailable = self.data[playerid]["claimblocks"]
        blocksinuse = self.data[playerid]["claimblocksused"]
        totalblocks = blocksavailable + blocksinuse
        claimlist = self.data[playerid]["claimlist"]
        totalclaims = len(claimlist)
        playerobject.message("")
        playerobject.message("&6Claims information for &e%s&6:" % playername)
        playerobject.message("&6Total claim blocks &5%s&6" % totalblocks)
        playerobject.message(
            "&6Blocks used: &5%s &6Blocks available: &5%s" % (
                blocksinuse, blocksavailable
            )
        )
        playerobject.message("&6Using &5%s&6 claims." % totalclaims)

    def _newclaim(self, player):
        playerid = str(player.mojangUuid)
        self.data[playerid]["selectionmode"] = "new"
        player.message("&2Entering claims selection mode...")
        player.message("&2Use gold shovel to select points (/spade)...")

    def _abandonclaim(self, player, thisclaimname, playerid):
        handle1 = self.data[playerid][
            "claiminfo"][thisclaimname]["handle1"]
        handle2 = self.data[playerid][
            "claiminfo"][thisclaimname]["handle2"]
        blocksize, length, width = self._getsizeclaim(handle1, handle2)
        if thisclaimname in self.data[playerid]["claiminfo"]:
            del self.data[playerid]["claiminfo"][thisclaimname]
        if thisclaimname in self.data[playerid]["claimlist"]:
            self.data[playerid]["claimlist"].remove(thisclaimname)
        player.sendBlock(handle1, BEDROCK, 0)
        player.sendBlock(handle2, BEDROCK, 0)
        self.regions.rgdelete(thisclaimname)
        self.data[playerid]["claimblocks"] += blocksize
        self.data[playerid]["claimblocksused"] -= blocksize
        player.message("&eClaim %s deleted!" % thisclaimname)

    def _claim(self, player, playerid):
        #  1) calculate the claim size parameters
        if self.data[playerid]["selectionpoint"] != "point2":
            player.message("&cNothing selected to claim!")
            return False
        lowcoord = self.data[playerid]["point3"]
        highcoord = self.data[playerid]["point4"]
        blocks, length, width = self._getsizeclaim(lowcoord, highcoord)
        playersblocks = self.data[playerid]["claimblocks"]

        if blocks < self.minclaimsize:
            player.message(
                "&cClaim (%d) is not minimum size of at least %d blocks." % (
                    blocks, self.minclaimsize
                )
            )
            return False
        if length < self.minclaimwidth or width < self.minclaimwidth:
            player.message(
                "&cClaim has to be at least %d blocks wide all "
                "around." % self.minclaimwidth
            )
            return False

        if blocks > playersblocks:
            player.message(
                "&cYou do not have enough blocks to make this claim."
            )
            player.message("&eYou have: %d" % playersblocks)
            player.message("&eYou need: %d" % blocks)
            return False
        #  2) look for interceptions
        dim = self.data[playerid]["dim1"]
        sel1coords = self.data[playerid]["point3"]
        sel2coords = self.data[playerid]["point4"]
        collisions = self.regions.intersecting_regions(
            dim, sel1coords, sel2coords, rect=True
        )
        if collisions:
            player.message("&cArea overlaps region(s):")
            player.message("&5%s" % str(collisions).replace("u'", "'"))
            player.message(
                "claimed areas can be discovered with a wooden stick..."
            )
            return False
        # get a new claims region name
        thisclaimname, humanname = self._get_claimname(
            playerid, player.hasPermission("vclaims.admin")
        )
        if not thisclaimname:
            player.message(
                "&cyou have claimed the maximum number of areas "
                "(%s)" % self.maxclaims
            )
            return False
        #  3) inspections passed, claim allowed.
        lowcorner = (sel1coords[0], 5, sel1coords[2])
        highcorner = (sel2coords[0], 255, sel2coords[2])
        handle1 = self.data[playerid]["point1"]
        handle2 = self.data[playerid]["point2"]

        self.regions.rgdefine(
            thisclaimname, playerid, dim, lowcorner, highcorner
        )
        self.regions.protection_on(thisclaimname)
        player.message(
            "&2Region &5%s&2 created and protected." % thisclaimname
        )
        self.data[playerid]["claimlist"].append(thisclaimname)
        self.data[playerid]["claiminfo"][thisclaimname] = {}
        self.data[playerid]["claiminfo"][thisclaimname][
            "handle1"] = handle1
        self.data[playerid]["claiminfo"][thisclaimname][
            "handle2"] = handle2
        self.data[playerid]["claimblocks"] -= blocks
        self.data[playerid]["claimblocksused"] += blocks
        self.data[playerid]["point1"] = (0, 0, 0)
        self.data[playerid]["point2"] = (0, 0, 0)
        self.data[playerid]["point3"] = (0, 0, 0)
        self.data[playerid]["point4"] = (0, 0, 0)
        self.data[playerid]["selectionpoint"] = "none"
        self.data[playerid]["selectionmode"] = "none"
        return thisclaimname

    def _editclaim(self, player, playerid, existingclaimname):
        # get existing claimdata
        pos1 = self.regions.getregioninfo(existingclaimname, "pos1")
        pos2 = self.regions.getregioninfo(existingclaimname, "pos2")
        if pos1 is False:
            player.message("&cClaim %s failed 'locate'!" % existingclaimname)
            return False
        thisclaimblocksbefore, exlength, exwidth = self._getsizeclaim(
            pos1, pos2
        )
        #  1) calculate the claim size parameters
        if self.data[playerid]["selectionpoint"] != "point2":
            player.message("&cNothing selected to claim!")
            return False
        lowcoord = self.data[playerid]["point3"]
        highcoord = self.data[playerid]["point4"]
        blocks, length, width = self._getsizeclaim(lowcoord, highcoord)
        playersblocksavail = self.data[playerid][
                                 "claimblocks"] + thisclaimblocksbefore
        if blocks < self.minclaimsize:
            player.message(
                "&cClaim (%d) is not minimum size of at least %d "
                "blocks." % (blocks, self.minclaimsize)
            )
            return False
        if length < self.minclaimwidth or width < self.minclaimwidth:
            player.message(
                "&cClaim has to be at least %d blocks wide all "
                "around." % self.minclaimwidth
            )
            return False

        if blocks > playersblocksavail:
            player.message(
                "&cYou do not have enough blocks to make this claim."
            )
            player.message("&eYou have: %d" % playersblocksavail)
            player.message("&eYou need: %d" % blocks)
            return False
        #  2) look for interceptions
        # must turn off protection momentarily to avoid self collision.
        self.regions.protection_off(existingclaimname)
        time.sleep(.1)
        dim = self.data[playerid]["dim1"]
        sel1coords = self.data[playerid]["point3"]
        sel2coords = self.data[playerid]["point4"]
        collisions = self.regions.intersecting_regions(
            dim, sel1coords, sel2coords, rect=True
        )
        # restore protection status
        self.regions.protection_on(existingclaimname)
        if collisions:
            player.message("&cArea overlaps region(s):")
            player.message("&5%s" % str(collisions).replace("u'", "'"))
            player.message(
                "claimed areas can be discovered with a wooden stick..."
            )
            return False
        #  3) inspections passed, resize allowed.
        # using same claim name
        lowcorner = (sel1coords[0], 5, sel1coords[2])
        highcorner = (sel2coords[0], 255, sel2coords[2])
        handle1 = self.data[playerid]["point1"]
        handle2 = self.data[playerid]["point2"]

        thisclaimname = self.regions.rgedit(
            existingclaimname, playername=player.username,
            edit_coords=True, low_corner=lowcorner, high_corner=highcorner,
        )
        player.message("Region %s edited." % thisclaimname)
        self.data[playerid]["claiminfo"][thisclaimname][
            "handle1"] = handle1
        self.data[playerid]["claiminfo"][thisclaimname][
            "handle2"] = handle2
        self.data[playerid][
            "claimblocks"] = playersblocksavail - blocks
        self.data[playerid][
            "claimblocksused"] += (blocks - thisclaimblocksbefore)
        self.data[playerid]["point1"] = (0, 0, 0)
        self.data[playerid]["point2"] = (0, 0, 0)
        self.data[playerid]["point3"] = (0, 0, 0)
        self.data[playerid]["point4"] = (0, 0, 0)
        self.data[playerid]["selectionpoint"] = "none"
        self.data[playerid]["selectionmode"] = "none"
        return str(thisclaimname)

    def _get_claimname(self, playerid, admin):
        x = 0
        humanname = self.data[playerid]["playername"]

        while True:
            claimname = "%s-%d" % (humanname, x)
            if claimname in self.data[playerid]["claimlist"]:
                break
            else:
                x += 1
                if x > self.maxclaims and not admin:
                    return False, False
        return claimname, humanname

    def _show(self, player, position, onlineuuid):
        if self.data[onlineuuid]["point3"] == (0, 0, 0):
            player.message("&cNo seletion to show!")
            return
        low = self.data[onlineuuid]["point3"]
        high = self.data[onlineuuid]["point4"]
        lowcorner = low[0], position[1] + 1, low[2]
        highcorner = (high[0], position[1] + 4, high[2])
        self.regions.client_show_cube(
            player, lowcorner, highcorner, sendblock=False
        )

    def _finishwithselectionmode(self, playeruuid):
        data = self.data[playeruuid]
        data["point1"] = (0, 0, 0)
        data["point2"] = (0, 0, 0)
        data["point3"] = (0, 0, 0)
        data["point4"] = (0, 0, 0)
        data["selectionpoint"] = "none"
        data["selectionmode"] = "none"
        data["selectiontarget"] = "none"
        self.data_storageobject.save()

    def _do_claim(self, player_msg_object, owneruuid,
                  dim, pos1, pos2, ycoords_of_feet=62):
        data = self.data[owneruuid]

        data["selectionpoint"] = "point2"
        data["dim1"] = dim
        data["dim2"] = dim
        data["point1"] = pos1
        data["point2"] = pos2
        low, high = self.regions.stat_normalize_selection(
            data["point1"],
            data["point2"]
        )
        highcorner = high[0], ycoords_of_feet + 1, high[2]
        lowcorner = low[0], ycoords_of_feet + 5, low[2]
        data["point3"] = lowcorner
        data["point4"] = highcorner
        self.data_storageobject.save()
        claimed = self._claim(player_msg_object, owneruuid)
        if claimed:
            player_msg_object.message("&6Claim action successful.")
            data["selectionmode"] = "none"

    @staticmethod
    def _getsizeclaim(coord1, coord2):
        # size is including boundary
        width = abs(coord2[0] - coord1[0]) + 1
        length = abs(coord2[2] - coord1[2]) + 1
        blocks = length * width
        return blocks, length, width
