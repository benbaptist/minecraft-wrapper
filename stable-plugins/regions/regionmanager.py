# coding=utf-8

NAME = "Region Manager"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.regionmanager"
VERSION = (0, 2, 2)
SUMMARY = "User interface for world regions editing and protection."
WEBSITE = ""
DESCRIPTION = """
Regions Manager is the front-end command interface for the regions
protection plugin and can be used to create, administer, and maintain
regions.  Also does some basic world edit functions.  It is not user
friendly and is intended for operation by an admin/staff member, but
this can be customized by permissions.  Regions Manager can itself
be used as a back end for a higher level player-friendly land claim
system.


"""
DEPENDENCIES = ["regions.py", ]


# The specific errors we need not worry about in the plugin API:
# noinspection PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyPep8Naming,PyClassicStyleClass,PyAttributeOutsideInit
class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log
        self.players = {}
        self.res_messages = {
            "Nosel": "&bYou must select a region first! (use wooden"
                     " axe or see help)",
            "bad_dim": "&bSelection points are in different dimensions!",
            "singleblock": "&bYou must select more than one block!",
            "column": "&bThe selection is not valid because it is a column.",
            "line": "&bThe selection is not valid because it is a line.",
            "wall": "&bThe selection is not valid because it is a wall."
        }
        self.rg_help_messages = {
            0: "&2//region &e<subcommand>&2 [region] <args>&r "
               " - Valid &esubcommands&r:",
            1: "&edefine &2<region>&f - creates a region",
            2: "&eresize &2<region>&f - resize a region",
            3: "&euse &2<region>&f - use <region>' for commands",
            4: "&eprotect &2<True|False|on|off>&f - Set region "
               "protection on/off",
            5: "&eroof|floor &2<height>&f - adjust y coord height/depth",
            6: "&edelete &2<region>&f - delete region '<region>'",
            7: "&edraw &2[region]&f - draw region '[region]'",
            8: "&efind &2<near|named|owner|region|here> <arg (except "
               "region|here)>&f - find regions]'",
            9: "&eshow &2<region>&f - display region metadata.",
            10: "&egoto &2<region>&f - Teleport to a random "
                "location in the region.",
            11: "&eset&f - type &2//region set&f for more info..."
        }
        self.getargs = self.api.helpers.getargs
        self.getint = self.api.helpers.get_int
        self.dumps = self.api.helpers.putjsonfile

    def onEnable(self):

        # get the regions plugin:
        self.regions = self.api.getPluginContext("com.suresttexas00.regions")
        if self.regions.version < 1.1:
            self.log.error(
                "Regions.py is out of date!, Regionmanager not enabled."
            )
            return False

        # region register help group
        self.api.registerHelp(
            "Regions-region", "Create and modify regions.",
            [
                ("//rg define <region>", "defines a region named <region>",
                 "region.define"),
                ("//rg use <region>", "use [<region>] for subsequent commands",
                 "region.wand"),
                ("//rg roof [region] <height>", "changes y coord height",
                 "region.adjust"),
                ("//rg floor [region] <height>", "changes y coord depth",
                 "region.adjust"),
                ("//rg protect [region] <True|False>",
                 "Set region protection.",
                 "region.protect"),
                ("//rg set'",
                 "Administer region permissions ('//rg set' for more...)",
                 "region.player"),
                ("//rg draw [region]", "draw the outline of 'region'",
                 "region.player"),
                ("//rg delete <region>", "delete '<region>'",
                 "region.delete"),
                ("//rg resize <region>", "resize <region> to new pos1, pos2",
                 "region.adjust"),
                ("//rg show <region>", "display metadata for <region>",
                 "region.adjust"),
                ("//rg find <find by> [arg]",
                 "<find by>: near [distance=50], named <text>, owner <text>, "
                 "region, here", "region.adjust"),
                ("//rg goto <region>", "goto region <region>",
                 "region.adjust")
            ]
        )

        self.api.registerHelp(
            "Regions-Tools", "Region selection tools",
            [
                ("//wand", "Gives the editing wand",
                 "region.wand"),
                ("//pos1", "Select pos1",
                 "region.wand"),
                ("//pos2", "Select pos2",
                 "region.wand"),
                ("//file", "display the region file name for the region "
                           "you are standing in.",
                 "region.player"),
                ("//home", "get placed 'somewhere' near one of your claims",
                 "region.home"),
                ("//jsondumps",
                 "save regions and files data (*.json) in wrapper folder"
                 " for viewing",
                 "region.dumps"),
            ]
        )

        self.api.registerHelp(
            "Regions-WorldEdit", "Region world editing tools",
            [
                ("//pos1", "Select pos1",
                 "region.wand"),
                ("//pos2", "Select pos2",
                 "region.wand"),
                ("//here",
                 "face the northwest corner of //copy destination",
                 "region.copy"),
                ("//replace <newTile> <Data> <oldTile> <Data>",
                 "replace blocks (see //fill)",
                 "region.replace"),
                ("//copy", "copies selection starting at corner you face "
                           "with //here",
                 "region.copy"),
                ("//fill <item> <metadata>",
                 "a more massive implementation of the minecraft /fill "
                 "command. It is essentially only limited by loaded chunks. "
                 "Command fails for any slice in an unloaded chunk. Command "
                 "fails for any slice over 32K. (a slice is a X times Y "
                 "Coord slice that is 1Z wide)",
                 "region.fill")
            ]
        )
        # /region perms mostly handled by subcommands
        self.api.registerCommand(
            ("/rg", "/reg", "/region"), self._region, "region.player"
        )

        self.api.registerCommand("/fill", self._rgfill, "region.fill")
        self.api.registerCommand("/replace", self._rgreplace, "region.replace")
        self.api.registerCommand("/copy", self._rgcopy, "region.copy")
        self.api.registerCommand("/here", self._here, "region.copy")

        self.api.registerCommand("/pos1", self._pos1, "region.wand")
        self.api.registerCommand("/pos2", self._pos2, "region.wand")
        self.api.registerCommand("/wand", self._wand, "region.wand")
        self.api.registerCommand("/file", self._file, "region.player")

        self.api.registerCommand("/home", self._home, "region.home")
        self.api.registerCommand("/jsondumps", self._jsondumps, "region.dumps")

        # Register default permissions
        # self.api.registerPermission("region.wand", True)
        # self.api.registerPermission("region.player", True)
        # self.api.registerPermission("region.delete", True)
        # self.api.registerPermission("region.define", True)
        # self.api.registerPermission("region.protect", True)
        # self.api.registerPermission("region.adjust", True)
        # self.api.registerPermission("region.multiple", True)
        # self.api.registerPermission("region.setowner", True)
        
    def _region(self, player, args):
        """
        The main command //region - this will parse subcommands only
        and pass the arguments to the subcommand.  This also decides
        the permissions.
        """
        if not player.hasPermission("region.player"):
            return
        if len(args) == 0:
            self._region_help(player)
            return
        if args[0].lower()[0:3] == "def" and (
                player.hasPermission("region.define")):
            self._rgdefine(player, args)
            return
        elif args[0].lower() == "use" and (
                player.hasPermission("region.select")):
            self._rguse(player, args)
            return
        elif args[0].lower()[0:4] == "prot" and (
                player.hasPermission("region.protect")):
            self._rgprotect(player, args)
            return
        elif args[0].lower() == "roof" and (
                player.hasPermission("region.adjust")):
            self._rgroof(player, args)
            return
        elif args[0].lower() == "floor" and (
                player.hasPermission("region.adjust")):
            self._rgfloor(player, args)
            return
        elif args[0].lower()[0:3] in ("rem", "del"):
            self._rgdelete(player, args)
            return
        elif args[0].lower() == "set":
            self._rgsetperms(player, args)
            return
        elif args[0].lower() == "draw":
            self._rgdraw(player, args)
            return
        elif args[0].lower() == "resize" and (player.hasPermission("region.adjust")):  # noqa
            self._rg_resize(player, args)
            return
        elif args[0].lower() == "find" and (player.hasPermission("region.adjust")):  # noqa
            self._rg_find(player, args)
            return
        elif args[0].lower() in ("show", "dis", "about", "display") and (
                player.hasPermission("region.adjust")):
            self._rg_display(player, args)
            return
        elif args[0].lower() == "goto":
            self._rg_goto(player, args)
            return
        if args[0].lower() != "help":
            player.message("&cSubcommand not recognized!")
        player.message("&aUsage:")
        self._region_help(player)
    
    @staticmethod
    def _regionhelp_set(player):
        player.message("&6Usage '//rg set [region] &e<attribute>&6 <player>'")
        player.message("&e   --Attributes--")
        # owner | canbreak | canplace | canaccess | ban
        player.message("&e owner &a- Set player as owner.")
        player.message(
            "&e break/canbreak &a- Allow specified player to break blocks."
        )
        player.message("&e place/canplace &a- Allow player to place blocks.")
        player.message("&e remove &a- remove all player's permissions.")
        player.message(
            "&e access/canaccess &a-player can operate things &a(eat/"
            "shoot/sleep,etc)."
        )

    def _region_help(self, player):
        for mess in self.rg_help_messages:
            player.message(self.rg_help_messages[mess])

    def _rgdefine(self, player, args):

        if len(args) == 2:
            regionname = args[1]
            result = self.regions.normalize_selection(
                player, size_shape_override=True
            )
            if result in self.res_messages:
                player.message(self.res_messages[result])
                return

            # op override to rewrite a region
            if args[1] in self.regions.rg_regions and not player.isOp():
                player.message(
                    "&cThat region name already exists, you cannot create it."
                )
                return

            # This intentionally uses the username for the region
            # if the user has permission to only create one (1) region.
            if not player.hasPermission("region.multiple"):
                regionname = player.username
                for region in self.regions.rg_regions:
                    if self.regions.rg_regions[region]["ownerUuid"] == player.uuid:  # noqa
                        player.message(
                            "&cYou already made another region.  You don't "
                            "have permission to make another."
                        )
                        return
            if regionname in self.regions.rg_regions:
                if regionname == player.username:
                    player.message(
                        "&cThis region has your username.  Due to your "
                        "permissions level, it will need to be deleted "
                        "before you can create another."
                    )
                else:
                    player.message(
                        "&cThis region is already defined.  You can't re-"
                        "define it. &rtry EDIT instead."
                    )
                return
            p = self.regions.get_memory_player(player.username)
            definedregion = self.regions.rgdefine(
                regionname, player.uuid,
                p["dim1"], p["sel1"], p["sel2"]
            )

            if definedregion:
                player.message(
                    {"text": "Region ", "color": "gold", "extra": [
                        {"text": definedregion, "color": "dark_purple"},
                        {"text": " created and selected!", "color": "gold"}
                    ]
                     }
                )
            return
        else:
            player.message("&bUsage '//rg define/select/create <regionname>'")
            return

    def _rguse(self, player, args):
        if len(args) == 2:
            name = (args[1])
            for namex in self.regions.rg_regions:
                if namex == name:
                    if not player.uuid == self.regions.rg_regions[namex]["ownerUuid"]:  # noqa
                        player.message(
                            {"text": "WARNING: Region selected for use, but "
                                     "is not owned by you.", "color": "Red"}
                        )
                    p = self.regions.get_memory_player(player.username)
                    p["dim1"] = self.regions.rg_regions[namex]["dim"]
                    p["dim2"] = self.regions.rg_regions[namex]["dim"]
                    p["sel1"] = (self.regions.rg_regions[name]["pos1"])
                    p["sel2"] = (self.regions.rg_regions[name]["pos2"])
                    p["regusing"] = name
                    player.message(
                        {"text": "Using region ", "color": "gold",
                         "extra": [{"text": name, "color": "dark_purple"},
                                   {"text": ".", "color": "gold"}]}
                    )
                    self.regions.normalize_selection(player, printresult=True)
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message("&bUsage '//region use <region>'")
            return

    def _rgprotect(self, player, args):
        if len(args) == 2:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 3:
            name = args[1]
            prot = (args[2].lower())[0]

            for namex in self.regions.rg_regions:
                if (prot == "f" or args[2].lower() == "off") and namex == name:
                    self.regions.protection_off(name)
                    player.message("&cRegion protection OFF!")
                    return
                if (prot == "t" or prot == "o") and namex == name:
                    self.regions.protection_on(name)
                    player.message("&bRegion protection ON!")
                    return
                # due to order of processing, "o" will default to "on"
                if prot not in ("t", "f", "o"):
                    player.message(
                        "&bUsage //rg protect [regionname] '<TRUE|FALSE>"
                    )
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message("&bUsage '//rg protect <regionname> <True|False>'")
            return

    def _insertSelectedRegionname(self, player, args):
        # args = self._insertSelectedRegionname(player, args)
        p = self.regions.get_memory_player(player.username)
        if p["regusing"] is None:
            return args
        if len(args) > 1:
            if args[1] == p["regusing"]:
                return args
        player.message(
            {"text": "None or invalid region specified. Using region ",
             "color": "gray", "extra": [
                {"text": p["regusing"], "color": "dark_purple"},
                {"text": ".", "color": "gray"}]
             }
        )
        allargs = args[0] + " " + p["regusing"]
        for x in range(1, len(args)):
            allargs = allargs + " " + args[x]
        args = allargs.split(" ")
        return args

    def _rgroof(self, player, args):
        """
        roof and floor can be safely changed since it is only the y
        axis being adjusted.
        """
        if len(args) == 2:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 3:
            y = int(args[2])
            name = (args[1])
            if y < 0 or y > 256:
                player.message(
                    "&bUsage '//rg roof [regionname] <height>'  - number"
                    " from 0-256"
                )
                return
            for namex in self.regions.rg_regions:
                if namex == name:
                    x = self.regions.rg_regions[name]["pos2"][0]
                    yfloor = self.regions.rg_regions[name]["pos1"][1]
                    z = self.regions.rg_regions[name]["pos2"][2]
                    if y <= yfloor:
                        player.message(
                            "&cYou can't lower the roof (%d) below the "
                            "floor (%d)" % (y, yfloor)
                        )
                        return
                    new = (x, y, z)
                    self.regions.rg_regions[name]["pos2"] = new
                    p = self.regions.get_memory_player(player.username)
                    p["sel2"] = new
                    player.message("&6Roof changed to y=%d!" % y)
                    self.regions.rgs_region_storage.save()
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message(
                "&bUsage '//rg roof [regionname] <height>'  - number from 0-256"
            )
            return

    def _rgfloor(self, player, args):
        """
        roof and floor can be safely changed since it is only the y
        axis being adjusted.
        """
        if len(args) == 2:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 3:
            y = int(args[2])
            name = (args[1])
            if y < 0 or y > 256:
                player.message(
                    "&bUsage '//rg floor <height>'  - number from 0-256"
                )
                return
            for namex in self.regions.rg_regions:
                if namex == name:
                    x = self.regions.rg_regions[name]["pos1"][0]
                    yroof = self.regions.rg_regions[name]["pos2"][1]
                    z = self.regions.rg_regions[name]["pos1"][2]
                    if y >= yroof:
                        player.message(
                            "&cYou can't raise the floor (%d) above the "
                            "roof (%d)" % (y, yroof)
                        )
                        return
                    new = (x, y, z)
                    self.regions.rg_regions[name]["pos1"] = new
                    p = self.regions.get_memory_player(player.username)
                    p["sel1"] = new
                    player.message("&6Floor changed to y=%d!" % y)
                    self.regions.rgs_region_storage.save()
                    return
            player.message("&cRegion %s not found..." % name)
            return
        else:
            player.message(
                "&bUsage '//rg floor [regionname] <height>'  - "
                "number from 0-256"
            )
            return

    def _rgdelete(self, player, args):
        if len(args) == 2:
            name = (args[1])
            for namex in self.regions.rg_regions:
                if namex == name:
                    if not player.hasPermission("region.delete"):
                        if not player.uuid == self.regions.rg_regions[namex]["ownerUuid"]:  # noqa
                            player.message(
                                {"text": "Command not authorized for "
                                         "this region", "color": "Red"}
                            )
                            return
                    p = self.regions.get_memory_player(player.username)
                    if self.regions.rg_regions[name] == p["regusing"]:
                        p["regusing"] = None
                    if self.regions.rgdelete(name):
                        player.message(
                            {"text": "Deleted Region ",
                             "color": "gold", "extra": [
                                {"text": name, "color": "dark_purple"},
                                {"text": ".", "color": "gold"}]
                             }
                        )
                    else:
                        player.message(
                            "&cThe region was already deleted!"
                        )
                    return
            player.message(
                "&cRegion %s not found..." % name
            )
            return
        else:
            player.message("&bUsage '//rg remove <region>'")
            return

    def _rgsetperms(self, player, args):
        if len(args) == 3:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 4:

            targetuuid = self.api.minecraft.lookupbyName(args[3]).string
            targetname = self.api.minecraft.lookupbyUUID(targetuuid)
            for namex in self.regions.rg_regions:
                if namex == args[1]:
                    if not player.hasPermission("region.setowner"):
                        if not player.uuid == self.regions.rg_regions[namex]["ownerUuid"]:  # noqa
                            player.message(
                                {"text": "You don't have permission to set "
                                         "this region's owner.", "color": "Red"}
                            )
                            return
                    if args[2].lower() == "owner":
                        editregion = self.regions.rgedit(
                            namex, new_owner_name=True, playername=targetname
                        )
                        player.message(
                            {"text": "Region ", "color": "gold", "extra": [
                                {"text": editregion, "color": "dark_purple"},
                                {"text": " is now owned by ", "color": "gold"},
                                {"text": targetname, "color": "dark_green"},
                                {"text": ".", "color": "gold"}]
                             }
                        )
                        return
                    if args[2].lower() in ("break", "canbreak"):
                        editregion = self.regions.rgedit(
                            namex, playername=targetname,
                            addbreak=True
                        )
                        player.message(
                            {"text": "Player ", "color": "gold", "extra": [
                                {"text": targetname, "color": "dark_green"},
                                {"text": " can now break blocks in region ",
                                 "color": "gold"},
                                {"text": editregion, "color": "dark_purple"},
                                {"text": ".", "color": "gold"}
                            ]
                             }
                        )
                        return
                    if args[2].lower() in ("place", "canplace"):
                        editregion = self.regions.rgedit(
                            namex, playername=targetname,
                            addplace=True
                        )
                        player.message(
                            {"text": "Player ",
                             "color": "gold", "extra": [
                                {"text": targetname, "color": "dark_green"},
                                {"text": " can now place blocks/operate stuff "
                                         "in region ", "color": "gold"},
                                {"text": editregion, "color": "dark_purple"},
                                {"text": ".", "color": "gold"}
                              ]
                             }
                        )
                        return
                    if args[2].lower() in ("access", "canaccess"):
                        editregion = self.regions.rgedit(
                            namex, playername=targetname,
                            addaccess=True
                        )
                        player.message(
                            {"text": "Player ",
                             "color": "gold", "extra": [
                                {"text": targetname, "color": "dark_green"},
                                {"text": " can now eat and do things in "
                                         "region ", "color": "gold"},
                                {"text": editregion, "color": "dark_purple"},
                                {"text": ".", "color": "gold"}
                              ]
                             }
                        )
                        return
                    if args[2].lower() == "ban":
                        editregion = self.regions.rgedit(
                            namex, playername=targetname, addban=True
                        )
                        player.message(
                            {"text": "Player ",
                             "color": "gold", "extra": [
                                {"text": targetname, "color": "dark_green"},
                                {"text": " has been added to your banlist for "
                                         "region ", "color": "gold"},
                                {"text": editregion, "color": "dark_purple"},
                                {"text": ".", "color": "gold"}
                              ]
                             }
                        )
                        return
                    if args[2].lower() in ("rem", "remove"):
                        editregion = self.regions.rgedit(
                            namex, playername=targetname,
                            remove=True
                        )
                        player.message(
                            {"text": "Player ", "color": "gold", "extra": [
                                {"text": targetname, "color": "dark_green"},
                                {"text": " removed from all region lists for "
                                         "region ", "color": "gold"},
                                {"text": editregion, "color": "dark_purple"},
                                {"text": ".", "color": "gold"}
                              ]
                             }
                        )
        else:
            self._regionhelp_set(player)

    def _rgdraw(self, player, args):
        if len(args) == 1:
            args = self._insertSelectedRegionname(player, args)
        if len(args) == 2:
            # //region draw [region]
            for namex in self.regions.rg_regions:
                if namex == args[1]:
                    pos1 = self.regions.rg_regions[namex]["pos1"]
                    pos2 = self.regions.rg_regions[namex]["pos2"]
                    draw_dim = self.regions.rg_regions[namex]["dim"]
                    playerdim = player.getDimension()
                    if playerdim != draw_dim:
                        player.message(
                            "&cYou are not in the dimension where the region "
                            "is located!"
                        )
                        return
                    player.message("&1Hold on, Lag may occur!!")
                    self.regions.client_show_cube(
                        player, pos1, pos2, sendblock=False
                    )
                    player.message("&2Done!!")
        else:
            player.message("&bUsage '//rg draw [region] '")
            player.message(
                "&bif you selected a region, you must define it first..."
            )
            return

    def _rg_resize(self, player, args):
        if len(args) != 2:
            player.message("&bUsage '//rg edit/resize <regionname>")
            player.message(
                "&bNOTE!  This command REQUIRES the <regionname> and a new "
                "wand (pos1, pos2) selection!"
            )
            return
        regionname = args[1]
        if regionname not in self.regions.rg_regions:
            player.message("&cRegion %s is not defined!" % regionname)
            return
        result = self.regions.normalize_selection(player)
        if result in self.res_messages:
            player.message(self.res_messages[result])
            return
        p = self.regions.get_memory_player(player.username)
        # include code to validate intersecting regions??
        result = self.regions.rgedit(
            regionname, edit_coords=True,
            low_corner=p["sel1"], high_corner=p["sel2"]
        )
        if result == regionname:
            player.message(
                "&6Region edit made: New coords - %s  and  %s" % (
                    str(p["sel1"]), str(p["sel2"])
                )
            )

    def _rg_find(self, player, args):

        """
        :param player: Player
        :args[1]: Subcommand (near, named, owner/ownedby, region, here)
        :args[2]: argument

        """
        subcommand = self.getargs(args, 1).lower()
        argument = self.getargs(args, 2).lower()
        if argument == "":
            argument = None
        x = player.getPosition()
        d = player.getDimension()
        results = []

        if subcommand == "near":
            radius = self.getint(argument)
            if radius == 0:
                radius = 50
            x1 = x[0] - radius
            y1 = 0
            z1 = x[2] - radius
            x2 = x[0] + radius
            y2 = 256
            z2 = x[2] + radius
            cube1 = (x1, y1, z1)
            cube2 = (x2, y2, z2)
            regions = self.regions.intersecting_regions(d, cube1, cube2)
            if regions:
                results += regions

        elif subcommand[0:4] == "name":
            if argument is None:
                player.message("&cNo name <arg>!")
                player.message(self.rg_help_messages[8])
                return
            for regions in self.regions.rg_regions:
                search = regions.lower().find(argument.lower())
                if search != -1:
                    results.append(regions)

        elif subcommand[0:3] == "own":
            if argument is None:
                player.message("&cNo owner <arg>!")
                player.message(self.rg_help_messages[8])
                return
            uuid = self.api.minecraft.lookupbyName(argument)
            if not uuid:
                player.message("&cNo such player '%s'" % argument)
                return
            for regions in self.regions.rg_regions:
                if self.regions.rg_regions[regions]["ownerUuid"] == uuid:
                    results.append(regions)

        elif subcommand == "region":
            region = self.regions.getregionfilename(x[0], x[2])
            if region in self.regions.rg_files:
                for files in self.regions.rg_files[region]:
                    results.append(files)

        elif subcommand == "here":
            region = self.regions.regionname(x, d)
            if region:
                results.append(region)
        else:
            player.message(self.rg_help_messages[8])
        if len(results) > 0:
            text = ", ".join(results)
            plural = ""
            if len(results) > 1:
                plural = "s"
            confirm = "&6Found %d record%s." % (len(results), plural)
            player.message(confirm)
            player.message({"text": text, "color": "dark_green"})
            player.message(confirm, 2)
        else:
            player.message("&4&lFound no records.", 2)

    def _rg_display(self, player, args):
        argument = self.getargs(args, 1).lower()
        if argument == "":
            player.message("&cNo <region> arg!")
            player.message(self.rg_help_messages[9])
            return
        if argument not in self.regions.rg_regions:
            player.message("&cNo such region '%s'!" % argument)
            player.message(self.rg_help_messages[8])
            return
        region = self.regions.rg_regions[argument]
        ownername = self.api.minecraft.lookupbyUUID(region["ownerUuid"])
        centerx = (region["pos1"][0] + region["pos2"][0]) // 2
        centery = (region["pos1"][1] + region["pos2"][1]) // 2
        centerz = (region["pos1"][2] + region["pos2"][2]) // 2

        location_info = "&aDim: &b%d&a, location: &b%d,%d,%d&a, Protected: &b%s" % (  # noqa
            region["dim"], centerx, centery, centerz, region["protected"]
        )
        breakplayers = self._get_names(region["breakplayers"])
        placeplayers = self._get_names(region["placeplayers"])
        accessplayers = self._get_names(region["accessplayers"])
        banplayers = self._get_names(region["banplayers"])
        player.message("&5Region: &a%s, &6Owner: &a%s" % (argument, ownername))
        player.message(location_info)
        player.message("&abreakplayers: {&e%s&a}" % breakplayers)
        player.message("&aplaceplayers: {&e%s&a}" % placeplayers)
        player.message("&aaccessplayers: {&e%s&a}" % accessplayers)
        player.message("&abanplayers: {&e%s&a}" % banplayers)

    def _get_names(self, uuids):
        names = []
        for uuid in uuids:
            name = self.api.minecraft.lookupbyUUID(uuid)
            if uuid:
                names.append(name)
        if len(names) < 0:
            return None
        else:
            return ", ".join(names)

    def _rg_goto(self, player, args):
        argument = self.getargs(args, 1).lower()
        if argument == "":
            player.message("&cNo <region> arg!")
            player.message(self.rg_help_messages[9])
            return
        if argument not in self.regions.rg_regions:
            player.message("&cNo such region '%s'!" % argument)
            player.message(self.rg_help_messages[8])
            return
        region = self.regions.rg_regions[argument]
        centerx = (region["pos1"][0] + region["pos2"][0]) // 2
        widthx = (region["pos2"][0] - region["pos1"][0])
        widthz = (region["pos2"][2] - region["pos1"][2])
        centerz = (region["pos1"][2] + region["pos2"][2]) // 2
        spread = (widthx + widthz) // 5
        self.api.minecraft.console(
            "spreadplayers %s %s 1 %d false %s" % (
                centerx, centerz, spread, player.username
            )
        )

    # Other commands section:
    # ---------------------------------------
    def _rgfill(self, player, args):
        if len(args) >= 1:
            # fill minecraft:glass 0
            blockdata = "0"
            # player can omit block data argument for block ids if it is just 0
            if len(args) == 2:
                blockdata = args[1]
            result = self.regions.normalize_selection(
                player, size_shape_override=True
            )
            if result in self.res_messages:
                player.message(self.res_messages[result])
                return
            p = self.regions.get_memory_player(player.username)
            if p["dim1"] != 0:
                player.message(
                    "&bSorry, but this command only functions in the "
                    "overworld..."
                )
                return
            self._console_fill(
                p["sel1"], p["sel2"], "fill", args[0], blockdata, "None", "0"
            )
            player.message(
                {"text": "Command completed- check console for results!",
                 "color": "gold"}
            )
        else:
            player.message(
                {"text": "No arguments specified. Try /help", "color": "red"}
            )
            return

    def _console_fill(self, pos1, pos2, method, newblockname, newblockdata,
                      oldblockname, oldblockdata):
        """
        :param pos1: lowest coordinates
        :param pos2: highest coordinates
        :param method: "replace" to replace blocks, anything else is "fill"
        :param newblockname: minecraft:name of block to fill with
        :param newblockdata: dataID of block (usually 0, unless a type, like
         stones: andesite, doirite, etc)
        :param oldblockname: minecraft:name of block being replaced/removed
        :param oldblockdata: dataID of block (usually 0)
        """
        x1, y1, z1 = pos1
        x2, y2, z2 = pos2
        for zdex in range(int(z1), (int(z2) + 1)):
            zstr = str(zdex)
            if method == "replace":
                textcommand = "fill %s %s %s %s %s %s %s %s replace %s %s" % (
                    x1, y1, zstr, x2, y2, zstr, newblockname, newblockdata,
                    oldblockname, oldblockdata
                )
            else:
                textcommand = "fill %s %s %s %s %s %s %s %s" % (
                    x1, y1, zstr, x2, y2, zstr, newblockname, newblockdata
                )
            self.api.minecraft.console(textcommand)

    def _rgreplace(self, player, args):
        if len(args) >= 1:
            # replace minecraft:air 0 minecraft:snow_layer 0
            #  (turn snow layer to air)
            if len(args) != 4:
                player.message(
                    {"text": "Wrong number of arguments specified.",
                     "color": "red"}
                )
                player.message(
                    {"text": "//replace <desired tilename> <dataValue> <tile"
                             " to be removed> <dV>"}
                )
            result = self.regions.normalize_selection(
                player, size_shape_override=True
            )
            if result in self.res_messages:
                player.message(self.res_messages[result])
                return
            p = self.regions.get_memory_player(player.username)
            if p["dim1"] != 0:
                player.message(
                    "&bSorry, but this command only functions in the "
                    "overworld..."
                )
                return
            self._console_fill(
                p["sel1"], p["sel2"], "replace", args[0],
                args[1], args[2], args[3]
            )
            player.message(
                {"text": "Command completed- check console for results!",
                 "color": "gold"}
            )
        else:
            player.message(
                {"text": "No arguments specified. Try /help", "color": "red"}
            )
            return

    def _rgcopy(self, *args):
        player = args[0]
        result = self.regions.normalize_selection(
            player, size_shape_override=True
        )
        if result in self.res_messages:
            player.message(self.res_messages[result])
            return
        p = self.regions.get_memory_player(player.username)
        if p["dim1"] != 0:
            player.message(
                "&bSorry, but this command only functions in the overworld..."
            )
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
            "clone %d %d %d %d %d %d %d %d %d replace normal" % (
                x1, y1, z1, x2, y2, z2, x, y, z
            )
        )

    def _pos1(self, player, args):
        if len(args) != 3:
            player.message("&cArguments not properly specified (three numbers)")
            return
        x = int(float((args[0])))
        y = int(float((args[1])))
        z = int(float((args[2])))
        dim = int(player.getDimension())
        p = self.regions.get_memory_player(player.username)
        p["dim1"] = dim
        p["sel1"] = (x, y, z)
        player.message("&dPoint one selected. (%d %d %d)" % (x, y, z))
        if p["regusing"] is not None:
            player.message(
                "&cYou were using region '%s'.  You are now selecting a "
                "new area." % p["regusing"]
            )
        p["regusing"] = None
        return False

    def _pos2(self, player, args):
        if len(args) != 3:
            player.message("&cArguments not properly specified (three numbers)")
            return
        x = int(float((args[0])))
        y = int(float((args[1])))
        z = int(float((args[2])))
        dim = int(player.getDimension())
        p = self.regions.get_memory_player(player.username)
        p["dim2"] = dim
        p["sel2"] = (x, y, z)
        player.message("&dPoint two selected. (%d %d %d)" % (x, y, z))
        if p["regusing"] is not None:
            player.message(
                "&cYou were using region '%s'.  You are now selecting a "
                "new area." % p["regusing"]
            )
        p["regusing"] = None
        return False

    def _here(self, *args):
        player = args[0]
        curpos = player.getPosition()
        x = int(curpos[0])
        z = int(curpos[2])
        self.api.minecraft.console(
            "tp %s %d ~ %d -45 45" % (str(player.username), x, z)
        )

    def _wand(self, *args):
        player = args[0]
        self.api.minecraft.console(
            "give %s minecraft:wooden_axe 1 63" % player.username
        )
        player.message(
            "&bleft and right click two different blocks to select a region."
        )

    def _file(self, player, args):
        if not player.hasPermission("region.player"):
            return
        coords = player.getPosition()
        filename = self.regions.getregionfilename(coords[0], coords[2])
        player.message({"text": "Region filename is ", "color": "aqua",
                        "extra": [{"text": filename, "color": "dark_purple"}]})

    def _jsondumps(self, *args):
        self.dumps(self.regions.rg_regions, "regions")
        self.dumps(self.regions.rg_files, "files")

    def _home(self, *args):
        player = args[0]
        for aregion in self.regions.rg_regions:
            if self.regions.rg_regions[aregion]["ownerUuid"] == player.uuid:
                x = self.regions.rg_regions[aregion]["pos1"][0]
                z = self.regions.rg_regions[aregion]["pos1"][2]
                self.api.minecraft.console(
                    "spreadplayers %s %s 1 2 false %s" % (x, z, player.username)
                )
                player.message(
                    "&5Make sure you /sethome again (this command won't "
                    "be here forever!"
                )
                return
        player.message(
            "&cBummer!  I could not find your old base (you never claimed it?)"
        )
        player.message(
            "&5I'll try to get you to a friends house..."
        )
        for aregion in self.regions.rg_regions:
            if player.uuid in self.regions.rg_regions[aregion]["accessplayers"]:
                x = self.regions.rg_regions[aregion]["pos1"][0]
                z = self.regions.rg_regions[aregion]["pos1"][2]
                self.api.minecraft.console(
                    "spreadplayers %s %s 1 2 false %s" % (x, z, player.username)
                )
                player.message(
                    "&5Make sure you /sethome again (this command won't "
                    "be here forever!"
                )
                return
        player.message(
            "&cWoe is you!  No home.. No friends.. Sorry man!"
        )
