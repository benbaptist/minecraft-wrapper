# -*- coding: utf-8 -*-

# p2 and py3 compliant

from __future__ import unicode_literals

import json
import os

from core.nbt import NBTFile
from core.items import Blocks


# noinspection PyBroadException
class Minecraft:
    """ This class contains functions related to in-game features directly. These methods are
    located at self.api.minecraft. """

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self._encoding = wrapper.config["General"]["encoding"]
        self.blocks = Blocks

    def isServerStarted(self):
        """ Returns a boolean if the server is fully booted or not. """
        if self.getServer():
            if self.getServer().state == 2:
                return True
        return False

    def getTimeofDay(self, dttmformat=0):
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

    def getAllPlayers(self):
        """ Returns a dict containing all players ever connected to the server """
        if self.wrapper.isonlinemode():
            online = True
        else:
            online = False
        players = {}
        for uuidf in os.listdir("wrapper-data/players"):
            puuid = uuidf.rsplit(".", 1)[0]
            if puuid in ("None", "False"):
                # remove any old bad objects
                os.remove("wrapper-data/players/" + uuidf)
                continue
            username = self.wrapper.getusername(puuid)
            if type(username) != str:
                continue
            if online:
                if str(self.wrapper.getuuidfromname(username)) == puuid:
                    continue
            with open("wrapper-data/players/" + uuidf) as f:
                data = f.read()
            try:
                players[puuid] = json.loads(data, self._encoding)
            except Exception as e:
                self.log.exception("Failed to load player data '%s':\n%s", puuid, e)
                os.remove("wrapper-data/players/" + uuidf)
        return players

    def console(self, string):
        """ Run a command in the Minecraft server's console. """
        try:
            self.getServer().console(string)
        except:
            pass

    def setBlock(self, x, y, z, tilename, datavalue=0, oldblockhandling="replace", datatag=None):
        """ Sets a block at the specified coordinates with the specific details. Will fail if the
         chunk is not loaded. """
        if not datatag:
            datatag = {}
        self.console("setblock %d %d %d %s %d %s %s"
                     % (x, y, z, tilename, datavalue, oldblockhandling,
                        json.dumps(datatag, self._encoding).replace('"', "")))

    def giveStatusEffect(self, player, effect, duration=30, amplifier=30):
        """ Gives the specified status effect to the specified target. """
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

    def summonEntity(self, entity, x=0, y=0, z=0, datatag=None):
        if not datatag:  # should not use mutable default arguments like dataTag={}
            datatag = {}
        """ Summons an entity at the specified coordinates with the specified data tag. """
        self.console("summon %s %d %d %d %s" % (entity, x, y, z, json.dumps(datatag, self._encoding)))

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
        """
        if irc:
            try:
                self.wrapper.irc.msgQueue.append(message)
            except Exception:
                pass
        try:
            self.wrapper.server.broadcast(message)
        except Exception:
            pass

    def teleportAllEntities(self, entity, x, y, z):
        """ Teleports all of the specific entity type to the specified coordinates. """
        self.console("tp @e[type=%s] %d %d %d" % (entity, x, y, z))

    def getPlayerDat(self, name):
        pass

    def getPlayer(self, username=""):
        """
        Returns the player object of the specified logged-in player. Will raise an exception if
        the player is not logged in.
        """
        try:
            return self.wrapper.server.players[str(username)]
        except Exception as e:
            self.log.error("No such player %s is logged in:\n%s", username, e)

    def lookupUUID(self, uuid):  # This function is just part of the API for plugin devs/users.
        """
        Returns the username from the specified UUID.
        If the player has never logged in before and isn't in the user cache, it will poll Mojang's API.
        The function will raise an exception if the UUID is invalid.
        """
        return self.wrapper.getusernamebyuuid(uuid)

    def getPlayers(self):  # returns a list of players
        """ Returns a list of the currently connected players. """
        return self.getServer().players

    # Get world-based information
    def getLevelInfo(self, worldname=False):
        """ Return an NBT object of the world's level.dat. """
        if not worldname:
            worldname = self.wrapper.server.worldName
        if not worldname:
            raise Exception("Server Uninitiated")
        f = NBTFile("%s/level.dat" % worldname, "rb")
        return f["Data"]

    def getSpawnPoint(self):
        """ Returns the spawn point of the current world. """
        return (int(str(self.getLevelInfo()["SpawnX"])), int(str(self.getLevelInfo()["SpawnY"])),
                int(str(self.getLevelInfo()["SpawnZ"])))

    def getTime(self):
        """ Returns the time of the world in ticks. """
        return int(str(self.getLevelInfo()["Time"]))

    def getServer(self):
        """ Returns the server context. """
        return self.wrapper.server

    def getWorld(self):
        """ Returns the world context. """
        return self.getServer().world

    def getWorldName(self):
        """ Returns the world's name. """
        return self.getServer().worldName
