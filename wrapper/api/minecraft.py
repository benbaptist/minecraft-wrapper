# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from __future__ import unicode_literals

import json
import os
from core.nbt import NBTFile
from core.entities import Items
from api.helpers import scrub_item_value
from proxy.mcpackets_cb import Packets as ClientBound
from proxy.mcpackets_sb import Packets as ServerBound


# noinspection PyPep8Naming
# noinspection PyBroadException
class Minecraft(object):
    """
    .. code:: python

        def __init__(self, wrapper)

    ..

    This class contains functions related to in-game features
    directly. These methods are accessed using 'self.api.minecraft'

    """

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self._encoding = wrapper.config["General"]["encoding"]
        self.serverpath = wrapper.config["General"]["server-directory"]
        self.interfacecfg = self.wrapper.configManager

        blockdata = Items()
        self.blocks = blockdata.itemslist

    def configWrapper(self, section, config_item, new_value, reload_file=False):
        """
        *New feature starting in version 0.8.12*

        Edits the Wrapper.Properties.json file

        :Args:
            :section:

            :config_item:

            :new_value:

            :reload_file: True to reload the config

        :returns: True or False, indicating Success or Failure

        """

        # detect and correct lists
        try:
            if len(new_value.split(',')) > 1:
                new_value = new_value.split(",")
        except:
            pass
        # correct any string to boolean or integer
        new_value = scrub_item_value(new_value)

        if self.interfacecfg.change_item(section, config_item, new_value):
            self.interfacecfg.save()
            if reload_file:
                self.interfacecfg.loadconfig()
            return True
        self.log.error("API.Minecraft configWrapper failed.")
        return False

    def isServerStarted(self):
        # should this be a property? (one-liner doc string suggests so..)
        """
        Return a boolean indicating if the server is
        fully booted or not.

        """
        if self.getServer():
            if self.getServer().state == 2:
                return True
        return False

    def getServerPackets(self, packets="CB"):
        if not self.wrapper.proxymode:
            return False

        server = self.getServer()
        version = server.protocolVersion

        if packets == "CB":
            return ClientBound(version)
        else:
            return ServerBound(version)

    def getTimeofDay(self, dttmformat=0):
        """
        get the "virtual" world time of day on the server.

        :arg dttmformat: 0 = ticks, 1 = Military, (else = civilian AM/PM).

            :ticks: are useful for timebased- events (like spawing
             your own mobs at night, etc).
            :Miliary/civilian: is useful for player displays.

        :returns: The appropriately formatted time string

        """
        # 0 = ticks, 1 = Military, else = civilian AM/PM, return -1 if no one
        # on or server not started
        if self.isServerStarted() is True:
            servertimeofday = self.getServer().timeofday
            ticktime = servertimeofday % 24000
            if dttmformat == 0 or ticktime == -1:
                return ticktime
            mth = (ticktime + 6000) / 10
            if mth > 2399:
                mth = - 2400
            mins = int(float(mth % 100) * float(.6))
            mth = (mth / 100)
            if dttmformat == 1:
                return "%02d:%02d" % (mth, mins)
            if mth > 12:
                ampm = "PM"
                cth = mth - 12
            else:
                ampm = "AM"
                cth = mth
            return "%d:%02d %s" % (cth, mins, ampm)
        return -1

    def giveStatusEffect(self, player, effect, duration=30, amplifier=30):
        """
        Gives the specified status effect to the specified target.

        :Args: (self explanatory? -see official Minecraft Wiki)

            :player: A player name or any valid string target
             selector (@p/e/a) with arguments ([r=...], etc)
            :effect:
            :duration:
            :amplifier:

        :returns: Nothing; runs in console

        """
        if type(effect) == int:
            effectconverted = str(effect)
        else:
            try:
                effectconverted = int(effect)
            # a non-number was passed, so we'll figure out what status
            # effect it was in word form
            except:
                if effect in self.wrapper.api.statusEffects:
                    effectconverted = str(
                        self.wrapper.api.statusEffects[effect])
                else:
                    raise Exception("Invalid status effect given!")
        if int(effectconverted) > 24 or int(effectconverted) < 1:
            raise Exception("Invalid status effect given!")
        self.console("effect %s %s %d %d" % (player, effectconverted,
                                             duration, amplifier))

    def getAllPlayers(self):
        """
        Returns a dict containing the uuids and associated
        login data of all players ever connected to the server.

        """
        alluuidfiles = os.listdir("wrapper-data/players")

        # do this now so we don't re-run it in each 'for .. in ..' loop
        if self.wrapper.isonlinemode():
            online = True
        else:
            online = False

        players = {}
        for uuid_file_found in alluuidfiles:
            player_uuid = uuid_file_found.rsplit(".", 1)[0]

            username = self.wrapper.uuids.getusernamebyuuid(player_uuid)
            if username in (False, None):
                player_uuid = "None"

            # remove any old bad 'None' and 'False' files.
            if player_uuid in ("None", "False"):
                os.remove("wrapper-data/players/%s" % uuid_file_found)
                continue

            # if the server is in online mode and the player's offline
            # and regular uuid are the same...
            if online:
                if player_uuid == self.wrapper.uuids.getuuidfromname(username):
                    continue

            with open("wrapper-data/players/%s" % uuid_file_found) as f:
                data = f.read()
            try:
                players[player_uuid] = json.loads(data, self._encoding)
            except Exception as e:
                self.log.error("Failed to load player data"
                               " '%s':\n%s", player_uuid, e)
                os.remove("wrapper-data/players/" + uuid_file_found)
        return players

    def getPlayers(self):  # returns a list of players
        """
        Returns a list of the currently connected players.

        """
        return self.getServer().players

    def getEntityControl(self):
        """
        Returns the server's entity controls context.  Will be None if
        the server is not up.

        Supported variables and methods:

        :These variables affect entity processing:
            :Property: Config Location

            :self.entityControl:
             config["Entities"]["enable-entity-controls"]

            :self.entityProcessorFrequency:
             config["Entities"]["entity-update-frequency"]

            :self.thiningFrequency:
             config["Entities"]["thinning-frequency"]

            :self.startThinningThreshshold:
             config["Entities"]["thinning-activation-threshhold"]

        :See api.entity for more about these methods:

                def killEntityByEID(self, eid, dropitems=False, count=1)

                def existsEntityByEID(self, eid)

                def getEntityInfo(self, eid)

                def countEntitiesInPlayer(self, playername)

                def countActiveEntities(self)

                def getEntityByEID(self, eid)


        """
        return self.wrapper.javaserver.entity_control

    def getPlayer(self, username=""):
        """
        Returns the player object of the specified logged-in player.
        Will raise an exception if the player is not logged in.

        :arg username: playername

        :returns: The Player Class object for "playername".

        """
        try:
            return self.wrapper.javaserver.players[str(username)]
        except Exception as e:
            self.log.error("No such player %s is logged in:\n%s", username, e)

    def getPlayerDat(self, name):
        pass
        # TODO a good idea

    def getOfflineUUID(self, name):
        """

        :arg name: gets UUID object based on "OfflinePlayer:<name>"

        :returns: a MCUUID object based on the name

        """
        return self.wrapper.uuids.getuuidfromname(name)

    def lookupUUID(self, uuid):
        """
        Returns a dictionary of {"uuid: the-uuid-of-the-player,
        "name": playername}. legacy function from the old 0.7.7 API.

        lookupbyUUID() is a better and more direct way to get the
        name from a uuid.

        :arg uuid:  player uuid

        :returns: a dictionary of two items, {"uuid: <player-uuid>,
         "name": <playername>}

        """
        name = self.lookupbyUUID(uuid)
        uuid = str(self.lookupbyName(name))
        dictitem = {"uuid": uuid, "name": name}
        return dictitem

    def lookupbyUUID(self, uuid):
        """
        Returns the username from the specified UUID.
        If the player has never logged in before and isn't in the user
        cache, it will poll Mojang's API.  The function will return
        False if the UUID is invalid.

        :arg uuid: string uuid with dashes

        :returns: username

        """
        return self.wrapper.uuids.getusernamebyuuid(uuid)

    def lookupbyName(self, name):
        """
        Returns the UUID from the specified username.
        If the player has never logged in before and isn't in the
        user cache, it will poll Mojang's API.  The function will
        return False if the name is invalid.

        :arg name:  player name

        :returns: a UUID object (wrapper type MCUUID)

        """
        return self.wrapper.uuids.getuuidbyusername(name)

    # World and console interaction

    def setLocalName(self, MojangUUID, desired_name, kick=True):
        """
        Set the local name on the server.  Understand that this
        may cause a vanilla server UUID change and loss of player
        data from the old name's offline uuid.

        """

        cache = self.getUuidCache()
        proper_name_spelling = self.lookupbyUUID(MojangUUID)
        if not proper_name_spelling:
            self.log.error("incorrect UUID %s supplied to"
                           " api.minecraft.setLocalName()", MojangUUID)
            return False

        orig_server_uuid = self.getOfflineUUID(proper_name_spelling)
        new_server_uuid = self.getOfflineUUID(desired_name)

        worldname = str(self.getWorldName())
        statsdir = ("%s/stats" % worldname)
        sourcedir = "%s/playerdata/%s.dat" % (worldname, orig_server_uuid)
        destdir = "%s/playerdata/%s.dat" % (worldname, new_server_uuid)

        # do the name change in the cache
        if MojangUUID in cache:
            cache[MojangUUID]["localname"] = desired_name
            cache.save()

        # kicking them is needed to complete the process
        if kick:
            self.console("kick %s Wrapper is changing your name..." %
                         proper_name_spelling)

        if not os.path.exists(sourcedir):
            self.log.error("(setLocalName): No such directory: %s", sourcedir)
            return False

        # copy files
        with open(sourcedir, 'rb') as f:
            data = f.read()
        with open(destdir, 'wb') as f:
            f.write(data)
        with open(("%s/%s.json" % (statsdir, orig_server_uuid)), 'rb') as f:
            data = f.read()
        with open(("%s/%s.json" % (statsdir, new_server_uuid)), 'wb') as f:
            f.write(data)

        return True

    def console(self, string):
        """
        Run a command in the Minecraft server's console.

        :arg string: Full command text(without slash)

        :returns: Nothing

        """
        try:
            self.getServer().console(string)
        except:
            pass

    def message(self, destination="", jsonmessage=""):
        """
        Used to message some specific target.

        :Args:
            :destination: playername or target
             selector '@a', 'suresttexas00' etc
            :jsonmessage: strict json chat message

        :returns: Nothing; succeeds or fails with no programmatic indication.

        """
        self.getServer().broadcast(self, jsonmessage, who=destination)

    def broadcast(self, message="", irc=False):
        """
        Broadcasts the specified message to all clients connected.
        message can be a JSON chat object, or a string with formatting
        codes using the & as a prefix. Setting irc=True will also
        broadcast the specified message on IRC channels that Wrapper.py
        is connected to. Formatting might not work properly.

        :Args:
            :message:  The message
            :irc: Also broadcast to IRC if set to True.

        :returns:  Nothing

        """
        if irc:
            try:
                self.wrapper.irc.msgQueue.append(message)
            except Exception:
                pass
        try:
            self.wrapper.javaserver.broadcast(message)
        except Exception:
            pass

    def deOp(self, name_to_deop, playerObj=None,):
        """
        De-ops player 'name_to_deop'.  If he is a super-op, the
        name is removed from superops.txt also.  Case sensitive!

        :Requires: Running server instance.

        :Args:
            :playerObj: This is the player that receives the command's
             output.  Setting 'None' uses the console operator (and
             permissions!). This player object must have OP level 10
             permission.
            :name_to_deop: The player to de-op.  Must match what is
             in superops.txt to remove superOP perms, but may deop
             the server ops.json file without case-sensitivity.

        :returns: True if success, a text message on failure.

        """
        result = self.wrapper.commands.command_deop(
            playerObj, (name_to_deop, ))
        return result

    def makeOp(self, nametoOP, argslist, playerObj=None):
        """
        Ops player 'nametoOP'.  Case sensitivity and other
        bahaviors of the command vary with server status and
        the arguments to 'argslist'

        :nametoOP: Name of player to OP.

        :playerObj: This is the player that receives the command's
         output.  Setting 'None' uses the console operator (and
         permissions!). This player object must have OP level 10
         permission.

        :Valid args for argslist:
            :-s: make player superop.txt entry.  Player will still
             not be superOP unless given appropriate level.
            :-o: use offline name and uuid.  This option only
             works if the server is not running!  Otherwise,
             the server uses its' default (depending on server
             mode).
            :-l: Flag for next argument to be a number
             corresponding to the desired level.  If the server is
             running, this argument only superops.txt is updated.
             if server is not running, the json.ops is also
             updated (to a maximum level of 4).
            :<number>: A number corresponding to the desired
             '-l' level.  These are two separate arguments and
             this number must be the next argument after -l in
             the list.

        :Notes:
            - Json.ops controls minecraft server permissions.
              This command CAN alter json.ops if the server is
              not running.
            - superops.txt controls wrapper commands, INCLUDING
              proxy ban commands.

        :returns: Nothing.  All output is directed to playerObj.

        """
        args = [nametoOP]
        for arg in argslist:
            args.append(arg)
        self.wrapper.commands.command_op(self, playerObj, args)

    def refreshOpsList(self):
        """
        OPs list is read from disk at startup.  Use this method
        to refresh the in-memory list from disk.

        """
        try:
            self.wrapper.javaserver.refresh_ops()
        except:
            # server is probably not up, so it will refresh at startup
            pass

    # functions must all be on one line to import to the documentation
    def setBlock(self, x, y, z, tilename, datavalue=0, oldblockhandling="replace", datatag=None):
        """
        Sets a block at the specified coordinates with the specific
        details. Will fail if the chunk is not loaded.

        :Args:  See the minecraft command wiki for these setblock arguments:

                :x:
                :y:
                :z:
                :tilename:
                :datavalue:
                :datatag:
                :oldblockhandling:

        :returns: Nothing.

        """
        if not datatag:
            datatag = {}
        self.console("setblock %d %d %d %s %d %s %s"
                     % (x, y, z, tilename, datavalue, oldblockhandling,
                        json.dumps(datatag, self._encoding).replace('"', "")))

    def summonEntity(self, entity, x=0, y=0, z=0, datatag=None):
        """
        Summons an entity at the specified coordinates with the
        specified data tag.

        :Args:

                :entity: string entity name type (capitalized correctly!)
                :x: coords
                :y:
                :z:
                :datatag: strict json text datatag


        :returns: Nothing - console executes command.

        """

        # should not use mutable default arguments like dataTag={}
        if not datatag:
            datatag = {}
        self.console("summon %s %d %d %d %s" % (
            entity, x, y, z, json.dumps(datatag, self._encoding)))

    def teleportAllEntities(self, entity, x, y, z):
        """
        Teleports all of the specific entity type to the specified coordinates.

        :Args:
                :entity: string entity name type (capitalized correctly!)
                :x: coords
                :y:
                :z:

        :returns: Nothing - console executes command.

        """
        self.console("tp @e[type=%s] %d %d %d" % (entity, x, y, z))

    # Get world-based information

    def getLevelInfo(self, worldname=False):
        """
        Get the world level.dat.

        :arg worldname:
            optional world name.  If not
            specified, Wrapper looks up the server worldname.

        :returns: Return an NBT object of the world's level.dat.

        """
        if not worldname:
            worldname = self.wrapper.javaserver.worldname
        if not worldname:
            raise Exception("Server Uninitiated")
        f = NBTFile("%s/%s/level.dat" % (self.serverpath, worldname), "rb")
        return f["Data"]

    def getGameRules(self):
        """
        Get the server gamerules.

        :returns: a dictionary of the gamerules.

        """
        game_rules = self.getLevelInfo()["GameRules"]
        rules = {}
        for rule in game_rules:
            rules[rule] = str(game_rules[rule])
            if rules[rule] == "true":
                rules[rule] = True
            elif rules[rule] == "false":
                rules[rule] = False
            else:
                rules[rule] = int(rules[rule])
        return rules

    def getSpawnPoint(self):
        """
        Get the spawn point of the current world.

        :returns: Returns the spawn point of the current world.

        """
        return (int(str(self.getLevelInfo()["SpawnX"])),
                int(str(self.getLevelInfo()["SpawnY"])),
                int(str(self.getLevelInfo()["SpawnZ"])))

    def getTime(self):
        """
        Gets the world time in ticks.  This is total ticks since
        the server started! modulus the value by 24000 to get the time.

        :returns: Returns the time of the world in ticks.

        """
        return int(str(self.getLevelInfo()["Time"]))

    def getServer(self):
        """
        Returns the server context.  Use at own risk - items
        in server are generally private or subject to change (you are
        working with an undefined API!)... what works in this wrapper
        version may not work in the next.

        :returns: The server context that this wrapper is running.

        """
        return self.wrapper.javaserver

    def getServerPath(self):
        """
        Gets the server's path.

        """
        return self.wrapper.javaserver.serverpath

    def getWorld(self):
        """
        Get the world context

        :returns: Returns the world context of 'api.world, class World'
         for the running server instance

        """
        return self.getServer().world

    def getWorldName(self):
        """
        Returns the world's name.

        """
        return self.getServer().worldname

    def getUuidCache(self):
        """
        Gets the wrapper uuid cache.  This is as far as the API goes.
        The format of the cache's contents are undefined by this API.

        """
        return self.wrapper.usercache

    # Ban related items - These wrap the proxy base methods

    # functions must all be on one line to import to the documentation
    def banUUID(self, playeruuid, reason="by wrapper api.", source="minecraft.api", expires=False):
        """
        Ban a player using the wrapper proxy system.

        :args:

                :playeruuid: Player's uuid... specify the mojangUuid
                 for online ban and offlineUuid for offline bans.

                :reason: Optional text reason.

                :source: Source (author/op) of ban.

                :expires: Optional expiration in time.time() format.
                 Expirations only work when wrapper handles the login
                 (proxy mode).. and only for online bans.

        :returns: String describing the operation's outcome.

        """
        return self.wrapper.proxy.banuuid(playeruuid, reason, source, expires)

    def banName(self, playername, reason="by wrapper api.", source="minecraft.api", expires=False):
        """
        Ban a player using the wrapper proxy system.  Will attempt to
        poll or read cache for name. If no valid name is found, does a
        name-only ban with offline-hashed uuid

        :args:

                :playername: Player's name... specify the mojangUuid for online
                 ban and offlineUuid for offline bans.

                :reason: Optional text reason.

                :source: Source (author/op) of ban.

                :expires: Optional expiration in time.time() format.
                 Expirations only work when wrapper handles the login
                 (proxy mode).. and only for online bans.

        :returns: String describing the operation's outcome.

        """
        useruuid = self.wrapper.uuids.getuuidbyusername(playername)
        if not useruuid:
            return self.wrapper.proxy.banuuidraw(useruuid, playername,
                                                 reason, source, expires)
        else:
            return self.wrapper.proxy.banuuid(playername, reason,
                                              source, expires)

    def banIp(self, ipaddress, reason="by wrapper api.", source="minecraft.api", expires=False):
        """
        Ban an ip address using the wrapper proxy system. Messages
        generated by process can be directed to a particular player's
        client or to the Console (default). Ban will fail if it is not
        a valid ip4 address.

        :args:

                :ipaddress: IP address to ban
                :reason: Optional text reason
                :source: Source (author/op) of ban.
                :expires: Optional expiration in time.time() format.

        :returns: String describing the operation's outcome.

        """
        return self.wrapper.proxy.banip(ipaddress, reason, source, expires)

    def pardonName(self, playername):
        """
        Pardon a player.

        :arg playername:  Name to pardon.

        :returns: String describing the operation's outcome.

        """
        return self.wrapper.proxy.pardonname(playername)

    def pardonUUID(self, playeruuid):
        """
        Pardon a player by UUID.

        :arg playeruuid:  UUID to pardon

        :returns: String describing the operation's outcome.

        """
        return self.wrapper.proxy.pardonuuid(playeruuid)

    def pardonIp(self, ipaddress):
        """
        Pardon an IP.

        :arg ipaddress: a valid IPV4 address to pardon.

        :returns:  String describing the operation's outcome.

        """
        return self.wrapper.proxy.pardonip(ipaddress)

    def isUUIDBanned(self, uuid):
        """
        Check if a uuid is banned.  Using this method also refreshes
        any expired bans and unbans them.

        :arg uuid: Check if the UUID of the user is banned

        :returns: True or False (banned or not banned)

        """
        return self.wrapper.proxy.isuuidbanned(uuid)

    def isIpBanned(self, ipaddress):
        """
        Check if a ipaddress is banned.  Using this method also
        refreshes any expired bans and unbans them.

        :arg ipaddress: Check if an ipaddress is banned

        :returns: True or False (banned or not banned)

        """
        return self.wrapper.proxy.isipbanned(ipaddress)
