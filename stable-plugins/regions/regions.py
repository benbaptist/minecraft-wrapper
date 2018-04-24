# coding=utf-8

import math
import threading
import time

from proxy.utils.constants import *

from sys import version_info
PY3 = version_info > (3,)

if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range

NAME = "Regions"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.regions"
VERSION = (1, 3, 1)
SUMMARY = "World regions editing and protection."
WEBSITE = "" 
DESCRIPTION = """
Regions is the back end implementation that takes care of the 'low-level'
implementation of the regions package; stuff like creation and 
maintenance of region data.  Regions also implements the actual process
of protecting the region from unauthorized player activity. It is 
intended to be implemented as the backend for other higher level, player 
friendly type plugins similar to bukkit GriefPrevention.
"""

# These just make the code more readable
BEDROCK = 7
BEACON = 138
TNT = 46


# The specific errors we need not worry about in the plugin API:
# noinspection PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyPep8Naming,PyClassicStyleClass,PyAttributeOutsideInit
class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log
        self.players = {}
        self.version = float("%d.%d" % (VERSION[0], VERSION[1]))

        # enable position tracking (disable if you have lag)
        # tracks players positions for back commands and region bans
        self.pos_tracking = True

        # whether TNT/item controls are active:
        self.itemcontrols = True

        # if tnt is specifically limited
        self.tntlimited = self.itemcontrols and True

        # whether a player can have TNT in a claim
        # change to `... and True` to allow TNT in claim
        self.tntinclaim = self.tntlimited and False
        # above this, TNT is not allowed, unless player is in their own region.
        self.tntlevel = 20

    def onEnable(self):
        try:
            wr = self.api.wrapper_version
        except AttributeError:
            wr = [0, 0, 0, None]
        numbervers = wr[0] * 10000 + wr[1] * 100 + wr[2]
        if numbervers < 10006:
            self.log.error(
                "Regions.py cannot run under this wrapper version. "
                "Regions is not enabled!"
            )
            return False

        # Storage:
        self.rgs_file_storage = self.api.getStorage(
            "files", False, pickle=True
        )
        self.rgs_region_storage = self.api.getStorage(
            "regions", False, pickle=True
        )

        # Storage Data:
        self.rg_files = self.rgs_file_storage.Data
        self.rg_regions = self.rgs_region_storage.Data

        # get packetset once server is started
        self.api.registerEvent("server.started", self._getpackets)

        self.api.registerEvent("player.dig", self._action_playerdig)
        self.api.registerEvent("player.place", self._action_playerplace)
        self.api.registerEvent("player.interact", self._action_playerinteract)

        # _restoreworld parameters
        self.run = True
        self.clicks_queue = []
        self.lastmessage = {}
        rw = threading.Thread(target=self._restoreworld,
                              name="restores", args=())
        rw.daemon = True
        rw.start()

        if self.pos_tracking:
            self.spawn = self.api.minecraft.getSpawnPoint()
            # player pos tracker
            self.movement_walk = 6
            self.movement_numbers = 10
            self.movement_tp = 100
            tr = threading.Thread(target=self._pos_tracker,
                                  name="tracker", args=())
            tr.daemon = True
            tr.start()

    def onDisable(self):
        self.run = False
        self.rgs_file_storage.close()
        self.rgs_region_storage.close()

    def _getpackets(self, payload):
        # proxy needs to start first..
        time.sleep(2)
        self.pkts_sb = self.api.minecraft.getServerPackets(packetset="SB")
        self.pkts_cb = self.api.minecraft.getServerPackets()

    def _pos_tracker(self):
        """Position tracker is also a global thread working with all player
         clients, so it must use the try-except clauses.  If it fails
         because one of the clients logs out, etc, the entire thread will
         fail to perform its job."""
        locs = {}
        while self.run:
            time.sleep(1)
            players = self.api.minecraft.getPlayers()
            for each in players:
                player = self.api.minecraft.getPlayer(each)

                try:
                    gm = player.getGamemode()
                    dim = player.getDimension()
                    uuid = player.uuid
                except AttributeError:
                    self.log.debug(
                        "region POS_tracker bad payload - missing GM or dim"
                    )
                    continue
                l_pos = player.getPosition()
                present_pos = int(l_pos[0]), int(l_pos[1]), int(l_pos[2]), dim
                if uuid not in locs:
                    locs[uuid] = {}
                    locs[uuid]["track"] = [present_pos, ]
                    locs[uuid]["back"] = present_pos
                    continue
                pos_triple = int(l_pos[0]), int(l_pos[1]), int(l_pos[2])
                if self._banned_from_area(gm, pos_triple, dim, player):
                    try:
                        # prime number of positions backwards from entering
                        new_pos = locs[uuid]["track"][-17]
                    except IndexError:
                        new_pos = self.spawn

                    self.api.minecraft.console(
                        "spreadplayers %s %s 1 2 false %s" % (
                            new_pos[0], new_pos[2], player.username)
                    )
                    continue
                if self._signif_move(
                        locs[uuid]["track"][-1],
                        present_pos,
                        self.movement_tp
                ):
                    locs[uuid]["back"] = locs[uuid]["track"][-1]
                if self._signif_move(
                        locs[uuid]["track"][-1],
                        present_pos,
                        self.movement_walk
                ):
                    locs[uuid]["track"].append(present_pos)
                    while len(locs[uuid]["track"]) > self.movement_numbers:  # noqa
                        locs[uuid]["track"].pop(0)

    def _banned_from_area(self, gamemode, pos, dim, player):
        if gamemode in (0, 2):
            activeregion = self.regionname(pos, dim)
            if activeregion:
                # if block/region not protected mode
                if not self.rg_regions[activeregion]["protected"]:
                    return True
                return player.uuid in (
                    self.rg_regions[activeregion]["banplayers"])

    def _restoreworld(self):
        """
        action | player | position

        Restore world is global thread that handles all player clients, so
        it must use the try-except clauses.  If it fails because one of the
        clients logs out, etc, the entire thread will fail to perform its job.
        """

        while self.run:
            time.sleep(.5)
            while len(self.clicks_queue) > 0:
                # grab next change
                action_tuple = self.clicks_queue.pop(0)
                action, player, position = action_tuple
                status = 1  # canceled digging
                face = 1
                if action == "break":
                    # get the original block to display
                    try:
                        # These must run in a try-except.  If it fails because
                        # one of the clients logged out, etc, the entire thread
                        # will fail to perform its job.
                        player.client.server_connection.packet.sendpkt(
                            self.pkts_sb.PLAYER_DIGGING[PKT],
                            [BYTE, POSITION, BYTE],
                            (status, position, face)
                        )
                    except AttributeError:
                        continue

                elif action == "place":
                    # get the original block to display
                    face_places = [(status, position, face)]
                    p = position
                    face_places.append((status, (p[0] - 1, p[1], p[2]), face))
                    face_places.append((status, (p[0] + 1, p[1], p[2]), face))
                    face_places.append((status, (p[0], p[1] - 1, p[2]), face))
                    face_places.append((status, (p[0], p[1] + 1, p[2]), face))
                    face_places.append((status, (p[0], p[1], p[2] - 1), face))
                    face_places.append((status, (p[0], p[1], p[2] + 1), face))

                    for places in face_places:
                        try:
                            player.client.server_connection.packet.sendpkt(
                                self.pkts_sb.PLAYER_DIGGING[PKT],
                                [BYTE, POSITION, BYTE],
                                places
                            )
                        except AttributeError:
                            continue
                    try:
                        for slots in player.client.inventory:
                                player.client.packet.sendpkt(
                                    self.pkts_cb.SET_SLOT[PKT],
                                    self.pkts_cb.SET_SLOT[PARSER],
                                    (0, slots, player.client.inventory[slots])
                                )
                    except AttributeError:
                        continue

    def _act_on_break(self, player, position, region):
        if player.uuid not in self.lastmessage:
            self.lastmessage[player.uuid] = time.time() - 10
        if time.time() - self.lastmessage[player.uuid] > 5:
            player.message(
                "&dSorry, you are not allowed to break things in "
                "region &6%s!" % region, 2
            )
            self.lastmessage[player.uuid] = time.time()
        player.sendBlock(position, 7, 0)
        self.clicks_queue.append(("break", player, position))

    def _act_on_place(self, player, position, region):
        if player.uuid not in self.lastmessage:
            self.lastmessage[player.uuid] = time.time() - 10
        if time.time() - self.lastmessage[player.uuid] > 5:
            player.message(
                "&dNo permission to do that in region &6%s" % region, 2
            )
            self.lastmessage[player.uuid] = time.time()

        # send air
        player.sendBlock(position, 0, 0)
        # send a barrier particle
        player.sendBlock(position, 35, 0, sendblock=False)
        self.clicks_queue.append(("place", player, position))

    def _action_playerdig(self, payload):
        """
        player break block / digging - Face (payload["face"]) 
        is the side of block being clicked.
        payloads {"player": self.getPlayerObject(), 
                  "position": position,
                  "action": "end_break/begin_break",
                  "face": data["face"]
        }
        """
        try:
            player = payload["player"]
            gamemode = player.getGamemode()
            dim = player.getDimension()
            position = payload["position"]
            try:
                itemid = player.getHeldItem()["id"]
            except TypeError:
                itemid = -1
        except AttributeError:
            self.log.debug(
                "region playerdig bad payload - Payload:\n%s" % (
                    str(payload)
                )
            )
            # bad player object - usually means player disconnected.
            return False

        if itemid == 271:
            action = payload["action"]
            p = self.get_memory_player(player.username)
            if p["wand"] and (
                    ((action == "end_break") and (gamemode == 1)) or (
                    (action == "begin_break") and (gamemode == 0))):
                p["sel1"] = position
                p["dim1"] = dim
                player.sendBlock(position, BEACON, 0)
                player.message(
                    "&dPoint one selected. (%d %d %d)" % (
                        position[0], position[1], position[2])
                )
                if p["regusing"] is not None:
                    player.message(
                        "&cYou were using region '%s'.  You are now "
                        "selecting a new area." % p["regusing"]
                    )
                p["regusing"] = None
                return False

        # creative and spectator ignore protections
        if gamemode in (1, 3):
            return True

        activeregion = self.regionname(position, dim)
        if activeregion:
            # if block/region not protected mode
            if self.rg_regions[activeregion]["protected"]:
                return self._whenmatchingcoordsbreak(
                    player, position, activeregion
                )

        # If nothing matches, land is free...
        return True

    def _action_playerplace(self, payload):
        """
        Player.place is the calculated location of a block to be placed 
        based on the "face" value.  This means that wrapper creates 
        two events from the same client action...  A right click (by 
        default).  One event is the actual block that was clicked 
        on (player.interact) and the location a placed block will 
        appear (player.place). player.place is a handy event for 'Wand' 
        use on pos2 because, even though inaccurate for selection (it
        selects the adjoining block), the fake blocks can be used to 
        build a virtual structure away into air blocks to select air 
        blocks that are otherwise "unclickable".
        """

        try:
            player = payload["player"]
            gamemode = player.getGamemode()
            dim = player.getDimension()
            position = payload["position"]
            try:
                itemid = payload["item"]["id"]
            except AttributeError:
                itemid = -1
        except AttributeError:
            self.log.debug(
                "region playerplace bad payload - Payload:\n%s" % (
                    str(payload)
                )
            )
            # bad player object - usually means player disconnected.
            return False

        # selection pos 2
        if itemid == 271:
            p = self.get_memory_player(player.username)
            if p["wand"]:
                p["dim2"] = dim
                p["sel2"] = position
                # send fake block
                player.sendBlock(position, BEACON, 0)
                player.message(
                    "&dPoint two selected. (%d %d %d)" % (
                        position[0], position[1], position[2]
                    )
                )
                if p["regusing"] is not None:
                    player.message(
                        "&cYou were using region '%s'.  You are now "
                        "selecting a new area." % (p["regusing"])
                    )
                p["regusing"] = None
                return False

        # creative and spectator ignore protections
        if gamemode in (1, 3):
            return True

        # generic TNT controls for all events - These only catch when
        #  item is not allowed even in claim
        if itemid == TNT and not self.tntinclaim:
            if position[1] > self.tntlevel:
                player.message(
                    "&dNo TNT ever allowed above y=%d..." % self.tntlevel
                )
                return False

        # cancel interactions in protected regions

        activeregion = self.regionname(position, dim)
        if activeregion:
            # if block/region not protected mode
            if self.rg_regions[activeregion]["protected"]:
                return self._whenmatchingcoordsplace(
                    player, position, activeregion, itemid
                )

        # TNT controls for all events - for all events outside of a claim.
        # if it is a claim, code never reaches this (already returned True...)
        if itemid == TNT and self.tntlimited and (
                position[1] > self.tntlevel):
            player.message(
                "&dNo TNT allowed above y=%d..." % self.tntlevel
            )
            return False

        # If nothing matches, land is free...
        return True

    def _action_playerinteract(self, payload):
        """
        Player interact prevents switch operations at the claims
        borders (player.place allows it).  This should prevent lava
        and water grief inside a claim, if the user takes
        precautions to keep their borders secure...
        """
        try:
            player = payload["player"]
            gamemode = int(player.getGamemode())
            dim = int(player.getDimension())
            position = payload["position"]
        # Bad player object, usually.
        except AttributeError:
            self.api.log("bad payload - missing Dim, GM, or POS")
            self.log.debug(
                "region player interaction bad payload - Payload:\n%s" % (
                    str(payload)
                )
            )
            return False

        # creative and spectator ignore protections
        if gamemode in (1, 3):
            return True

        activeregion = self.regionname(position, dim)
        if activeregion:
            # if block/region not protected mode
            if not self.rg_regions[activeregion]["protected"]:
                return self._whenmatchingcoordsinteract(
                    player, position, activeregion
                )

        # If nothing matches, land is free...
        return True

    def rgdefine(self, regionname: str, owneruuid: str, dimension: int,
                 low_corner: tuple, high_corner: tuple):
        """
        Create a region entry in regions file. Protection is off and
        no additional players are added by default.
        
        :param regionname: Unique region name
        :param owneruuid: the uuid of the owner/admininstrator of region
        :param dimension: dimension
        :param low_corner: coordinates (x, y, x) of lowest corner.
        :param high_corner: coordinates (x, y, x) of highest corner.
        
        :return: region's name if success, None if region already exists.
        """
        playername = self.api.minecraft.lookupbyUUID(owneruuid)
        if regionname not in self.rg_regions:
            self.rg_regions[regionname] = {}
            self.rg_regions[regionname]["ownerUuid"] = owneruuid
            self.rg_regions[regionname]["pos1"] = low_corner
            self.rg_regions[regionname]["pos2"] = high_corner
            self.rg_regions[regionname]["dim"] = dimension
            self.rg_regions[regionname]["protected"] = False
            self.rg_regions[regionname]["flgs"] = {}
            self.rg_regions[regionname]["breakplayers"] = {}
            self.rg_regions[regionname]["placeplayers"] = {}
            self.rg_regions[regionname]["accessplayers"] = {}
            self.rg_regions[regionname]["banplayers"] = {}
            return regionname
        self.log.debug("Region '%s' already exists." % regionname)

    def rgdelete(self, region_name: str):
        """
        delete the specified region.

        :param region_name: Region name

        """

        if region_name not in self.rg_regions:
            self.log.debug(
                "deletion of non-existent region %s was attempted.  Purging "
                "that reference from region files list to be safe"
                "..." % region_name
            )
            self._purge_name_outoffiles(region_name)
            
            return False
        dim = self.getregioninfo(region_name, "dim")
        low_coords = self.getregioninfo(region_name, "pos1")
        hi_coords = self.getregioninfo(region_name, "pos1")

        applicable_files = self.getregionlist(dim, low_coords, hi_coords)
        for each_file in applicable_files:
            self._delete_name_fromfiles(region_name, each_file)

        del self.rg_regions[region_name]
        self.rgs_file_storage.save()
        self.rgs_region_storage.save()
        return True

    def getregioninfo(self, regionname: str, infokey: str):
        """
        Get a specific piece of keyed information from a region.

        :param regionname:
        :param infokey:  One of the valid keys.
            :valid keys:
                All player type keys (except ownerUuid) contain a list of
                player uuids.
                --------------
                `pos1` - lower northwest corner (lowest x,y,z)
                `pos2` - upper southeast corner
                `dim` - The dimension, of course...
                `ownerUuid` - uuid of region's owner.
                `protected` - whether the region is protected.
                 `flgs` (unused)
                `breakplayers` - players that can break blocks.
                `placeplayers` - players that can place blocks.
                `accessplayers` - operate switches, buckets, open chests, etc.
                `banplayers` - players on this list get TP-ed out of the region.

        :return:
        """
        try:
            return self.rg_regions[regionname][infokey]
        except KeyError:
            self.log.debug("bad region/key - %s %s" % (regionname, infokey))
            return False

    def getregionlist(self, prot_dim, lowcoords, highcoords):
        """
        Calculate the regions ("x.y.z.mca" files) overlapped by the area
        represented by lowcoords - highcoords and return a list of region
        files that overlap the area.

         **internal working limitation** If the potential exists to
        span more than 4 regions (> 513 blocks wide), then the regionnamed
        area is assigned not to a specific region in the region files, but
        to the "%d__global__" % dim file (files are located in files.json/pkl.

        :param prot_dim: The dimension where the region is located
        :param lowcoords: lowest northwest corner (lowest coord on all 3 axes)
        :param highcoords: Upper southeast corner (highest coord on all 3 axes)
        :return: A list of region files (i.e. "r.1.0.mca") covered by the area,
        prefixed by D_ (where D is the dimension).
        """
        filelist = []

        lowxregion = self.chunk2region(self.coord2chunk(lowcoords[0]))
        lowzregion = self.chunk2region(self.coord2chunk(lowcoords[2]))

        highxregion = self.chunk2region(self.coord2chunk(highcoords[0]))
        highzregion = self.chunk2region(self.coord2chunk(highcoords[2]))

        # optimized for python 3 (python 2 will run slow)
        # +1 because that must include highxregion in range
        for x_region in xrange(lowxregion, highxregion + 1, 1):  
            for z_region in xrange(lowzregion, highzregion + 1, 1):
                filelist.append(
                    "%d_r.%d.%d.mca" % (prot_dim, x_region, z_region))
        return filelist

    def getchunknumber2d(self, x, z):
        """Get chunk number as x.z from coords x, z
        :param x coord
        :param z coord
        """
        xchunk = self.coord2chunk(x)
        zchunk = self.coord2chunk(z)
        return "%d.%d" % (xchunk, zchunk)
    
    def getchunk3d(self, x, y, z):
        """Get actaul 3D chunk tuple from coords
        :param x coord
        :param y coord
        :param z coord
        """
        xchunk = self.coord2chunk(x)
        ychunk = self.coord2chunk(y)
        zchunk = self.coord2chunk(z)
        return xchunk, ychunk, zchunk

    def getregionfilename(self, x: int, z: int):
        """Get region filename from Coords x,
        :param x coord
        :param z coord
        """
        xregion = self.chunk2region(self.coord2chunk(x))
        zregion = self.chunk2region(self.coord2chunk(z))
        return "r.%d.%d.mca" % (xregion, zregion)

    def regionname(self, position: tuple, dim: int):
        """
        Return the name of the region where this position and
        dimension are.  Return False if not located in a region.
        :param position: (x, y, z) coords
        :param dim: dimension

        """
        action_region = "%s_%s" % (
            dim, self.getregionfilename(position[0], position[2])
        )
        # if region has protected items/regionnames
        if action_region in self.rg_files:
            # look at what regionnames are listed
            for region_name in self.rg_files[action_region]:
                if region_name in self.rg_regions:
                    if self._blocks_match(region_name, position):
                        return str(region_name)
        return False

    def intersecting_regions(self, dim: int,
                             sel1coords: tuple, sel2coords: tuple,
                             rect=False):
        """
        This method is used to check if a prospective cube or area intersects
        with any existing regions.

        :param dim: - both supplied coords are assumed in same dimension!
        :param sel1coords: Coords tuple (Must use (x, y, z), even if rect=True!)
        :param sel2coords: Coords tuple (Must use (x, y, z), even if rect=True!)
        :param rect: default is cubical

        :return: a list of intersecting regions (or None if none found)
        """
        matchingregions = []
        region_claims = []
        lowcoord, highcoord = self.stat_normalize_selection(
            sel1coords, sel2coords
        )
        # get list of possible regions covered by this area
        area_regions = self.getregionlist(dim, lowcoord, highcoord)

        # find out which ones have claims/regions

        # Allow each dim to have a global region.  Usually this would enforce
        #  a build height in the nether or something...
        if "%s__global__" % dim in self.rg_files:
            filelist = ["%s__global__" % dim]
        else:
            filelist = []

        for region in area_regions:
            # if a region "file" exists
            if region in self.rg_files:
                # append region into the filelist
                filelist.append(region)

        # get the names of the claims/regions in those various region.mca's
        for eachregionfile in filelist:
            for eachclaim in self.rg_files[eachregionfile]:
                region_claims.append(eachclaim)

        # search this group of region definitions for matches/overlaps
        for each_claim in region_claims:
            regionname = str(each_claim)
            if regionname not in self.rg_regions:
                continue
            cube1 = (
                self.rg_regions[regionname]["pos1"],
                self.rg_regions[regionname]["pos2"]
            )
            if rect is True:
                if self._areas_overlap_rect(cube1, (lowcoord, highcoord)):
                    matchingregions.append(regionname)
            else:
                if self._areas_overlap_cube(cube1, (lowcoord, highcoord)):
                    matchingregions.append(regionname)
        if len(matchingregions) > 0:
            return matchingregions

    def rgedit(self, regionname: str, playername=False,
               new_owner_name=False, flags=False,
               edit_coords=False, low_corner=(0, 0, 0), high_corner=(0, 0, 0),
               addbreak=False, addplace=False, addaccess=False, addban=False,
               remove=False, unban=False):
        """
        Edit a region entry in regions file.  Regionname is required!
        Dimension and regionname changes cannot be done - the region
        must be deleted and re-created.

        :param regionname: Name of the region
        :param new_owner_name: Specify a new owner.
        :param flags: (TODO not implemented)

        :param edit_coords: If true, use next two args to edit the region
         boundaries.
        :param low_corner:
        :param high_corner:

        :param playername: Playername - Used for the following;
        :param addbreak: - Playername can break blocks.
        :param addplace:  - Playername can place blocks.
        :param addaccess:  - Playername can access controls/chests, etc.
        :param addban: Ban playername from this region.
        :param remove: Remove access to region (owner still has access always).
        :param unban: Un ban player name
        :returns: regionname if the region exists (and edits presumed
         to be made).  False if region does not exist.  Nothing is likely
         if another falure occured.

        """
        # Make sure a properly defined region with this name exists.
        if regionname not in self.rg_regions:
            return False
        # get current region size/position/status.
        protected = self.rg_regions[regionname]["protected"]
        # turn off protection for editing.  resizing, etc, can affect
        #  what goes in the regionfile index lists
        if protected:
            self.protection_off(regionname)
        time.sleep(.1)
        _region = self.rg_regions[regionname]
        # edit applicable parameters
        if new_owner_name:
            new_uuid = self.api.minecraft.lookupbyName(playername).string
            _region["ownerUuid"] = new_uuid
        if edit_coords:
            lowcoord, highcoord = self.stat_normalize_selection(
                low_corner, high_corner
            )
            _region["pos1"] = lowcoord
            _region["pos2"] = highcoord
        if flags:
            _region["flgs"] = flags

        if playername:
            playeruuid = self.api.minecraft.lookupbyName(playername).string

            if addbreak:
                if playeruuid not in _region["breakplayers"]:
                    _region["breakplayers"][playeruuid] = playername
            if addplace:
                if playeruuid not in _region["placeplayers"]:
                    _region["placeplayers"][playeruuid] = playername
            if addaccess:
                if playeruuid not in _region["accessplayers"]:
                    _region["accessplayers"][playeruuid] = playername
            if addban:
                if playeruuid not in _region["banplayers"]:
                    _region["banplayers"][playeruuid] = playername

            if remove:
                if playeruuid in _region["breakplayers"]:
                    del _region["breakplayers"][playeruuid]
                if playeruuid in _region["placeplayers"]:
                    del _region["placeplayers"][playeruuid]
                if playeruuid in _region["accessplayers"]:
                    del _region["accessplayers"][playeruuid]

            if unban:
                if playeruuid in _region["banplayers"]:
                    del _region["banplayers"][playeruuid]
        self.rgs_region_storage.save()

        if protected:
            self.protection_on(regionname)
        return regionname

    def protection_on(self, region_name):
        """basic steps to protect region:
        1) calculate the regions overlapping the claim
        2) see if those regions exist in the list of regions containing
           protected areas
        3) add the region to the list of regions if needed.
        4) add this regionname to the file for that region
           :returns True if success.
        """
        if region_name not in self.rg_regions:
            self.log.error(
                "protection for non-existent region %s was "
                "attempted." % region_name
            )
            return
        prot_dim = self.rg_regions[region_name]["dim"]
        lowcoords = self.rg_regions[region_name]["pos1"]
        highcoords = self.rg_regions[region_name]["pos2"]
        # get list of possible regions covered by this area ("D_r.1.0.mca"
        regionfilelist = self.getregionlist(prot_dim, lowcoords,
                                            highcoords)
        for regionfile in regionfilelist:
            # if region "file" already exists
            if regionfile in self.rg_files:
                # only append it if not already there
                if region_name not in self.rg_files[regionfile]:
                    # append regionname into the rgfile
                    self.rg_files[regionfile].append(region_name)
                    self.rg_regions[region_name]["protected"] = True
            else:
                self.rg_files[regionfile] = []
                self.rg_files[regionfile].append(region_name)
                self.rg_regions[region_name]["protected"] = True
        self.rgs_region_storage.save()
        return self.rg_regions[region_name]["protected"]

    def protection_off(self, region_name):
        """basic steps to unprotect region:
        1) calculate the regions (*.mca files) the claim overlaps
        2) remove the regionname from that regionfile list.
        3) if the list is now empty, delete the list too.
        :returns True if success.
        """

        if region_name not in self.rg_regions:
            self.log.error(
                "un-protect for non-existent region %s was "
                "attempted." % region_name
            )
            return

        prot_dim = self.rg_regions[region_name]["dim"]
        lowcoords = self.rg_regions[region_name]["pos1"]
        highcoords = self.rg_regions[region_name]["pos2"]
        regionfilelist = self.getregionlist(prot_dim, lowcoords, highcoords)
        # list of "possible" regions to check
        for regionfile in regionfilelist:
            # if region "file" already exists
            if regionfile in self.rg_files:
                if region_name in self.rg_files[regionfile]:
                    # remove regionname from regionfile
                    self.rg_files[regionfile].remove(region_name)
                    self.rg_regions[region_name]["protected"] = False
                # then regionnames have been removed from file
                if len(self.rg_files[regionfile]) < 1:
                    # so delete the region file from file list
                    del self.rg_files[regionfile]
        self.rgs_region_storage.save()
        return not self.rg_regions[region_name]["protected"]

    def _purge_name_outoffiles(self, region_name):
        """purge of all the named references found in any file."""
        for rg_file in self.rg_files:
            self._delete_name_fromfiles(region_name, rg_file)
        self.rgs_file_storage.save()

    def _delete_name_fromfiles(self, region_name, region_file):
        """delete a name from a file."""
        if region_file in self.rg_files:
            if region_name in self.rg_files[region_file]:  # noqa
                self.rg_files[region_file].remove(region_name)
            # remove empty file
            if len(self.rg_files[region_file]) < 1:
                del self.rg_files[region_file]
        self.rgs_file_storage.save()

    def _areas_overlap_rect(self, rect1, rect2):
        """
        Just a wrapper for _areas_overlap_cube that disregards the y axis.
        
        :param rect1 = object(cube): these are "cube" type.
        :param rect2 = object(cube): 
        :return: 
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
        cube definition is two 3-axis tuples that define the 
        upper high point an lower low point of a cube:
        cube = (0,0,0), (12,63,12)
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

        # check y edges for intersection (should skip if no "edge" 
        #  y and yy differ more than 1)
        for y_range in y_range_item:
            # any side edge inside cube2 using
            # same/zero y coordinates will cause this check
            # to skip (for rectangle areas versus cubical)
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

        # zz (i.e. zz+1 range) already checked on x_range
        for z_range in z_range_item:
            if all(self._point_inside(cube2, (x, y, z_range))):
                return True
            if all(self._point_inside(cube2, (x, yy, z_range))):
                return True
            if all(self._point_inside(cube2, (xx, y, z_range))):
                return True
            if all(self._point_inside(cube2, (xx, yy, z_range))):
                return True
        return False

    def _blocks_match(self, region_name, position):
        cube = (
            self.rg_regions[region_name]["pos1"],
            self.rg_regions[region_name]["pos2"]
        )
        return all(self._point_inside(cube, position))

    def _whenmatchingcoordsplace(self, player, position, regionname, item):
        """ 
        Returns Boolean indicating if the submitted position is 
        inside the region
        """
        if self.rg_regions[regionname]["ownerUuid"] == player.uuid:
            # code will end here for players in their own regions/claims
            return True
        if player.uuid in self.rg_regions[regionname]["placeplayers"]:
            return True
        self._act_on_place(player, position, regionname)
        return False

    def _whenmatchingcoordsinteract(self, player, position, regionname):
        """ 
        Returns Boolean indicating if the submitted position is 
        inside the region
        """
        if self.rg_regions[regionname]["ownerUuid"] == player.uuid:
            # code will end here for players in their own regions/claims
            return True
        elif player.uuid in self.rg_regions[regionname]["accessplayers"]:
            return True
            # send a barrier particle
        player.sendBlock(position, 35, 0, sendblock=False)
        return False

    def _whenmatchingcoordsbreak(self, player, position, regionname):
        """ 
        Returns Boolean indicating if the submitted position is 
        inside the region
        """
        if self.rg_regions[regionname]["ownerUuid"] == player.uuid:
            # code will end here for players in their own regions/claims
            return True
        elif player.uuid in self.rg_regions[regionname]["breakplayers"]:
            return True
        self._act_on_break(player, position, regionname)
        return False

    def normalize_selection(self, player, size_shape_override=False, printresult=False):  # noqa
        """
        A cube is always defined by regions as being
        the two corners: lower northwest (pos1) and upper southeast (pos2).
        No matter what opposite corners are specifid, this normalizes them,
        resetting them to UNW and LSE.

        Reads the players sel1 and sel1 of `get_memory_player()`, and
        interprets these coordinates as two opposing corners of a cube.
        It then determines which two of the cube's 8 corners represent
        the lowest and highest of all three axes and returns
        them to sel1 and sel2 in that order.

        :param player: Player
        :param size_shape_override: Set to True to allow selection of
         single block, column, line, or wall (things only a block thick).
        :param printresult: Echo result to player message.

        :returns: True if success, otherwise text:
            :bad_dim: - dimensions are not the same.
            :Nosel: Not a valid or complete selection.
            :singleblock|column|line|wall: invalid block wide selections.

        """
        p = self.get_memory_player(player.username)
        if p["dim1"] != p["dim2"]:
            return "bad_dim"
        if p["sel1"] and p["sel2"]:
            p["sel1"], p["sel2"] = self.stat_normalize_selection(
                p["sel1"], p["sel2"]
            )
        else:
            return "Nosel"
        if printresult is True:
            player.message(
                "Pos1 ( lower northwest corner) = %d, %d, %d" % (
                    p["sel1"][0], p["sel1"][1], p["sel1"][2])
            )
            player.message(
                "Pos2 ( upper southeast corner) = %d, %d, %d" % (
                    p["sel2"][0], p["sel2"][1], p["sel2"][2])
            )
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

    def get_memory_player(self, name):
        """
        Get the player's selection data.  Selection data is not saved
        between reboots.

        :param name: valid player name.

        :returns:  A dictionary of player selection data.
        {
            "sel1"
            "sel2"
            "dim1"
            "dim2"
            "regusing"
            "wand"
            }

        """
        try:
            return self.players[name]
        except KeyError:
            self.players[name] = {
                "sel1": None, "sel2": None, "dim1": None, "dim2": None,
                "regusing": None,
                "wand": self.api.minecraft.getPlayer(
                    name).hasPermission("region.wand")
            }
            return self.players[name]

    def client_show_cube(self, player, pos1, pos2, block=35, corner=51,
                         sendblock=True, numparticles=1, particle_data=1):
        """
        Present a cube's edges to the player's client to outline a region.

        :param player:
        :param pos1:
        :param pos2:
        :param block:
        :param corner:
        :param sendblock:
        :param numparticles:
        :param particle_data:
        :return:
        """
        playerposition = player.getPosition()
        ppos = (playerposition[0], playerposition[1], playerposition[2])
        xlow, ylow, zlow = pos1
        xhi, yhi, zhi = pos2

        # this prevents rendering boundaries that may be out of view.
        if xhi > (ppos[0] + 96):
            xhi = int((ppos[0] + 96))
        if xlow < (ppos[0] - 96):
            xlow = int((ppos[0] - 96))
        if zhi > (ppos[2] + 96):
            zhi = int((ppos[2] + 96))
        if zlow < (ppos[2] - 96):
            zlow = int((ppos[2] - 96))
        if zlow > zhi:
            zlow = zhi
        if xlow > xhi:
            xlow = xhi

        # create our range objects BEFORE we start the loops
        # this is ok (range) for py2 since we'll re-use the y and z lists
        x_coord_range = range(xlow, xhi)
        y_coord_range = range(ylow, yhi)
        z_coord_range = range(zlow, zhi)

        # Render our cube
        for x in x_coord_range:
            if xlow == pos1[0]:
                position1 = (x, ylow, zlow)
                position3 = (x, yhi, zlow)
                player.sendBlock(position1, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position3, block, 0, sendblock, numparticles,
                                 particle_data)
            if xhi == pos2[0]:
                position2 = (x, ylow, zhi)
                position4 = (x, yhi, zhi)
                player.sendBlock(position2, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position4, block, 0, sendblock, numparticles,
                                 particle_data)
            for y in y_coord_range:
                position1 = (xlow, y, zlow)
                position2 = (xlow, y, zhi)
                position3 = (xhi, y, zlow)
                position4 = (xhi, y, zhi)
                player.sendBlock(position1, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position2, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position3, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position4, block, 0, sendblock, numparticles,
                                 particle_data)
            for z in z_coord_range:
                position1 = (xlow, ylow, z)
                position2 = (xlow, yhi, z)
                position3 = (xhi, ylow, z)
                position4 = (xhi, yhi, z)
                player.sendBlock(position1, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position2, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position3, block, 0, sendblock, numparticles,
                                 particle_data)
                player.sendBlock(position4, block, 0, sendblock, numparticles,
                                 particle_data)
            if sendblock:
                player.sendBlock(pos2, corner << 4, sendblock, numparticles,
                                 particle_data)
        return

    @staticmethod
    def stat_normalize_selection(coords1, coords2):
        """
        takes two 3-axis coordinate tuples, interprets these coordinates as two
        opposing corners of a cube.  It then determines which two of the cubes 
        8 corners represent the lowest and highest of all three axes and returns
        them in that order.
        :param coords1: any x,y,z corner of a cube
        :param coords2: the opposite corner x, y, z
        :return: lowest x,y,z corner, highest x,y,z corner
        """
        x1 = int(coords1[0])
        y1 = int(coords1[1])
        z1 = int(coords1[2])
        x2 = int(coords2[0])
        y2 = int(coords2[1])
        z2 = int(coords2[2])
        # get low and high corners
        if x1 <= x2:
            lowx = x1
            hix = x2
        else:
            lowx = x2
            hix = x1

        if y1 <= y2:
            lowy = y1
            hiy = y2
        else:
            lowy = y2
            hiy = y1

        if z1 <= z2:
            lowz = z1
            hiz = z2
        else:
            lowz = z2
            hiz = z1

        lowcoords = (lowx, lowy, lowz)
        highcoords = (hix, hiy, hiz)
        return lowcoords, highcoords

    @staticmethod
    def _point_inside(cube, point):
        firstcorner, secondcorner = cube
        xmin, xmax = firstcorner[0] - 1, secondcorner[0] + 1
        yield xmin < point[0] < xmax
        zmin, zmax = firstcorner[2] - 1, secondcorner[2] + 1
        yield zmin < point[2] < zmax
        ymin, ymax = firstcorner[1] - 1, secondcorner[1] + 1
        yield ymin < point[1] < ymax

    @staticmethod
    def coord2chunk(coord):
        if coord >= 0:
            return int((coord // 16))
        else:
            return -int(((abs(coord) + 15) // 16))

    @staticmethod
    def chunk2region(chunk):
        return int(math.floor(chunk // 32.0))

    @staticmethod
    def chunk2coord(chunk):
        if chunk >= 0:
            return chunk * 16
        else:
            return -int((abs(chunk)) * 16)

    @staticmethod
    def region2chunk(region):
        return region * 32.0

    @staticmethod
    def _signif_move(prev: tuple, pres: tuple, threshhold: int):
        """
        When coordinates `prev` and `pres` change by `threshhold` amount.

        :param prev:
        :param pres:
        :param threshhold:
        :return:
        """
        if abs(prev[0] - pres[0]) > threshhold:
            return True
        if abs(prev[2] - pres[2]) > threshhold:
            return True
        if abs(prev[1] - pres[1]) > threshhold:
            return True
        if prev[3] != pres[3]:
            return True
        return False
