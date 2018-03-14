NAME = "clock"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.clock"
VERSION = (0, 1)
SUMMARY = "clock plugin"
WEBSITE = ""
DEPENDENCIES = False
DISABLED = False
DESCRIPTION = "clock plugin using getTimeofDay()"


class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log

    def onEnable(self):
        self.api.registerCommand("clock", self._clock, None)
        self.api.registerHelp(
            "Clock", "clock command", [
                ("/clock [0-2]",
                 "show minecraft time of day (0/ticks, 1/military, 2/am-pm)",
                 None)]
        )

    def onDisable(self):
        """ onDisable is a required method"""
        pass

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
