import time
NAME = "Teleport"
AUTHOR = "C0ugar"
ID = "net.version6.minecraft.plugins.teleport"
SUMMARY = "Teleport commands, similar to tpa commands in Bukkit Essentials."
DESCRIPTION = """Teleport plugin.
Permissions:
teleport.tpa - use /tpa
teleport.tpahere - use /tpahere
teleport.deny - prevents people from sending tpa requests to a player with this permission node"""
WEBSITE = ""
VERSION = (0, 2, 1)

TIMEOUT = 120


class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        # change these if desired
        self.usePermissions = False  # Perms - 'teleport.tpahere', 'teleport.tpa', or 'teleport.denied'
        self.useVanillaBehavior = False  # mask TPA plugin.  Hide help group and give generic "unknown command" message.

        # Don't change this - automatically detects Global plugin
        self.hasDependencyGlobal = True
        """ if SurestTexas00 global plugin available, gets it for use in Teleports.  The global plugin simply tracks
        and stores the users location prior to teleport.  This is for use in commands by other plugins, like "/back",
        which need to know where the user was before the teleport. """
        try:
            self.globalset = api.getPluginContext("com.suresttexas00.plugins.global")
        except:
            self.hasDependencyGlobal = False

    def onEnable(self):
        self.data = {}
        if self.hasDependencyGlobal is True:
            if "teleport_useVanillaBehavior" in self.globalset.config:
                if self.globalset.config["teleport_useVanillaBehavior"] == "true":
                    self.useVanillaBehavior = True
            if "teleport_usePermissions" in self.globalset.config:
                if self.globalset.config["teleport_usePermissions"] == "true":
                    self.usePermissions = True

        if self.useVanillaBehavior is False:
            if self.usePermissions is True:
                self.api.registerHelp("Teleport", "Commands from the Teleport plugin", [
                    ("/tpa", "Request to teleport to the specified player.", "teleport.tpa"),
                    ("/tpahere", "Request that the specified player teleport to you.", "teleport.tpahere"),
                    ("/tpaccept", "Accept a teleport request.", None),
                    ("/tpdeny", "Reject a teleport request.", None),
                ])
            else:
                self.api.registerHelp("Teleport", "Commands from the Teleport plugin", [
                    ("/tpa", "Request to teleport to the specified player.", None),
                    ("/tpahere", "Request that the specified player teleport to you.", None),
                    ("/tpaccept", "Accept a teleport request.", None),
                    ("/tpdeny", "Reject a teleport request.", None),
                ])

        if (self.usePermissions is True) and (self.useVanillaBehavior is False):
            self.api.registerCommand("tpa", self.tpa, "teleport.tpa")
            self.api.registerCommand("tpahere", self.tpahere, "teleport.tpahere")
        else:
            self.api.registerCommand("tpa", self.tpa, None)
            self.api.registerCommand("tpahere", self.tpahere, None)

        # tpaccept/deny don't have permissions
        self.api.registerCommand("tpaccept", self.tpaccept, None)
        self.api.registerCommand("tpdeny", self.tpdeny, None)

    def onDisable(self):
        pass

    def tpa(self, player, args):
        """ Request teleport to another player position """
        if self._permitted(player, "teleport.tpa") is False:
            return
        self._doTeleportRequest(player, "tpa", args)

    def tpahere(self, player, args):
        """ Request another player to teleport to your position """
        if self._permitted(player, "teleport.tpahere") is False:
            return
        self._doTeleportRequest(player, "tpahere", args)

    def tpaccept(self, player, args):
        """ Accept teleport request """
        otherPlayer = self._doTestTeleportReply(player)
        if otherPlayer:
            player.message({"text": "Teleport request accepted.", "color": "yellow"})
            otherPlayer.message({"text": "%s accepted your teleport request." % player.username, "color": "yellow"})
            if self.data[player.username]['direction'] == 'tpa':
                who = otherPlayer
                where = player
            else:
                who = player
                where = otherPlayer
            who.message({"text": "Teleporting to %s." % where.username, "color": "yellow"})
            pos = where.getPosition()
            if self.hasDependencyGlobal is True:
                self.globalset.backlocation(who)
            self.minecraft.console("tp %s %d %d %d" % (who.username, pos[0], pos[1], pos[2]))
        if player.username in self.data:
            del self.data[player.username]

    def tpdeny(self, player, args):
        """ Reject teleport request """
        otherPlayer = self._doTestTeleportReply(player)
        if otherPlayer:
            player.message({"text": "Teleport request denied.", "color": "yellow"})
            otherPlayer.message({"text": "%s denied your teleport request." % player.username, "color": "yellow"})
        if player.username in self.data:
            del self.data[player.username]

    def _doTeleportRequest(self, player, cmd, args):
        """ Essential tests before teleport request """
        if len(args) == 0:
            player.message({"text": "Use /%s <playername>" % cmd, "color": "gray"})
            return
        if not player.getDimension() == 0:
            player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
            return
        try:
            otherPlayer = self.minecraft.getPlayer(args[0])
        except:
            otherPlayer = None
        if not otherPlayer:
            player.message({"text": "Error: Player not found.", "color": "red"})
            return
        if otherPlayer.hasPermission("teleport.denied"):
            player.message({"text": "That player is restricted from Teleport system use.", "color": "light_purple"})
            return
        if player == otherPlayer:
            player.message({"text": "Error: Can't play alone", "color": "red"})
            return
        if not otherPlayer.getDimension() == 0:
            player.message({"text": "Sorry, but %s is not in this world." % otherPlayer.username, "color": "red"})
            return
        if otherPlayer.username in self.data:
            if self.data[otherPlayer.username]['requester'] == player.username \
                    and self.data[otherPlayer.username]['direction'] == cmd:
                player.message({"text": "Request is already sent to %s" % otherPlayer.username, "color": "red"})
                return
        if cmd == "tpa":
            otherPlayer.message(
                {"text": "%s has requested to teleport to you." % player.username, "color": "gold"})
        else:
            otherPlayer.message(
                {"text": "%s has requested that you teleport to them." % player.username, "color": "gold"})
        otherPlayer.message({"text": "To teleport, type /tpaccept.", "color": "gold"})
        otherPlayer.message({"text": "To deny this request, type /tpdeny.", "color": "gold"})
        otherPlayer.message({"text": "This request will timeout after %d deconds." % TIMEOUT, "color": "gold"})
        player.message({"text": "Request sent to %s" % otherPlayer.username, "color": "gold"})
        self.data[otherPlayer.username] = {}
        self.data[otherPlayer.username]['time'] = time.time()
        self.data[otherPlayer.username]['requester'] = player.username
        self.data[otherPlayer.username]['direction'] = cmd

    def _doTestTeleportReply(self, player):
        """ Essential tests before teleport reply """
        if player.username not in self.data:
            if self._permitted(player, "teleport.tpahere") is False:
                return None
            player.message({"text": "Error: You do not have a pending request", "color": "red"})
            return None
        if not player.getDimension() == 0:
            player.message({"text": "Sorry, but you can't do this from the Nether or End.", "color": "red"})
            return None
        if self.data[player.username]['time'] < (time.time() - TIMEOUT):
            player.message({"text": "Error: Teleport request has timed out.", "color": "red"})
            return None
        try:
            otherPlayer = self.minecraft.getPlayer(self.data[player.username]['requester'])
        except:
            otherPlayer = None
        if not otherPlayer:
            player.message(
                {"text": "Error: You do not have a pending request", "color": "red"})
            return None
        if not otherPlayer.getDimension() == 0:
            player.message(
                {"text": "Sorry, but %s is not in this world any more." % otherPlayer.username, "color": "red"})
            return None
        return otherPlayer

    def _permitted(self,player, permission):
        """check for player permission to run a command.  This routine returns false
        if the player has no permission and prints a vanilla 'unknown command' message
        versus the wrapper's 'permission denied' type message
        Usage: if self._permitted(player, 'somepermissions.permission') is False: return """
        if (self.usePermissions is True) and player.hasPermission(permission) is False:
            player.message("&cUnknown Command. Try /help for a list of commands")
            return False
        return True
