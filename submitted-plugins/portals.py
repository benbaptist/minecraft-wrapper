# -*- coding: utf-8 -*-

import time
from SurestLib import read_config

NAME = "portals"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.portals"
VERSION = (0, 2)
SUMMARY = "A plugin to create portals"
WEBSITE = ""
DESCRIPTION = """ This plugin creates portals with maximum use and cooldown features
portal plugin and individual portal configuration properties are stored in:
[minecraftfolder]/plugins/portals/
Sample 'portals.properties':
```
numberofportals = 2
timeout = 120
(blank line required)
```
Sample portal files 'portal0.properties' and 'portal1.properties'
portal0:
```
location = 3275 103 2672
backlocation = 3259 104 2669 0 0
timeout = 14400
maxuses = 5
CommCount = 2
command0 = spreadplayers -5000 2000 300 5000 false %s
command1 = gamemode 0 %s
(blank line)
```
portal1:
```
location = 3275 103 2671
backlocation = 3259 104 2669 0 0
timeout = 14400
maxuses = 5
CommCount = 2
command0 = spreadplayers 5000 5000 300 5000 false %s
command1 = gamemode 0 %s
(blank line)
```
"""


class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        self.portalcount = 0
        self.portals = {}
        self.config = {}
        # self.default_path = "%s/plugins/portals" % self.api.minecraft.serverpath  # i.e., minecraftfolder/plugins/portals
        self.default_path = "./plugins/portals"  # use wrapper apather

        self.data_storageobject = self.api.getStorage("portals", True)
        self.data = self.data_storageobject.Data

        # You can edit this information if you just want a single speadplayers portal
        # 'spreadplayers <x> <z> <spreadDistance> <maxRange> <respectTeams> <player ...>'
        self.default_config = {"numberofportals": "1",
                               "timeout": "120"  # ...between "any" portal use - "Not implemented"
                               }

        self.default_portal = {"location": "-84 64 -185",  # ...of portal; what player's position must be.
                               # keep in mind that the 1.12 minecraft reckons block locations a bit off
                               # from previous versions
                               "backlocation": "0 63 10 0 0",  # unused
                               "timeout": "120",  # ... between portal uses
                               "maxuses": "0",  # 0 means unlimited use
                               "CommCount": "1",  # number of commands that follow (starting with command0)
                               "command0": "spreadplayers 0 0 300 5000 false %s"
                               }

    def onEnable(self):

        self.config = read_config(self, self.default_path, "portals.properties", self.default_config)
        if int(self.config["numberofportals"]) > 0:
            self.portalcount = int(int(self.config["numberofportals"]))
            for portal in range(self.portalcount):
                portalname = "portal%d" % portal
                self.portals[portalname] = read_config(self, self.default_path, "portal%d.properties" % portal,
                                                       self.default_portal)
            self.api.registerEvent("timer.second", self._onSecond)
        else:
            self.log.info("No portals were loaded.")
            self.log.info("No portal timer.second event registered!")

    def onDisable(self):
        self.data_storageobject.close()

    def _onSecond(self, payload):
        serverplayers = self.api.minecraft.getPlayers()
        for x in serverplayers:
            currentplayer = self.api.minecraft.getPlayer(x)
            position = currentplayer.getPosition()
            currposition = "%d %d %d" % (int(position[0]), int(position[1]), int(position[2]))
            for portal in range(self.portalcount):
                portalname = "portal%d" % portal
                if self.portals[portalname]["location"] == currposition:
                    self.doportalcommand(portal, currentplayer)
                    return

    def doportalcommand(self, portal, player):
        portalname = "portal%d" % portal
        self.data_storageobject.save()
        portaldata = self.portals[portalname]
        maxuses = int(portaldata["maxuses"])
        timeout = int(portaldata["timeout"])
        name = str(player.username)
        uuid = str(player.mojangUuid)
        if uuid not in self.data:
            self.data[uuid] = {}
        if portalname not in self.data[uuid]:
            self.data[uuid][portalname] = {}
            self.data[uuid][portalname]["use"] = "1"
            self.data[uuid][portalname]["time"] = time.time()
            self.data[uuid][portalname]["notified"] = time.time()
            player.message("&6Activating portal.  &5Portal time out: &b%s&5 seconds  Portal maxuses: &b%s" %
                           (timeout, maxuses))
        # MAX USES
        if maxuses > 0 and (int(self.data[uuid][portalname]["use"]) > maxuses):
            if time.time() - 10 > int(self.data[uuid][portalname]["notified"]):  # notify every 5 secs while in portal
                player.message("&5You've exceeded the max uses for this portal and worn the portal out!")
                self.data[uuid][portalname]["notified"] = time.time()
                return
            return  # return without notifying player
        # TIMER COOLDOWN
        if time.time() < int(self.data[uuid][portalname]["time"]):
            if time.time() - 5 > int(self.data[uuid][portalname]["notified"]):
                remainingtime = int(self.data[uuid][portalname]["time"]) - time.time()
                player.message("&5You can't use this portal for another %d seconds" % remainingtime)
                self.data[uuid][portalname]["notified"] = time.time()
                return
            return  # return without notifying player
        commandcount = int(portaldata["CommCount"])
        # Run each command
        for command in range(commandcount):
            cbtext = portaldata["command%d" % command]
            # _sample code if you were tracking a player's previous location (for a back command)
            # if cbtext.split(" ")[0] in ("tp", "spreadplayers"):  # detect teleport commands
            #     backloc = portaldata["backlocation"].split(" ")
            #     self.globalset.backlocation(player, manualcoords=backloc)  # Save player's /back location
            if "%s" in cbtext:
                self.api.minecraft.console(cbtext % name)
            else:
                self.api.minecraft.console(cbtext)
        # update cooldown and usage counts
        self.data[uuid][portalname]["use"] = str(int(self.data[uuid][portalname]["use"]) + 1)
        self.data[uuid][portalname]["time"] = time.time() + timeout
        self.data_storageobject.save()
        return
