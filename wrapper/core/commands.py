# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.
from pprint import pprint

import time
import json

import core.buildinfo as buildinfo
from api.helpers import format_bytes, getargs, getargsafter, readout
from api.helpers import get_int, set_item, getjsonfile, putjsonfile
# noinspection PyProtectedMember
from api.helpers import _secondstohuman, _showpage
from utils.crypt import get_passphrase


# noinspection PyBroadException,PyMethodMayBeStatic
class Commands(object):

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.config = wrapper.config
        self.config_manager = wrapper.configManager
        self.perms = wrapper.perms
        self.cipher = self.wrapper.cipher
        self.commands = {}
        self.reset_confirmed = False
        self.reset_timeout = time.time()

    def __getitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        return self.commands[index]

    def __setitem__(self, index, value):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        self.commands[index] = value
        return self.commands[index]

    def __delitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        del self.commands[index]

    def __iter__(self):
        for i in self.commands:
            yield i

    def playercommand(self, payload):
        player = payload["player"]
        command = str(payload["command"]).lower()
        commandtext = "/%s %s" % (command, " ".join(payload["args"]))
        player.message(commandtext)
        if command not in ("password", "othersensitivecommand"):
            self.log.info("%s executed: %s", payload["player"], commandtext)

        # We should get out of this by creating a wrapper command registering set # noqa

        if command in ("plugins", "pl"):
            self.command_plugins(player)
            return

        # some minecraft commands (like op, ban, kick) will have implementations
        # that should vary based on whether proxymode is enabled and are
        # defined here to supercede the minecraft version.
        # all commands here override their Minecraft equivalent.

        elif command == "op":
            return self.command_op(player, payload)

        elif command == "deop":
            return self.command_deop(player, payload)

        elif command == "kick":
            return self.command_kick(player, payload)

        elif command == "whitelist":
            return self.command_whitelist(player, payload)

        elif command == "wrapper":
            return self.command_wrapper(player, payload)

        elif command == "reload":
            return self.command_reload(player, payload)

        elif command in ("help", "?"):
            return self.command_help(player, payload)

        elif command == "playerstats":
            return self.command_playerstats(player, payload)

        elif command in ("permissions", "perm", "perms", "super"):
            return self.command_perms(player, payload)

        elif command in ("ent", "entity", "entities"):
            return self.command_entities(player, payload)

        elif command in (
                "config", "con", "prop", "property", "properties"):
            return self.command_setconfig(player, payload)

        elif self.wrapper.proxymode and command == "ban":
            return self.command_banplayer(player, payload)

        elif self.wrapper.proxymode and command == "pardon":
            return self.command_pardon(player, payload)

        elif self.wrapper.proxymode and command == "ban-ip":
            return self.command_banip(player, payload)

        elif self.wrapper.proxymode and command == "pardon-ip":
            return self.command_pardonip(player, payload)

        elif command == "password":
            return self.command_password(player, payload)
        # This section calls the commands defined by api.registerCommand()
        for pluginID in self.commands:
            command = payload["command"]
            if pluginID == "Wrapper.py":
                try:
                    self.commands[pluginID][command](payload["player"],
                                                     payload["args"])
                except Exception as e:
                    self.log.debug("Exception in 'Wrapper.py' while"
                                   " trying to run '%s' command:\n%s",
                                   (command, e))
                continue
            if pluginID not in self.wrapper.plugins:
                continue
            plugin = self.wrapper.plugins[pluginID]
            if not plugin["good"]:
                continue
            if command in self.commands[pluginID]:
                try:
                    command = self.commands[pluginID][command]
                    # require super op to bypass explicit permission
                    if player.hasPermission(
                            command["permission"]) or player.isOp() > 4:
                        command["callback"](payload["player"], payload["args"])
                    else:
                        player.message(
                            {"translate": "commands.generic.permission",
                             "color": "red"})
                    return
                except Exception as e:
                    self.log.exception(
                        "Plugin '%s' errored out when executing command:"
                        " '<%s> /%s':\n%s", pluginID,
                        payload["player"], command, e)
                    payload["player"].message(
                        {"text": "An internal error occurred in wrapper"
                         "while trying to execute this command. Apologies.",
                         "color": "red"})
                    return

        # command was not executed by werapper, so try server.
        player.execute(commandtext)

    def command_sample(self, player, payload):
        # just a sample command as a pattern for new commands
        """
        :args:
            :player: is the calling player object, equivalent to
             payload['player']

            :payload: dictionary of:
                :args: ["list, "of", "all", "args"]
                :player: caller player object
                :command: type:string = the command that was called
                :playername: - additional argument when run from in-game
                 (proxy mode)?
        """
        if not self._superop(player, 3):
            return False
        pprint(payload)

    def command_setconfig(self, player, payload):
        # only allowed for console and SuperOP 10
        if not self._superop(player, 9):
            return False

        commargs = payload["args"]
        section = getargs(commargs, 0)
        item = getargs(commargs, 1)
        if section.lower() in ("sections", "section", "header", "headers"):
            sections = ""
            for headers in self.config:
                sections += "%s\n" % headers
            player.message("&6Config sections")
            player.message("&6_______________")
            player.message("&9%s" % sections)
            return
        if section in self.config and item.lower() in (
                "item", "items", "list", "show"):
            items = ""
            for item in self.config[section]:
                items += "%s: %s\n" % (item, self.config[section][item])
            player.message("&6Items in section %s:" % section)
            player.message("&6_______________________________________________")
            player.message("&9%s" % items)
            return
        if section.lower() == "help" or len(commargs) < 3:
            player.message("&cUsage: /config <section> <item>"
                           " <desired value> [reload?(T/F)]")
            player.message("&c - Config headers and items are case-sensative!")
            player.message("&c       /config sections - view section headers")
            player.message("&c       /config <section> items"
                           " - view section items")
            return
        newvalue = getargs(commargs, 2)
        reloadfile = False
        if len(commargs) > 3:
            optionalreload = getargs(commargs, 3)
            if optionalreload.lower() in ("t", "true", "y", "yes"):
                reloadfile = True
        self.wrapper.api.minecraft.configWrapper(
            section, item, newvalue, reloadfile)

    def command_banplayer(self, player, payload):
        if not player.isOp() > 2:
            player.message("&cPermission Denied")
            return False

        commargs = payload["args"]
        playername = getargs(commargs, 0)
        banexpires = False
        reason = "the Ban Hammer has Spoken"
        timeunit = 86400  # days is default
        lookupuuid = self.wrapper.uuids.getuuidbyusername(playername)
        if not lookupuuid:
            player.message({"text": "Not a valid Username!", "color": "red"})
            return False
        if len(commargs) > 1:
            # check last argument for "d:<days>
            unitsare = commargs[len(commargs) - 1][0:2].lower()
            if unitsare in ("d:", "h:"):
                if unitsare == "h:":
                    timeunit /= 24
                units = int(float(commargs[len(commargs) - 1][2:]))
                if units > 0:
                    banexpires = time.time() + (units * timeunit)
            reason = getargsafter(commargs, 1)

        returnmessage = self.wrapper.proxy.banuuid(
            lookupuuid, reason, player.username, banexpires)
        if returnmessage[:6] == "Banned":
            player.message({"text": "%s" % returnmessage, "color": "yellow"})
        else:
            player.message({"text": "UUID ban failed!", "color": "red"})
            player.message(returnmessage)
        return returnmessage

    def command_banip(self, player, payload):
        if not player.isOp() > 2:
            player.message("&cPermission Denied")
            return False

        commargs = payload["args"]
        ipaddress = getargs(commargs, 0)
        banexpires = False
        reason = "the Ban Hammer has Spoken"
        if len(commargs) > 1:
            # check last argument for "d:<days>
            if commargs[len(commargs)-1][0:2].lower() == "d:":
                days = int(float(commargs[len(commargs)-1][2:]))
                if days > 0:
                    banexpires = time.time() + (days * 86400)
            reason = getargsafter(commargs, 1)

        returnmessage = self.wrapper.proxy.banip(
            ipaddress, reason, player.username, banexpires)
        if returnmessage[:6] == "Banned":
            player.message({"text": "%s" % returnmessage, "color": "yellow"})
        else:
            player.message({"text": "IP ban failed!", "color": "red"})
            player.message(returnmessage)
        return returnmessage

    def command_pardon(self, player, payload):
        if not player.isOp() > 2:
            player.message("&cPermission Denied")
            return False

        commargs = payload["args"]
        playername = getargs(commargs, 0)
        byuuid = True
        # last five letters of last argument
        if str(getargs(commargs, -1))[-5:].lower() == "false":
            byuuid = False
        lookupuuid = self.wrapper.uuids.getuuidbyusername(playername)
        if not lookupuuid and byuuid:
            player.message({"text": "Not a valid Username!", "color": "red"})
            return False
        if byuuid:
            returnmessage = self.wrapper.proxy.pardonuuid(lookupuuid)
        else:
            returnmessage = self.wrapper.proxy.pardonname(playername)

        if returnmessage[:8] == "pardoned":
            player.message({"text": "player %s unbanned!  You must restart "
                                    "the server for this to take effect on the "
                                    "Local server. Proxy should respect this "
                                    "Starting NOW." %
                                    playername, "color": "yellow"})
        else:
            player.message({"text": "player unban %s failed!" %
                                    playername, "color": "red"})
        player.message(returnmessage)
        return returnmessage

    def command_pardonip(self, player, payload):
        if not player.isOp() > 2:
            player.message("&cPermission Denied")
            return False

        commargs = payload["args"]
        ipaddress = getargs(commargs, 0)

        returnmessage = self.wrapper.proxy.pardonip(ipaddress)
        if returnmessage[:8] == "pardoned":
            player.message({"text": "IP address %s unbanned!  You must restart "
                                    "the server for this to take effect on the "
                                    "Local server. Proxy should respect this "
                                    "Starting NOW." %
                                    ipaddress, "color": "yellow"})
        else:
            player.message({"text": "IP unban %s failed!" %
                                    ipaddress, "color": "red"})
        player.message(returnmessage)
        return returnmessage

    def command_entities(self, player, payload):
        if not self._superop(player, 5):
            player.message("&cPermission Denied")
            return False
        if not self.wrapper.proxymode:
            player.message(
                "&cProxy mode is off - Entity control is not enabled.")

        entitycontrol = self.wrapper.proxy.entity_control
        if not entitycontrol:
            # only console could be the source:
            readout("ERROR - ",
                    "No entity code found. (no proxy/server started?)",
                    separator="", pad=10,
                    usereadline=self.wrapper.use_readline,
                    player=player)
            return
        commargs = payload["args"]
        if len(commargs) < 1:
            pass
        elif commargs[0].lower() in (
                "c", "count", "s", "sum", "summ", "summary"):
            player.message(
                "Entities loaded: %d" % entitycontrol.countActiveEntities())
            return
        elif commargs[0].lower() in ("k", "kill"):
            eid = get_int(getargs(commargs, 1))
            count = get_int(getargs(commargs, 2))
            if count < 1:
                count = 1
            entitycontrol.killEntityByEID(
                eid, dropitems=False, count=count)
            return
        elif commargs[0].lower() in ("l", "list", "sh", "show" "all"):
            nice_list = {}
            for ent in entitycontrol.entities:
                nice_list[entitycontrol.entities[
                    ent].eid] = entitycontrol.entities[ent].entityname
            player.message("Entities: \n%s" % nice_list)
            return
        elif commargs[0].lower() in ("p", "player", "name"):
            if len(commargs) < 3:
                player.message("&c/entity player <name> count/list")
                return
            them = entitycontrol.countEntitiesInPlayer(commargs[1])
            if commargs[2].lower() in ("l", "list", "sh", "show" "all"):
                player.message("Entities: \n%s" % json.dumps(them, indent=2))
            else:
                player.message("%d entities exist in %s's client." %
                               (len(them), commargs[1]))
            return

        player.message("&cUsage: /entity count")
        player.message("&c       /entity list")
        player.message("&c       /entity player <name> count")
        player.message("&c       /entity player <name> list")
        player.message("&c       /entity kill <EIDofEntity> [count]")

    def command_wrapper(self, player, payload):
        if not self._superop(player):
            return False

        buildstring = self.wrapper.getbuildstring()
        if len(getargs(payload["args"], 0)) > 0:
            subcommand = getargs(payload["args"], 0)
            if subcommand == "update":
                player.message(
                    {"text": "Checking for new Wrapper.py updates...",
                     "color": "yellow"}
                )
                update = self.wrapper.get_wrapper_update_info()
                if update:
                    version, repotype, reponame = update
                    build = version[4]

                    player.message(
                        "New Wrapper.py %s version %s is available! (current "
                        "build is #%s)" % (
                            repotype, version, buildinfo.__version__  # noqa
                        )
                    )
                    player.message("&aPerforming update...")
                    if self.wrapper.performupdate(version, reponame):
                        player.message(
                            "&aUpdate completed! Version %s #%d (%s) is now "
                            "installed. Please reboot Wrapper.py to apply "
                            "changes." % (version, build, repotype)
                        )
                    else:
                        player.message(
                            "&cAn error occured while performing update."
                        )
                        player.message(
                            "&cPlease check the Wrapper.py console as soon as "
                            "possible for an explanation and traceback."
                        )
                        player.message(
                            "&cIf you are unsure of the cause, please file a "
                            "bug report on http://github.com/benbaptist/minecra"
                            "ft-wrapper with the traceback."
                        )
                else:
                    player.message("&cNo new Wrapper.py versions available.")
            elif subcommand == "halt":
                player.message("&cHalting Wrapper.py... goodbye!")
                self.wrapper.shutdown()
            elif subcommand in ("mem", "memory"):
                server_bytes = self.wrapper.javaserver.getmemoryusage()
                if server_bytes:
                    amount, units = format_bytes(server_bytes)
                    player.message(
                        "&cServer Memory: %s %s (%s bytes)" % (
                            amount, units, server_bytes
                        )
                    )
                else:
                    player.message(
                        "&cError: Couldn't retrieve memory usage for an "
                        "unknown reason"
                    )
        else:
            player.message(
                {"text": "Wrapper.py Version %s" % buildstring,
                 "color": "gray", "italic": True}
            )
        return

    def command_reload(self, player, payload):
        if not player.isOp() > 3:
            player.message("&cPermission Denied")
            return False

        if getargs(payload["args"], 0) == "server":
            # payload = {"args": ""}
            return
        try:
            self.wrapper.plugins.reloadplugins()
            player.message({"text": "Plugins reloaded.", "color": "green"})
            if self.wrapper.javaserver.getservertype() != "vanilla":
                player.message(
                    {"text": "Note: If you meant to reload the server's plugin"
                             "s and not Wrapper.py's plugins, run `/reload ser"
                             "ver` or from the console, use `/raw /reload` or "
                             "`reload` (with no slash).", "color": "gold"})
        except Exception as e:
            self.log.exception("Failure to reload plugins:\n%s" % e)
            player.message({"text": "An error occurred while reloading plugins"
                                    ". Please check the console immediately"
                                    " for a traceback.", "color": "red"})
        return False

    def command_help(self, player, payload):
        helpgroups = [{"name": "Minecraft",
                       "description": "List regular server commands"}]
        for hid in self.wrapper.help:
            plugin = self.wrapper.help[hid]
            for helpitem in plugin:
                helpgroups.append(
                    {"name": helpitem, "description": plugin[helpitem][0]})
        if len(getargs(payload["args"], 1)) > 0:
            group = getargs(payload["args"], 0)
            page = getargs(payload["args"], 1)
        else:
            group = ""
            page = getargs(payload["args"], 0)
        try:
            page = int(page) - 1
        except:
            if len(page) > 0:
                group = page
            page = 0

        # This controls cases where user typed '/help <plugin>'
        if len(group) > 0:
            # if player typed (or clicked) '/help Minecraft [page]'
            if group == "Minecraft":
                player.execute("help %d" % (page + 1))
                time.sleep(.1)
                player.message({
                    "text": "",
                    "extra": [{
                        "text": "Page %s" % (page + 2),
                        "color": "blue",
                        "underlined": True,
                        "clickEvent": {
                            "action": "run_command",
                            "value": "%shelp Minecraft %d" % (
                                self.wrapper.proxy.command_prefix,
                                page + 2)
                        }
                    }, {
                        "text": " "
                    }]
                })
            else:
                # Padding, for the sake of making it look a bit nicer
                player.message(" ")
                for hid in self.wrapper.help:
                    for groupname in self.wrapper.help[hid]:
                        #  if groupName.lower() == group:
                        if groupname == group:
                            group = self.wrapper.help[hid][groupname][1]
                            items = []
                            # i is each help item, like:
                            # ('/bmlist', 'List bookmark names', None)
                            for i in group:
                                command, args, permission = i[0].split(
                                    " ")[0], "", None
                                if len(i[0].split(" ")) > 1:
                                    # if there are args after the command
                                    args = getargsafter(i[0].split(" "), 1)

                                # will only display if player has permission
                                if not player.hasPermission(i[2]):
                                    if player.isOp():
                                        permission = {
                                            "text": "You do not have permission to"  # noqa
                                                    " use this command.",
                                            "color": "gray", "italic": True
                                        }
                                        items.append({
                                            "text": "",
                                            "extra": [{
                                                "text": command,
                                                "color": "gray",
                                                "italic": True,
                                                "hoverEvent": {
                                                    "action": "show_text",
                                                    "value": permission
                                                }
                                            }, ]
                                        })
                                    continue
                                if len(i) > 1 and player.isOp():
                                    permission = {"text": "Requires permission '%s'." % i[2],  # noqa
                                                  "color": "gray",
                                                  "italic": True}
                                items.append({
                                    "text": "",
                                    "extra": [{
                                        "text": command,
                                        "color": "gold",
                                        "clickEvent": {
                                            "action": "suggest_command",
                                            "value": "%s%s" % (
                                                self.wrapper.proxy.command_prefix,  # noqa
                                                command[1:])
                                        },
                                        "hoverEvent": {
                                            "action": "show_text",
                                            "value": permission
                                        }
                                    }, {
                                        "text": " " + args,
                                        "color": "red",
                                        "italic": True
                                    }, {
                                        "text": " - %s " % i[1]
                                    }]
                                })
                            if len(items) == 0:
                                items.append({
                                    "text": "",
                                    "extra": [{
                                        "text": "No permission to run any of these commands",  # noqa
                                        "color": "gray",
                                        "italic": "true",

                                    }]
                                })
                            _showpage(
                                player, page, items, "help %s" % groupname,
                                4,
                                command_prefix=self.wrapper.proxy.command_prefix)  # noqa
                            return
                player.message("&cThe help group '%s' does not exist." % group)

        # Plain old /help - print list of help groups
        else:
            items = []
            for v in helpgroups:
                shortdesc = v["description"][0:30]
                if len(shortdesc) < len(v["description"]):
                    shortdesc = shortdesc + "..."
                groupcolor = "gold"
                if v["name"] == "Minecraft":
                    groupcolor = "white"
                items.append({
                    "text": "",
                    "extra": [
                        {
                            "text": "%s " % v["name"],
                            "color": groupcolor,
                            "hoverEvent": {
                                "action": "show_text",
                                "value": v["description"]
                            }
                        },
                        {
                            "text": "[click help]",
                            "color": "blue",
                            "clickEvent": {
                                "action": "run_command",
                                "value": "%shelp %s" % (
                                    self.wrapper.proxy.command_prefix,
                                    v["name"])
                            },
                            "hoverEvent": {
                                "action": "show_text",
                                "value": "%shelp %s" % (
                                    self.wrapper.proxy.command_prefix,
                                    v["name"])
                            }
                        },
                        {
                            "text": " - " + shortdesc
                        }]
                })
            _showpage(player, page, items, "help", 8,
                      command_prefix=self.wrapper.proxy.command_prefix)
        return False

    def command_password(self, player, payload):
        if not player.isOp() > 4:
            player.message("&cPermission Denied")
            return
        command = getargs(payload["args"], 0)

        def showhelp():
            player.message("&2Usage: /password <group> <item> <data>")
            player.message(
                "&2 in console, use 'prompt' for <data> to be invisibly")
            player.message(
                "&2  prompted if there is an 'over the shoulder' concern.")
            player.message(
                "&2 Sample usage to change IRC remote control password:")
            player.message(
                "&2  /password IRC control-irc-pass NEWsuckypassword")

        if command in ("help", "h", "info", "about"):
            showhelp()
            return
        group = getargs(payload["args"], 0)
        setting = getargs(payload["args"], 1)
        data = getargsafter(payload["args"], 2)
        if data == "prompt":
            data = get_passphrase("Please enter data to be hashed/stored")
        if group not in self.config:
            player.message(
                "&c wrapper.properties has no such group '%s'" % group)
            showhelp()
            return
        if setting not in self.config[group]:
            player.message(
                "&c There is no item '%s' in group '%s'" % (setting, group))
            return
        final_data = self.cipher.encrypt(data)
        player.message("&2 data encrypted!")
        self.config[group][setting] = final_data
        self.config_manager.save()

    def command_playerstats(self, player, payload):
        if not player.isOp() > 3:
            player.message("&cPermission Denied")
            return
        # this, like all commands, is being run in a thread.
        player.message("&ePlease wait as I research this..", position=2)
        subcommand = getargs(payload["args"], 0)
        totalplaytime = {}
        players = self.wrapper.api.minecraft.getAllPlayers()
        for each_uuid in players:
            if "logins" not in players[each_uuid]:
                continue
            playername = self.wrapper.uuids.getusernamebyuuid(each_uuid)
            totalplaytime[playername] = [0, 0]
            for i in players[each_uuid]["logins"]:
                totalplaytime[
                    playername][0] += players[each_uuid]["logins"][i] - int(i)
                totalplaytime[playername][1] += 1

        if subcommand == "all":
            player.message("&6----- All Players' Playtime -----")
            for name in totalplaytime:
                seconds = totalplaytime[name][0]
                result = _secondstohuman(seconds)
                player.message("&e%s:&6 %s (%d logins)" %
                               (name, result, totalplaytime[name][1]))
        else:
            topplayers = []
            for username in totalplaytime:
                topplayers.append((totalplaytime[username][0], username))
            topplayers.sort()
            topplayers.reverse()
            player.message("&6----- Top 10 Players' Playtime -----")
            for i, p in enumerate(topplayers):
                result = _secondstohuman(p[0])
                player.message("&7%d. &e%s:&6 %s" % (i + 1, p[1], result))
                if i == 9:
                    break
        return

    def command_kick(self, player, payload):
        if not self._superop(player, 3):
            return False
        player_name = getargs(payload["args"], 0)
        all_args = getargsafter(payload["args"], 1)
        if all_args == "":
            reason = {'translate': 'multiplayer.disconnect.kicked'}
        else:
            reason = {'translate': 'multiplayer.disconnect.kicked',
                      'text': all_args}

        self.wrapper.javaserver.kick_player(player_name, reason)

    def command_whitelist(self, player, payload):
        if player.isOp() < 3:
            return False
        wl_commands = {
            "add": self._command_whitelist_add,
            "list": self._command_whitelist_list,
            "off": self._command_whitelist_off,
            "on": self._command_whitelist_on,
            "reload": self._command_whitelist_reload,
            "remove": self._command_whitelist_remove,
            "offline": self._command_whitelist_offline,
            "online": self._command_whitelist_online,
        }
        wl_comm = getargs(payload["args"], 0)
        wl_arg = getargs(payload["args"], 1)
        if wl_comm in wl_commands:
            wl_commands[wl_comm](player, wl_arg)
        else:
            player.message(
                {"text": 'Usage: /whitelist <on|off|list|add|remove|reload>',
                 'color': 'white'})
            player.message(
                {"text": 'Additional Proxy mode Usage: \n       /whitelist on'
                         'line - Convert whitelist to online uuids (turns off '
                         'Proxy and restarts wrapper)\n       /whi'
                         'telist offline - Convert whitelist to offline uuids '
                         '(wrapper will attempt to start the proxy)',
                 'color': 'yellow'})

    def _command_whitelist_add(self, player, arg):
        if not self.wrapper.proxymode:
            player.execute("whitelist add %s" % arg)
            player.message("..Working.  Server may lag.")
            player.message("...")
            return
        whitelist = getjsonfile(
            "whitelist", self.wrapper.serverpath, self.wrapper.encoding
        )
        online_uuid = self.wrapper.uuids.getuuidbyusername(arg).string

        if online_uuid in (None, False):
            player.message("&c INVALID NAME")
            return
        proper_spelled = self.wrapper.uuids.getusernamebyuuid(online_uuid)
        off_line = self.wrapper.uuids.getuuidfromname(proper_spelled).string

        add_record = True
        for index, entry in enumerate(whitelist):
            # Name is already there; just update uuid
            if whitelist[index]["name"] == proper_spelled:
                whitelist[index]["uuid"] = off_line
                add_record = False
                break
            # uuid is correct offline; make sure name matches
            elif whitelist[index]["uuid"] == off_line:
                whitelist[index]["name"] = proper_spelled
                add_record = False
                break
            # uuid is online version; correct to offline and edit username
            elif whitelist[index]["uuid"] == online_uuid:
                whitelist[index]["uuid"] = off_line
                whitelist[index]["name"] = proper_spelled
                add_record = False
                break

        if add_record:
            jsonitem = {"uuid": off_line, "name": proper_spelled}
            whitelist.append(jsonitem)

        putjsonfile(whitelist, "whitelist", self.wrapper.serverpath,)
        player.message("Done!")
        player.execute("whitelist reload")

    def _command_whitelist_list(self, player, _arg):
        player.execute("whitelist list")

    def _command_whitelist_off(self, player, _arg):
        player.execute("whitelist off")

    def _command_whitelist_on(self, player, _arg):
        player.execute("whitelist on")

    def _command_whitelist_reload(self, player, _arg):
        player.execute("whitelist reload")

    def _command_whitelist_remove(self, player, arg):
        player.execute("whitelist remove %s" % arg)
        player.execute("whitelist reload")

    def _command_whitelist_offline(self, player, _arg):
        world = self.wrapper.api.minecraft.getWorldName()
        curr_wd = "%s/%s" % (self.wrapper.serverpath, world)
        if not world:
            player.message("No server world found, so UUID's not converted...")
        whitelist = getjsonfile(
            "whitelist", self.wrapper.serverpath, self.wrapper.encoding
        )
        for index, entry in enumerate(whitelist):
            onlineuuid = self.wrapper.uuids.getuuidbyusername(
                whitelist[index]["name"])
            if not onlineuuid:
                player.message(
                    "Could not find Mojangs entry for %s" % whitelist[index][
                        "name"])
                player.message("&cSkipped!")
                continue
            correctnamed = self.wrapper.uuids.getusernamebyuuid(
                onlineuuid.string)
            whitelist[index]["name"] = correctnamed
            newuuid = self.wrapper.uuids.getuuidfromname(correctnamed).string
            whitelist[index]["uuid"] = newuuid
            if world:
                self.wrapper.uuids.convert_files(onlineuuid, newuuid, curr_wd)
        putjsonfile(whitelist, "whitelist", self.wrapper.serverpath)

        # This part will convert files in wrapper's player cache, irresp. of whitelist  # noqa
        player.message("Converting cached UUID files...")
        if world:
            self.wrapper.uuids.convert_user(self.wrapper.serverpath, world,
                                            onlinemode=False)
        player.message("Done!")
        player.execute("whitelist reload")

        self.wrapper.api.minecraft.changeServerProps("online-mode", False)
        self.wrapper.javaserver.restart()
        player.message("Attempting to re-start the proxy (server is in"
                       "offline mode now.")
        self.wrapper.enable_proxymode()

    def _command_whitelist_online(self, player, _arg):
        uuidlist = []
        whitelist = getjsonfile(
            "whitelist", self.wrapper.serverpath, self.wrapper.encoding
        )
        for index, entry in enumerate(whitelist):
            newuuid = self.wrapper.uuids.getuuidbyusername(
                whitelist[index]["name"])
            if newuuid:
                uuidlist.append(newuuid.string)
                whitelist[index]["uuid"] = newuuid.string
        putjsonfile(whitelist, "whitelist", self.wrapper.serverpath, )
        player.message("Converting UUID files...")
        world = self.wrapper.api.minecraft.getWorldName()
        if world:
            self.wrapper.uuids.convert_user(self.wrapper.serverpath, world,
                                            uuid_=uuidlist, onlinemode=True)
        else:
            player.message("No server world found, so UUID's not converted...")
        player.message("Done!")
        player.execute("whitelist reload")
        self.wrapper.api.minecraft.changeServerProps("online-mode", True)
        restartmess = "The server is now going to online mode."
        player.kick(restartmess)
        self.wrapper.javaserver.restart(restartmess)
        if self.wrapper.proxymode:
            self.log.info("Wrapper must shutdown to fully close the Proxy.")
            self.wrapper.disable_proxymode()
            self.wrapper.shutdown()

    def command_deop(self, player, payload):
        """DeOP has lower permission level"""
        if not self._superop(player, 3):
            return False
        operator_name = getargs(payload["args"], 0)
        if self.wrapper.javaserver.state == 2:
            # deop from server
            self.wrapper.javaserver.console("deop %s" % operator_name)

            # deop from superops.txt
            file_text = ""
            owner_names = self.wrapper.javaserver.ownernames
            for eachname in owner_names:
                if eachname != operator_name:
                    if eachname not in ("<op_player_1>", "<op_player_2>"):
                        file_text += "%s=%s\n" % (
                            eachname, owner_names[eachname])
            with open("superops.txt", "w") as f:
                f.write(file_text)
            time.sleep(.1)
            self.wrapper.javaserver.refresh_ops()
            return True
        else:
            player.message("&cdeop requires a running server instance")
            return "deop requires a running server instance"

    def command_op(self, player, payload):
        if not self._superop(player, 9):
            return False

        # get argument flags
        flags = [x.lower() for x in payload["args"]]
        superop = "-s" in flags
        op_level = "-l" in flags
        offline_mode = "-o" in flags

        new_operator_name = getargs(payload["args"], 0)
        if new_operator_name == "":
            player.message({'with': [{'translate': 'commands.op.usage'}],
                            'translate': 'commands.generic.usage',
                            'color': 'red'})
            return

        valid_uuid = self.wrapper.uuids.getuuidbyusername(new_operator_name)
        if not offline_mode and valid_uuid in (None, False):
            player.message(
                "&c'%s' is not a valid player name!" % new_operator_name)
            return False

        if offline_mode:
            name = new_operator_name
            uuid = str(self.wrapper.uuids.getuuidfromname(name))
        else:
            uuid = str(valid_uuid)
            name = self.wrapper.uuids.getusernamebyuuid(uuid)

        superlevel = 4  # default

        if op_level:
            for index, x in enumerate(flags):
                if x == "-l":
                    break
            # noinspection PyUnboundLocalVariable
            arg_level = get_int(getargs(flags, index + 1))
            superlevel = max(1, arg_level)

        if superop and superlevel > 4:
            superlevel = max(5, superlevel)
        # 2 = make sure server STARTED
        if self.wrapper.javaserver.state == 2:
            self.wrapper.javaserver.console("op %s" % name)

        # if not, wrapper makes ops.json edits
        else:
            self.wrapper.javaserver.refresh_ops(read_super_ops=False)
            oplist = self.wrapper.javaserver.operator_list
            newop_item = {
                "uuid": uuid,
                "name": name,
                "level": min(4, superlevel),
                "bypassesPlayerLimit": False
            }
            if oplist:
                for op, ops in enumerate(oplist):
                    # We don't expect it is already there, but if so...
                    if uuid == ops["uuid"]:
                        oplist.pop(op)
                oplist.append(newop_item)
            else:
                oplist = [newop_item, ]
            result = putjsonfile(oplist, "ops")
            if result:
                player.message("&6Ops.json file saved ok.")
            else:
                player.message("&cSomething went wrong writing ops.json.")
        # update the superops.txt file
        if superop:
            set_item(name, superlevel, "superops.txt")
            player.message("&6Updated as SuperOP.")

        time.sleep(.5)
        self.wrapper.javaserver.refresh_ops()

    def command_perms(self, player, payload):
        if not self._superop(player, 5):
            return False

        def usage(l):
            player.message("&cUsage: /%s %s" % (payload["command"], l))

        command = getargs(payload["args"], 0)

        if command in ("help", "h", "info", "about"):
            self.reset_confirmed = False
            subcommand = getargs(payload["args"], 1)
            if subcommand in ("group", "groups", "gr", "g"):
                player.message("&2/perms group <groupname> ...")
                player.message("&2  new/info -create new group / get info")
                player.message("&2  set <node> <value>  -set a perm for this group")  # noqa
                player.message("&2  delete -deletes the group entirely")
                player.message("&2  remove <node> -just remove a node")

            elif subcommand in ("users", "user", "use", "u"):
                player.message("&2/perms user <player> ...")
                player.message("&2  info -display permissions for a player")
                player.message("&2  group <group> -assign player to <group>")
                player.message("&2  group <group> remove -remove player from <group>")  # noqa
                player.message("&2  set <node> <value>  -set a perm for this player")  # noqa
                player.message("&2  remove <node>  -remove perm <node> for this player")  # noqa
            else:
                player.message("&2The primary subcommands are group, user, RESET")  # noqa
                player.message("&2Help with groups use: /perms help groups")
                player.message("&2Help with users use: /perms help users")

        elif command in ("gr", "group", "groups"):
            self.reset_confirmed = False
            group = getargs(payload["args"], 1)
            subcommand = getargs(payload["args"], 2)

            if subcommand == "new":
                call_result = self.perms.group_create(group)
                player.message("&a%s" % call_result)

            elif subcommand == "delete":
                call_result = self.perms.group_delete(group)
                player.message("&a%s" % call_result)

            elif subcommand == "set":
                node = getargs(payload["args"], 3)
                value = getargsafter(payload["args"], 4)
                call_result = self.perms.group_set_permission(
                    group, node, value)
                if call_result:
                    player.message("&aGroup permission %s set to %s.",
                                   node, value)
                else:
                    usage("groups %s set <permissionNode> <value>" % group)

            elif subcommand == "remove":
                node = getargs(payload["args"], 3)
                call_result = self.perms.group_delete_permission(group, node)
                player.message("&a%s" % call_result)

            elif subcommand == "info":
                if group not in self.wrapper.wrapper_permissions.Data["groups"]:
                    player.message("&cGroup '%s' does not exist!" % group)
                    return
                player.message("&aUsers in the group '%s':" % group)
                for uuid in self.wrapper.wrapper_permissions.Data["users"]:
                    if group in self.wrapper.wrapper_permissions.Data[
                            "users"][uuid]["groups"]:
                        player.message("%s: &2%s" % (
                            self.wrapper.uuids.getusernamebyuuid(uuid), uuid))
                player.message("&aPermissions for the group '%s':" % group)
                for node in self.wrapper.wrapper_permissions.Data[
                        "groups"][group]["permissions"]:
                    value = self.wrapper.wrapper_permissions.Data[
                        "groups"][group]["permissions"][node]
                    if value:
                        player.message("- %s: &2%s" % (node, value))
                    elif not value:
                        player.message("- %s: &4%s" % (node, value))
                    else:
                        player.message("- %s: &7%s" % (node, value))
            else:
                player.message("&6List of groups:&b %s" %
                               ", ".join(self.wrapper.wrapper_permissions.Data["groups"]))  # noqa
                usage("groups <groupName> [new|delete(group)"
                      "|info]/[set|remove(node) <node> <value>]")
                player.message("&cTry '/perms help groups' for more info...")

        elif command in ("user", "users"):
            self.reset_confirmed = False
            username = getargs(payload["args"], 1)
            subcommand = getargs(payload["args"], 2)
            uuid = self.wrapper.uuids.getuuidbyusername(username)
            if str(uuid) not in self.wrapper.wrapper_permissions.Data["users"]:
                self.perms.fill_user(str(uuid))
            if subcommand in ("group", "groups"):
                group = getargs(payload["args"], 3)
                remove = getargs(payload["args"], 4) == "remove"
                if len(group) > 0 and len(str(uuid)) > 0:
                    if remove:
                        call_result = self.perms.remove_group(str(uuid), group)
                    else:
                        call_result = self.perms.set_group(str(uuid), group)
                    if not call_result:
                        player.message(
                            "&ccommand failed, check wrapper log for info.")
                    else:
                        player.message("&aCommand succeeded.")
                else:
                    usage("users <username> group <groupName> [remove]")

            elif subcommand == "set":
                node = getargs(payload["args"], 3)
                value = getargsafter(payload["args"], 4)
                if len(node) > 0:
                    call_result = self.perms.set_permission(str(uuid), node, value)  # noqa
                    player.message("&a%s" % call_result)
                else:
                    usage("users %s set <permissionNode> [value]" % username)

            elif subcommand == "remove":
                node = getargs(payload["args"], 3)
                if len(node) > 0:
                    call_result = self.perms.remove_permission(str(uuid), node)
                    player.message("&a%s" % call_result)
                else:
                    usage("users %s remove <permissionNode>" % username)

            elif subcommand == "info":
                player.message("&aUser '%s' is in these groups: " % username)
                for group in self.wrapper.wrapper_permissions.Data["users"][str(uuid)]["groups"]:  # noqa
                    player.message("- %s" % group)
                player.message(
                    "&aUser '%s' is granted these individual permissions (not "
                    "including permissions inherited from groups): " % username)
                for node in self.wrapper.wrapper_permissions.Data[
                        "users"][str(uuid)]["permissions"]:
                    value = self.wrapper.wrapper_permissions.Data[
                        "users"][str(uuid)]["permissions"][node]
                    if value:
                        player.message("- %s: %s" % (node, value))
                    elif not value:
                        player.message("- %s: %s" % (node, value))
                    else:
                        player.message("- %s: %s" % (node, value))
            else:
                usage("users <username> <group/set/remove/info>")
                player.message("&cTry '/perms help users' for more info...")

        elif command == "RESET":
            if self.reset_confirmed and ((time.time() - self.reset_timeout) < 30):  # noqa
                self.perms.clear_group_data()
                self.perms.clear_user_data()
                self.reset_confirmed = False
                player.message("&cGroup and player permissions have been cleared!")  # noqa
            else:
                self.reset_timeout = time.time()
                self.reset_confirmed = True
                player.message("&cARE YOU SURE?")
                player.message("&cThis will delete all groups and clear "
                               "all user permissions!")
                player.message("Confirm your intent by running '/perms "
                               "RESET' again within 30 seconds.")
        else:
            self.reset_confirmed = False
            usage("<help/groups/users/RESET> (Note: RESET is case-sensitive!)")
            player.message("&cAlias commands: /perms, /perm, /super")
        return False

    def command_plugins(self, player):
        # CONSOLE should use the pretty version designed for console.
        if not player.isOp() > 3:
            player.message("&cPermission Denied")
            return False

        player.message({
            "text": "List of plugins installed:",
            "color": "red",
            "italic": True
        })
        for pid in self.wrapper.plugins:
            plugin = self.wrapper.plugins[pid]
            name = plugin["name"]
            version = ".".join([str(_) for _ in plugin["version"]])
            summary = plugin["summary"]
            description = plugin["description"]
            if description is None:
                description = "No description is available for this plugin"
            if summary is None:
                summary = "Plugin %s" % name
            summary = {
                "text": summary,
                "color": "white",
                "hoverEvent": {
                    "action": "show_text",
                    "value": description
                }
            }
            player.message({
                "text": name,
                "color": "dark_green",
                "hoverEvent": {
                    "action": "show_text",
                    "value": "Filename: %s | ID: %s" % (
                        plugin["filename"], pid)
                },
                "extra": [{
                    "text": " v%s" % version,
                    "color": "dark_gray"
                }, {
                    "text": " - ",
                    "color": "white"
                }, summary]
            })

    def _superop(self, player, superoplevel=4):
        if player.isOp() < superoplevel:
            player.message("&cPermission Denied - reserved for"
                           " SuperOPs (file 'superops.txt')")
            return False
        return True
