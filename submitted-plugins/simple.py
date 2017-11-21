# -*- coding: utf-8 -*-

from SurestLib import makenamevalid
from SurestLib import printlist
from SurestLib import permitted

from sys import version_info
PY3 = version_info > (3,)

if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range

# region Header
NAME = "Simple"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.simple"
VERSION = (0, 7, 0)  # the version number, with commas in place of periods. add more commas if needed.
SUMMARY = "Provide simple home sethome and mail commands"  # a quick, short summary of the plugin seen in /plugins
WEBSITE = "http://tic.theimaginecraft.com/plugins"  # the developer's or plugin's website
DESCRIPTION = "This is the basic 'simple' plugin to provide the basic everyday commands, like 'sethome', 'home', " \
              "spawn, etc.  A lightweight plugin to get some basic beyond-vanilla commands.  " \
              "Stores it's data using Global plugin."
DEPENDENCIES = ["global.py"]
DISABLED = True

# endregion


# noinspection PyBroadException,PyUnusedLocal
class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        self.globalset = api.getPluginContext("com.suresttexas00.plugins.global")
        self.config = self.globalset.config
        self.usePermissions = True  # Use Perms - 'toolbox.chunktools', etc
        self.useVanillaBehavior = True  # mask plugin - give generic "unknown command" message for non-permitted actons.

        self.pkt_playerlist = None

    def onEnable(self):
        # DATA - all data is in self.globalset

        self.api.registerHelp("Commands", "General commands on the server", [
            ("/spawn", "TP to the world spawn.", None),
            ("/back", "Return to a pervious location.", "simple.back"),
            ("/sethome", "Set your home and spawnpoint at your present position.", None),  # TODO
            ("/home", "TP to your home (must sethome first)", None),
            ("/mail <send|read|clear> <username|-all> <your message>", "Type /mail help for additional info.",
             "simple.mail"),
            ("/van <join|leave>",
             "Send player leave/join message to chat.  No argument causes removal from TAB list", "simple.van"),
            ("/suicide", "Kills you - beware of losing your stuff!", "simple.suicide")])

        self.api.registerEvent("server.started", self._server_up)

        # REGISTER COMMANDS
        self.api.registerCommand("spawn", self._spawn, None)
        self.api.registerCommand("back", self._back, "simple.back")
        self.api.registerCommand("sethome", self._sethome, None)  # TODO
        self.api.registerCommand("home", self._home, None)  # TODO
        # self.api.registerCommand("home", self._home, "simple.home")
        self.api.registerCommand("homes", self._homes, "staff.homes")  # TODO
        self.api.registerCommand("mail", self._mail, "simple.mail")
        self.api.registerCommand("van", self._van, "simple.van")
        self.api.registerCommand("suicide", self._suicide, None)
        self.api.registerCommand("clock", self._clock, None)

    def onDisable(self):
        pass

    def _server_up(self, payload):
        if self.pkt_playerlist is None:
            self.pkt_playerlist = self.api.minecraft.getServerPackets().PLAYER_LIST_ITEM

    def _clock(self, *args):
        player = args[0]
        arguments = args[1]
        timeformat = 2
        if len(arguments) > 0:
            timeformat = int(arguments[0])
        worldtime = self.api.minecraft.getTimeofDay(timeformat)
        if timeformat == 0:
            player.message("Time: %s ticks" % worldtime)
        else:
            player.message("Time: %s" % worldtime)
        pass

    def _suicide(self, *args):
        player = args[0]
        if permitted(player, "simple.suicide", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayer = str(player.username)
        if (player.getGamemode() == 2) or (player.getGamemode() == 3):
            if player.hasPermission("staff.hide"):
                player.setGamemode(0)
        if player.getDimension == 0:
            self.globalset.backlocation(player)
        self.api.minecraft.console("kill %s" % thisplayer)
        return

    def _spawn(self, player, args):
        if player.hasPermission("spawn.deny"):
            player.message("denied!")
            return
        # check for home qualification
        playeruuid = str(player.mojangUuid)
        playerhome = self.globalset.readhome(playeruuid)
        if playerhome[1] == 0:
            player.message({"text": "You may not return to spawn with out using /sethome first...", "color": "red"})
            return

        if not player.getDimension() == 0:
            player.message({"text": "Sorry, but the spawnpoint is in the overworld...", "color": "red"})
            return
        spawn = self.config["SlashSpawnCoords"].split(",")
        player.message("&eWarping to spawn...")
        self.globalset.backlocation(player)
        self.api.minecraft.console("tp %s %s %s %s" % (player.username, spawn[0], spawn[1], spawn[2]))
        player.setGamemode(0)

    def _back(self, player, args):
        if permitted(player, "simple.back", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if not player.getDimension() == 0:
            player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
            return
        placewas = self.globalset.playerdata[str(player.mojangUuid)]["back"]
        if len(placewas) == 1:
            placewas = placewas.split(",")
        if len(placewas) < 5:
            print(placewas)
            player.message({"text": "Some sort of error occured (invalid previous location)...", "color": "red"})
            return
        self.globalset.backlocation(player)
        self.api.minecraft.console("tp %s %s %s %s %s %s" %
                                   (player.username, placewas[0], placewas[1], placewas[2], placewas[3], placewas[4]))
        return

    def _sethome(self, player, args):
        if player.hasPermission("home.deny"):
            player.message("denied!")
            return
        if not player.getDimension() == 0:
            player.message({"text": "Sorry, but you can only set a home in the overworld...", "color": "red"})
            return
        if not player.getGamemode() == 0:
            player.message({"text": "Sorry, but you can only set a home in survival mode...", "color": "red"})
            return
        name = str(player.mojangUuid)
        if len(args) == 0:
            player.message({"text": "Home set!", "color": "gold"})
            positionofplayer = player.getPosition()
            coords = (positionofplayer[0], positionofplayer[1], positionofplayer[2])
            self.globalset.writehome(name, coords)
            self.api.minecraft.console("spawnpoint %s %s %s %s" % (player.username, coords[0], (coords[1]), coords[2]))
        else:
            player.message({"text": "sethome does not take any arguments!", "color": "red"})

    def _homes(self, player, args):
        if permitted(player, "staff.homes", self.usePermissions, self.useVanillaBehavior) is False:
            return
        # print args
        if len(args) > 0:
            if args[0].lower() == "help":
                player.message(
                    {"text": "/homes ", "color": "gold", "extra":
                        [{"text": "[page]", "color": "red"}, {"text": "-Display list of homes.", "color": "white"}]})
                player.message(
                    {"text": "/homes ", "color": "gold", "extra":
                        [{"text": "<radius|name> <search criteria> [page]", "color": "red"},
                         {"text": "-Search for specific homes.", "color": "white"}]})
                player.message(
                    {"text": "-page is optional, defaults to 1", "color": "yellow"})
                player.message(
                    {"text": "-radius argument (number) is blocks distance in a square.", "color": "yellow"})
                player.message(
                    {"text": "-name argument is any text portion of player name.", "color": "yellow"})
                return
        page = 0
        x = 0
        searchradius = 0
        homeslist = []
        textsearch = ""
        homefound = False
        positionofplayer = player.getPosition()
        pcoords = (positionofplayer[0], positionofplayer[1], positionofplayer[2])
        if len(args) == 1:
            try:
                page = int(args[0])
            except:
                pass
        if len(args) > 1 and args[0].lower() == "radius":
            try:
                searchradius = int(args[1])
            except:
                pass
        if len(args) > 1 and args[0].lower() == "name":
            try:
                textsearch = args[1]
            except:
                pass
        if len(args) > 2:
            try:
                page = int(args[2])
            except:
                pass
        if page == 0:
            page = 1
        xlow = int(pcoords[0]) - searchradius
        xhigh = int(pcoords[0]) + searchradius
        zlow = int(pcoords[2]) - searchradius
        zhigh = int(pcoords[2]) + searchradius
        for homex in self.globalset.homes["homes"]:
            try:
                nameofplayer = self.globalset.mail.key(homex)["humanname"]
                # nameofplayer = self.api.minecraft.lookupUUID(homex)["name"]
            except:
                nameofplayer = homex
            # ####### Fix old player records that are not in mail file
            #  MAIL SECTION
            # uuidbox = str(homex)
            # if uuidbox not in self.globalset.mail:
            #    self.globalset.mail[uuidbox] = {}
            # if "humanname" not in self.globalset.mail[uuidbox]:
            #    self.globalset.mail[uuidbox]["humanname"] = nameofplayer
            #    # this is not part of the "if..not in.." on purpose.. every logon we need the latest name with
            #    # this playerUUID. The idea, of course is future support of name changes...
            # if "inbox" not in self.globalset.mail[uuidbox]:
            #    self.globalset.mail[uuidbox]["inbox"] = {}
            # if "flag" not in self.globalset.mail[uuidbox]:
            #    self.globalset.mail[uuidbox]["flag"] = {}
            #    self.globalset.mail[uuidbox]["flag"] = "N"  # first time logon -we set mail flag down "N"
            # ##########
            if searchradius == 0 and textsearch == "":
                homecoord = str(self.globalset.homes["homes"][homex]).split(", ")
                homecoords = (homecoord[0]).split(".")[0].replace("[", "") + ", " + \
                             (homecoord[1]).split(".")[0] + ", " + (homecoord[2]).split(".")[0]
                homeslist.append({"text": nameofplayer + "- ", "color": "gold",
                                  "extra": [{"text": homecoords, "color": "dark_green"}]})
                x += 1
                homefound = True
            if searchradius != 0:
                homecoord = str(self.globalset.homes["homes"][homex]).split(", ")
                hx = int((homecoord[0]).split(".")[0].replace("[", "").replace("(", ""))
                hz = int((homecoord[2]).split(".")[0].replace("]", "").replace(")", ""))
                if (hx > xlow) and (hx < xhigh) and (hz > zlow) and (hz < zhigh):
                    homecoords = (homecoord[0]).split(".")[0].replace("[", "") + ", " + \
                                 (homecoord[1]).split(".")[0] + ", " + (homecoord[2]).split(".")[0]
                    homeslist.append({"text": nameofplayer + "- ", "color": "gold",
                                      "extra": [{"text": homecoords, "color": "dark_green"}]})
                    x += 1
                    homefound = True
            if textsearch != "":
                homecoord = str(self.globalset.homes["homes"][homex]).split(", ")
                search = nameofplayer.find(textsearch)
                if search != -1:
                    homecoords = (homecoord[0]).split(".")[0].replace("[", "") + ", " + \
                                 (homecoord[1]).split(".")[0] + ", " + (homecoord[2]).split(".")[0]
                    homeslist.append({"text": nameofplayer + "- ", "color": "gold",
                                      "extra": [{"text": homecoords, "color": "dark_green"}]})
                    x += 1
                    homefound = True
        if homefound is False:
            homeslist.append({"text": "No homes found!", "color": "red"})
        printlist(homeslist, "player homes", x, player, page)
        return

    def _home(self, player, args):
        # if permitted(player, "simple.home", self.usePermissions, self.useVanillaBehavior) is False:
        #    return
        if player.hasPermission("sethome.deny"):
            player.message("denied!")
            return
        if player.getDimension() != 0:
            player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
            return
        if player.hasPermission("staff.home") and (len(args) == 2):
            subcomm = args[1].lower()
            name = makenamevalid(self, args[0], False, False)
            nameuuid = makenamevalid(self, args[0], False, True)
            if subcomm in ("mandel", "mandelete", "manrem", "manremove", "deluuid"):
                if not (player.hasPermission("staff.home.admin")):  # only admin or higher has this perm
                    player.message("&cSorry, you dont have permission to delete homes.")
                    return
                nameuuid = args[0]
                try:
                    del self.globalset.homes["homes"][nameuuid]
                    player.message(
                        "&edeleted %s's house...You will need to reload the plugins to see changes." % nameuuid)
                except:
                    player.message("&cSorry, Could not locate %s's home entry." % nameuuid)
                return
            if name == "[]":
                player.message({"text": "Invalid name (check spelling and 'consider' using /alias?)", "color": "red"})
                return
            coords = self.globalset.readhome(nameuuid)
            if (subcomm in ("delete", "del", "rem", "remove")) and (
                    player.hasPermission("staff.home.admin")):  # only admin or higher has this perm
                if coords[1] == 0:
                    player.message("&c%s does not have a home to delete." % name)
                    return
                del self.globalset.homes["homes"][nameuuid]
                player.message("&edeleted %s's house...You will need to reload the plugins to see changes." % name)
                return
            if subcomm == "visit":
                if coords[1] == 0:
                    player.message("&c%s does not have a home (you can set it for him if he wants)" % name)
                    return
                player.message("&eWarping you %s's house..." % name)
                self.globalset.backlocation(player)
                self.api.minecraft.console("tp %s %s %s %s" % (player.username, coords[0], (coords[1]), coords[2]))
                if player.hasPermission("staff.hide") and (player.getGamemode() != 3):
                    player.setGamemode(3)
                return
            if subcomm == "set":
                if coords[1] == 0 or (player.hasPermission("staff.home.admin")):
                    positionofplayer = player.getPosition()
                    coords = (positionofplayer[0], positionofplayer[1], positionofplayer[2])
                    self.globalset.writehome(nameuuid, coords)
                    self.api.minecraft.console("spawnpoint %s %s %s %s" % (name, coords[0], (coords[1]), coords[2]))
                    affirmation = ("Sethome for %s.  When he dies or executes /home, he will spawn here" % name)
                    player.message({"text": affirmation, "color": "gold"})
                    return
                player.message("&cYou can't create a home for %s - this feature is only "
                               "allowed to be used once for a new player." % name)
                return
            player.message({"text": "Usage - /home <player> <visit/set/delete>", "color": "red"})
            return
        name = str(player.mojangUuid)
        if len(args) == 0:
            coords = self.globalset.readhome(name)
            if coords[1] == 0:
                player.message("&c&lYou never set a home! type /sethome first..")
                return
            player.message("&eWarping you home...")
            self.globalset.backlocation(player)
            self.api.minecraft.console("tp %s %s %s %s" % (player.username, coords[0], (coords[1]), coords[2]))
            self.api.minecraft.console(
                "spawnpoint %s %s %s %s" % (player.username, coords[0], (coords[1] + 1), coords[2]))
            if (player.getGamemode() == 2) or (player.getGamemode() == 3):
                player.setGamemode(0)
            return
        else:
            if player.hasPermission("staff.home"):
                player.message({"text": "Usage - /home [<player> <visit/set>]", "color": "red"})
            else:
                player.message({"text": "home does not take any arguments!", "color": "red"})
            return

    def _van(self, player, args):
        if permitted(player, "simple.van", self.usePermissions, self.useVanillaBehavior) is False:
            return
        playersonline = self.minecraft.getPlayers()
        playeruuid = player.serverUuid  # or should it be offlineUuid?
        vanisher_name = player.username
        playerleft = False
        if len(args) == 1:
            rawtext = {"text": "", "color": "yellow", "extra": [{"text": str(player.username),
                                                                 "color": "aqua"}, {"text": " left the game"}]}
            if args[0].lower() == "leave":
                playerleft = True
                player.setGamemode(3)
            if args[0].lower() == "join":
                # self.api.minecraft.console('/tellraw @a {"translate":"multiplayer.player.joined",\
                # "with":["%s"]}' % player.username)
                rawtext = {"text": "", "color": "yellow", "extra": [{"text": str(player.username),
                                                                     "color": "aqua"}, {"text": " joined the game"}]}
            for playerXX in playersonline:
                eachplayer = self.api.minecraft.getPlayer(playerXX)
                eachplayer.message(rawtext)

        if len(args) == 0 or playerleft is True:  # remove player from all logged in tab lists
            for playerXX in playersonline:
                if vanisher_name != self.api.minecraft.getPlayer(playerXX).username:
                    self.api.minecraft.getPlayer(playerXX).client.send(self.pkt_playerlist,
                                                                       "varint|varint|uuid", (4, 1, playeruuid))

    def _namevalid(self, namedplayer):  # wrapper of makenamevalid(name, False, True) now - just returns UUID
        returnuuid = makenamevalid(self, namedplayer, online=False, return_uuid=True)
        if returnuuid == "[]":  # if we did not find a name match, ie a UUID...
            returnuuid = "-nope"
        return returnuuid

    def _mail(self, player, args):
        if permitted(player, "simple.mail", self.usePermissions, self.useVanillaBehavior) is False:
            return
        subcommand2 = ""
        mess = ""
        listedplayer = ""
        subcommand = "show"
        if len(args) > 0:
            subcommand = str(args[0])
        if len(args) > 1:
            subcommand2 = str(args[1]).lower()
        if len(args) > 2:
            for x in xrange(2, len(args)):
                mess = "%s%s " % (mess, str(args[x]))
                mess = mess.replace("\"", "'")
        if subcommand2 != "":
            if (subcommand2 in ("console", "[console]")) and (subcommand == "read"):
                subcommand2 = "[CONSOLE]"
            listedplayer = subcommand2
            subcommand2 = makenamevalid(self, subcommand2, False, False)
        if subcommand == "show":
            nomail = True
            for x in self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"]:
                player.message({"text": "Message from: " + str(x), "color": "yellow"})
                nomail = False
            if nomail is True:
                player.message({"text": "There are no messages in your inbox", "color": "yellow"})
                return
            player.message({"text": "Type /mail read <username> to read messages.", "color": "green"})
            player.message({"text": "Type /mail send <username> <message> to send a message.", "color": "green"})
            return
        if subcommand == "clear":
            if self.globalset.mail[str(self._namevalid(str(player.username)))]["flag"] == "Y":
                player.message({"text": "Can't clear your mailbox because new mail just came in!", "color": "red"})
                player.message({"text": "Please use /mail read first.", "color": "red"})
                return
            if subcommand2 == "":
                self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"] = {}
                player.message({"text": "Mailbox cleared!", "color": "yellow"})
            else:
                if subcommand2.lower() == "console":
                    subcommand2 = "[CONSOLE]"
                for _ in self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"]:
                    if subcommand2 in self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"]:
                        del self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"][subcommand2]
                        player.message({"text": "deleted all messages from " + subcommand2, "color": "yellow"})
                        return
                player.message({"text": "There were no messages from a player called " + subcommand2, "color": "red"})
                return
            return
        if subcommand == "read":
            if listedplayer == "":
                nomail = True
                for x in self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"]:
                    mess = str(self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"][str(x)])
                    player.message({"text": "Message(s) from " + str(x) + ":", "color": "yellow"})
                    player.message({"text": mess, "color": "aqua"})
                    self.globalset.mail[str(self._namevalid(str(player.username)))]["flag"] = "N"
                    nomail = False
                if nomail is True:
                    player.message({"text": "There are no messages in your inbox", "color": "yellow"})
                    return
                player.message({"text": "Use /mail read <username> to just see one player's message", "color": "gold"})
                return
            else:
                if listedplayer == "[CONSOLE]":
                    subcommand2 = "[CONSOLE]"
                for _ in self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"]:
                    if subcommand2 in self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"]:
                        mess = str(
                            self.globalset.mail[str(self._namevalid(str(player.username)))]["inbox"][subcommand2])
                        player.message({"text": "Message(s) from " + subcommand2 + ":", "color": "yellow"})
                        player.message({"text": mess, "color": "aqua"})
                        self.globalset.mail[str(self._namevalid(str(player.username)))]["flag"] = "N"
                        return
                player.message({"text": "There are no messages from a player called " + listedplayer, "color": "red"})
                return
        if subcommand == "send" and (not subcommand2 == "") and (not mess == ""):
            if listedplayer == "-all":
                if not player.hasPermission("simple.mail.all"):
                    player.message({"text": "You do not have permission to use '-all'.", "color": "red"})
                    return
                for idlookup in self.globalset.mail:
                    if "[CONSOLE]" not in self.globalset.mail[str(idlookup)]["inbox"]:
                        self.globalset.mail[str(idlookup)]["inbox"]["[CONSOLE]"] = ""
                    self.globalset.mail[str(idlookup)]["inbox"]["[CONSOLE]"] = \
                        str(self.globalset.mail[str(idlookup)]["inbox"]["[CONSOLE]"]) + "-" + mess + """
"""                          # line break
                    self.globalset.mail[str(idlookup)]["flag"] = "Y"
                player.message({"text": "Broadcast message sent!", "color": "yellow"})
                return
            returneduuid = self._namevalid(subcommand2)
            if str(returneduuid) == "-nope":
                errtext = (
                    "No mailbox for '%s' was found!  Either you typed the name incorrectly or they have not been on "
                    "this server since the mail function was added." % listedplayer)
                player.message({"text": errtext, "color": "red"})
                return
            else:
                # player.message("found player %s as UUID:%s" % (subcommand2, returneduuid))
                if str(player.username) not in self.globalset.mail[returneduuid]["inbox"]:
                    # incoming mail is simply organized by player name, not UUIDs
                    self.globalset.mail[returneduuid]["inbox"][str(player.username)] = ""  # create item is not existing
                self.globalset.mail[returneduuid]["inbox"][str(player.username)] = \
                    str(self.globalset.mail[returneduuid]["inbox"][str(player.username)]) + mess + """
"""      # break the lines up
                self.globalset.mail[returneduuid]["flag"] = "Y"
                player.message({"text": "Message sent!", "color": "yellow"})
                return
        if subcommand == "help":
            player.message(
                {"text": "/mail", "color": "dark_green", "extra":
                    [{"text": " - <send/read/clear/show> <username/-all> <your message> ", "color": "red"},
                     {"text": "A username is required to 'send' a message.  Username is optional for 'read' and clear."
                              "  if a username is not specified, read shows all mails in inbox. You must type the "
                              "user's name exactly.  Only console OP can mail '-all'.  'show' displays a list of users"
                              " who have mail for you.", "color": "white"}]})
            return
        player.message({"text": "Command format/arguments incorrect - Try /mail help for help.", "color": "red"})
