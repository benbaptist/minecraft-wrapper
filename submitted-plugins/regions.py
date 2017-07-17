# -*- coding: utf-8 -*-

import SurestLib

from sys import version_info
PY3 = version_info > (3,)

if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range

# region Header
NAME = "Regions"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.regions"  # the ID of the plugin, used internally for storage
VERSION = (0, 2, 2)
SUMMARY = "World regions editing and protection."
WEBSITE = ""  # the developer's or plugin's website
DESCRIPTION = """Creates and maintains regions.  Also does some basic world edit functions.
Region protection features can be used manually as a stand-alone protection plugin, or can
be implemented as the backend of a higher level, player friendly type plugin similar to
GriefPrevention. """

"""
Administrator information-

Permission nodes:
--------------------------------------------------------------------------
node                 description                        suggested OP level
--------------------------------------------------------------------------
region.fill         - fill command                      - OWNER/OP
region.copy         - copy command                      - OWNER/OP
region.replace      - replace command                   - OWNER/OP
region.delete       - delete regions                    - OP/admin
region.define       - create regions                    - admin/mod
region.protect      - set region prot                   - admin/mod
region.adjust       - change region size (incl //pos1)  - admin/mod
region.wand         - use selection tool                - possibly anyone?
region.player       - basic command user perms          - possibly anyone?
region.multiple     - own more than one region          - admin/mod
region.setowner     - set any region's owner            - admin/mod

--------------------------------------------------------------------------
API methods:
--------------------------------------------------------------------------
@staticmethod
getregionlist(prot_dim, lowcoords, highcoords)

@staticmethod
normalizeSelection(coords1, coords2)

protection_on(self, region_name)

protection_off(self, region_name)

rgdefine(self, regionname, ownerUUID, ownername, dimension, lowCorner, highCorner)

rgdelete(self, regionname)

rgedit(self, regionname, playername=False, lowCorner=False, highCorner=False,
       addbreakUUID=False, addplaceUUID=False, addaccessUUID=False, removeUUID=False,
       addbanUUID=False, unbanUUID=False, ownerUUID=False, flags=False)

regionname(self, position, dim):

getregioninfo(self, regionname, infokey)

intersecting_regions(self, dim, sel1coords, sel2coords, rect=False)
--------------------------------------------------------------------------
"""

# endregion


