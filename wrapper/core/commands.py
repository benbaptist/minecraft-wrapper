# -*- coding: utf-8 -*-

# p2 and py3 compliant (no PyCharm IDE-flagged errors)
#  (still has weak warnings in both versions)

import ast
import random
import time
import json

from utils.helpers import format_bytes, getargs, getargsafter, secondstohuman, showpage, readout


# noinspection PyBroadException
class Commands:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.config = wrapper.config

        self.commands = {}

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
        self.log.info("%s executed: /%s %s", payload["player"], payload["command"], " ".join(payload["args"]))
        # We should get of this by creating a wrapper command registering set
        if str(payload["command"]).lower() in ("plugins", "pl"):
            self.command_plugins(player)
            return True
        # make sure any command returns a True-ish item, or the chat packet will continue to the server
        if payload["command"] == "wrapper":
            self.command_wrapper(player, payload)
            return True

        if payload["command"] == "reload":
            self.command_reload(player, payload)
            return True

        if payload["command"] in ("help", "?"):
            self.command_help(player, payload)
            return True

        if payload["command"] == "playerstats":
            self.command_playerstats(player, payload)
            return True

        if payload["command"] in ("permissions", "perm", "perms", "super"):
            self.command_perms(player, payload)
            return True

        if str(payload["command"]).lower() in ("ent", "entity", "entities"):
            self.command_entities(player, payload)
            return True

        if str(payload["command"]).lower() in ("config", "con", "prop", "property", "properties"):
            self.command_setconfig(player, payload)
            return True

        if str(payload["command"]).lower() == "ban":
            self.command_banplayer(player, payload)
            return True

        if str(payload["command"]).lower() == "pardon":
            self.command_pardon(player, payload)
            return True

        if str(payload["command"]).lower() == "ban-ip":
            self.command_banip(player, payload)
            return True

        if str(payload["command"]).lower() == "pardon-ip":
            self.command_pardonip(player, payload)
            return True

        # This section calls the commands defined by api.registerCommand()
        for pluginID in self.commands:
            command = payload["command"]
            if pluginID == "Wrapper.py":
                try:
                    self.commands[pluginID][command](payload["player"], payload["args"])
                except Exception as e:
                    self.log.debug("Exception in 'Wrapper.py' while trying to run '%s' command:\n%s", (command, e))
                continue
            if pluginID not in self.wrapper.plugins:
                continue
            plugin = self.wrapper.plugins[pluginID]
            if not plugin["good"]:
                continue
            commandname = payload["command"]
            if commandname in self.commands[pluginID]:
                try:
                    command = self.commands[pluginID][commandname]
                    if player.hasPermission(command["permission"]):
                        command["callback"](payload["player"], payload["args"])
                    else:
                        player.message({"translate": "commands.generic.permission", "color": "red"})
                    return True
                except Exception as e:
                    self.log.exception("Plugin '%s' errored out when executing command: '<%s> /%s':\n%s",
                                       pluginID, payload["player"], command, e)
                    payload["player"].message({"text": "An internal error occurred in wrapper"
                                                       "while trying to execute this command. Apologies.",
                                               "color": "red"})
                    return True

        # Changed the polarity to make sense and allow commands to have return values
        # returning False here will mean no plugin or wrapper command was parsed (so it passes to server).
        return False

    def command_setconfig(self, player, payload):
        if player.isOp() < 4:  # only allowed for console and high level OP
            player.message({"text": "Unknown command. Try /help for a list of commands", "color": "red"})
            return
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
        if section in self.config and item.lower() in ("item", "items", "list", "show"):
            items = ""
            for item in self.config[section]:
                items += "%s: %s\n" % (item, self.config[section][item])
            player.message("&6Items in section %s:" % section)
            player.message("&6__________________________________________________")
            player.message("&9%s" % items)
            return
        if section.lower() == "help" or len(commargs) < 3:
            player.message("&cUsage: /config <section> <item> <desired value> [reload?(T/F)]")
            player.message("&c - Config headers and items are case-sensative!")
            player.message("&c       /config sections - view section headers")
            player.message("&c       /config <section> items - view section items")
            return
        newvalue = getargs(commargs, 2)
        reloadfile = False
        if len(commargs) > 3:
            optionalreload = getargs(commargs, 3)
            if optionalreload.lower() in ("t", "true", "y", "yes"):
                reloadfile = True
        self.wrapper.api.minecraft.configWrapper(section, item, newvalue, reloadfile)

    def command_banplayer(self, player, payload):
        if player.isOp() > 2:  # specify an op level for the command.
            commargs = payload["args"]
            playername = getargs(commargs, 0)
            banexpires = False
            reason = "the Ban Hammer has Spoken"
            timeunit = 86400  # days is default
            lookupuuid = self.wrapper.getuuidbyusername(playername)
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

            returnmessage = self.wrapper.proxy.banuuid(lookupuuid, reason, player.username, banexpires)
            if returnmessage[:6] == "Banned":
                player.message({"text": "%s" % returnmessage, "color": "yellow"})
            else:
                player.message({"text": "UUID ban failed!", "color": "red"})
                player.message(returnmessage)
            return returnmessage

    def command_banip(self, player, payload):
        if player.isOp() > 2:
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

            returnmessage = self.wrapper.proxy.banip(ipaddress, reason, player.username, banexpires)
            if returnmessage[:6] == "Banned":
                player.message({"text": "%s" % returnmessage, "color": "yellow"})
            else:
                player.message({"text": "IP ban failed!", "color": "red"})
                player.message(returnmessage)
            return returnmessage

    def command_pardon(self, player, payload):
        if player.isOp() > 2:  # see http://minecraft.gamepedia.com/Server.properties#Minecraft_server_properties
            commargs = payload["args"]
            playername = getargs(commargs, 0)
            byuuid = True
            if str(getargs(commargs, -1))[-5:].lower() == "false":  # last five letters of last argument
                byuuid = False
            lookupuuid = self.wrapper.getuuidbyusername(playername)
            if not lookupuuid and byuuid:
                player.message({"text": "Not a valid Username!", "color": "red"})
                return False
            if byuuid:
                returnmessage = self.wrapper.proxy.pardonuuid(lookupuuid)
            else:
                returnmessage = self.wrapper.proxy.pardonname(playername)

            if returnmessage[:8] == "pardoned":
                player.message({"text": "player %s unbanned!" % playername, "color": "yellow"})
            else:
                player.message({"text": "player unban %s failed!" % playername, "color": "red"})
            player.message(returnmessage)
            return returnmessage

    def command_pardonip(self, player, payload):
        if player.isOp() > 2:  # see http://minecraft.gamepedia.com/Server.properties#Minecraft_server_properties
            commargs = payload["args"]
            ipaddress = getargs(commargs, 0)

            returnmessage = self.wrapper.proxy.pardonip(ipaddress)
            if returnmessage[:8] == "pardoned":
                player.message({"text": "IP address %s unbanned!" % ipaddress, "color": "yellow"})
            else:
                player.message({"text": "IP unban %s failed!" % ipaddress, "color": "red"})
            player.message(returnmessage)
            return returnmessage

    def command_entities(self, player, payload):
        if player.isOp() > 2:
            entitycontrol = self.wrapper.javaserver.entity_control
            if not entitycontrol:
                # only console could be the source:
                readout("ERROR - ", "No entity code found. (no server started?)", separator="",
                        pad=10, usereadline=self.wrapper.use_readline)
                return
            commargs = payload["args"]
            if len(commargs) < 1:
                pass
            elif commargs[0].lower() in ("c", "count", "s", "sum", "summ", "summary"):
                player.message("Entities loaded: %d" % entitycontrol.countActiveEntities())
                return
            elif commargs[0].lower() in ("k", "kill"):
                eid = getargs(commargs, 1)
                count = getargs(commargs, 2)
                if count < 1:
                    count = 1
                    entitycontrol.killEntityByEID(eid, dropitems=False, finishstateof_domobloot=True, count=count)
                return
            elif commargs[0].lower() in ("l", "list", "sh", "show" "all"):
                player.message("Entities: \n%s" % entitycontrol.entities)
                return
            elif commargs[0].lower() in ("p", "player", "name"):
                if len(commargs) < 3:
                    player.message("&c/entity player <name> count/list")
                    return
                them = entitycontrol.countEntitiesInPlayer(commargs[1])
                if commargs[2].lower() in ("l", "list", "sh", "show" "all"):
                    player.message("Entities: \n%s" % json.dumps(them, indent=2))
                else:
                    player.message("%d entities exist in %s's client." % (len(them), commargs[1]))
                return

            player.message("&cUsage: /entity count")
            player.message("&c       /entity list")
            player.message("&c       /entity player <name> count")
            player.message("&c       /entity player <name> list")
            player.message("&c       /entity kill <EIDofEntity> [count]")

    def command_wrapper(self, player, payload):
        if not player.isOp():
            return
        buildstring = self.wrapper.getbuildstring()
        if len(getargs(payload["args"], 0)) > 0:
            subcommand = getargs(payload["args"], 0)
            if subcommand == "update":
                player.message({"text": "Checking for new Wrapper.py updates...", "color": "yellow"})
                update = self.wrapper.get_wrapper_update_info()
                if update:
                    version, build, repotype = update
                    player.message("&bNew Wrapper.py Version %s (Build #%d) available!)" %
                                   (".".join([str(_) for _ in version]), build))
                    player.message("&bYou are currently on %s." % self.wrapper.getbuildstring())
                    player.message("&aPerforming update...")
                    if self.wrapper.performupdate(version, build, repotype):
                        player.message("&aUpdate completed! Version %s #%d (%s) is now installed. "
                                       "Please reboot Wrapper.py to apply changes." % (version, build, repotype))
                    else:
                        player.message("&cAn error occured while performing update.")
                        player.message("&cPlease check the Wrapper.py console as soon as possible "
                                       "for an explanation and traceback.")
                        player.message("&cIf you are unsure of the cause, please file a bug report "
                                       "on http://github.com/benbaptist/minecraft-wrapper with the traceback.")
                else:
                    player.message("&cNo new Wrapper.py versions available.")
            elif subcommand == "halt":
                player.message("&cHalting Wrapper.py... goodbye!")
                self.wrapper.shutdown()
            elif subcommand in ("mem", "memory"):
                server_bytes = self.wrapper.javaserver.getmemoryusage()
                if server_bytes:
                    amount, units = format_bytes(server_bytes)
                    player.message("&cServer Memory: %s %s (%s bytes)" % (amount, units, server_bytes))
                else:
                    player.message("&cError: Couldn't retrieve memory usage for an unknown reason")
            elif subcommand == "random":
                player.message("&cRandom number: &a%d" % random.randrange(0, 99999999))
        else:
            player.message({"text": "Wrapper.py Version %s" % buildstring, "color": "gray", "italic": True})
        return

    def command_reload(self, player, payload):
        if player.isOp():
            if getargs(payload["args"], 0) == "server":
                return
            try:
                self.wrapper.plugins.reloadplugins()
                player.message({"text": "Plugins reloaded.", "color": "green"})
                if self.wrapper.javaserver.getservertype() != "vanilla":
                    player.message({"text": "Note: If you meant to reload the server's plugins and not "
                                            "Wrapper.py's plugins, run `/reload server` or "
                                            "from the console, use `/raw /reload` or `reload` (with no "
                                            "slash).", "color": "gold"})
            except Exception as e:
                self.log.exception("Failure to reload plugins:\n%s" % e)
                player.message({"text": "An error occurred while reloading plugins. Please check the console "
                                        "immediately for a traceback.", "color": "red"})
            return False

    def command_help(self, player, payload):
        helpgroups = [{"name": "Minecraft", "description": "List regular server commands"}]
        for hid in self.wrapper.help:
            plugin = self.wrapper.help[hid]
            for helpitem in plugin:
                helpgroups.append({"name": helpitem, "description": plugin[helpitem][0]})
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
            if group == "Minecraft":  # if player typed (or clicked) '/help Minecraft [page]'
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
                            "value": "%shelp Minecraft %d" % (self.wrapper.command_prefix, page + 2)
                        }
                    }, {
                        "text": " "
                    }]
                })
            else:
                # Padding, for the sake of making it look a bit nicer
                player.message(" ")
                for hid in self.wrapper.help:
                    for groupName in self.wrapper.help[hid]:
                        #  if groupName.lower() == group:
                        if groupName == group:
                            group = self.wrapper.help[hid][groupName][1]
                            items = []
                            for i in group:
                                command, args, permission = i[0].split(" ")[0], "", None
                                if i[0].split(" ") > 1:
                                    args = getargsafter(i[0].split(" "), 1)
                                if not player.hasPermission(i[2]):
                                    continue
                                if len(i) > 1 and player.isOp():
                                    permission = {"text": "Requires permission '%s'." % i[2],
                                                  "color": "gray", "italic": True}
                                items.append({
                                    "text": "",
                                    "extra": [{
                                        "text": command,
                                        "color": "gold",
                                        "clickEvent": {
                                            "action": "suggest_command",
                                            "value": "%s%s" % (self.wrapper.command_prefix, command[1:])
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
                            showpage(player, page, items, "help %s" % groupName, 4,
                                     command_prefix=self.wrapper.command_prefix)
                            return
                player.message("&cThe help group '%s' does not exist." % group)

        # Plain old /help - print list of help groups
        else:
            items = []
            for v in helpgroups:
                items.append({
                    "text": "",
                    "extra": [{
                        "text": "%s\n" % v["name"],
                        "color": "gold",
                    }, {
                        "text": "/help %s 1" % v["name"],
                        "color": "blue",
                        "clickEvent": {
                            "action": "run_command",
                            "value": "%shelp %s" % (self.wrapper.command_prefix, v["name"])
                        }
                    }, {
                        "text": " - " + v["description"]
                    }]
                })
            showpage(player, page, items, "help", 4, command_prefix=self.wrapper.command_prefix)
        return False

    def command_playerstats(self, player, payload):
        subcommand = getargs(payload["args"], 0)
        if player.isOp():
            totalplaytime = {}
            players = self.wrapper.api.minecraft.getAllPlayers()
            for uu in players:
                if "logins" not in players[uu]:
                    continue
                playername = self.wrapper.getusernamebyuuid(uu)
                totalplaytime[playername] = [0, 0]
                for i in players[uu]["logins"]:
                    totalplaytime[playername][0] += players[uu]["logins"][i] - int(i)
                    totalplaytime[playername][1] += 1

            if subcommand == "all":
                player.message("&6----- All Players' Playtime -----")
                for name in totalplaytime:
                    seconds = totalplaytime[name][0]
                    result = secondstohuman(seconds)
                    player.message("&e%s: &6%s (%d logins)" % (name, result, totalplaytime[name][1]))  # 86400.0
            else:
                topplayers = []
                for username in totalplaytime:
                    topplayers.append((totalplaytime[username][0], username))
                topplayers.sort()
                topplayers.reverse()
                player.message("&6----- Top 10 Players' Playtime -----")
                for i, p in enumerate(topplayers):
                    result = secondstohuman(p[0])
                    player.message("&7%d. &e%s: &6%s" % (i + 1, p[1], result))
                    if i == 9:
                        break
            return

    def command_perms(self, player, payload):
        if "groups" not in self.wrapper.permissions:
            self.wrapper.permissions["groups"] = {}
        if "users" not in self.wrapper.permissions:
            self.wrapper.permissions["users"] = {}
        if "Default" not in self.wrapper.permissions["groups"]:
            self.wrapper.permissions["groups"]["Default"] = {"permissions": {}}
        if player.isOp():
            def usage(l):
                player.message("&cUsage: /%s %s" % (payload["command"], l))
            command = getargs(payload["args"], 0)
            if command == "groups":
                group = getargs(payload["args"], 1)
                subcommand = getargs(payload["args"], 2)
                if subcommand == "new":
                    self.wrapper.permissions["groups"][group] = {"permissions": {}}
                    player.message("&aCreated a new permissions group '%s'!" % group)
                elif subcommand == "delete":
                    if group not in self.wrapper.permissions["groups"]:
                        player.message("&cGroup '%s' does not exist!" % group)
                        return
                    del self.wrapper.permissions["groups"][group]
                    player.message("&aDeleted permissions group '%s'." % group)
                elif subcommand == "set":
                    if group not in self.wrapper.permissions["groups"]:
                        player.message("&cGroup '%s' does not exist!" % group)
                        return
                    node = getargs(payload["args"], 3)
                    value = getargsafter(payload["args"], 4)
                    if len(value) == 0:
                        value = True
                    if value in ("True", "False"):
                        value = ast.literal_eval(value)
                    if len(node) > 0:
                        self.wrapper.permissions["groups"][group]["permissions"][node] = value
                        player.message("&aAdded permission node '%s' to group '%s'!" % (node, group))
                    else:
                        usage("groups %s set <permissionNode> [value]" % group)
                elif subcommand == "remove":
                    if group not in self.wrapper.permissions["groups"]:
                        player.message("&cGroup '%s' does not exist!" % group)
                        return
                    node = getargs(payload["args"], 3)
                    if node in self.wrapper.permissions["groups"][group]["permissions"]:
                        del self.wrapper.permissions["groups"][group]["permissions"][node]
                        player.message("&aRemoved permission node '%s' from group '%s'." % (node, group))
                elif subcommand == "info":
                    if group not in self.wrapper.permissions["groups"]:
                        player.message("&cGroup '%s' does not exist!" % group)
                        return
                    player.message("&aUsers in the group '%s':" % group)
                    for uuid in self.wrapper.permissions["users"]:
                        if group in self.wrapper.permissions["users"][uuid]["groups"]:
                            player.message("%s: &2%s" % (self.wrapper.getusernamebyuuid(uuid), uuid))
                    player.message("&aPermissions for the group '%s':" % group)
                    for node in self.wrapper.permissions["groups"][group]["permissions"]:
                        value = self.wrapper.permissions["groups"][group]["permissions"][node]
                        if value:
                            player.message("- %s: &2%s" % (node, value))
                        elif not value:
                            player.message("- %s: &4%s" % (node, value))
                        else:
                            player.message("- %s: &7%s" % (node, value))
                else:
                    player.message("&cList of groups: %s" % ", ".join(self.wrapper.permissions["groups"]))
                    usage("groups <groupName> [new/delete/set/remove/info]")
            elif command == "users":
                username = getargs(payload["args"], 1)
                subcommand = getargs(payload["args"], 2)
                uuid = self.wrapper.getuuidbyusername(username).string
                if not uuid:
                    player.message("&cNo valid UUID exists for '%s'." % username)
                    return False
                if len(username) > 0:
                    if uuid not in self.wrapper.permissions["users"]:
                        self.wrapper.permissions["users"][uuid] = {"groups": [], "permissions": {}}
                if subcommand == "group":
                    group = getargs(payload["args"], 3)
                    if len(group) > 0:
                        if group not in self.wrapper.permissions["groups"]:
                            player.message("&cGroup '%s' does not exist!" % group)
                            return
                        if group not in self.wrapper.permissions["users"][uuid]["groups"]:
                            self.wrapper.permissions["users"][uuid]["groups"].append(group)
                            player.message("&aAdded user '%s' to group '%s'!" % (username, group))
                        else:
                            self.wrapper.permissions["users"][uuid]["groups"].remove(group)
                            player.message("&aRemoved user '%s' from group '%s'!" % (username, group))
                    else:
                        usage("users <username> group <groupName>")
                elif subcommand == "set":
                    node = getargs(payload["args"], 3)
                    value = getargsafter(payload["args"], 4)
                    if len(value) == 0:
                        value = True
                    if value in ("True", "False"):
                        value = ast.literal_eval(value)
                    if len(node) > 0:
                        self.wrapper.permissions["users"][uuid]["permissions"][node] = value
                        player.message("&aAdded permission node '%s' to player '%s'!" % (node, username))
                    else:
                        usage("users %s set <permissionNode> [value]" % username)
                elif subcommand == "remove":
                    node = getargs(payload["args"], 3)
                    if node not in self.wrapper.permissions["users"][uuid]["permissions"]:
                        player.message("&cPlayer '%s' never had permission '%s'!" % (username, node))
                        return
                    if node in self.wrapper.permissions["users"][uuid]["permissions"]:
                        del self.wrapper.permissions["users"][uuid]["permissions"][node]
                        player.message("&aRemoved permission node '%s' from player '%s'." % (node, username))
                        return
                elif subcommand == "info":
                    player.message("&aUser '%s' is in these groups: " % username)
                    for group in self.wrapper.permissions["users"][uuid]["groups"]:
                        player.message("- %s" % group)
                    player.message("&aUser '%s' is granted these individual permissions "
                                   "(not including permissions inherited from groups): " % username)
                    for node in self.wrapper.permissions["users"][uuid]["permissions"]:
                        value = self.wrapper.permissions["users"][uuid]["permissions"][node]
                        if value:
                            player.message("- %s: &2%s" % (node, value))
                        elif not value:
                            player.message("- %s: &4%s" % (node, value))
                        else:
                            player.message("- %s: &7%s" % (node, value))
                else:
                    usage("users <username> <group/set/remove/info>")
            else:
                usage("<groups/users/RESET> (Note: RESET is case-sensitive!)")
                player.message("&cAlias commands: /perms, /perm, /super")
            return False

    def command_plugins(self, player):
        # CONSOLE should use the pretty version designed for console.
        if player.isOp():
            player.message({
                "text": "List of plugins installed:",
                "color": "red",
                "italic": True
            })
            for pid in self.wrapper.plugins:
                plugin = self.wrapper.plugins[pid]
                if plugin["good"]:
                    name = plugin["name"]
                    version = plugin["version"]
                    summary = plugin["summary"]
                    description = plugin["description"]
                else:
                    name = pid
                    version = None
                    summary = None
                    description = ""
                if summary is None:
                    summary = {
                        "text": "No description is available for this plugin",
                        "color": "gray",
                        "italic": True,
                        "hoverEvent": {
                            "action": "show_text",
                            "value": description
                        }
                    }
                else:
                    summary = {
                        "text": summary,
                        "color": "white",
                        "hoverEvent": {
                            "action": "show_text",
                            "value": description
                        }
                    }

                if version is None:
                    version = "v?.?"
                else:
                    version = ".".join([str(_) for _ in version])
                if plugin["good"]:
                    player.message({
                        "text": name,
                        "color": "dark_green",
                        "hoverEvent": {
                            "action": "show_text",
                            "value": "Filename: %s | ID: %s" % (plugin["filename"], pid)
                        },
                        "extra": [{
                            "text": " v%s" % version,
                            "color": "dark_gray"
                        }, {
                            "text": " - ",
                            "color": "white"
                        }, summary]
                    })
                else:
                    player.message({
                        "text": name,
                        "color": "dark_red",
                        "extra": [{
                            "text": " - ",
                            "color": "white"
                        }, {
                            "text": "Failed to import this plugin!",
                            "color": "red",
                            "italic": "true"
                        }]
                    })
                return False
