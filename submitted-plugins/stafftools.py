# -*- coding: utf-8 -*-

from SurestLib import makenamevalid
from SurestLib import printlist
from SurestLib import permitted

from sys import version_info
PY3 = version_info > (3,)

if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range

NAME = "Admins"  # the visible name of the plugin, seen in /plugins and whatnot.
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.staff"  # the ID of the plugin, used internally for storage
VERSION = (0, 7, 0)  # the version number, with commas in place of periods. add more commas if needed.
SUMMARY = "Staff tools."  # a quick, short summary of the plugin seen in /plugins
WEBSITE = "http://tic.theimaginecraft.com/plugins"  # the developer's or plugin's website
DESCRIPTION = "Handles implementation of staff privilege commands.  Things like /ban, " \
              "/warps /gm3 /gm /kick /mute, etc."
DEPENDENCIES = ["global.py", "vanillaclaims.py"]
DISABLED = True
ENFORCESURVIVALGAMEMODE = True


# noinspection PyBroadException
class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        self.useVanillaBehavior = True  # mask staff plugin.  Give "unknown command" message.
        self.usePermissions = True  # use permissions (not consistent in some plugins -only applies to actual command)

        self.claimsdata = self.api.getPluginContext("com.suresttexas00.plugins.vanillaclaims")
        self.globalset = self.api.getPluginContext("com.suresttexas00.plugins.global")
        self.staff = self.api.getStorage("Staff", True)  # this is a test

    def onEnable(self):

        # region DEFAULTS
        if "warps" not in self.staff:
            self.staff["warps"] = {}
        # endregion

        self.api.registerHelp("Commands", "General commands on the server", [
            ("/home <player> <visit|set>", "Set a new player's home or TP to an existing home.", "staff.home"),  # TODO
            ("/home <player|UUID> <set|del|mandel>",  # TODO
             "Set/delete any player's home. Manual delete requires UUID", "staff.home.admin"),
            ("/homes <radius|name|help/[page])> <search criteria> [page]",  # TODO
             "list existing player homes.", "staff.homes"),
            # ("/ban <player> <reason>", "Ban player", "staff.ban"),
            # ("/xban <player> <reason>", "Ban player, even if he has never been on before", "staff.ban.x"),
            # ("/sudo <player> <Command ... >", "Run a command/chat as <player>", "staff.sudo"),
            ("/speed <number> [fly/walk]", "change your speed (only flight works)", "staff.speed"),
            ("/namechange <oldname> <newname> [override]", "give player a new name [override] changes"
                                                           "name without moving their player file",
                                                           "staff.namechange"),
            ("/filter add|del|list <desired> <undesireable text> [forceAll substitution? T/F]",
             "Substitute objectionable text", "staff.filter"),
            ("/delwarp <warp name>", "delete a warp", "staff.delwarp"),
            ("/setwarp <warp name>", "set a warp", "staff.setwarp"),
            ("/pop <player>", "'pops' a player open, killing him, spilling his inventory", "staff.pop"),
            ("/warps", "list of warps", None),
            ("/warp <name>", "warp to <name>", None),
            ("/nether", "sends you to nether", "staff.nether"),
            ("/end", "sends you to the end", "staff.end"),
            ("/erasep",
             "when you use /nether or /end, overworld portals are created that should be erased when you are done",
             "staff.erasep"),
            ("/suicide", "Kills you - beware of losing your stuff!", "simple.suicide"),
            ("/addmember <player>", "adds <player> to 'member' rank!", "staff.promote.member"),
            ("/gamemode 3", "(/gm 3|/gm3) Switches gamemode to Spectator", "staff.gm3"),
            ("/gamemode 2",
             "(/gm 2|/gm2) Switches gamemode to Adventure (use /home /spawn to revert to survival)", "staff.gm2"),
            ("/tpto <player>", "TP to player.", "staff.tpto"),
            ("/website", "display a link to our website", "staff.website"),
            ("/alias <add|del|list> <desired name/command> <Current name/command>",
             "Rename command or player", "staff.alias"),
            ("/kick <player> <reason>", "Kick player, reason must be specified", "staff.kick")
            # ("/mute <player>", "mute a player", "staff.mute"),
            # ("/unmute <player>", "unmute a player", "staff.unmute")
            ])

        # region REGISTER COMMANDS
        self.api.registerCommand("filter", self._filter, None)
        # self.api.registerCommand("xban", self._xban, None)
        # self.api.registerCommand("ban", self._ban, "staff.ban")
        self.api.registerCommand("namechange", self._namechange, None)
        # self.api.registerCommand("sudo", self._sudo, None)
        self.api.registerCommand("pop", self._pop, None)
        self.api.registerCommand("speed", self._speed, None)
        self.api.registerCommand("seen", self._seen, None)
        self.api.registerCommand("delwarp", self._delwarp, None)
        self.api.registerCommand("setwarp", self._setwarp, None)
        self.api.registerCommand("warps", self._warps, None)
        self.api.registerCommand("warp", self._warp, None)
        self.api.registerCommand("erasep", self._erasep, None)
        self.api.registerCommand("nether", self._nether, None)
        self.api.registerCommand("end", self._end, None)
        self.api.registerCommand(("gm", "gamemode"), self._gamemode, "staff.gm")
        self.api.registerCommand("gm3", self._gm3, None)
        self.api.registerCommand("gm2", self._gm2, None)
        self.api.registerCommand("tpto", self._tpto, None)
        self.api.registerCommand("alias", self._alias, None)
        self.api.registerCommand("kick", self._kick, None)
        # self.api.registerCommand("mute", self._mute, None)
        # self.api.registerCommand("unmute", self._unmute, None)
        self.api.registerCommand(("addmember", "makemember"), self._makemember, None)
        self.api.registerCommand("website", self._website, "staff.website")
        # self.api.registerCommand("//try", self._try, "execute.code")

        # social spy for OPS - these get registered in leiu of the minecraft command
        self.api.registerCommand(("tell", "msg", "m", "whisper", "wh", "w"), self._tell, None)
        """end register commands section"""
        # endregion

    def onDisable(self):
        self.staff.close()

    # def _try(self, *args):
    #    player = args[0]
    #    x = ""
    #    wrapper = self.api.minecraft.wrapper
    #    print("V3")
    #    comm = " ".join(args[1])
    #    comms = comm.split("%%")
    #    for commands in comms:
    #        print(commands)
    #        exec(commands)
    #    player.message("%s - done!" % x)

    def _tell(self, player, args):
        # check to make sure there are arguments
        if len(args) <= 1:
            player.message({"text": "Usage: /tell <player> <private message ...>", "color": "red"})
            return
        # set some variables
        otherplayer = str(makenamevalid(self, args[0], True, False))
        if otherplayer == "[]":
            player.message({"text": "That player cannot be found", "color": "red"})
            return
        mess = ""
        playerisop = False  # in this context, has spcial spy permissions....
        targetison = False
        targetisop = False
        if player.hasPermission("staff.socialspy"):
            playerisop = True
        for index in range(len(args) - 1):
            mess = mess + args[index + 1] + " "
        mess = mess.replace("\"", "'")
        # Error checking for not self
        if otherplayer == player.username:
            player.message({"text": "You can't send a private message to yourself!", "color": "red"})
            return
        # Error checking for valid otherplayer and if he has social spy permissions
        for playernames in self.api.minecraft.getPlayers():
            if str(self.api.minecraft.getPlayer(playernames) == str(otherplayer)):
                targetison = True
            if self.api.minecraft.getPlayer(otherplayer).hasPermission("staff.socialspy"):
                targetisop = True
        # The MEAT of function
        if targetison is True:
            if not playerisop:  # just do what /tell usually does if source player not OP
                player.message("&7&oYou whisper to %s: %s" % (otherplayer, mess))			# client only message
            else:
                # The op should get to see his own message..
                optext2 = {"text": "You-> " + otherplayer + "]: " + mess, "color": "aqua"}
                player.message(optext2)													# client only message
            ############
            if not targetisop:		# send message to destination player in standard minecraft format if he
                                    # is not OP either
                rawtext = player.username + " whispers to you: " + mess
                rawtext = "{\"text\":" + "\"" + rawtext + "\"" + ", \"color\":\"gray\", \"italic\":\"true\"}"
                self.api.minecraft.console(
                    "tellraw %s %s" % (otherplayer, rawtext))  # RAW To destination client
            else:
                # if target is an OP, he should get the message in an upgraded format because we will
                # #	not include it in his social spy (other Ops get it though)
                optext2 = "{\"text\": \"%s-> You] %s\", \"color\": \"aqua\"}" % (player.username, mess)
                self.api.minecraft.console(
                    "tellraw %s %s" % (otherplayer, optext2))  # RAW To destination client
            # socialspy text for op display------------------------------
            optext2 = "{\"text\": \"%s->%s: \", \"color\": \"aqua\", \"color\": " \
                      "\"gray\", \"extra\": [{\"text\": \"%s\"," \
                      " \"color\": \"aqua\"}]}" % (player.username, otherplayer, mess)
            # this will loop through all players and message them if they are op
            for opdex in self.api.minecraft.getPlayers():
                if self.api.minecraft.getPlayer(opdex).hasPermission("staff.socialspy"):
                    if str(self.api.minecraft.getPlayer(opdex)) == str(player.username):
                        # if this OP is the message originator,
                        pass
                        # no need to do anything
                    elif str(self.api.minecraft.getPlayer(opdex)) == str(otherplayer):
                        # if this OP is the other player, he already got message!
                        pass
                    else:
                        # if op was not a party in the converation or it is a no-op conversation,
                        # it is sent to destination OP using default format
                        self.api.minecraft.console(
                            "tellraw %s %s" % (self.api.minecraft.getPlayer(opdex), optext2))
        else:
            player.message({"text": "That player cannot be found", "color": "red"})
            return

    def _sudo(self, player, args):
        if permitted(player, "staff.sudo", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) > 1:
            otherplayername = str(makenamevalid(self, args[0], True, False))
            try:
                otherplayer = self.minecraft.getPlayer(otherplayername)
            except:
                player.message({"text": "That player cannot be found", "color": "red"})
                return
            if otherplayer.isOp() or otherplayer.hasPermission("staff.sudo.block"):
                player.message("&cYou're not allowed to impersonate %s!" % otherplayername)
                return
            otherplayer.say(" ".join(args[1:]))
        else:
            player.message("&cUsage: /sudo <username> <command ...>")

    def _namechange(self, player, args):
        if permitted(player, "staff.namechange", self.usePermissions, self.useVanillaBehavior) is False:
            return

        oldname = self.api.utils.getArgs(args, 0)
        newname = self.api.utils.getArgs(args, 1)

        mojang_uuid = self.api.minecraft.lookupUUID(oldname)
        if self.api.minecraft.setLocalName(mojang_uuid, newname):
            player.message("operation succeeded...")
        else:
            player.message("&cThe operation may not have completely succeeded.  Check the "
                           "console/logs for information about this")

    def _xban(self, player, args):
        # deprecating this...
        if permitted(player, "staff.ban.x", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayer = str(player.username)
        if len(args) < 1:
            player.message({"text": "Usage: /xban <player> <reason>", "color": "red"})
            return
        reason = ""
        if len(args) < 2:
            reason = "The Ban Hammer has Spoken!"
        else:
            for x in xrange(1, len(args)):
                reason = reason + str(args[x]) + " "
            reason = reason.replace("\"", "'")
        targetplayer = str(makenamevalid(self, args[0], False, False))
        if targetplayer == "[]":
            targetplayer = args[0]
            self.api.minecraft.console("ban %s %sby %s" % (targetplayer, reason, thisplayer))
            player.message({"text": "Ban request sent to Console for processing:", "color": "yellow"})
            player.message("ban %s %sby %s" % (targetplayer, reason, thisplayer))
            return
        else:
            player.message("Player %s has been on this server.  Use /ban instead." % (str(args[0])))
            return

    def _ban(self, player, args):
        # TODO fix for wrapper bans
        thisplayer = str(player.username)
        if len(args) < 1:
            player.message({"text": "Usage: /ban <player> <reason>", "color": "red"})
            return
        if len(args) < 2:
            player.message({"text": "Usage: /ban <player> <MUST GIVE A REASON!>", "color": "red"})
            return
        reason = ""
        for x in xrange(1, len(args)):
            reason = reason + str(args[x]) + " "
        reason = reason.replace("\"", "'")
        targetplayer = str(makenamevalid(self, args[0], False, False))
        if targetplayer == str(player.username):
            player.message({"text": "You can't ban yourself!", "color": "red"})
            return
        if targetplayer != "[]":
            self.api.minecraft.console("ban %s %sby %s" % (targetplayer, reason, thisplayer))
            player.message({"text": "Ban request sent to Console for processing:", "color": "yellow"})
            player.message("ban %s %sby %s" % (targetplayer, reason, thisplayer))
            return
        else:
            player.message(
                "you want to ban %s but that player has not been on.  Did you spell the name correctly?"
                % (str(args[0])))
            return

    def _pop(self, player, args):
        if permitted(player, "staff.pop", self.usePermissions, self.useVanillaBehavior) is False:
            return
        target = args[0]
        self.api.minecraft.console("gamerule keepInventory false")
        self.api.minecraft.console("kill %s" % target)
        self.api.minecraft.console("gamerule keepInventory true")
        return

    def _speed(self, player, args):
        if permitted(player, "staff.speed", self.usePermissions, self.useVanillaBehavior) is False:
            return
        gamemode = player.getGamemode()
        arg0, arg1, bitflags = 1.0, "fly", 0x00
        if gamemode == 1:
            bitflags += 0x05
        if gamemode == 3:
            bitflags += 0x04
        try:
            arg0 = float(args[0]) / 10.0
            arg1 = args[1]
        except:
            pass
        fly = 0.05
        walk = 0.1
        value = arg0
        if arg1 == "walk":
            walk = arg0
        else:
            fly = arg0 / 2
            if gamemode == 1 or gamemode == 3:
                bitflags += 0x02
        if value > 0.3:
            if not player.hasPermission("staff.speed.high"):
                player.message({"text": "You don't have permission to go that fast.", "color": "red"})
                return
        if 0.3 < value < 0.6:
            if not player.hasPermission("staff.speed.overspeed"):
                player.message({"text": "You don't have permission to go that fast.", "color": "red"})
                return
            player.message({"text": "Overspeed limit exceeded..", "color": "red"})
        if value >= 0.6:
            if not player.hasPermission("staff.speed.op"):
                player.message({"text": "You don't have permission to go that fast.", "color": "red"})
                return
            player.message({"text": "You're speed is dangerously high! CAUTION!", "color": "red"})
        player.fly_speed = fly
        player.field_of_view = walk
        # player.creative = bitflags
        player.setPlayerAbilities(True)

    def _seen(self, player, args):
        if permitted(player, "staff.seen", self.usePermissions, self.useVanillaBehavior) is False:
            return
        arg0 = self.api.utils.getArgs(args, 0)
        if arg0 == "":
            player.message({"text": "No argument specified.", "color": "red"})
            player.message({"text": "Usage: /seen <name> [search]", "color": "red"})
            return
        arg1 = self.api.utils.getArgs(args, 1)

        x = len(arg0.split("."))
        if x != 4:  # if it is not an "x.x.x.x" IPv4, then a "name"
            targetplayername = str(makenamevalid(self, arg0, False, False))
            targetplayeruuid = str(makenamevalid(self, args[0], False, True))

            if (targetplayername == "[]" or targetplayeruuid == "[]") and arg1 != "search":
                player.message({"text": "Invalid name/ip.", "color": "red"})
                player.message(
                    {"text": "You can ignore this by using '/seen <name> search' to force lookup names",
                     "color": "green"})
                return

            # get their offline uuid (server uuid)
            offlineuuid = str(self.api.minecraft.getOfflineUUID(arg0))

            # Process invalid names (perform lookup).
            if targetplayername == "[]" or targetplayeruuid == "[]":

                # Get real UUID (if valid)
                mojanguuid = str(self.api.minecraft.lookupbyName(arg0))
                if mojanguuid is False:
                    mojanguuid = "invalid Mojang account"

                # Get the name (if Mojang UUID was valid)
                correctcaps = str(self.api.minecraft.lookupbyUUID(mojanguuid))
                if correctcaps is False:
                    correctcaps = "invalid Mojang account"
                else:
                    # Recalculate the offline hash for the new capitalization spelling
                    offlineuuid = str(self.api.minecraft.getOfflineUUID(targetplayername))

                player.message("")
                player.message(
                    {"text": arg0 + " was never HERE, but...", "color": "dark_purple"})
                player.message(
                    {"text": "Local UUID:   ", "color": "dark_purple",
                     "extra": [{"text": offlineuuid, "color": "gold"}]})
                player.message(
                    {"text": "Mojang UUID:  ", "color": "dark_purple",
                     "extra": [{"text": mojanguuid, "color": "gold"}]})
                if mojanguuid != "invalid Mojang account":
                    player.message(
                        {"text": "Proper capitalization:  ",
                         "color": "dark_purple", "extra": [{"text": correctcaps, "color": "gold"}]})
                    player.message(
                        {"text": "Correct Local UUID:  ",
                         "color": "dark_purple", "extra": [{"text": offlineuuid, "color": "gold"}]})
                    return
                return
            if targetplayeruuid not in self.globalset.playerdata:
                player.message("")
                player.message({"text": "Very limited information is available for this older player:",
                                "color": "dark_purple"})
                player.message({"text": "Player Name:  ", "color": "dark_purple",
                                "extra": [{"text": targetplayername, "color": "dark_green"}]})
                player.message({"text": "Local UUID:   ", "color": "dark_purple",
                                "extra": [{"text": offlineuuid, "color": "dark_green"}]})
                player.message({"text": "Mojang UUID:  ", "color": "dark_purple",
                                "extra": [{"text": targetplayeruuid, "color": "dark_green"}]})
                return
            if "IP" not in self.globalset.playerdata[targetplayeruuid]:
                player.message("")
                player.message({"text": "Only limited information is available:", "color": "dark_purple"})
                player.message({"text": "Player Name:  ", "color": "dark_purple",
                                "extra": [{"text": targetplayername, "color": "dark_green"}]})
                player.message({"text": "Local UUID:   ", "color": "dark_purple",
                                "extra": [{"text": offlineuuid, "color": "dark_green"}]})
                player.message({"text": "Mojang UUID:  ", "color": "dark_purple",
                                "extra": [{"text": targetplayeruuid, "color": "dark_green"}]})
                return
            if "Dim" not in self.globalset.playerdata[targetplayeruuid]:
                self.globalset.playerdata[targetplayeruuid]["Dim"] = {}
            if "Pos" not in self.globalset.playerdata[targetplayeruuid]:
                self.globalset.playerdata[targetplayeruuid]["Pos"] = {}
            hisip = self.globalset.playerdata[targetplayeruuid]["IP"]
            hispos = self.globalset.playerdata[targetplayeruuid]["Pos"]
            hisdim = self.globalset.playerdata[targetplayeruuid]["Dim"]
            lastlogin = self.globalset.playerdata[targetplayeruuid]["lastLoginDim"] + " " \
                + str(self.globalset.playerdata[targetplayeruuid]["lastLogin"])
            player.message("")
            player.message({"text": "About " + targetplayername + " -", "color": "dark_purple"})
            player.message({"text": "Local UUID:  ", "color": "gold",
                            "extra": [{"text": offlineuuid, "color": "dark_green"}]})
            player.message({"text": "Online UUID: ", "color": "gold",
                            "extra": [{"text": targetplayeruuid, "color": "dark_green"}]})
            player.message({"text": "Last login:  ", "color": "gold",
                            "extra": [{"text": lastlogin, "color": "dark_green"}]})
            player.message({"text": "IP Address:  ", "color": "gold",
                            "extra": [{"text": hisip, "color": "dark_blue",
                                       "clickEvent": {"action": "open_url",
                                                      "value": "https://db-ip.com/%s" % hisip
                                                      }}]})
            player.message({"text": "Last pos:    ", "color": "gold",
                            "extra": [{"text": str(hispos), "color": "purple",
                                       "clickEvent": {"action": "run_command",
                                                      "value": "/tp %d %d %d\n" % (hispos[0], hispos[1], hispos[2], )
                                                      }
                                       }]})
            player.message({"text": "Last dimens: ", "color": "gold", "extra": [
                {"text": str(hisdim).replace("0", "World").replace("-1", "Nether").replace("1", "End"),
                 "color": "dark_green"}]})
            return

    def _setwarp(self, player, args):
        if permitted(player, "staff.setwarp", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) >= 1:
            warp = args[0].lower()  # new warps are case insensitive
            node = "staff"
            if len(args) > 1:
                node = args[1]
            pos = player.getPosition()  # retrieves (x, y, x, yaw, pitch)
            self.staff["warps"][warp] = (pos[0], pos[1], pos[2], node, pos[3], pos[4])
            player.message({"text": "Created warp '%s'." % warp, "color": "yellow"})
        else:
            player.message({"text": "Usage: /setwarp <name> [permissionnode]", "color": "red"})
            player.messsage(" - Don't use [permissionnode], Unless you know the available permissions.")

    def _delwarp(self, player, args):
        if permitted(player, "staff.delwarp", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) == 1:
            warp = args[0]  # delwarp must be CaSe EXact match...
            if warp not in self.staff["warps"]:
                player.message({"text": "The warp '%s' doesn't exist." % warp, "color": "red"})
                return
            del self.staff["warps"][warp]
            player.message({"text": "deleted warp '%s'." % warp, "color": "yellow"})
        else:
            player.message({"text": "Usage: /delwarp <name>", "color": "red"})

    def _warp(self, player, args):
        if player.hasPermission("warp.deny"):
            player.message("denied!")
            return
        if len(args) == 1:
            warp = args[0]
            if warp not in self.staff["warps"]:
                player.message({"text": "The warp '%s' doesn't exist." % warp, "color": "red"})
                return False
            perm = "staff.warp"
            if len(self.staff["warps"][warp]) > 3:
                perm = "%s.warp" % (self.staff["warps"][warp][3])
            if player.hasPermission(perm) or (perm.lower() == "none.warp") or \
                    player.hasPermission("staff.warp.allwarps"):
                player.message({"text": "Teleporting you to '%s'." % warp, "color": "green"})
                if len(self.staff["warps"][warp]) > 5:
                    self.globalset.backlocation(player)
                    self.api.minecraft.console("tp %s %d %d %d %d %d"
                                               % (player.username, self.staff["warps"][warp][0],
                                                  self.staff["warps"][warp][1], self.staff["warps"][warp][2],
                                                  self.staff["warps"][warp][4], self.staff["warps"][warp][5]))
                else:
                    self.api.minecraft.console("tp %s %d %d %d"
                                               % (player.username, self.staff["warps"][warp][0],
                                                  self.staff["warps"][warp][1], self.staff["warps"][warp][2]))
                if player.hasPermission("staff.hide") and (perm == "staff.warp") and player.getGamemode() != 3:
                    player.setGamemode(3)
                    return
                if ENFORCESURVIVALGAMEMODE:
                    player.setGamemode(0)
            else:
                player.message({"text": "The warp '%s' doesn't exist..." % warp, "color": "red"})
        else:
            player.message({"text": "Usage: /warp <name>", "color": "red"})
            player.message({"text": "       /warps (see the list of warps)", "color": "white"})

    def _warps(self, *args):
        player = args[0]
        warplist = []
        for warp in self.staff["warps"]:
            perm = "%s.warp" % (self.staff["warps"][warp][3])
            if (perm.lower() == "none.warp") or player.hasPermission(perm) or \
                    player.hasPermission("staff.warp.allwarps"):
                if player.hasPermission("staff.warp.allwarps"):
                    warplist.append(warp + "(" + self.staff["warps"][warp][3] + ")")
                else:
                    warplist.append(warp)
        warptext = ", ".join(warplist)
        displaytext = {"text": "List of warps:  ", "color": "yellow", "extra": [{"text": warptext, "color": "green"}]}
        player.message(displaytext)

    def _gamemode(self, player, args):
        if len(args) < 1:
            player.message("&cYou did not specify a gamemode!")
            return
        if args[0][:2].lower() == "sp":
            args[0] = "3"
        if (args[0][:1]).lower() in ("0", "1", "2", "3", "c", "s", "a"):
            args[0] = (args[0][:1]).lower()
        else:
            player.message("&cNot a valid gamemode number.")
            return
        playername = str(player.username)
        if len(args) > 1:
            playername = str(makenamevalid(self, args[1], True, False))
        if playername == "[]":
            playername = str(player.username)
        if str(player.username) != playername and not player.hasPermission("staff.gm.others"):
            player.message("&cNo permission to set another's gamemode!")
            return
        if not player.hasPermission("staff.gm3") and args[0] == "3":
            player.message("&cNo permission to set gamemode 3!")
            return
        if not player.hasPermission("staff.gm2") and args[0] in ("a", "2"):
            player.message("&cNo permission to set gamemode 2!")
            return
        if not player.hasPermission("staff.gm1") and args[0] in ("c", "1"):
            player.message("&cNo permission to set creative mode!")
            return
        if not player.hasPermission("staff.gm0") and args[0] in ("s", "0"):
            player.message("&cNo permission to set gamemode!")
            return
        self.api.minecraft.console("gamemode %s %s" % (args[0], playername))

    def _gm3(self, *args):
        player = args[0]
        if permitted(player, "staff.gm3", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayer = str(player.username)
        self.api.minecraft.console("gamemode 3 %s" % thisplayer)
        return

    def _gm2(self, *args):
        player = args[0]
        if permitted(player, "staff.gm2", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayer = str(player.username)
        self.api.minecraft.console("gamemode 2 %s" % thisplayer)
        return

    def _erasep(self, *args):
        player = args[0]
        if permitted(player, "staff.erasep", self.usePermissions, self.useVanillaBehavior) is False:
            return
        spawn = self.api.minecraft.getSpawnPoint()
        self.api.minecraft.console(
            "fill %s 251 %s %s 251 %s minecraft:glass" % (spawn[0] + 4, spawn[2] - 2, spawn[0] - 1, spawn[2] + 2))
        self.api.minecraft.console(
            "fill %s 252 %s %s 255 %s minecraft:air" % (spawn[0] + 4, spawn[2] - 2, spawn[0] - 1, spawn[2] + 2))
        self.api.minecraft.console(
            "fill %s 252 %s %s 255 %s minecraft:air" % (spawn[0] + 3, spawn[2] - 1, spawn[0], spawn[2] + 1))
        player.message({"text": "erasure commands sent to console...", "color": "yellow"})

    def _nether(self, *args):
        player = args[0]
        if permitted(player, "staff.nether", self.usePermissions, self.useVanillaBehavior) is False:
            return
        playermode = str(player.getGamemode())
        if str(player.getDimension()) == "-1":
            player.message({"text": "You are already in the nether...", "color": "red"})
            return False
        spawn = self.api.minecraft.getSpawnPoint()
        self.api.minecraft.console("setblock %s 252 %s minecraft:stone" % (spawn[0], spawn[2]))
        self.api.minecraft.console("setblock %s 253 %s minecraft:portal" % (spawn[0], spawn[2]))
        if playermode[0] == "3":
            self.api.minecraft.console("gamemode 2 %s" % str(player.username))
        self.api.minecraft.console("tp %s %s 253 %s" % (str(player.username), spawn[0], spawn[2]))
        player.message(
            {"text": "A nether portal was left at spawn. remember to remove it.  ('/erasep')", "color": "red"})

    def _end(self, *args):
        player = args[0]
        if permitted(player, "staff.end", self.usePermissions, self.useVanillaBehavior) is False:
            return
        playermode = str(player.getGamemode())
        if player.getDimension() == 1:
            player.message({"text": "You are already in the end...", "color": "red"})
            return False
        if player.getDimension() == -1:
            player.message({"text": "You must be in the overworld first...", "color": "red"})
            return False
        spawn = self.api.minecraft.getSpawnPoint()
        self.api.minecraft.console("setblock %s 252 %s minecraft:bedrock" % (spawn[0] + 2, spawn[2]))
        self.api.minecraft.console("setblock %s 253 %s minecraft:end_portal" % (spawn[0] + 2, spawn[2]))
        self.api.minecraft.console("setblock %s 255 %s minecraft:bedrock" % (spawn[0] + 2, spawn[2]))
        self.api.minecraft.console("setblock %s 253 %s minecraft:bedrock" % (spawn[0] + 2, spawn[2] + 1))
        self.api.minecraft.console("setblock %s 254 %s minecraft:bedrock" % (spawn[0] + 2, spawn[2] + 1))
        self.api.minecraft.console("setblock %s 253 %s minecraft:bedrock" % (spawn[0] + 2, spawn[2] - 1))
        self.api.minecraft.console("setblock %s 254 %s minecraft:bedrock" % (spawn[0] + 2, spawn[2] - 1))
        self.api.minecraft.console("setblock %s 253 %s minecraft:bedrock" % (spawn[0] + 3, spawn[2]))
        self.api.minecraft.console("setblock %s 254 %s minecraft:bedrock" % (spawn[0] + 3, spawn[2]))
        self.api.minecraft.console("setblock %s 253 %s minecraft:bedrock" % (spawn[0] + 1, spawn[2]))
        self.api.minecraft.console("setblock %s 254 %s minecraft:bedrock" % (spawn[0] + 1, spawn[2]))
        if playermode[0] == "3":
            self.api.minecraft.console("gamemode 2 %s" % str(player.username))
        self.api.minecraft.console("tp %s %s 253 %s" % (str(player.username), spawn[0] + 2, spawn[2]))
        player.message({"text": "An end portal was left at spawn. remember to remove it. ('/erasep')", "color": "red"})

    def _tpto(self, player, args):
        if permitted(player, "staff.tpto", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayer = str(player.username)
        if len(args) < 1:
            player.message({"text": "Usage: /tpto <player> (you did not supply a player)", "color": "red"})
            return
        # collect info on player and his target.
        targetplayer = str(makenamevalid(self, args[0], True, False))
        # player not on...
        if targetplayer == "[]":
            player.message("you want tpto %s but he is not on.  Did you spell the name correctly?" % targetplayer)
            return
        tplayerobj = self.minecraft.getPlayer(targetplayer)
        targetplayerdim = str(tplayerobj.getDimension())
        playerdim = str(player.getDimension())
        if playerdim == "-1":
            playerdim = "nether"
        if playerdim == "1":
            playerdim = "end"
        if targetplayerdim == "-1":
            targetplayerdim = "nether"
        if targetplayerdim == "1":
            targetplayerdim = "end"
        # 1)same dimension...
        if targetplayerdim == playerdim:
            self.api.minecraft.console("tp %s %s" % (thisplayer, targetplayer))
            if player.hasPermission("staff.hide") and player.getGamemode() != 3:
                player.setGamemode(3)
            player.message("teleported you to %s" % targetplayer)
            return
        # 2) if player is in nether or end, they must go back to overworld
        if playerdim == "end" or playerdim == "nether":
            if targetplayerdim == "0":
                targetplayerdim = "overworld"
            player.message("%s is in the %s.  Go to the %s and try again."
                           % (targetplayer, targetplayerdim, targetplayerdim))
            return
        # 3) player is in overworld and target is in nether/end:
        if targetplayerdim == "end" or targetplayerdim == "nether":
            player.message("%s is in the %s.  Use '/%s' to go to the %s."
                           % (targetplayer, targetplayerdim, targetplayerdim, targetplayerdim))
            return
        errortext = ("Command Failed for some reason! report variables: Target=%s in %s You= in %s"
                     % (targetplayer, targetplayerdim, playerdim))
        player.message({"text": errortext, "color": "red"})
        return

    def _makemember(self, *args):
        """/addmember <player>", "adds <player> to 'member' rank!", "staff.promote.member"""
        player = args[0]
        arg = args[1]
        if permitted(player, "staff.promote.member", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(arg) == 1:
            # makenamevalid(self, namedplayer, online=True, returnUUiD=True) returns "[]" if not found
            name = makenamevalid(self, arg[0], True, False)
            playeruuid = makenamevalid(self, arg[0], True, True)
            if name == "[]":
                player.message({"text": "Player must be on to promote.", "color": "red"})
                return
            theplayer = self.api.minecraft.getPlayer(name)
            if theplayer.hasGroup("member"):
                player.message({"text": "Player is already promoted.", "color": "red"})
                return
            if theplayer.hasGroup("examen"):
                player.message({"text": "Sorry! This player requires Owner permission to promote.", "color": "red"})
                return
            # check time on server
            blocksavailable = self.claimsdata.data["player"][playeruuid]["claimblocks"]
            blocksinuse = self.claimsdata.data["player"][playeruuid]["claimblocksused"]
            totalblocks = blocksavailable + blocksinuse
            if totalblocks < 1035:
                player.message({"text": "Player has not played enough on the server.", "color": "purple"})
                return

            # check for home qualification
            playerhome = self.globalset.readhome(playeruuid)
            if playerhome[1] == 0:
                player.message({"text": "Player has no /home to qualify for member.", "color": "purple"})
                return
            theplayer.setGroup("member")
            if theplayer.hasGroup("member"):
                self.api.minecraft.console("/say %s is now a member of this server!" % name)
            else:
                player.message({"text": "setGroup() Command failed.", "color": "red"})
                player.message({"text": "Try running '--perms users <ign> info' first...", "color": "red"})
            return
        else:
            player.message({"text": "Usage: /addmember <playername>", "color": "red"})

    def _alias(self, player, args):
        if permitted(player, "staff.alias", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisuuid = str(player.mojangUuid)
        if len(args) < 1:
            player.message(
                {"text": "Usage: /alias add/del/list <Alias> <Current name/command> (can also rename commands)",
                 "color": "red"})
            return
        if args[0].lower() == "list":
            page = 0
            if len(args) > 1:
                page = int(args[1])
            if page == 0:
                page = 1
            if len(self.globalset.playerdata[thisuuid]["nicks"]) < 2:
                player.message({"text": "You have no aliases", "color": "red"})
                return
            nicklist = []
            x = 0
            for nicks in self.globalset.playerdata[thisuuid]["nicks"]:
                if nicks != "op":
                    nicklist.append(
                        {"text": nicks + "- ", "color": "aqua",
                         "extra": [{"text": self.globalset.playerdata[thisuuid]["nicks"][nicks],
                                    "color": "dark_green"}]})
                    x += 1
            printlist(nicklist, "aliases", x, player, page)
            return
        if (len(args) == 2) and (args[0].lower() == "del"):
            try:
                del self.globalset.playerdata[thisuuid]["nicks"][str(args[1])]
                player.message({"text": "That alias has been deleted successfully", "color": "gold"})
                return
            except:
                player.message({"text": "That alias could not be deleted! (did it exist?)", "color": "red"})
                return
        if (len(args) == 3) and (args[0].lower() == "add"):
            self.globalset.playerdata[thisuuid]["nicks"][str(args[1])] = str(args[2])
            msgtext = ("You can now use '%s' in place of '%s'." % (str(args[1]), str(args[2])))
            player.message({"text": msgtext, "color": "gold"})
            return
        player.message(
            {"text": "Usage: /alias add/del/list <Alias> <Current name/command> (can also rename commands)",
             "color": "red"})
        return

    def _filter(self, player, args):
        if permitted(player, "staff.filter", self.usePermissions, self.useVanillaBehavior) is False:
            return
        if len(args) < 1:
            player.message(
                {"text": "Usage: /filter add/del/list <desired> <undesireable text> [forceAll substitution? T/F]",
                 "color": "red"})
            return
        if args[0].lower() == "list":
            page = 0
            if len(args) > 1:
                page = int(args[1])
            if page == 0:
                page = 1
            if len(self.globalset.filter["subs"]) < 1:
                player.message(
                    {"text": "There are no aliases (this should just about never happen, since defaults are"
                             " pre-programmed.)", "color": "red"})
                return
            filterlist = []
            x = 0
            for filters in self.globalset.filter["subs"]:
                if self.globalset.filter["subs"][filters]["Force_all"] == "T":
                    filterlist.append(
                        {"text": filters + "- ", "color": "aqua",
                         "extra": [{"text": self.globalset.filter["subs"][filters]["sub"],
                                    "color": "dark_green"},
                                   {"text": " (" + self.globalset.filter["subs"][filters]["Force_all"] + ")",
                                    "color": "dark_red"}]})
                else:
                    filterlist.append(
                        {"text": filters + "- ", "color": "aqua",
                         "extra": [{"text": self.globalset.filter["subs"][filters]["sub"],
                                    "color": "dark_green"},
                                   {"text": " (" + self.globalset.filter["subs"][filters]["Force_all"] + ")",
                                    "color": "dark_green"}]})
                x += 1
            printlist(filterlist, "filters", x, player, page)
            return
        if (len(args) == 2) and (args[0].lower() == "del"):
            try:
                del self.globalset.filter["subs"][str(args[1])]
                player.message({"text": "The text has been deleted successfully", "color": "gold"})
                return
            except:
                player.message({"text": "That text could not be deleted! (did it exist?)", "color": "red"})
                return
        # self.globalset.filter["subs"][subs]["sub"]
        # self.globalset.filter["subs"][subs]["Force_all"] == "T"
        if (len(args) == 4) and (args[0].lower() == "add") and (args[3].lower() in ("t", "f")):
            self.globalset.filter["subs"][str(args[2])] = {}
            self.globalset.filter["subs"][str(args[2])]["sub"] = str(args[1])
            self.globalset.filter["subs"][str(args[2])]["Force_all"] = str(args[3])
            msgtext = ("'%s' will now be filtered in place of '%s'." % (str(args[1]), str(args[2])))
            player.message({"text": msgtext, "color": "gold"})
            return
        player.message(
            {"text": "Usage: /filter add/del/list <desired> <undesireable text> <forceAll substitution? T/F>",
             "color": "red"})
        return

    def _kick(self, player, args):
        if permitted(player, "staff.kick", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayer = str(player.username)
        if len(args) < 1:
            player.message({"text": "Usage: /kick <player> <reason>", "color": "red"})
            return
        if len(args) < 2:
            player.message({"text": "Usage: /kick <player> <MUST GIVE A REASON!>", "color": "red"})
            return
        reason = ""
        for x in xrange(1, len(args)):
            reason = reason + str(args[x]) + " "
        reason = reason.replace("\"", "'")
        targetplayer = str(makenamevalid(self, (args[0]), True, False))
        if targetplayer == "[]":
            player.message("you want to kick %s but he is not on.  Did you spell the name correctly?" % (str(args[0])))
            return
        if self.api.minecraft.getPlayer(
                targetplayer).hasPermission("staff.kick") or self.api.minecraft.getPlayer(targetplayer).isOp():
            player.message({"text": "You are not premitted to do this to staff!", "color": "red"})
            return
        if targetplayer == str(player.username):
            player.message({"text": "You can't kick yourself!", "color": "red"})
            return
        self.api.minecraft.console("kick %s %sby %s" % (targetplayer, reason, thisplayer))

    def _unmute(self, player, args):
        if permitted(player, "staff.unmute", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayername = str(player.username)
        targetplayername = targetplayeruuid = targetuuid = "[]"
        if len(args) <= 0:
            player.message({"text": "Missing name/argument.", "color": "red"})
            return
        if len(args) > 0:
            targetplayername = str(makenamevalid(self, args[0], False, False))
            targetplayeruuid = str(makenamevalid(self, args[0], False, True))
            targetuuid = targetplayeruuid
        if targetplayername == "[]" or targetplayeruuid == "[]":
            player.message({"text": "Invalid or missing name/uuid.", "color": "red"})
            return
        try:
            # The purpose of this is to raise an error if player is not on
            # was - targetplayerobject = (self.api.minecraft.getPlayer(targetplayername))
            self.api.minecraft.getPlayer(targetplayername)
        except:
            player.message({"text": "Player offline.. trying to unmute via UUID...", "color": "dark_purple"})
            if len(targetuuid) != 36:
                player.message({"text": "Having problems with this UUID.. restart may be needed!", "color": "red"})
                return
        if self.globalset.readmute(targetuuid, "mute") is False:
            muter = self.globalset.readmute(targetuuid, "muteby")
            if muter == thisplayername:
                muter = "you"
            rawtext = ("O_o??  He was either not muted or %s already unmuted him..." % muter)
            player.message({"text": rawtext, "color": "red"})
            return
        self.globalset.writemute(targetuuid, False, 0, "Unmute command", thisplayername)
        try:
            self.api.minecraft.getPlayer(targetplayername).message(
                "[Staff]%s restored your chat abilities.  Continue to be respectful and observe the rules."
                % thisplayername)
            player.message({"text": "Player chat restored!", "color": "gold"})
            return
        except:
            player.message({"text": "Player may not be on, but his chat ability is restored", "color": "yellow"})
            return

    def _mute(self, player, args):
        if permitted(player, "staff.mute", self.usePermissions, self.useVanillaBehavior) is False:
            return
        thisplayername = str(player.username)
        if len(args) <= 0:
            player.message({"text": "Missing name/argument.", "color": "red"})
            return
        targetplayername = str(makenamevalid(self, args[0], True, False))
        targetuuid = str(makenamevalid(self, args[0], True, True))
        if targetplayername == "[]" or targetuuid == "[]":
            player.message({"text": "Invalid/missing name (or player is not on).", "color": "red"})
            return
        if not player.isOp():  # op can do so if he pleases
            if self.api.minecraft.getPlayer(targetplayername).isOp() \
                    or self.api.minecraft.getPlayer(targetplayername).hasPermission("staff.mute"):
                player.message({"text": "You can't do this to fellow staff!", "color": "red"})
                return
        if self.globalset.readmute(targetuuid, "mute") is True:
            muter = self.globalset.readmute(targetuuid, "muteby")
            rawtext = ("Player has already been muted by %s." % muter)
            player.message({"text": rawtext, "color": "red"})
            return
        self.globalset.writemute(targetuuid, True, 0, "mute command", thisplayername)
        self.api.minecraft.getPlayer(targetplayername).message(
            "You have been muted by %s.  You must respectfully approach %s to resolve this situation.  Use /msg %s"
            % (thisplayername, thisplayername, thisplayername))
        player.message(
            {"text": "Player muted!  he will only be able to message staff (please be respectful and professional!)",
             "color": "gold"})
        return

    def _website(self, *args):
        player = args[0]
        if permitted(player, "staff.website", self.usePermissions, self.useVanillaBehavior) is False:
            return
        self.api.minecraft.broadcast({"text": "",
                                      "extra": [
                                          {"text": "=> Link to our ",
                                           "color": "blue"},
                                          {"text": "Website",
                                           "color": "dark_blue",
                                           "underlined": "true",
                                           "hoverEvent": {
                                               "action": "show_text",
                                               "value": "Click to open website"},
                                           "clickEvent": {
                                               "action": "open_url",
                                               "value": "http://www.SurestCraft.com"}},
                                          {"text": ".",
                                           "color": "blue"}]})