class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log
        self.players = {}
        
        self.itemcontrols = True
        self.tntlimited = True
        self.tntlevel = 20  # above this, TNT is not allowed.
        self.tntinclaim = False
        self.miscPlaceableBlocks = (323, 324, 330, 331, 342, 343, 356, 389,
                                    397, 404, 407, 416, 425, 426, 427, 428,
                                    429, 430, 431)

        self.usePermissions = False  # Use Perms - 'toolbox.chunktools', etc
        self.useVanillaBehavior = False  # give generic "unknown command" message.

        # Storages:
        self.regiondirectory_storageobject = self.api.getStorage("regionfiles", True)
        self.regions_storageobject = self.api.getStorage("regions", True)

        # Storage Data:
        self.regiondirectory = self.regions_storageobject.Data
        self.regions = self.regions_storageobject.Data

    # region _Events subsection
    def onEnable(self):
        # init data
        if "files" not in self.regiondirectory:
            self.regiondirectory["files"] = {}
        if "regions" not in self.regions:
            self.regions["regions"] = {}

        # region register help group
        self.api.registerHelp("Regions", "World region, edit, guard, and logger.", [
            ("//rg define <region>", "defines a region named <region>", "region.define"),
            ("//rg resize <region>", "resize <region> to new pos1, pos2", "region.define"),
            ("//rg protect [region] <True|False>", "Set region protected from breakage", "region.protect"),
            ("//rg roof [region] <height>", "changes y coord height", "region.adjust"),
            ("//rg floor [region] <height>", "changes y coord depth", "region.adjust"),
            ("//rg delete <region>", "remove / delete '<region>'", "region.delete"),
            ("//rg set [region name] <owner-break-place-access-remove>  <playername>'",
             "Change region flags/permissions", "region.player"),
            ("//wand", "Gives the editing wand", "region.wand"),
            ("//pos1", "Select pos1", "region.wand"),
            ("//pos2", "Select pos2", "region.wand"),
            ("//home", "get placed 'somewhere' near one of your claims", None),
            ("//here", "face the northwest corner of //copy destination", "region.wand"),
            ("//replace <newTile> <Data> <oldTile> <Data>", "replace blocks (see //fill)", "region.replace"),
            ("//copy", "copies selection starting at corner you face with //here", "region.copy"),
            ("//fill <item> <metadata>", "a more massive implementation of the minecraft /fill command. It is "
                                         "essentially only limited by loaded chunks. command fails for any slice "
                                         "in an unloaded chunk. Command fails for any slice over 32K. (a slice is a "
                                         "X times Y Coord slice that is 1Z wide)", "region.fill")])
        # endregion

        # region register events
        self.api.registerEvent("player.dig", self.action_playerdig)
        self.api.registerEvent("player.place", self.action_playerplace)
        self.api.registerEvent("player.interact", self.action_playerinteract)
        # endregion

        # region register commands
        self.api.registerCommand(("/rg", "/reg", "/region"), self._region, None)  # perms mostly handled by subcommands
        self.api.registerCommand("/fill", self._rgfill, None)
        self.api.registerCommand("/replace", self._rgreplace, None)
        self.api.registerCommand("/copy", self._rgcopy, None)
        self.api.registerCommand("/pos1", self._pos1, None)
        self.api.registerCommand("/pos2", self._pos2, None)
        self.api.registerCommand("/here", self._here, None)
        self.api.registerCommand("/wand", self._wand, None)
        self.api.registerCommand("/home", self._home, None)
        # endregion

        # Register default permissions
        self.api.registerPermission("region.wand", True)
        self.api.registerPermission("region.delete", True)
        self.api.registerPermission("region.define", True)
        self.api.registerPermission("region.protect", True)
        self.api.registerPermission("region.adjust", True)
        self.api.registerPermission("region.player", True)
        self.api.registerPermission("region.multiple", True)
        self.api.registerPermission("region.setowner", True)

    def onDisable(self):
        self.regiondirectory_storageobject.close()
        self.regions_storageobject.close()

    def action_playerinteract(self, payload):
        """included player interact to prevent switch operations at the claims borders (player.place allows it)
        this should prevent lava and water grief inside the claim"""
        player = payload["player"]
        try:
            gamemode = int(player.getGamemode())
            dim = int(player.getDimension())
            position = (payload["position"][0], payload["position"][1], payload["position"][2])
        except AttributeError:
            self.api.log("bad payload - missing Dim, GM, or POS")
            self.api.log(str(payload))
            return False  # bad player object
        # cancel interactions in protected regions
        if gamemode == 0 or gamemode == 2:  # creative and spectator ignore protections
            globalregions = "%s__global__" % dim
            actionregion = "%s_%s" % (dim, SurestLib.getregionnumber(position[0], position[2]))
            if actionregion in self.regiondirectory["files"]:  # if region has protected items/regionnames
                for regionnames in self.regiondirectory["files"][actionregion]:  # look at what regionnames are listed
                    if regionnames in self.regions["regions"]:
                        if self._blocks_match(regionnames, position):
                            return self._whenmatchingcoordsinteract(player, position, regionnames)
            if globalregions in self.regiondirectory["files"]:
                for regionnames in self.regiondirectory["files"][globalregions]:  # see what global regions are listed
                    if regionnames in self.regions["regions"]:
                        if self._blocks_match(regionnames, position):
                            return self._whenmatchingcoordsinteract(player, position, regionnames)
            # If nothing matches, land is free...
        return True

    def action_playerplace(self, payload):
        """
        Player.place is the calculated location of a block to be placed based on the "face" value.  This means that
        wrapper creates two events from the same client action...  A right click (by default).  One event is the actual
        block that was clicked on (player.interact) and the location a placed block will appear (player.place).
        player.place is a handy event for 'Wand' use on pos2 because, even though inaccurate for selection (it
        selects the adjoining block), the fake blocks can be used to build a virtual structure away into air blocks
        to select air blocks that are otherwise "unclickable".
        """
        player = payload["player"]
        try:
            gamemode = int(player.getGamemode())
            dim = int(player.getDimension())
            position = (payload["position"][0], payload["position"][1], payload["position"][2])
            item = player.getHeldItem()
        except AttributeError:
            self.log.error("bad payload - missing Dim, GM, item or POS")
            self.log.error(str(payload))
            return False  # bad player object
        p = self._getMemoryPlayer(player.username)
        try:
            itemid = item["id"]
        except TypeError:
            itemid = "none"
        
        # generic TNT controls for all events - These only catch when item is not allowed even in claim
        if gamemode == 0 or gamemode == 2:  # creative and spectator ignore protections
            if self.itemcontrols is True:
                if itemid == 46:  # TNT
                    if self.tntinclaim is False:
                        if (self.tntlimited is True) and (position[1] > self.tntlevel):
                            player.message("&dNo TNT here...")
                            return False
            
        # selection pos 2
        if itemid == 271:
            if player.hasPermission("region.wand"):
                dim = int(player.getDimension())
                p["dim2"] = dim
                p["sel2"] = position
                player.sendBlock(position, 138, 0)  # send fake block
                player.message("&dPoint two selected. (%d %d %d)" % (position[0], position[1], position[2]))
                if p["regusing"] is not None:
                    player.message("&cYou were using region '%s'.  You are now selecting a new area." % (p["regusing"]))
                p["regusing"] = None
                return False
        # cancel placed item in protected regions
        if gamemode == 0 or gamemode == 2:  # creative and spectator ignore protections
            globalregions = "%s__global__" % dim
            actionregion = "%s_%s" % (dim, SurestLib.getregionnumber(position[0], position[2]))
            if actionregion in self.regiondirectory["files"]:  # if region has protected items/regionnames
                for regionnames in self.regiondirectory["files"][actionregion]:  # look at what regionnames are listed
                    if regionnames in self.regions["regions"]:
                        if self._blocks_match(regionnames, position):
                            return self._whenmatchingcoordsplace(player, position, regionnames, itemid)
            if globalregions in self.regiondirectory["files"]:
                for regionnames in self.regiondirectory["files"][globalregions]:  # see what global regions are listed
                    if regionnames in self.regions["regions"]:
                        if self._blocks_match(regionnames, position):
                            return self._whenmatchingcoordsplace(player, position, regionnames, itemid)
            # If nothing matches, land is free...

        # TNT controls for all events - for all events out of a claim.
        if gamemode == 0 or gamemode == 2:  # creative and spectator ignore protections
            if self.itemcontrols is True:
                if itemid == 46:  # TNT
                    if (self.tntlimited is True) and (position[1] > self.tntlevel):
                        player.message("&dNo TNT here...")
                        return False

        return True

    def action_playerdig(self, payload):
        """
        player break block / digging - Face (payload["face"]) is the side of block being clicked
        payloads {"player": self.getPlayerObject(), "position": position, "action": "end_break/begin_break",
        "face": data["face"]}
        """
        player = payload["player"]
        action = payload["action"]
        #try:
        gamemode = int(player.getGamemode())
        item = player.getHeldItem()
        #except AttributeError:
            #self.log.error("bad payload - missing GM or Item")
            #self.log.error(str(payload))
            #return False  # bad player object - usually means bad internet or player already disconnected.
        dim = int(player.getDimension())
        # # obtain item id
        try:
            itemid = item["id"]
        except TypeError:
            itemid = "none"
        p = self._getMemoryPlayer(player.username)
        position = payload["position"]
        # selection pos 1
        if player.hasPermission("region.wand"):
            if itemid == 271 and (
                    ((action == "end_break") and (gamemode == 1)) or (
                        (action == "begin_break") and (gamemode == 0))):
                p["sel1"] = position
                p["dim1"] = dim
                player.sendBlock(position, 138, 0)
                player.message("&dPoint one selected. (%d %d %d)" % (position[0], position[1], position[2]))
                if p["regusing"] is not None:
                    player.message("&cYou were using region '%s'.  You are now selecting a new area." % p["regusing"])
                p["regusing"] = None
                return False
        # cancel break in protected area
        if gamemode == 0 or gamemode == 2:  # creative and spectator ignore protections
            globalregions = "%s__global__" % dim
            action_region = "%s_%s" % (dim, SurestLib.getregionnumber(position[0], position[2]))
            if action_region in self.regiondirectory["files"]:  # if region has protected items/regionnames
                for regionnames in self.regiondirectory["files"][action_region]:  # look at what regionnames are listed
                    if regionnames in self.regions["regions"]:
                        if self._blocks_match(regionnames, position):
                            return self._whenmatchingcoordsbreak(player, position, regionnames)
            if globalregions in self.regiondirectory["files"]:
                for regionnames in self.regiondirectory["files"][globalregions]:  # see what global regions are listed
                    if regionnames in self.regions["regions"]:
                        if self._blocks_match(regionnames, position):
                            return self._whenmatchingcoordsbreak(player, position, regionnames)
            # If nothing matches, land is free...
        return True

    """end _Events subsection"""
    # endregion

    # region block protection methods
    def _blocks_match(self, region_name, position):
        if region_name not in self.regions["regions"]:
            return False
        cube = (self.regions["regions"][region_name]["pos1"], self.regions["regions"][region_name]["pos2"])
        return all(self._point_inside(cube, position))  # block is protected -see if player allowed to place it.

    def _whenmatchingcoordsplace(self, player, position, regionname, item):
        """code to run when match
        player, (self.regions["regions"][name], p
        return _whenMatchingcoords(player, position, name, payload["item"])
        """
        p = self._getMemoryPlayer(player.username)
        p["lastregion"] = regionname
        if str(player.mojangUuid) in (self.regions["regions"][regionname]["ownerUuid"]):
            return True  # code will end here for players in their own regions/claims
        if not str(player.mojangUuid) in (self.regions["regions"][regionname]["placeplayers"]):
            if item in self.miscPlaceableBlocks or item < 198:  # send air to replace placed items only
                player.message("&dNo permission to do that for region %s" % regionname)
                player.sendBlock(position, 0, 0)
            player.sendBlock(position, 35, 0, sendblock=False)  # send a barrier particle
            return False
        return True

    def _whenmatchingcoordsinteract(self, player, position, regionname):
        """code to run when match
        player, (self.regions["regions"][name], p
        return _whenMatchingcoords(player, position, name, payload["item"])
        """
        p = self._getMemoryPlayer(player.username)
        p["lastregion"] = regionname
        if str(player.mojangUuid) in (self.regions["regions"][regionname]["ownerUuid"]):
            return True  # code will end here for players in their own regions/claims
        if "all" in (self.regions["regions"][regionname]["accessplayers"]):
            return True
        if not str(player.mojangUuid) in (self.regions["regions"][regionname]["accessplayers"]):
            player.sendBlock(position, 35, 0, sendblock=False)  # send a barrier particle
            return False
        return True

    def _whenmatchingcoordsbreak(self, player, position, regionname):
        """code to run when match
        player, (self.regions["regions"][name], p
        return _whenMatchingcoords(player, position, regionname)
        """
        p = self._getMemoryPlayer(player.username)
        p["lastregion"] = regionname
        if str(player.mojangUuid) in (self.regions["regions"][regionname]["ownerUuid"]):
            return True  # code will end here for players in their own regions/claims
        if not str(player.mojangUuid) in (self.regions["regions"][regionname]["breakplayers"]):
            player.message("&dSorry, you are not allowed to break that!")
            player.sendBlock(position, 7, 0)
            return False
        return True

    @staticmethod
    def _point_inside(cube, point):
        firstcorner, secondcorner = cube
        xmin, xmax = firstcorner[0] - 1, secondcorner[0] + 1
        yield xmin < point[0] < xmax
        zmin, zmax = firstcorner[2] - 1, secondcorner[2] + 1
        yield zmin < point[2] < zmax
        ymin, ymax = firstcorner[1] - 1, secondcorner[1] + 1
        yield ymin < point[1] < ymax

    def _areas_overlap_rect(self, rect1, rect2):
        """
        Just a wrapper for _areas_overlap_cube that disregards the y axis.
        """
        rect1lower, rect1upper = rect1
        rect2lower, rect2upper = rect2
        x1, z1 = rect1lower[0], rect1lower[2]
        x2, z2 = rect1upper[0], rect1upper[2]
        xx1, zz1 = rect2lower[0], rect2lower[2]
        xx2, zz2 = rect2upper[0], rect2upper[2]
        cube1lower = (x1, 0, z1)
        cube1upper = (x2, 0, z2)
        cube2lower = (xx1, 0, zz1)
        cube2upper = (xx2, 0, zz2)
        cube1 = (cube1lower, cube1upper)
        cube2 = (cube2lower, cube2upper)
        return self._areas_overlap_cube(cube1, cube2)

    def _areas_overlap_cube(self, cube1, cube2):
        """
        Returns true if cubes intersect.  Returns False is not.
        """
        cube1_lower, cube1_upper = cube1
        x, y, z = cube1_lower
        xx, yy, zz = cube1_upper
        # in case cube2 is entirely inside cube1 / vice-versa:
        cube2cornerpoint = cube2[0]  # get lower coord tuple of cube2
        if all(self._point_inside(cube1, cube2cornerpoint)):
                return True

        y_range_item = xrange(y + 1, yy)
        x_range_item = xrange(x, xx + 1)
        z_range_item = xrange(z, zz)

        # check y edges for intersection (should skip if no "edge" y and yy differ more than 1)
        for y_range in y_range_item:  # any side edge inside cube2
            # using same/zero y coordinates will cause this check to skip (for rectangle areas versus cubical)
            if all(self._point_inside(cube2, (x, y_range, z))):
                return True
            if all(self._point_inside(cube2, (x, y_range, zz))):
                return True
            if all(self._point_inside(cube2, (xx, y_range, z))):
                return True
            if all(self._point_inside(cube2, (xx, y_range, zz))):
                return True
        # x and z edges
        for x_range in x_range_item:
            if all(self._point_inside(cube2, (x_range, y, z))):
                return True
            if all(self._point_inside(cube2, (x_range, y, zz))):
                return True
            if all(self._point_inside(cube2, (x_range, yy, z))):
                return True
            if all(self._point_inside(cube2, (x_range, yy, zz))):
                return True
        for z_range in z_range_item:  # zz (i.e. zz+1 range) already checked on x_range
            if all(self._point_inside(cube2, (x, y, z_range))):
                return True
            if all(self._point_inside(cube2, (x, yy, z_range))):
                return True
            if all(self._point_inside(cube2, (xx, y, z_range))):
                return True
            if all(self._point_inside(cube2, (xx, yy, z_range))):
                return True
        return False

    # endregion

    # region shared methods

    def _normalizeSelection(self, player, size_shape_override=False, printresult=False):
        p = self._getMemoryPlayer(player.username)
        if p["dim1"] != p["dim2"]:
            return "badDim"
        if p["sel1"] and p["sel2"]:
            p["sel1"], p["sel2"] = self.normalizeSelection(p["sel1"], p["sel2"])
        else:
            return "Nosel"
        if printresult is True:
            player.message("Pos1 ( lower northwest corner) = %d, %d, %d" % (p["sel1"][0], p["sel1"][1], p["sel1"][2]))
            player.message("Pos2 ( upper southeast corner) = %d, %d, %d" % (p["sel2"][0], p["sel2"][1], p["sel2"][2]))
        if size_shape_override:
            return True
        if p["sel1"] == p["sel2"]:
            return "singleblock"
        if (p["sel1"][0] == p["sel2"][0]) and (p["sel1"][2] == p["sel2"][2]):
            return "column"
        if (p["sel1"][0] == p["sel2"][0]) or (p["sel1"][2] == p["sel2"][2]):
            if p["sel2"][1] == p["sel1"][1]:
                return "line"
            else:
                return "wall"
        return True

    def _getMemoryPlayer(self, name):
        if name not in self.players:
            self.players[name] = {"sel1": None,
                                  "sel2": None, "dim1": None, "dim2": None, "regusing": None, "lastregion": False}
        return self.players[name]

    def _insertSelectedRegionname(self, player, args):  # args = self._insertSelectedRegionname(player, args)
        p = self._getMemoryPlayer(player.username)
        if p["regusing"] is None:
            return args
        if len(args) > 1:
            if args[1] == p["regusing"]:
                return args
        player.message({"text": "None or invalid region specified. Using region ", "color": "gray",
                        "extra": [{"text": p["regusing"], "color": "dark_purple"}, {"text": ".", "color": "gray"}]})
        allargs = args[0] + " " + p["regusing"]
        for x in range(1, len(args)):
            allargs = allargs + " " + args[x]
        args = allargs.split(" ")
        return args

    def _console_fill(self, pos1, pos2, method, newblockname, newblockdata, oldblockname, oldblockdata):
        """
        :param pos1: lowest coordinates
        :param pos2: highest coordinates
        :param method: "replace" to replace blocks, anything else is "fill"
        :param newblockname: minecraft:name of block to fill with
        :param newblockdata: dataID of block (usually 0, unless a type, like stones: andesite, doirite, etc)
        :param oldblockname: minecraft:name of block being replaced/removed
        :param oldblockdata: dataID of block (usually 0)
        """
        x1, y1, z1 = pos1
        x2, y2, z2 = pos2
        for zdex in range(int(z1), (int(z2) + 1)):
            zstr = str(zdex)
            if method == "replace":
                textcommand = "fill %s %s %s %s %s %s %s %s replace %s %s" % \
                              (x1, y1, zstr, x2, y2, zstr, newblockname, newblockdata, oldblockname, oldblockdata)
            else:
                textcommand = "fill %s %s %s %s %s %s %s %s" % (x1, y1, zstr, x2, y2, zstr, newblockname, newblockdata)
            self.api.minecraft.console(textcommand)

    """end shared methods subsection"""
    # endregion

    # region Top-level commands (registered commands)
    def _wand(self, *args):
        player = args[0]
        if SurestLib.permitted(player, "region.wand", self.usePermissions, self.useVanillaBehavior) is False:
            return
        self.api.minecraft.console("give %s minecraft:wooden_axe 1" % player.username)
        player.message("&bleft and right click two different blocks to select a region.")

    # region Top-level commands (registered commands)
    def _home(self, *args):
        player = args[0]

        for aregion in self.regions["regions"]:
            if self.regions["regions"][aregion]["ownerUuid"] == str(player.mojangUuid):
                x = self.regions["regions"][aregion]["pos1"][0]
                z = self.regions["regions"][aregion]["pos1"][2]
                self.api.minecraft.console("spreadplayers %s %s 1 2 false %s" % (x, z, player.username))
                player.message("&5Make sure you /sethome again (this command won't be here forever!")
                return
        player.message("&cBummer!  I could not find your old base (you never claimed it?)")
        player.message("&5I'll try to get you to a friends house...")
        for aregion in self.regions["regions"]:
            if str(player.mojangUuid) in self.regions["regions"][aregion]["accessplayers"]:
                x = self.regions["regions"][aregion]["pos1"][0]
                z = self.regions["regions"][aregion]["pos1"][2]
                self.api.minecraft.console("spreadplayers %s %s 1 2 false %s" % (x, z, player.username))
                player.message("&5Make sure you /sethome again (this command won't be here forever!")
                return
        player.message("&cWoe is you!  No home.. No friends.. Sorry man!")

    def _pos1(self, player, args):
        if SurestLib.permitted(player, "region.wand", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) != 3:
            player.message("&cArguments not properly specified (three numbers)")
            return
        x = int(float((args[0])))
        y = int(float((args[1])))
        z = int(float((args[2])))
        dim = int(player.getDimension())
        p = self._getMemoryPlayer(player.username)
        p["dim1"] = dim
        p["sel1"] = (x, y, z)
        player.message("&dPoint one selected. (%d %d %d)" % (x, y, z))
        if p["regusing"] is not None:
            player.message("&cYou were using region '%s'.  You are now selecting a new area." % p["regusing"])
        p["regusing"] = None
        return False

    def _pos2(self, player, args):
        if SurestLib.permitted(player, "region.wand", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) != 3:
            player.message("&cArguments not properly specified (three numbers)")
            return
        x = int(float((args[0])))
        y = int(float((args[1])))
        z = int(float((args[2])))
        dim = int(player.getDimension())
        p = self._getMemoryPlayer(player.username)
        p["dim2"] = dim
        p["sel2"] = (x, y, z)
        player.message("&dPoint two selected. (%d %d %d)" % (x, y, z))
        if p["regusing"] is not None:
            player.message("&cYou were using region '%s'.  You are now selecting a new area." % p["regusing"])
        p["regusing"] = None
        return False

    def _here(self, *args):
        player = args[0]
        if SurestLib.permitted(player, "region.wand", self.usePermissions, self.useVanillaBehavior) is False:
            return
        curpos = player.getPosition()
        x = int(curpos[0])
        z = int(curpos[2])
        self.api.minecraft.console("tp %s %d ~ %d -45 45" % (str(player.username), x, z))

    def _region(self, player, args):
        """
        The main command //region - this will parse subcommands only and pass the arguments to the
        subcommand.  This also decides the permissions.
        """
        if SurestLib.permitted(player, "region.player", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) == 0:
            self._regionhelp(player)
            return
        if args[0].lower() in ("define", "def", "create") and (player.hasPermission("region.define")):
            print (args)
            self._rgdefine(player, args)
            return
        if args[0].lower() in ("select", "sel", "use") and (player.hasPermission("region.select")):
            self._rguse(player, args)
            return
        if args[0].lower() in ("prot", "protect", "protection") and (player.hasPermission("region.protect")):
            self._rgprotect(player, args)
            return
        if args[0].lower() == "roof" and (player.hasPermission("region.adjust")):
            self._rgroof(player, args)
            return
        if args[0].lower() == "floor" and (player.hasPermission("region.adjust")):
            self._rgfloor(player, args)
            return
        if args[0].lower() in ("remove", "rem", "delete", "del", "erase"):
            self._rgdelete(player, args)
            return
        if args[0].lower() in ("set", "flags", "setflag", "flag"):
            self._rgsetflags(player, args)
            return
        if args[0].lower() == "use":
            self._rguse(player, args)
            return
        if args[0].lower() == "draw":
            self._rgdraw(player, args)
            return
        if args[0].lower() in ("edit", "resize", "editcoords", "change") and (player.hasPermission("region.adjust")):
            self._rg_resize(player, args)
            return
        if args[0].lower() != "help":
            player.message("&cSubcommand not recognized!")
        player.message("&aUsage:")
        player.message("&2//region <&esubcommand&2> [region] <args>&r  - Valid &esubcommand&rs:")
        player.message("&edefine &2<region>&f - creates a region")
        player.message("&eresize &2<region>&f - resize a region")
        player.message("&euse &2<region>&f - use <region>' for commands")
        player.message("&eprotect &2<True|False|on|off>&f - Set region protection on/off")
        player.message("&eroof|floor &2<height>&f - adjust y coord height/depth")
        player.message("&edelete &2<region>&f - delete region '<region>'")
        player.message("&edraw &2[region]&f - draw region '[region]'")
        player.message("&eset&f - type &2//region set&f for more info...")

    def _rgfill(self, player, args):
        if SurestLib.permitted(player, "region.fill", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) >= 1:
            # fill minecraft:glass 0
            blockdata = "0"
            if len(args) == 2:
                blockdata = args[1]  # player can omit block data argument for block ids if it is just 0
            result = self._normalizeSelection(player)
            if result == "Nosel":
                player.message("&bYou must select a region first! (use wooden axe or see help)")
                return
            if result == "badDim":
                player.message("&bSelection points are in different dimensions!")
                return
            p = self._getMemoryPlayer(player.username)
            if p["dim1"] != 0:
                player.message("&bSorry, but this command only functions in the overworld...")
                return
            self._console_fill(p["sel1"], p["sel2"], "fill", args[0], blockdata, "None", "0")
            player.message({"text": "Command completed- check console for results!", "color": "gold"})
        else:
            player.message({"text": "No arguments specified. Try /help", "color": "red"})
            return

    def _rgreplace(self, player, args):
        if SurestLib.permitted(player, "region.replace", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) >= 1:
            # replace minecraft:air 0 minecraft:snow_layer 0  (turn snow layer to air)
            if len(args) != 4:
                player.message({"text": "Wrong number of arguments specified.", "color": "red"})
                player.message({"text": "//replace <desired tilename> <dataValue> <tile to be removed> <dV>"})
            result = self._normalizeSelection(player)
            if result == "Nosel":
                player.message("&bYou must select a region first! (use wooden axe or see help)")
                return
            if result == "badDim":
                player.message("&bSelection points are in different dimensions!")
                return
            p = self._getMemoryPlayer(player.username)
            if p["dim1"] != 0:
                player.message("&bSorry, but this command only functions in the overworld...")
                return
            self._console_fill(p["sel1"], p["sel2"], "replace", args[0], args[1], args[2], args[3])
            player.message({"text": "Command completed- check console for results!", "color": "gold"})
        else:
            player.message({"text": "No arguments specified. Try /help", "color": "red"})
            return

    def _rgcopy(self, *args):
        player = args[0]
        if SurestLib.permitted(player, "region.copy", self.usePermissions, self.useVanillaBehavior) is False:
            return
        result = self._normalizeSelection(player)
        if result == "Nosel":
            player.message("&bYou must select a region first! (use wooden axe or see help)")
            return
        if result == "badDim":
            player.message("&bSelection points are in different dimensions!")
            return
        p = self._getMemoryPlayer(player.username)
        if p["dim1"] != 0:
            player.message("&bSorry, but this command only functions in the overworld...")
            return
        curpos = player.getPosition()
        x = int(curpos[0]) + 1
        y = int(curpos[1])
        z = int(curpos[2]) + 1
        x1 = p["sel1"][0]
        y1 = p["sel1"][1]
        z1 = p["sel1"][2]
        x2 = p["sel2"][0]
        y2 = p["sel2"][1]
        z2 = p["sel2"][2]
        self.api.minecraft.console(
            "clone %d %d %d %d %d %d %d %d %d replace normal" % (x1, y1, z1, x2, y2, z2, x, y, z))

    # endregion

    # region //region subcommands
    def _rgdefine(self, player, args):
        if len(args) == 2:
            regionname = args[1]
            result = self._normalizeSelection(player, size_shape_override=True)
            if result == "Nosel":
                player.message("&bYou must select a region first! (use wooden axe or see help)")
                return
            if result == "badDim":
                player.message("&bSelection points are in different dimensions!")
                return
            if result is not True:
                player.message("&cThe selection is not valid because it is a %s." % result)
                return
            if args[1] in self.regions["regions"] and not player.isOp():  # op override to rewrite a region
                player.message("&cThat region name already exists, you cannot create it")
                return

            # This intentionally uses the username for the region if the user has permission to only create one (1).
            if not player.hasPermission("region.multiple"):
                regionname = player.username
                for region in self.regions["regions"]:
                    if self.regions["regions"][region]["ownerUuid"] == str(player.mojangUuid):
                        player.message("&cYou already own another region.  You don't have permission to make another.")
                        return
            if regionname in self.regions["regions"]:
                player.message("&cThis region is already defined.  You can't re-define it. &rtry EDIT instead.")
                return
            p = self._getMemoryPlayer(player.username)
            definedregion = self.rgdefine(regionname,
                                          str(player.mojangUuid),
                                          str(player.username),
                                          p["dim1"], p["sel1"], p["sel2"])

            player.message({"text": "Region ", "color": "gold", "extra": [
                {"text": definedregion, "color": "dark_purple"}, {"text": " created and selected!", "color": "gold"}]})

            return
        else:
            player.message("&bUsage '//rg define/select/create <regionname>'")
            return

    def _rgprotect(self, player, args):
        if len(args) == 2:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 3:
            name = args[1]
            prot = (args[2].lower())[0]

            for namex in self.regions["regions"]:
                if (prot == "f" or args[2].lower() == "off") and namex == name:
                    self.protection_off(name)
                    player.message("&cRegion protection OFF!")
                    return
                if (prot == "t" or prot == "o") and namex == name:
                    self.protection_on(name)
                    player.message("&bRegion protection ON!")
                    return
                if prot not in ("t", "f", "o"):  # due to order of processing, "o" will default to "on"
                    player.message("&bUsage //rg protect [regionname] '<TRUE|FALSE>")
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message("&bUsage '//rg protect <regionname> <True|False>'")
            return

    def _rg_resize(self, player, args):
        if len(args) != 2:
            player.message("&bUsage '//rg edit/resize <regionname>")
            player.message("&bNOTE!  This command REQUIRES the <regionname> and a new wand (pos1, pos2) selection!")
            return
        regionname = args[1]
        if regionname not in self.regions["regions"]:
            player.message("&cRegion %s is not defined!" % regionname)
            return
        result = self._normalizeSelection(player)
        if result == "Nosel":
            player.message("&bYou must select an area first! (use wooden axe or see help)")
            return
        if result == "singleblock":
            player.message("&bYou must select more than one block!")
            return
        if result == "badDim":
            player.message("&bSelection points are in different dimensions!")
            return
        p = self._getMemoryPlayer(player.username)
        # include code to validate intersecting regions??
        result = self.rgedit(regionname, edit_coords=True,
                             low_corner=p["sel1"], high_corner=p["sel2"])
        if result == regionname:
            player.message("&6Region edit made: New coords - %s  and  %s" % (str(p["sel1"]), str(p["sel2"])))

    def _rgroof(self, player, args):
        """
        roof and floor can be safely changed since it is only the y axis being adjusted.
        """
        if len(args) == 2:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 3:
            y = int(args[2])
            name = (args[1])
            if y < 0 or y > 256:
                player.message("&bUsage '//rg roof [regionname] <height>'  - number from 0-256")
                return
            for namex in self.regions["regions"]:
                if namex == name:
                    x = self.regions["regions"][name]["pos2"][0]
                    yfloor = self.regions["regions"][name]["pos1"][1]
                    z = self.regions["regions"][name]["pos2"][2]
                    if y <= yfloor:
                        player.message("&cYou can't lower the roof (%d) below the floor (%d)" % (y, yfloor))
                        return
                    new = (x, y, z)
                    self.regions["regions"][name]["pos2"] = new
                    p = self._getMemoryPlayer(player.username)
                    p["sel2"] = new
                    player.message("&6Roof changed to y=%d!" % y)
                    self.regions_storageobject.save()
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message("&bUsage '//rg roof [regionname] <height>'  - number from 0-256")
            return

    def _rgfloor(self, player, args):
        """
        roof and floor can be safely changed since it is only the y axis being adjusted.
        """
        if len(args) == 2:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 3:
            y = int(args[2])
            name = (args[1])
            if y < 0 or y > 256:
                player.message("&bUsage '//rg floor <height>'  - number from 0-256")
                return
            for namex in self.regions["regions"]:
                if namex == name:
                    x = self.regions["regions"][name]["pos1"][0]
                    yroof = self.regions["regions"][name]["pos2"][1]
                    z = self.regions["regions"][name]["pos1"][2]
                    if y >= yroof:
                        player.message("&cYou can't raise the floor (%d) above the roof (%d)" % (y, yroof))
                        return
                    new = (x, y, z)
                    self.regions["regions"][name]["pos1"] = new
                    p = self._getMemoryPlayer(player.username)
                    p["sel1"] = new
                    player.message("&6Floor changed to y=%d!" % y)
                    self.regions_storageobject.save()
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message("&bUsage '//rg floor [regionname] <height>'  - number from 0-256")
            return

    def _rgdelete(self, player, args):
        if len(args) == 2:
            name = (args[1])
            for namex in self.regions["regions"]:
                if namex == name:
                    if not player.hasPermission("region.delete"):
                        if not str(player.mojangUuid) == self.regions["regions"][namex]["ownerUuid"]:
                            player.message({"text": "Command not authorized for this region", "color": "Red"})
                            return
                    p = self._getMemoryPlayer(player.username)
                    if self.regions["regions"][name] == p["regusing"]:
                        p["regusing"] = None
                    if self.rgdelete(name):
                        player.message({"text": "Deleted Region ", "color": "gold", "extra": [
                            {"text": name, "color": "dark_purple"}, {"text": ".", "color": "gold"}]})
                    else:
                        player.message(
                            "&cThe region was not deleted!  Try again (there may be a duplicate named region")
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message("&bUsage '//rg remove <region>'")
            return

    def _rgsetflags(self, player, args):
        if len(args) == 3:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 4:
            targetuuid = SurestLib.makenamevalid(self, args[3], False, True)
            targetname = SurestLib.makenamevalid(self, args[3], False, False)
            for namex in self.regions["regions"]:
                if namex == args[1]:
                    if not player.hasPermission("region.setowner"):
                        if not str(player.mojangUuid) == self.regions["regions"][namex]["ownerUuid"]:
                            player.message(
                                {"text": "You don't have permission to set this region's owner.", "color": "Red"})
                            return
                    if args[2].lower() == "owner":
                        editregion = self.rgedit(namex, owner_uuid=targetuuid)
                        player.message(
                            {"text": "Region ", "color": "gold", "extra": [{"text": editregion, "color": "dark_purple"},
                                                                           {"text": " is now owned by ",
                                                                            "color": "gold"},
                                                                           {"text": targetname, "color": "dark_green"},
                                                                           {"text": ".", "color": "gold"}]})
                        return
                    if args[2].lower() in ("break", "canbreak"):
                        editregion = self.rgedit(namex, playername=targetname, addbreak_uuid=targetuuid)
                        player.message(
                            {"text": "Player ", "color": "gold", "extra": [{"text": targetname, "color": "dark_green"},
                                                                           {"text": " can now break blocks in region ",
                                                                            "color": "gold"},
                                                                           {"text": editregion, "color": "dark_purple"},
                                                                           {"text": ".", "color": "gold"}]})
                        return
                    if args[2].lower() in ("place", "canplace"):
                        editregion = self.rgedit(namex, playername=targetname, addplace_uuid=targetuuid)
                        player.message(
                            {"text": "Player ",
                             "color": "gold", "extra":
                                [{"text": targetname, "color": "dark_green"},
                                 {"text": " can now place blocks/operate stuff in region ",
                                  "color": "gold"}, {"text": editregion, "color": "dark_purple"},
                                 {"text": ".", "color": "gold"}]})
                        return
                    if args[2].lower() in ("access", "canaccess"):
                        editregion = self.rgedit(namex, playername=targetname, addaccess_uuid=targetuuid)
                        player.message(
                            {"text": "Player ",
                             "color": "gold", "extra":
                                [{"text": targetname, "color": "dark_green"},
                                 {"text": " can now eat and do things in region ",
                                  "color": "gold"}, {"text": editregion, "color": "dark_purple"},
                                 {"text": ".", "color": "gold"}]})
                        return
                    if args[2].lower() == "ban":
                        player.message("Feature not implemented yet...")
                        return
                    if args[2].lower() in ("rem", "remove"):
                        editregion = self.rgedit(namex, remove_uuid=targetuuid, unban_uuid=targetuuid)
                        player.message(
                            {"text": "Player ", "color": "gold", "extra":
                                [{"text": targetname, "color": "dark_green"},
                                 {"text": " removed from all region lists for region ", "color": "gold"},
                                 {"text": editregion, "color": "dark_purple"}, {"text": ".", "color": "gold"}]})
        else:
            player.message("&bUsage '//rg set [region] <owner|canbreak|canplace|canaccess|ban|remove> <player>'")
            player.message("'[region]' - defaults to region selected with '//rg use <region>'")
            player.message("'<owner>' - set new owner")
            player.message("'<canbreak/break>' - allow specified player to break.")
            player.message("'<canplace/place>' - allow player to place blocks.")
            player.message("'<canaccess/access>' - allow player operate things/eat/shoot/sleep, etc.")
            player.message("'<remove>' - remove player permissions from region.")
            player.message("'<ban>' - [not supported at this time...]")
            return

    def _rgdraw(self, player, args):
        if len(args) == 1:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 2:
            # //region draw [region]
            for namex in self.regions["regions"]:
                if namex == args[1]:
                    pos1 = self.regions["regions"][namex]["pos1"]
                    pos2 = self.regions["regions"][namex]["pos2"]
                    draw_dim = self.regions["regions"][namex]["dim"]
                    playerdim = player.getDimension()
                    if playerdim != draw_dim:
                        player.message("&cYou are not in the dimension where the region is located!")
                        return
                    player.message("&1Hold on, Lag may occur!!")
                    SurestLib.client_show_cube(player, pos1, pos2, sendblock=False)
                    player.message("&2Done!!")
        else:
            player.message("&bUsage '//rg draw [region] '")
            player.message("&bif you selected a region, you must define it first...")
            return

    def _rguse(self, player, args):
        if len(args) == 2:
            name = (args[1])
            for namex in self.regions["regions"]:
                if namex == name:
                    if not str(player.mojangUuid) == self.regions["regions"][namex]["ownerUuid"]:
                        player.message(
                            {"text": "WARNING: Region selected for use, but is not owned by you.", "color": "Red"})
                    p = self._getMemoryPlayer(player.username)
                    p["dim1"] = self.regions["regions"][namex]["dim"]
                    p["dim2"] = self.regions["regions"][namex]["dim"]
                    p["sel1"] = (self.regions["regions"][name]["pos1"])
                    p["sel2"] = (self.regions["regions"][name]["pos2"])
                    p["regusing"] = name
                    player.message({"text": "Using region ", "color": "gold",
                                    "extra": [{"text": name, "color": "dark_purple"}, {"text": ".", "color": "gold"}]})
                    self._normalizeSelection(player, printresult=True)
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message("&bUsage '//region use <region>'")
            return

    @staticmethod
    def _regionhelp(player):
        player.message("&bUsage '//rg set [region] <owner|canbreak|canplace|canaccess|ban> <player>'")
        pass

    """end //region subcommands"""
    # endregion

    # region PUBLIC SECTION

    def rgdefine(self, regionname, owner_uuid, ownername, dimension, low_corner, high_corner):
        """ create a region entry in regions file.  regionname, ownerUUID and ownername
        can be anything, based on the context.  Dimension and the two corners must be valid
        dimension number and coords."""
        self.regions["regions"][regionname] = {}
        self.regions["regions"][regionname]["ownerUuid"] = owner_uuid
        self.regions["regions"][regionname]["pos1"] = low_corner
        self.regions["regions"][regionname]["pos2"] = high_corner
        self.regions["regions"][regionname]["dim"] = dimension
        self.regions["regions"][regionname]["protected"] = False
        self.regions["regions"][regionname]["flgs"] = {}
        self.regions["regions"][regionname]["breakplayers"] = {}
        self.regions["regions"][regionname]["breakplayers"][owner_uuid] = ownername
        self.regions["regions"][regionname]["placeplayers"] = {}
        self.regions["regions"][regionname]["placeplayers"][owner_uuid] = ownername
        self.regions["regions"][regionname]["accessplayers"] = {}
        self.regions["regions"][regionname]["accessplayers"][owner_uuid] = ownername
        self.regions["regions"][regionname]["banplayers"] = {}
        return regionname

    def rgdelete(self, regionname):
        """
        unprotect and delete the specified region.
        """
        self.protection_off(regionname)
        del self.regions["regions"][regionname]
        if regionname in self.regions["regions"]:
            self.regions_storageobject.save()
            return False
        self.regions_storageobject.save()
        return True

    def rgedit(self, regionname, playername=False, edit_coords=False, low_corner=(0, 0, 0), high_corner=(0, 0, 0),
               addbreak_uuid=False, addplace_uuid=False, addaccess_uuid=False, remove_uuid=False,
               addban_uuid=False, unban_uuid=False, owner_uuid=False, flags=False):
        """
        Edit a region entry in regions file.  Regionname is required! Dimension and
        regionname changes cannot be done - the region must be deleted and re-created.
        Assign other portions to be edited as something other than False. ownerUUID,
        flags, corner, remove, and unban changes do not require a playername. All other
        player changes require the playername.
        lowcorner and highcorner need to be specified together.
        returns regionname if the region exists (and edits presumed to be made)
        """
        if regionname not in self.regions["regions"]:  # Make sure a properly defined region with this name exists.
            return
        # get current region size/position/status.
        protected = self.regions["regions"][regionname]["protected"]
        # turn off protection for editing.  resizing, etc, can affect what goes in the regionfile index lists
        if protected:
            self.protection_off(regionname)
        # edit applicable parameters
        if owner_uuid:
            self.regions["regions"][regionname]["ownerUuid"] = owner_uuid
        if edit_coords:
            lowcoord, highcoord = self.normalizeSelection(low_corner, high_corner)
            self.regions["regions"][regionname]["pos1"] = lowcoord
            self.regions["regions"][regionname]["pos2"] = highcoord
        if flags:
            self.regions["regions"][regionname]["flgs"] = flags
        if addbreak_uuid and playername:
            if addbreak_uuid not in self.regions["regions"][regionname]["breakplayers"]:
                self.regions["regions"][regionname]["breakplayers"][addbreak_uuid] = playername
        if addplace_uuid and playername:
            if addplace_uuid not in self.regions["regions"][regionname]["placeplayers"]:
                self.regions["regions"][regionname]["placeplayers"][addplace_uuid] = playername
        if addaccess_uuid and playername:
            if addaccess_uuid not in self.regions["regions"][regionname]["accessplayers"]:
                self.regions["regions"][regionname]["accessplayers"][addaccess_uuid] = playername
        if addban_uuid and playername:
            if addban_uuid not in self.regions["regions"][regionname]["banplayers"]:
                self.regions["regions"][regionname]["banplayers"][addban_uuid] = playername
        if remove_uuid:
            if remove_uuid in self.regions["regions"][regionname]["breakplayers"]:
                del self.regions["regions"][regionname]["breakplayers"][remove_uuid]
            if remove_uuid in self.regions["regions"][regionname]["placeplayers"]:
                del self.regions["regions"][regionname]["placeplayers"][remove_uuid]
            if remove_uuid in self.regions["regions"][regionname]["accessplayers"]:
                del self.regions["regions"][regionname]["accessplayers"][remove_uuid]
        if unban_uuid:
            if unban_uuid in self.regions["regions"][regionname]["banplayers"]:
                del self.regions["regions"][regionname]["banplayers"][unban_uuid]
        self.regions_storageobject.save()
        if protected:
            self.protection_on(regionname)
        return regionname

    def protection_on(self, region_name):
        """basic steps to protect region:
        1) calculate the regions overlapping the claim
        2) see if those regions exist in the list of regions containing protected areas
        3) add the region to the list of regions if needed.
        4) add this regionname to the file for that region"""
        if region_name not in self.regions["regions"]:
            self.log.error("protection for non-existent region %s was attempted." % region_name)
            return
        prot_dim = self.regions["regions"][region_name]["dim"]
        lowcoords = self.regions["regions"][region_name]["pos1"]
        highcoords = self.regions["regions"][region_name]["pos2"]
        regionfilelist = self.getregionlist(prot_dim, lowcoords, highcoords)  # find regions covered by coords
        for regionfile in regionfilelist:
            if regionfile in self.regiondirectory["files"]:  # if region "file" already exists
                if region_name not in self.regiondirectory["files"][regionfile]:  # only append it if not already there
                    self.regiondirectory["files"][regionfile].append(region_name)  # append regionname into the rgfile
                    self.regions["regions"][region_name]["protected"] = True
            else:
                self.regiondirectory["files"][regionfile] = []
                self.regiondirectory["files"][regionfile].append(region_name)
                self.regions["regions"][region_name]["protected"] = True
        self.regiondirectory_storageobject.save()
        self.regions_storageobject.save()

    def protection_off(self, region_name):
        """basic steps to unprotect region:
        1) calculate the regions (*.mca files) the claim overlaps
        2) remove the regionname from that regionfile list.
        3) if the list is now empty, delete the list too."""
        if region_name not in self.regions["regions"]:
            self.log.error("un-protect for non-existent region %s was attempted." % region_name)
            return
        prot_dim = self.regions["regions"][region_name]["dim"]
        lowcoords = self.regions["regions"][region_name]["pos1"]
        highcoords = self.regions["regions"][region_name]["pos2"]
        regionfilelist = self.getregionlist(prot_dim, lowcoords, highcoords)
        for regionfile in regionfilelist:  # list of "possible" regions to check
            if regionfile in self.regiondirectory["files"]:  # if region "file" already exists
                if region_name in self.regiondirectory["files"][regionfile]:
                    self.regiondirectory["files"][regionfile].remove(region_name)  # remove regionname from regionfile
                self.regions["regions"][region_name]["protected"] = False
                if len(self.regiondirectory["files"][regionfile]) < 1:  # then regionnames have been removed from file
                    del self.regiondirectory["files"][regionfile]  # so delete the region file from file list
        self.regiondirectory_storageobject.save()
        self.regions_storageobject.save()

    def regionname(self, position, dim):
        global_regions = "%s__global__" % dim
        action_region = "%s_%s" % (dim, SurestLib.getregionnumber(position[0], position[2]))
        if action_region in self.regiondirectory["files"]:  # if region has protected items/regionnames
            for regionnames in self.regiondirectory["files"][action_region]:  # look at what regionnames are listed
                if regionnames in self.regions["regions"]:
                    if self._blocks_match(regionnames, position):
                        return str(regionnames)
        if global_regions in self.regiondirectory["files"]:
            for regionnames in self.regiondirectory["files"][global_regions]:  # see what global regions are listed
                if regionnames in self.regions["regions"]:
                    if self._blocks_match(regionnames, position):
                        return str(regionnames)
        return False

    def getregioninfo(self, regionname, infokey):
        if regionname in self.regions["regions"]:
            if infokey in self.regions["regions"][regionname]:
                return self.regions["regions"][regionname][infokey]
        self.log.error("bad region/key - %s %s" % (regionname, infokey))
        return False

    def intersecting_regions(self, dim, sel1coords, sel2coords, rect=False):
        """
        :param dim: - used only for search process.  It is assumed to be same as supplied coords!
        :param sel1coords: Coords tuple (Must use all three coords, even if rect=True!)
        :param sel2coords: Coords tuple (Must use all three coords, even if rect=True!)
        :param rect: default is cubical
        :return: a list of intersecting regions (or None)
        """
        matchingregions = []
        searchregions = []
        lowcoord, highcoord = self.normalizeSelection(sel1coords, sel2coords)
        # get list of possible regions covered by this area
        area_regions = self.getregionlist(dim, lowcoord, highcoord)
        # find out which ones have claims/regions
        if "%s__global__" % dim in self.regiondirectory["files"]:
            filelist = ["%s__global__" % dim]
        else:
            filelist = []
        for region in area_regions:
            if region in self.regiondirectory["files"]:  # if a region "file" exists in protected mode
                filelist.append(region)  # append region into the protectionlist
        # get the names of the claims/regions in those various region.mca's
        for eachregionfile in filelist:
            for eachclaim in self.regiondirectory["files"][eachregionfile]:
                searchregions.append(eachclaim)
        # search this group of region definitions for matches/overlaps
        for regions in searchregions:
            regionname = str(regions)
            if regionname not in self.regions["regions"]:
                continue
            cube1 = (self.regions["regions"][regionname]["pos1"], self.regions["regions"][regionname]["pos2"])
            if rect is True:
                if self._areas_overlap_rect(cube1, (lowcoord, highcoord)):
                    matchingregions.append(regionname)
            else:
                if self._areas_overlap_cube(cube1, (lowcoord, highcoord)):
                    matchingregions.append(regionname)
        if len(matchingregions) < 1:
            return None
        return matchingregions

    @staticmethod
    def normalizeSelection(coords1, coords2):
        """
        takes two 3-axis coordinate tuples, interprets these coordinates as two
        opposing corners of a cube.  It then determines which of the cubes 2 corners
        represent the lowest and highest of all three axes and returns
        them in that order.
        :param coords1: any x,y,z corner of a cube
        :param coords2: the opposite corner x, y, z
        :return: lowest x,y,z corner, highest x,y,z corner
        """
        lowx = x1 = int(coords1[0])
        lowy = y1 = int(coords1[1])
        lowz = z1 = int(coords1[2])
        hix = x2 = int(coords2[0])
        hiy = y2 = int(coords2[1])
        hiz = z2 = int(coords2[2])
        # get low and high corners
        if x1 <= x2:
            lowx = x1
        if x1 > x2:
            lowx = x2
        if y1 <= y2:
            lowy = y1
        if y1 > y2:
            lowy = y2
        if z1 <= z2:
            lowz = z1
        if z1 > z2:
            lowz = z2
        if x1 >= x2:
            hix = x1
        if x1 < x2:
            hix = x2
        if y1 >= y2:
            hiy = y1
        if y1 < y2:
            hiy = y2
        if z1 >= z2:
            hiz = z1
        if z1 < z2:
            hiz = z2
        lowcoords = (lowx, lowy, lowz)
        highcoords = (hix, hiy, hiz)
        return lowcoords, highcoords

    @staticmethod
    def getregionlist(prot_dim, lowcoords, highcoords):
        """
        Calculate the regions ("x.y.z.mca" files) overlapped by the area
        represented by lowcoords - highcoords.  If the potential exists to
        span more than 4 regions (> 513 blocks wide), then the regionnamed
        area is assigned not to specific region, but "%d__global__" % prot_dim.
        :param prot_dim: The dimension where the region is located
        :param lowcoords: lowest northwest corner (lowest coord on all 3 axes)
        :param highcoords: Upper southeast corner (highest coord on all 3 axes)
        :return: A list of region files (i.e. "r.1.0.mca") covered by the area,
        prefixed by D_ (where D is the dimension).
        """
        filelist = []
        lowx = lowcoords[0]
        lowz = lowcoords[2]
        highx = highcoords[0]
        highz = highcoords[2]
        if highx - lowx > 513 or highz - lowz > 513:
            filelist.append("%s__global__" % prot_dim)  # covers large areas that could span > 2 regions width/height
            return filelist
        rgfilea = "%s_%s" % (prot_dim, SurestLib.getregionnumber(lowx, lowz))
        rgfileb = "%s_%s" % (prot_dim, SurestLib.getregionnumber(highx, lowz))
        rgfilec = "%s_%s" % (prot_dim, SurestLib.getregionnumber(highx, highz))
        rgfiled = "%s_%s" % (prot_dim, SurestLib.getregionnumber(lowx, highz))
        filelist.append(rgfilea)
        if rgfilea != rgfileb:
            filelist.append(rgfileb)
        if rgfilea != rgfilec:
            filelist.append(rgfilec)
        if rgfilea != rgfiled:
            filelist.append(rgfiled)
        return filelist
        # pass

    """ end PUBLIC SECTION"""
    # endregion
