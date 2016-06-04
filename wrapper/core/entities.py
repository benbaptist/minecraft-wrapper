# -*- coding: utf-8 -*-

import time
from utils.helpers import putjsonfile, getjsonfile

try:
    import requests
except ImportError:
    requests = False

ENTITIES = {  # partial list of entities
    48: {"Name": "Mob"},
    49: {"Name": "Monster"},
    50: {"Name": "Creeper", "size": (0.6, 1.8)},
    51: {"Name": "Skeleton", "size": (0.6, 1.8)},
    52: {"Name": "Spider", "size": (1.4, 0.9)},
    53: {"Name": "Giant Zombie", "size": (3.6, 10.8)},
    54: {"Name": "Zombie", "size": (0.6, 1.8)},
    55: {"Name": "Slime", "size": (0.6, 0.6)},
    56: {"Name": "Ghast", "size": (4, 4)},
    57: {"Name": "Zombie Pigman", "size": (0.6, 1.8)},
    58: {"Name": "Enderman", "size": (0.6, 2.9)},
    90: {"Name": "Pig"},
    91: {"Name": "Sheep"},
    92: {"Name": "Cow"},
    93: {"Name": "Chicken"},
    94: {"Name": "Squid"}
}


class Entities:
    def __init__(self):
        self.entitylist = ENTITIES
        self._getgrahamentities()
        pass

    def _getgrahamentities(self):
        frequency = 2592000  # 30 days.
        oldcopy = False
        ondisk = getjsonfile("entities", "./wrapper-data/json/")
        if ondisk:
            if (time.time() - ondisk["lastrefresh"]) > frequency:
                oldcopy = True
        if not ondisk or oldcopy is True:
            if requests:
                r = requests.get("http://minecraft-ids.grahamedgecombe.com/entities.json")
                if r.status_code == 200:
                    objects = r.json()
                    diskfile = {
                        "lastrefresh": time.time(),
                        "data": objects
                    }
                    putjsonfile(diskfile, "entities", "./wrapper-data/json/")
                    ondisk = diskfile
                else:
                    if ondisk:
                        diskfile = {
                            "lastrefresh": time.time(),
                            "data": ondisk["data"]
                        }
                        putjsonfile(diskfile, "entities", "./wrapper-data/json/")
                    else:
                        self.entitylist = ENTITIES
                        return
            else:
                self.entitylist = ENTITIES
                return
        if ondisk:
            entities = {}
            for item in ondisk["data"]:
                entities[item["type"]] = {"name": item["name"]}
            self.entitylist = entities
