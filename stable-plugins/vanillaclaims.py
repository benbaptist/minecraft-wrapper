# -*- coding: utf-8 -*-

import time
import threading

NAME = "VanillaClaims"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.vanillaclaims"
VERSION = (0, 9, 0)
SUMMARY = "Simple player-friendly land claim system"
WEBSITE = ""
DESCRIPTION = "Uses regions.py as the backend for protecting player claims."
DEPENDENCIES = ["regions.py", ]

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

    def onDisable(self):
        self.run = False
        self.data_storageobject.close()

    def get_claim_data(self, playerobj):
        """
        Get the player's claim data.

        :param playerobj:
        :returns:  A dictionary of player claim data.

        """
        try:
            return self.data[playerobj.uuid]
        except KeyError:
            self.data[playerobj.uuid] = {
                "blocks": self.defaultclaimblocks,
                "blocksused": 0,
                "activity": 0,
                "playername": playerobj.username,
                "claimlist": [],
                "claiminfo": {},
                "laston": time.time(),
                "admin": playerobj.hasPermission("vclaims.admin")
            }
            return self.data[playerobj.uuid]

    def get_player_data(self, name):
        """
        Get the player's selection data.  Selection data is not saved
        between reboots.

        :param name: player name.

        :returns:  A dictionary of player selection data.
        {
            "point1"
            "point2"
            "dim1"
            "dim2"
            "mode"  # selection modes ...
            "point" # which point is being selected
            "proposed"  # cubic tuple (a set of hi/low coords)
            "rgedit" name of region being edited/resized
            }
        """
        try:
            return self.player_dat[name]
        except KeyError:
            self.player_dat[name] = {}
            self._finishwithselectionmode(name)
            return self.player_dat[name]

    def _track_activity(self):
        """
        Each item is a playeruuid, player object entry.
        """

        while self.run:
            time.sleep(.4)
            self._on_timer()
            time.sleep(.4)
            self._on_timer()
            while len(self.action_queue) > 0:
                # grab next change
                player = self.action_queue.pop(0)
                p = self.get_claim_data(player)
                # block increaser
                p["activity"] += 1
                activities = p["activity"]
                if activities % self.actionsperblock is not 0:
                    continue
                p["activity"] = 0
                if p["blocks"] < self.maxclaimblocks:
                    p["blocks"] += 1

    def _on_timer(self):
        """
        Puts each player in or out of claims mode.
        Modes:
          None: has no shovel
          Idle: has shovel, no action taken yet

        """
        while self.run:
            time.sleep(.5)
            for players in self.api.minecraft.getPlayers():
                player = self.api.minecraft.getPlayer(players)
                try:
                    itemid = player.getHeldItem()["id"]
                except AttributeError:
                    # probably a bad player object
                    continue

                p = self.get_player_data(player.username)

                # "mode" = selection mode
                if itemid == 284 and p["mode"] is None:
                    player.message(
                        "&2Claims shovel active... Click an area to edit "
                        "or to claim."
                    )
                    p["mode"] = "idle"

                if itemid != 284 and p["mode"]:
                    player.message(
                        "&2Shovel put away... Switching out of claims "
                        "mode"
                    )
                    self._finishwithselectionmode(player.username)

    def playerSpawned(self, payload):
        try:
            player = payload["player"]
        except AttributeError:
            self.log.error("VanillaClaims player spawn not successful.  "
                           "Payload: %s" % payload)
            return
        cl = self.get_claim_data(player)
        cl["laston"] = time.time()
        cl["admin"] = player.hasPermission("vclaims.admin")

    def action_dig(self, payload):
        try:
            player = payload["player"]
            action = payload["action"]
            itemid = player.getHeldItem()["id"]
        except AttributeError:
            # probably a bad player object
            return False
        if itemid == 284:
            if action == "begin_break":
                try:
                    position = payload["position"]
                    dim = player.getDimension()
                except AttributeError:
                    return False
                self.wand_use(player, player.uuid, position, dim)
            return False

        # update activity
        if action == "end_break":
            self.action_queue.append(player)

    def action_place(self, payload):
        try:
            player = payload["player"]
            itemid = player.getHeldItem()["id"]
        except AttributeError:
            return False

        if itemid == 284:
            try:
                dim = int(player.getDimension())
                clickposition = payload["clickposition"]
            except AttributeError:
                return False
            self.wand_use(player, player.uuid, clickposition, dim)
            # never allow gold shovel use - reserved for claims
            return False
        self.action_queue.append(player)

    def wand_use(self, player, playeruuid, position, dim):
        """

        :param player:
        :param playeruuid:
        :param position:
        :param dim:
        :return:
        """

        p = self.get_player_data(player.username)
        cl = self.get_claim_data(player)

        # point = self.data[playeruuid]["point"]
        # mode = p["mode"]
        anyregion = self.regions.regionname(position, dim)
        if anyregion:
            region_owner_uuid = self.regions.getregioninfo(
                anyregion, "ownerUuid"
            )
        else:
            region_owner_uuid = False

        # find the selection mode
        # first click point1 determines the selection mode
        if p["point"] == "point1":
            # If not your claim, draw it and go back to idle mode
            if region_owner_uuid and region_owner_uuid != playeruuid:
                # TODO draw the claim you are in, message with "not your claim"
                otheruuid = self.regions.getregioninfo(
                    anyregion, "ownerUuid"
                )
                othername = self.api.minecraft.lookupbyUUID(otheruuid)
                player.message("&cThis area is claimed by %s..." % othername)
                point1 = self.regions.getregioninfo(
                    anyregion, "pos1"
                )
                point2 = self.regions.getregioninfo(
                    anyregion, "pos2"
                )
                x = int(position[0])
                y = int(position[1]) - 1
                z = int(position[2])
                self._show(player, (x, y, z), point1, point2)
                self._reset_selections(playeruuid)
                p["mode"] = "idle"
                return
            # if unclaimed, go to 'new' mode
            elif not anyregion and p["mode"] == "idle":
                p["mode"] = "new"
                return
            # If your claim, then go to 'edit' mode (but don't make first point)
            elif region_owner_uuid == playeruuid and p["mode"] == "idle":
                p["mode"] = "edit"
                p["rgedit"] = anyregion
                # TODO STUFF to draw claim, place edit markers
                player.sendBlock(cl["claiminfo"][anyregion]["handle1"],
                                 LITREDSTONEORE, 0)
                player.sendBlock(cl["claiminfo"][anyregion]["handle2"],
                                 LITREDSTONEORE, 0)
                player.message(
                    {
                        "text":
                            "You are now editing the claim marked by the "
                            "restone corners.  Select a new corner (to cancel, "
                            "put shovel away).",
                        "color": "gold"
                    }
                )
                return
            else:
                # -we know it is not claimed (or is owned by player)
                # only successful selection as point1 enables point2
                p["point1"] = position
                p["dim1"] = dim
                p["point"] = "point2"
                # re-draw new point1 as point1 color (diamond)
                player.sendBlock(p["point1"], DIAMONDBLOCK, 0)
                return
        elif p["point"] == "point2":
            # If not your claim, draw the conflicting claim
            if region_owner_uuid and region_owner_uuid != playeruuid:
                # TODO draw the claim you are in, message with "not your claim"
                return
            p["point2"] = position
            p["dim2"] = dim
            # Stay at point two until successful (unless user cycles wand)
            p["point"] = "point2"
            # UNLESS, they re-select point1:
            if p["point2"] == p["point1"]:
                p["point"] = "point1"
                # TODO tell player to continue with selecting first point.
                return
            # or dimensions don't match:
            if p["dim1"] != p["dim2"]:
                self._reset_selections(playeruuid)
                p["mode"] = "idle"
                return
        # We now have a 'tentative' claim we can validate:
        # We know it's corner points were not claimed... but:
        p["proposed"] = self.regions.stat_normalize_selection(
            p["point1"], p["point2"]
        )
        newclaim = self._claim(player)
        if newclaim:
            # player.sendBlock(position, GOLDBLOCK, 0)
            player.message("&6Second Corner selected.")
            player.message("&6Claim action successful.")

            pos1 = cl["claiminfo"][newclaim]["handle1"]
            pos2 = cl["claiminfo"][newclaim]["handle2"]

            player.sendBlock(pos1, DIAMONDBLOCK, 0)
            player.sendBlock(pos2, GOLDBLOCK, 0)

            low = self.regions.getregioninfo(newclaim, "pos1")
            high = self.regions.getregioninfo(newclaim, "pos2")
            x = int(pos2[0])
            y = int(pos2[1]) - 1
            z = int(pos2[2])
            self._show(player, (x, y, z), low, high)
            p["mode"] = None
            p["point"] = "point1"
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
                p["point1"],
                LITREDSTONEORE, 0
            )
            player.sendBlock(
                p["point2"],
                LITREDSTONEORE, 0
            )
            self.data[playeruuid]["point"] = "error"
            return

    def _claim(self, player):
        playerid = player.uuid
        p = self.get_player_data(player.username)
        cl = self.get_claim_data(player)
        #  1) calculate the claim size parameters
        lowcoord = p["proposed"][0]
        highcoord = p["proposed"][1]
        blocks, length, width = self._getsizeclaim(lowcoord, highcoord)
        playersblocks = cl["blocks"]
        usedblocks = cl["blocksused"]
        if p["mode"] == "edit":
            # credit back blocks used by an existing claim being edited.
            pos1 = self.regions.getregioninfo(p["rgedit"], "pos1")
            pos2 = self.regions.getregioninfo(p["rgedit"], "pos2")
            x_dia = pos2[0] - pos1[0]
            z_dia = pos2[2] - pos1[2]
            usedblocks -= (x_dia * z_dia)

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

        if blocks > playersblocks - usedblocks:
            player.message(
                "&cYou do not have enough blocks to make this claim."
            )
            player.message("&eYou have: %d" % playersblocks)
            player.message("&eYou need: %d" % blocks)
            return False

        #  2) look for intersecting regions
        collisions = self.regions.intersecting_regions(
            p["dim1"], lowcoord, highcoord, rect=True
        )
        if collisions:
            if p["mode"] == "edit" and len(
                    collisions) < 2 and p["rgedit"] in collisions:
                collisions.remove(p["rgedit"])
            if len(collisions) > 0:
                player.message("&cArea overlaps region(s):")
                player.message("&5%s" % str(collisions).replace("u'", "'"))
                return False

        if p["mode"] == "edit":
            self._delete_claim(player, p["rgedit"], playerid)

        # get a new claims region name
        thisclaimname, humanname = self._get_claimname(
            playerid, cl["admin"]
        )
        if not thisclaimname:
            player.message(
                "&cyou have claimed the maximum number of areas "
                "(%s)" % self.maxclaims
            )
            return False
        #  3) inspections passed, claim allowed.
        lowcorner = (lowcoord[0], 5, lowcoord[2])
        highcorner = (highcoord[0], 255, highcoord[2])
        handle1 = p["point1"]
        handle2 = p["point2"]
        self.regions.rgdefine(
            thisclaimname, playerid, p["dim1"], lowcorner, highcorner
        )
        self.regions.protection_on(thisclaimname)
        player.message(
            "&2Region &5%s&2 created and protected." % thisclaimname
        )

        cl["claimlist"].append(thisclaimname)
        cl["claiminfo"][thisclaimname] = {}
        cl["claiminfo"][thisclaimname]["handle1"] = handle1
        cl["claiminfo"][thisclaimname]["handle2"] = handle2
        cl["blocksused"] += blocks

        self._reset_selections(player.username)

        p["mode"] = None
        return thisclaimname

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
        self._claimblocks(player, player.uuid, player.username)

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
        blocksinuse = self.data[targetuuid]["blocksused"]
        if subcommmand == "add":
            self.data[targetuuid]["blocks"] += amount
            player.message(
                "&eAdded %s blocks to player %s" % (amount, targetname)
            )
        if subcommmand == "sub":
            self.data[targetuuid]["blocks"] -= amount
            player.message(
                "&eremoved %s blocks from player %s" % (amount, targetname)
            )
        if subcommmand == "set":
            self.data[targetuuid]["blocks"] = amount
            player.message("&eset %s's blocks to %s" % (targetname, amount))
        if subcommmand == "info":
            self._claimblocks(player, targetuuid, targetname)
            return
        amount = self.data[targetuuid]["blocks"]
        player.message("&2%s has %s blocks." % (targetname, amount))

    def _spade(self, *args):
        player = args[0]
        self.api.minecraft.console(
            "give %s minecraft:golden_shovel 1 32" % player.username
        )

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
        self._quick_claim(
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
        point1 = self.regions.getregioninfo(
            regionname, "pos1"
        )
        point2 = self.regions.getregioninfo(
            regionname, "pos2"
        )
        x = int(pos[0])
        y = int(pos[1]) - 1
        z = int(pos[2])
        self._show(player, (x, y, z), point1, point2)
        player.message("&eRegion: &5%s" % regionname)

    def _claimblocks(self, playerobject, playerid, playername):
        totalblocks = self.data[playerid]["blocks"]
        blocksinuse = self.data[playerid]["blocksused"]
        blocksavailable = totalblocks - blocksinuse

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

    def _delete_claim(self, player, claimname, ownerid):
        cl = self.get_claim_data(player)
        handle1 = cl["claiminfo"][claimname]["handle1"]
        handle2 = cl["claiminfo"][claimname]["handle2"]
        blocksize, length, width = self._getsizeclaim(handle1, handle2)
        if claimname in cl["claiminfo"]:
            del cl["claiminfo"][claimname]
        if claimname in cl["claimlist"]:
            cl["claimlist"].remove(claimname)
        self.regions.clicks_queue.append(["break", player, handle1])
        self.regions.clicks_queue.append(["break", player, handle2])
        self.regions.rgdelete(claimname)
        cl["blocksused"] -= blocksize

    def _abandonclaim(self, player, thisclaimname, playerid):
        self._delete_claim(player, thisclaimname, playerid)
        player.message("&eClaim %s deleted!" % thisclaimname)

    def _get_claimname(self, playerid, admin):
        x = 0
        humanname = self.data[playerid]["playername"]

        while True:
            claimname = "%s-%d" % (humanname, x)
            if claimname not in self.data[playerid]["claimlist"]:
                break
            else:
                x += 1
                if x > self.maxclaims and not admin:
                    return False, False
        return claimname, humanname

    def _show(self, player, position, low, high):
        """

        :param player:
        :param position:
        :param low:
        :param high:
        :return:
        """
        lowcorner = low[0], position[1] + 1, low[2]
        highcorner = (high[0], position[1] + 4, high[2])
        self.regions.client_show_cube(
            player, lowcorner, highcorner, sendblock=False
        )

    def _finishwithselectionmode(self, playername):
        self._reset_selections(playername)
        p = self.player_dat[playername]
        p["mode"] = None

    def _reset_selections(self, playername):
        p = self.player_dat[playername]
        p["point1"] = [0, 0, 0]
        p["point2"] = [0, 0, 0]
        p["dim1"] = 0
        p["dim2"] = 0
        p["point"] = "point1"
        p["proposed"] = [0, 0, 0], [0, 0, 0]
        p["rgedit"] = None

    def _quick_claim(self, player_msg_object, owneruuid,
                     dim, pos1, pos2, ycoords_of_feet=62):
        data = self.data[owneruuid]

        data["point"] = "point2"
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
            data["mode"] = "none"

    @staticmethod
    def _getsizeclaim(coord1, coord2):
        # size is including boundary
        width = abs(coord2[0] - coord1[0]) + 1
        length = abs(coord2[2] - coord1[2]) + 1
        blocks = length * width
        return blocks, length, width
