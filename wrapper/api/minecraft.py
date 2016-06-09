# -*- coding: utf-8 -*-

# p2 and py3 compliant

from __future__ import unicode_literals

import json
import os
from core.nbt import NBTFile
from core.entities import Items


# noinspection PyBroadException
class Minecraft:
    """ This class contains functions related to in-game features directly. These methods are
    located at self.api.minecraft. """

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.proxy = wrapper.proxy
        self.log = wrapper.log
        self._encoding = wrapper.config["General"]["encoding"]
        self.serverpath = wrapper.config["General"]["server-directory"]

        blockdata = Items()
        self.blocks = blockdata.itemslist

    def isServerStarted(self):
        """

        Returns: Returns a boolean if the server is fully booted or not.

        """
        if self.getServer():
            if self.getServer().state == 2:
                return True
        return False

    def getTimeofDay(self, dttmformat=0):
        """
        Returns the "virtual" world time of day on the server.

        Args:
            dttmformat: 0 = ticks, 1 = Military, (else = civilian AM/PM). Ticks are useful for
                timebased- events (like spawing your own mobs at night, etc). Miliary or civilian
                is useful for player displays.

        Returns: The appropriately formatted time string

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

        Args:
            player: A player name or any valid string target selector (@p/e/a) with arguments ([r=...], etc)
            effect:
            duration:
            amplifier:

        Returns: Nothing; runs in console

        """
        if type(effect) == int:
            effectconverted = str(effect)
        else:
            try:
                effectconverted = int(effect)
            except:  # a non-number was passed, so we'll figure out what status effect it was in word form
                if effect in self.wrapper.api.statusEffects:
                    effectconverted = str(self.wrapper.api.statusEffects[effect])
                else:
                    raise Exception("Invalid status effect given!")
        if int(effectconverted) > 24 or int(effectconverted) < 1:
            raise Exception("Invalid status effect given!")
        self.console("effect %s %s %d %d" % (player, effectconverted, duration, amplifier))

    def getAllPlayers(self):
        """

        Returns: Returns a dict containing the uuids and associated login data of all
        players ever connected to the server.

        """
        if self.wrapper.isonlinemode():
            online = True
        else:
            online = False
        players = {}
        for uuidf in os.listdir("wrapper-data/players"):
            puuid = uuidf.rsplit(".", 1)[0]

            username = self.wrapper.getusernamebyuuid(puuid)
            if type(username) != str:
                puuid = "None"

            # remove any old bad objects
            if puuid in ("None", "False"):
                os.remove("wrapper-data/players/" + uuidf)
                continue

            offinelineuuid = self.wrapper.getuuidfromname(username)
            if online:
                if offinelineuuid == puuid:
                    continue
            with open("wrapper-data/players/" + uuidf) as f:
                data = f.read()
            try:
                players[puuid] = json.loads(data, self._encoding)
            except Exception as e:
                self.log.error("Failed to load player data '%s':\n%s", puuid, e)
                os.remove("wrapper-data/players/" + uuidf)
        return players

    def getPlayers(self):  # returns a list of players
        """

        Returns: Returns a list of the currently connected players.

        """
        return self.getServer().players

    def getPlayer(self, username=""):
        """
        Returns the player object of the specified logged-in player. Will raise an exception if
        the player is not logged in.
        Args:
            username: playername

        Returns: The Player Class object for "playername".

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
        :param name: gets UUID object based on "OfflinePlayer:<playername>"
        :return: a MCUUID object based on the name
        """
        return self.wrapper.getuuidfromname(name)

    def lookupName(self, uuid):  # This function is just part of the API for plugin devs/users.
        """
        Returns the username from the specified UUID.
        If the player has never logged in before and isn't in the user cache, it will poll Mojang's API.
        The function will raise an exception if the UUID is invalid.

        Args:
            uuid: string uuid with dashes

        Returns: username

        """
        return self.wrapper.getusernamebyuuid(uuid)

    def lookupUUID(self, name):  # This function is just part of the API for plugin devs/users.
        """
        Returns the UUID from the specified username.
        If the player has never logged in before and isn't in the user cache, it will poll Mojang's API.
        The function will raise an exception if the name is invalid.

        Args:
            name:  player name

        Returns: a UUID object (wrapper type MCUUID)

        """
        return self.wrapper.getuuidbyusername(name)

    # World and console interaction

    def console(self, string):
        """
        Run a command in the Minecraft server's console.
        Args:
            string: Full command text(without slash)

        Returns: Nothing

        """
        try:
            self.getServer().console(string)
        except:
            pass

    def message(self, destination="", jsonmessage=""):
        """
        Used to message some specific target.

        Args:
            destination: playername or target selector '@a', 'suresttexas00' etc
            jsonmessage: strict json chat message

        Returns: Nothing; succeeds or fails with no programmatic indication.

        """
        self.console("tellraw %s %s" % (destination, json.dumps(jsonmessage, self._encoding)))

    def broadcast(self, message="", irc=False):
        """
        Broadcasts the specified message to all clients connected. message can be a JSON chat object,
        or a string with formatting codes using the & as a prefix. Setting irc=True will also broadcast
        the specified message on IRC channels that Wrapper.py is connected to. Formatting might not
        work properly.

        Args:
            message:
            irc: Broadcast to IRC if set to True.

        Returns:

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

    def setBlock(self, x, y, z, tilename, datavalue=0, oldblockhandling="replace", datatag=None):
        """
        Sets a block at the specified coordinates with the specific details. Will fail if the
         chunk is not loaded.
        Args:  See wiki for setblock
            x:
            y:
            z:
            tilename:
            datavalue:
            oldblockhandling:
            datatag:

        Returns: Nothing.

        """
        if not datatag:
            datatag = {}
        self.console("setblock %d %d %d %s %d %s %s"
                     % (x, y, z, tilename, datavalue, oldblockhandling,
                        json.dumps(datatag, self._encoding).replace('"', "")))

    def summonEntity(self, entity, x=0, y=0, z=0, datatag=None):
        """
        Summons an entity at the specified coordinates with the specified data tag.
        Args:
            entity: string entity name type (capitalized correctly!)
            x: coords
            y:
            z:
            datatag: strict json text datatag

        Returns: Nothing - console executes command.

        """
        if not datatag:  # should not use mutable default arguments like dataTag={}
            datatag = {}
        self.console("summon %s %d %d %d %s" % (entity, x, y, z, json.dumps(datatag, self._encoding)))

    def teleportAllEntities(self, entity, x, y, z):
        """
        Teleports all of the specific entity type to the specified coordinates.

        Args:
            entity: string entity name type (capitalized correctly!)
            x: coords
            y:
            z:

        Returns: Nothing - console executes command.

        """
        self.console("tp @e[type=%s] %d %d %d" % (entity, x, y, z))

    # Get world-based information

    def getLevelInfo(self, worldname=False):
        """

        Args:
            worldname: optional world name.  If not specified, Wrapper looks up the server worldname.

        Returns: Return an NBT object of the world's level.dat.

        """
        if not worldname:
            worldname = self.wrapper.javaserver.worldname
        if not worldname:
            raise Exception("Server Uninitiated")
        f = NBTFile("%s/%s/level.dat" % (self.serverpath, worldname), "rb")
        return f["Data"]

    def getSpawnPoint(self):
        """

        Returns: Returns the spawn point of the current world.

        """
        return (int(str(self.getLevelInfo()["SpawnX"])), int(str(self.getLevelInfo()["SpawnY"])),
                int(str(self.getLevelInfo()["SpawnZ"])))

    def getTime(self):
        """

        Returns: Returns the time of the world in ticks.

        """
        return int(str(self.getLevelInfo()["Time"]))

    def getServer(self):
        """

        Returns: Returns the server context.

        """
        return self.wrapper.javaserver

    def getWorld(self):
        """

        Returns: Returns the world context.

        """
        return self.getServer().world

    def getWorldName(self):
        """

        Returns: Returns the world's name.

        """
        print("getworldname = %s" % self.getServer().worldname)
        return self.getServer().worldname

    # Ban related items - These simply wrap the proxy base methods
    def banUUID(self, playeruuid, reason="by wrapper api.", source="minecraft.api", expires=False):
        """
        Ban a player using the wrapper proxy system.

        Args:
            playeruuid: Player's uuid... specify the mojangUuid for online ban and offlineUuid
                for offline bans.
            reason: Optional text reason.
            source: Source (author/op) of ban.
            expires: Optional expiration in time.time() format.  Expirations only work when wrapper
                handles the login (proxy mode).. and only for online bans.

        Returns: String describing the operation's outcome.
        """
        return self.wrapper.proxy.banuuid(playeruuid, reason, source, expires)

    def banName(self, playername, reason="by wrapper api.", source="minecraft.api", expires=False):
        """
        Ban a player using the wrapper proxy system.  Will attempt to poll or read cache for name. If
        no valid name is found, does a name-only ban with offline-hashed uuid

        Args:
            playername: Player's name... specify the mojangUuid for online ban and offlineUuid
                for offline bans.
            reason: Optional text reason
            source: Source (author/op) of ban.
            expires: Optional expiration in time.time() format.  Expirations only work when wrapper
                handles the login (proxy mode).. and only for online bans.

        Returns: String describing the operation's outcome.
        """
        useruuid = self.wrapper.getuuidbyusername(playername)
        if not useruuid:
            return self.wrapper.proxy.banuuidraw(useruuid, playername, reason, source, expires)
        else:
            return self.wrapper.proxy.banuuid(playername, reason, source, expires)

    def banIp(self, ipaddress, reason="by wrapper api.", source="minecraft.api", expires=False):
        """
        Ban an ip address using the wrapper proxy system. Messages generated by process can be directed to
        a particular player's client or to the Console (default). Ban will fail if it is not a valid ip4
        address.

        Args:
            ipaddress: IP address to ban
            reason: Optional text reason
            source: Source (author/op) of ban.
            expires: Optional expiration in time.time() format.

        Returns: String describing the operation's outcome.
        """
        return self.wrapper.proxy.banip(ipaddress, reason, source, expires)

    def pardonName(self, playername):
        """

        Args:
            playername:

        Returns: String describing the operation's outcome.

        """
        return self.wrapper.proxy.pardonname(playername)

    def pardonUUID(self, playeruuid):
        """

        Args:
            playeruuid:

        Returns: String describing the operation's outcome.

        """
        return self.wrapper.proxy.pardonuuid(playeruuid)

    def pardonIp(self, ipaddress):
        """

        Args:
            ipaddress:

        Returns:  String describing the operation's outcome.

        """
        return self.wrapper.proxy.pardonip(ipaddress)

    def isUUIDBanned(self, uuid):
        """
        Check if a uuid is banned.  Using this method also refreshes any expired bans and unbans them.

        Args:
            uuid: Check if the UUID of the user is banned

        Returns: True or False (banned or not banned)

        """
        return self.wrapper.proxy.isuuidbanned(uuid)

    def isIpBanned(self, ipaddress):
        """
        Check if a ipaddress is banned.  Using this method also refreshes any expired bans and unbans them.

        Args:
            ipaddress: Check if an ipaddress is banned

        Returns: True or False (banned or not banned)

        """
        return self.wrapper.proxy.isipbanned(ipaddress)
