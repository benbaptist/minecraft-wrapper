# -*- coding: utf-8 -*-

# pip install --user pygeoip
try:
    import pygeoip
except ImportError:
    pygeoip = False
    DEPENDENCIES = ["ImportError: could not import package pygeoip", ]

NAME = "Geode"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.geode"
VERSION = (0, 1, 0)
SUMMARY = "Lookup player's country based on ip."
WEBSITE = ""
DESCRIPTION = """
Test plugin to lookup player's country using pygeoip.
"""


# noinspection PyPep8Naming,PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyClassicStyleClass,PyAttributeOutsideInit
class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log

    def onEnable(self):
        self.api.registerEvent("player.login", self.login)
        self.data_storageobject = self.api.getStorage(
            "geode", world=False, pickle=False
        )
        self.data = self.data_storageobject.Data
        self.gi = pygeoip.GeoIP('/usr/share/GeoIP/GeoIP.dat',
                                flags=pygeoip.const.MMAP_CACHE)

    def onDisable(self):
        self.data_storageobject.close()

    def login(self, payload):
        playerObj = payload["player"]
        print(playerObj.ipaddress)
        x = self.gi.country_code_by_addr(playerObj.ipaddress)
        self.log.info(
            "%s logged on from an ip (%s) in country '%s'." % (
                playerObj.username, playerObj.ipaddress, x)
        )
