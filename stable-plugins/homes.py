# -*- coding: utf-8 -*-

NAME = "homes"
AUTHOR = "SurestTexas"
ID = "com.suresttexas00.plugins.homes"
SUMMARY = "Home commands"
DESCRIPTION = """Home plugin similar to Bukkit Essentials home commands. 
This is merging of "net.version6.minecraft.plugins.home" by C0ugar, and
SurestTexas00's "Simple" homes plugin.  Inspired by the simplicity and 
elegance of design in C0ugar's version, but augmented with the more full-
featured and robust "Simple" plugin.  Most notably, this uses the Simple 
convention of using UUID's, not names, to key home data.  More features 
are also present, including admin features. Also hooks with the player 
spawnpoint and bed use.

With Wrapper versions over 0.15.7, this will implement non-proxy usage with
an additional "set"/"mark" command to get the player's position.  Allows
commands to be run with old style !<command> convention.
"""
WEBSITE = ""
VERSION = (1, 0, 0)


# noinspection PyMethodMayBeStatic,PyAttributeOutsideInit
class Main:
    """Permissions:
    None - sethome/home
    home.deny - use to prevent sethome/home
    home.admin - player can use admin commands
    home.admin.visit - visit anotherplayers home
    home.admin.homes
    home.admin.super - more dangerous commands like deleting someone's home

    Warning about non-proxy usage - getDimension() returns overworld
      by default, so a person could !sethome on the overworld and
      !home to those coordinates in the nether or end!
    """
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        self.getarg = self.api.helpers.getargs
        self.getint = self.api.helpers.get_int

    def onEnable(self):
        self.data = self.api.getStorage("homes", False)

        self.api.registerHelp("homes", "Commands from the Home plugin", [
            ("/sethome", "Save curremt position as home", None),
            ("/home", "Teleports you to your home set by /sethome", None),
            ("/home <player> set", "set a home for <player>", "home.admin"),
            ("/home <player> visit", "Visit <player>'s home",
             "home.admin.visit"),
            ("/home <player> del", "Delete <player>'s home",
             "home.admin.super"),
            ("/homes", "Find and administer homes", "home.admin.homes"),
        ])

        self.api.registerCommand("sethome", self.sethome)
        self.api.registerCommand("home", self.home)
        self.api.registerCommand("homes", self._homes, "home.admin.homes")

        # This implements ! commands for non-proxy use of this plugin
        self.api.registerEvent("player.message", self._np_commands)

    def onDisable(self):
        self.data.close()

    # This implements ! commands for non-proxy use of this plugin
    def _np_commands(self, payload):
        player = payload["player"]
        words = payload["message"].split(" ")
        if words[0][0] == "!":
            command = words[0][1:].lower()
            if len(words) > 1:
                subcomm = words[1].lower()
            else:
                subcomm = "nope"
            if command in ("homes", "home") and subcomm in ("?", "h", "help"):
                player.message("&eHome plugin Help:")
                player.message("&e!set - set your position.")
                player.message("&e!sethome - set your home (after !set).")
                player.message("&e!home - Go to your home.")
                player.message("&e!homes - advanced topic.")
            elif command == "home":
                self.home(player, words[1:])
            elif command == "sethome":
                self.sethome(player, words[1:])
            elif command in ("mark", "set"):
                self.api.minecraft.console("/tp %s ~ ~ ~ " % player.username)
            elif command == "homes" and player.hasPermission("home.admin.homes"):  # noqa
                self._homes(player, words[1:])

    def sethome(self, player, args):
        if player.hasPermission("home.deny"):
            player.message(
                {"text": "You are not permitted to use this command.",
                 "color": "red"})
            return
        # people confuse this with the essentials plugin that uses home names
        if len(args) > 0:
            player.message({"text": "sethome does not take any arguments!",
                            "color": "red"})
            return
        position = player.getPosition()
        self._sethome(player, player.username, str(player.mojangUuid), position)

    def _sethome(self, userobj, username, playeruuid, xyzcoords):
        if not userobj.getDimension() == 0:
            userobj.message(
                {"text": "Sorry, but you can't do this from the Nether or End.",
                 "color": "red"}
            )
            return
        self.data.Data[playeruuid] = xyzcoords
        # also change their spawnpoint
        self.api.minecraft.console("spawnpoint %s %s %s %s" % (
            username, xyzcoords[0], (xyzcoords[1]), xyzcoords[2]))

        userobj.message({"text": "Home location set. Use /home to return here",
                         "color": "green"})

    def home(self, player, args):
        if len(args) == 0:
            self._player_home(player)
            return
        if not player.hasPermission("home.admin"):
            player.message(
                {"text": "You are not permitted to use this command.",
                 "color": "red"})
            return
        if not len(args) == 2:
            player.message(
                {"text": "Usage - /home <player> <visit/set/delete>",
                 "color": "red"})
            return
        self._admin_home(player, args[0], args[1].lower())
        # admin_player, username, command)

    def _player_home(self, player):
        if player.hasPermission("home.deny"):
            player.message(
                {"text": "You are not permitted to use this command.",
                 "color": "red"})
            return
        if not player.getDimension() == 0:
            player.message(
                {"text": "Sorry, but you can't do this from the Nether or End.",
                 "color": "red"})

            return
        userid = str(player.mojangUuid)
        if userid not in self.data.Data:
            player.message(
                {"text": "Home is not set. Use /sethome.", "color": "red"})
            return
        player.message(
            {"text": "Teleporting you to your home.", "color": "green"})
        self.api.minecraft.console(
            "tp %s %s %s %s" % (player.username, self.data.Data[userid][0],
                                self.data.Data[userid][1],
                                self.data.Data[userid][2]))

    def _admin_home(self, admin_player, username, command):
        polleduuid = self.api.minecraft.lookupbyName(username)
        if polleduuid:
            polleduuid = str(polleduuid)
        else:
            admin_player.message(
                {"text": "The name %s is not a valid name!" % username,
                 "color": "red"})
            return

        if (command in ("delete", "del", "rem", "remove")) and (
                admin_player.hasPermission("home.admin.super")):
            if polleduuid not in self.data.Data:
                admin_player.message(
                    "&c%s does not have a home to delete." % username
                )
                return
            del self.data.Data[polleduuid]
            admin_player.message("&edeleted %s's home..." % username)
            return

        if command in ("sethome", "set"):
            # only a higher admin can change an existing home.
            # if no home is set, any helpful person with home.admin can help:
            if polleduuid in self.data.Data and not admin_player.hasPermission(
                    "home.admin.super"
            ):
                admin_player.message(
                    "&cYou can't create a home for %s - this feature is only "
                    "allowed to be used once for a new player." % username)
                return
            position = admin_player.getPosition()
            self._sethome(admin_player, username, polleduuid, position)
            return

        if command == "visit":
            if not admin_player.hasPermission("home.admin.visit"):
                admin_player.message(
                    "&cSorry, you do not have visiting permissions")
                return
            if polleduuid not in self.data.Data:
                admin_player.message(
                    "&c%s does not have a home (you can set it for "
                    "him if he wants)" % username
                )
                return
            admin_player.message("&eWarping you %s's house..." % username)
            position = self.data.Data[polleduuid]
            self.api.minecraft.console("tp %s %s %s %s" % (
                admin_player.username, position[0], (position[1]),
                position[2]))
            return

    def _homes(self, player, args):
        if len(args) > 0:
            if args[0].lower() == "help":
                self._homes_help(player)
                return

        page = self.getint(self.getarg(args, 0))
        if page == 0:
            page = self.getint(self.getarg(args, 2))
        if page == 0:
            page = 1

        subcomm = self.getarg(args, 0).lower()
        textsearch = self.getarg(args, 1)
        searchradius = self.getint(textsearch)
        pos = player.getPosition()
        coords = (pos[0], pos[1], pos[2])
        xlow = self.getint(coords[0]) - searchradius
        xhigh = self.getint(coords[0]) + searchradius
        zlow = self.getint(coords[2]) - searchradius
        zhigh = self.getint(coords[2]) + searchradius

        homeslist = []
        homefound = False

        if subcomm in ("radius", "r", "rad") and searchradius > 0:
            for eachhome in self.data.Data:
                loc = self.data.Data[eachhome]
                playername = self.api.minecraft.lookupbyUUID(eachhome)
                textcoords = "%.1f, %.1f, %.1f" % (loc[0], loc[1], loc[2],)
                hx = self.getint(loc[0])
                hz = self.getint(loc[2])

                if (hx > xlow) and (hx < xhigh) and (hz > zlow) and (hz < zhigh):  # noqa
                    homeslist.append(
                        self._make_homes_item(playername, textcoords)
                    )
                    homefound = True

        elif subcomm in ("name", "n", "nm", "named") and textsearch != "":
            for eachhome in self.data.Data:
                loc = self.data.Data[eachhome]
                playername = self.api.minecraft.lookupbyUUID(eachhome)
                textcoords = "%.1f, %.1f, %.1f" % (loc[0], loc[1], loc[2],)
                search = playername.lower().find(textsearch.lower())
                if search != -1:
                    homeslist.append(
                        self._make_homes_item(playername, textcoords)
                    )
                    homefound = True

        else:
            for eachhome in self.data.Data:
                loc = self.data.Data[eachhome]
                playername = self.api.minecraft.lookupbyUUID(eachhome)
                textcoords = "%.1f, %.1f, %.1f" % (loc[0], loc[1], loc[2],)
                homeitem = self._make_homes_item(playername, textcoords)
                homeslist.append(homeitem)
                homefound = True

        if homefound is False:
            homeslist.append({"text": "No homes found!", "color": "red"})

        self.printlist(homeslist, "player homes", len(homeslist), player, page)
        return

    def _make_homes_item(self, playername, textcoords):
        returnitem = {
            "text": playername + "- ",
            "color": "gold",
            "extra": [{"text": textcoords,
                       "color": "dark_green",
                       "clickEvent": {
                           "action": "suggest_command",  # "run_command",
                           "value": "/home %s visit" % playername
                       },
                       "hoverEvent": {
                           "action": "show_text",
                           "value": {"text": "Visit %s's home" % playername,
                                     "color": "dark_blue",
                                     "bold": "false"}
                       }
                       },
                      {"text": " [X]",
                       "color": "dark_red",
                       "bold": "true",
                       "clickEvent": {
                           "action": "suggest_command",
                           "value": "/home %s delete" % playername},
                       "hoverEvent": {
                           "action": "show_text",
                           "value": {"text": "Delete %s's home!" % playername,
                                     "color": "dark_red"}
                       }
                       }
                      ]
        }
        return returnitem

    def _homes_help(self, player):
        player.message(
            {"text": "/homes ", "color": "gold", "extra":
                [{"text": "[page]", "color": "red"},
                 {"text": "-Display list of homes.",
                  "color": "white"}]})
        player.message(
            {"text": "/homes ", "color": "gold", "extra":
                [{"text": "<radius|name> <search criteria> [page]",
                  "color": "red"},
                 {"text": "-Search for specific homes.",
                  "color": "white"}]})
        player.message(
            {"text": "-page is optional, defaults to 1",
             "color": "yellow"})
        player.message(
            {
                "text": "-radius argument (number) is blocks distance "
                        "in a square.",
                "color": "yellow"})
        player.message(
            {
                "text": "-name argument is any text portion of player name.",
                "color": "yellow"})
        return

    def printlist(self, itemlist, itemdesc, linecount, playerobj, page):
        """
        'Takes an itemlist and prints it'
        :param itemlist: list of help items.
        :param itemdesc: name of items.
        :param linecount: total number of item lines
        :param playerobj: player object
        :param page: page to print (player.message)

        """
        # explicit floor division, converted to float 'x.0'
        pages = float(linecount // 7)
        # this means a partial page still exists
        if pages != linecount / 7.0:
            pages += 1
        if pages < 2:
            page = 1
        if page > pages:
            page = pages
        playerobj.message(
            {"text": "List of " + itemdesc + ": ", "color": "yellow",
             "extra": [{"text": "Page " + str(page) + " of " + str(pages),
                        "color": "green"}]
             }
        )
        y = (page - 1) * 7
        while y < ((page - 1) * 7) + 7:
            try:
                playerobj.message(itemlist[y])
            except Exception as e:
                print("error with printlist (SurestLib): \n%s" % e)
            y += 1
        return
