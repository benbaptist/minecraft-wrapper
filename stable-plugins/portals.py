# -*- coding: utf-8 -*-

import time
import threading

NAME = "portals"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.portals"
VERSION = (1, 0, 1)
SUMMARY = "A plugin to create portals"
WEBSITE = ""
DESCRIPTION = """
This plugin creates portals with maximum use and cooldown features.  It is
up to you to create the physical appearance of the portals.
"""


# noinspection PyPep8Naming,PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyClassicStyleClass,PyAttributeOutsideInit
class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        self.portalcount = 0

        self.data_storageobject = self.api.getStorage(
            "portals", world=False, pickle=False
        )
        self.portals = self.data_storageobject.Data

        # 'spreadplayers <x> <z> <spreadDistance> <maxRange> <respectTeams> <player ...>'  # noqa

        # You can edit this information if you just want a single speadplayers
        #  portal.
        self.default_portal = {
            "location": "-95 64 235",  # of portal.
            # keep in mind that the 1.12 minecraft reckons block locations
            #  a bit off from previous versions
            "backlocation": "0 63 10 0 0",  # unused
            "timeout": "120",  # ... between portal uses
            "maxuses": "0",  # 0 means unlimited use
            "CommCount": "2",  # number of commands (starting with command0)
            "command0": "spreadplayers 0 0 100 1000 false %s",
            "command1": "spawnpoint %s"
        }

    def onEnable(self):
        if self.portals == {}:
            self.portals["numberofportals"] = 1
            self.portals["timeout"] = 120
            self.portals["users"] = {}
            self.portals["portal0"] = self.default_portal

        self.portalcount = self.portals["numberofportals"]

        self.run = True

        t = threading.Thread(target=self._on_timer,
                              name="ontimer_portals", args=())
        t.daemon = True
        t.start()

    def onDisable(self):
        self.run = False
        self.data_storageobject.close()

    def _on_timer(self):
        while self.run:
            time.sleep(.5)
            serverplayers = self.api.minecraft.getPlayers()
            for x in serverplayers:
                currentplayer = self.api.minecraft.getPlayer(x)
                position = currentplayer.getPosition()
                currposition = "%d %d %d" % (
                    int(position[0]), int(position[1]), int(position[2]))
                for portal in range(self.portalcount):
                    portalname = "portal%d" % portal
                    if self.portals[portalname]["location"] == currposition:
                        self.doportalcommand(portal, currentplayer)

    def doportalcommand(self, portal, player):
        portalname = "portal%d" % portal
        self.data_storageobject.save()
        portaldata = self.portals[portalname]
        maxuses = int(portaldata["maxuses"])
        timeout = int(portaldata["timeout"])
        name = player.name
        uuid = player.uuid
        if uuid not in self.portals["users"]:
            self.portals["users"][uuid] = {}
        if portalname not in self.portals["users"][uuid]:
            self.portals["users"][uuid][portalname] = {}
            self.portals["users"][uuid][portalname]["use"] = "1"
            self.portals["users"][uuid][portalname]["time"] = time.time()
            self.portals["users"][uuid][portalname]["notified"] = time.time()
            player.message(
                "&6Activating portal.  &5Portal time out: &b%s&5 seconds  "
                "Portal maxuses: &b%s" % (timeout, maxuses)
            )
        # MAX USES
        if maxuses > 0 and (int(self.portals["users"][uuid][portalname]["use"]) > maxuses):  # noqa
            # notify every 5 secs while in portal
            if time.time() - 10 > int(self.portals["users"][uuid][portalname]["notified"]):  # noqa
                player.message(
                    "&5You've exceeded the max uses for this "
                    "portal and worn the portal out!"
                )
                self.portals["users"][uuid][portalname]["notified"] = time.time()  # noqa
                return
            # return without notifying player
            return
        # TIMER COOLDOWN
        if time.time() < int(self.portals["users"][uuid][portalname]["time"]):
            if time.time() - 5 > int(self.portals["users"][uuid][portalname]["notified"]):  # noqa
                remainingtime = int(
                    self.portals["users"][uuid][portalname]["time"]
                ) - time.time()
                player.message(
                    "&5You can't use this portal for another "
                    "%d seconds" % remainingtime
                )
                self.portals["users"][uuid][portalname]["notified"] = time.time()  # noqa
                return
            # return without notifying player
            return
        commandcount = int(portaldata["CommCount"])
        # Run each command
        for command in range(commandcount):
            cbtext = portaldata["command%d" % command]
            # code for keeping track of a player's previous location.
            # detect teleport commands
            if cbtext.split(" ")[0] in ("tp", "spreadplayers"):
                # Save player's /back location
                self.portals["users"][uuid]["backlocation"] = player.getPosition()  # noqa

            if "%s" in cbtext:
                self.api.minecraft.console(cbtext % name)
            else:
                self.api.minecraft.console(cbtext)
        # update cooldown and usage counts
        self.portals["users"][uuid][portalname]["use"] = str(
            int(self.portals["users"][uuid][portalname]["use"]) + 1
        )
        self.portals["users"][uuid][portalname]["time"] = time.time() + timeout
        self.data_storageobject.save()
        return
