# -*- coding: utf-8 -*-
 
import time
import struct
import os
import StringIO
import datetime
import json

NAME = "SmallBrother"
ID = "com.benbaptist.plugins.smallbrother"
VERSION = (0, 1)
SUMMARY = "SmallBrother is a lightweight logging plugin for Wrapper.py!"
DESCRIPTION = SUMMARY + "\n\nThe name comes from the old Bukkit plugin, BigBrother.\n\n" \
                        "See /sb help for usage on how to use SmallBrother."
# all block actions are logged in a user's own file named after their UUID. 
# block action format: block (ushort), damage value (byte), position (long / 8 bytes)

# LIMITATIONS:
# only loggs block placements; lava and water "placement" generate console errors (logger does not check action type)
# Toggle mode is the only working mode.. and it only works for left-clicking (dig action)
# Does not seem to
#
# Plugin also uses absolute server paths and not the wrapper/server directory splits, so wrapper and server must
#  be in the same folder for this plugin
#

class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        
        self.time = 0		
        self.toggled = []

    def onEnable(self):
        self.api.registerEvent("player.dig", self.breakBlock)
        self.api.registerEvent("player.place", self.placeBlock)
        self.api.registerEvent("timer.second", self.timer)

        self.api.registerEvent("server.started", self.onServerStart)

        self.api.registerCommand("sb", self._sb)
        if self.minecraft.isServerStarted():
            self.onServerStart({})

    def onDisable(self):
        self.logger.flush()

    def onServerStart(self, payload):
        self.logger = Logger(self.minecraft.getWorldName())
        self.logger.init()

    def timer(self, payload):
        if not self.minecraft.isServerStarted():
            return
        self.time += 1
        if self.time == 60 * 2:
            self.logger.flush()
            self.time = 0

    def breakBlock(self, payload):  # print self.minecraft.getServer().world.getBlock(payload["position"])
        player = payload["player"]
        x, y, z = payload["position"]
        uuid = player.mojangUuid
        if player.name in self.toggled:
            actions = self.lookupBlock(x, y, z)
            for action in actions:
                self.displayEntry(player, action)
            if len(actions) < 1:
                player.message({"text": "Could not find any actions in the specified area.", "color": "red"})
            else:
                player.message({"text": "End of list.", "color": "red", "bold": True})
            return False
        else:
            self.logger.dig_block(uuid, x, y, z, -1, 0)

    def placeBlock(self, payload):
        if payload["item"] is None:
            return
        player = payload["player"]
        x, y, z = (0, 0, 0)
        if payload["position"]:
            x, y, z = payload["position"]

        uuid = player.mojangUuid
        if player.name in self.toggled and payload["position"]:
            actions = self.lookupBlock(x, y, z)
            for action in actions:
                self.displayEntry(player, action)
            if len(actions) < 1:
                player.message({"text": "Could not find any actions in the specified area.", "color": "red"})
            else:
                player.message({"text": "End of list.", "color": "red", "bold": True})
            return False
        else:
            if payload["item"]["id"] and payload["position"]:
                self.logger.place_block(uuid, x, y, z, payload["item"]["id"], payload["item"]["damage"])

    @staticmethod
    def localize(p):
        return ((p[0] / 2048.0) - int(p[0] / 2048.0)) * 2048, p[1], ((p[2] / 2048.0) - int(p[2] / 2048.0)) * 2048

    @staticmethod
    def deny(player):
        if player.isOp():
            return True
        else:
            player.message("&cYou are not authorized to run this command. Shoo!")
            return False

    def _sb(self, player, args):
        if not self.deny(player):
            return
        if len(args) > 0:
            subcommand = args[0]
            if subcommand == "area":
                # radius = args[1]  # squareRadius, not circular. not really a true radius.
                player.message("&cApologies, but this command has not been implemented yet.")
            elif subcommand == "toggle":
                if player.username in self.toggled:
                    self.toggled.remove(player.username)
                    player.message("&c&lSmallBrother: &r&cTurned off check mode.")
                else:
                    self.toggled.append(player.username)
                    player.message("&c&lSmallBrother: &r&bTurned on check mode. "
                                   "Left/right click on a block to check the history.")
            elif subcommand == "block":
                x, y, z = int(args[1]), int(args[2]), int(args[3])
                actions = self.lookupBlock(x, y, z)
                for action in actions:
                    self.displayEntry(player, action)
                if len(actions) < 1:
                    player.message({"text": "Could not find any actions in the specified area.", "color": "red"})
                else:
                    player.message({"text": "End of list.", "color": "red", "bold": True})
            elif subcommand == "help":
                player.message("&lSmallBrother's commands:")
                commands = {"toggle":
                            {"text": "Toggles breaking or placing blocks that check for "
                                     "events in the block that you placed or broke.", "args": ""},
                            "area":
                                {"text": "Scan the square radius around the player for events.",
                                 "args": "<squareRadius>"},
                            "block":
                                {"text": "Checks those specific coordinates for action.",
                                 "args": "<x> <y> <z>"}}

                for i in commands:
                    com = commands[i]
                    player.message("&b&l/sb %s &r&c&o%s: &r&a%s" % (i, com["args"], com["text"]))
            else:
                player.message("&c&lSmallBrother: &r&cUnknown sub-command '%s'. "
                               "Please see /sb help for a list of sub-commands." % subcommand)
        else:
            player.message("&a&lSmallBrother v1.0")
            player.message("&aFor help with SmallBrother's commands, run /sb help.")

    def displayEntry(self, player, action):
        j = []
        timestamp = datetime.datetime.fromtimestamp(int(action[1])).strftime('%Y-%m-%d %H:%M:%S')
        uuid, blocktype, payload = action[0], action[2], action[3]
        playername = self.minecraft.lookupUUID(uuid)["name"]
        if playername is None:
            player.message("Sorry, I could not locate a player with the specified UUID: %s" % str(uuid))
        j.append({"text": "[%s] " % timestamp, "color": "gray"})
        j.append({"text": "%s " % playername,
                  "color": "dark_aqua",
                  "hoverEvent": {"action": "show_text", "value": uuid}})
        if type in ("place_block", "dig_block"):
            if type == "place_block": 
                j.append({"text": "placed "})
            elif type == "dig_block": 
                j.append({"text": "broke "})
            item = json.dumps({"id": payload["block"], "Damage": 0, "Count": 1, "tag": {}}).replace('"', "")
            j.append({"text": payload["block"],
                      "color": "dark_red",
                      "hoverEvent": {"action": "show_item", "value": item}})
        player.message({"text": "", "extra": j})

    def getLoggedUUIDs(self):
        l = os.listdir("%s%s" % (self.logger.getPath(), "region"))
        a = []
        for i in l:
            if len(i) > 25:
                a.append(i)
        return a
        # return os.listdir(self.logger.getPath() + "region")

    def lookupBlock(self, x, y, z):
        actions = []
        for uuid in self.getLoggedUUIDs():
            chunk = Reader(uuid, self.logger.worldName)
            for action in chunk.load():
                timestamp, actiontype, payload = action
                if actiontype in ("place_block", "dig_block"):
                    if payload["position"] == (x, y, z):
                        actions.append([uuid, timestamp, actiontype, payload])
        return actions


class Reader:
    def __init__(self, uuid, worldname):
        self.uuid = uuid
        self.worldName = worldname
        self.actions = []

    def load(self):
        if os.path.exists(self.getPath() + "region/%s" % self.uuid):
            self.file = open(self.getPath() + "region/%s" % self.uuid, "r")
            self.parse()
        return self.actions

    def getPath(self):
        return "%s/SmallBrother/" % self.worldName

    def getPayload(self):
        length = struct.unpack("B", self.file.read(1))[0]
        payload = self.file.read(length)
        if len(payload) == 0:
            raise EOFError
        return StringIO.StringIO(payload)

    def getPacket(self):
        self.packet = self.getPayload()
        packetid = self.read_byte()
        timestamp = self.read_double()
        return packetid, timestamp

    def read_byte(self):
        return struct.unpack("b", self.packet.read(1))[0]

    def read_ubyte(self):
        return struct.unpack("B", self.packet.read(1))[0]

    def read_short(self):
        return struct.unpack("h", self.packet.read(2))[0]

    def read_ushort(self):
        return struct.unpack("H", self.packet.read(2))[0]

    def read_int(self):
        return struct.unpack("i", self.packet.read(4))[0]

    def read_double(self):
        return struct.unpack("d", self.packet.read(8))[0]

    def read_position(self):
        return self.read_int(), self.read_ubyte(), self.read_int()

    def read(self, expressions):
        data = {}
        for i in expressions.split("|"):
            name, datatype = i.split(":")
            if datatype == "byte":
                data[name] = self.read_byte()
            if datatype == "ubyte":
                data[name] = self.read_ubyte()
            if datatype == "short":
                data[name] = self.read_short()
            if datatype == "ushort":
                data[name] = self.read_ushort()
            if datatype == "double":
                data[name] = self.read_double()
            if datatype == "position":
                data[name] = self.read_position()
        return data

    def parse(self):
        while True:
            try:
                packetid, timestamp = self.getPacket()
            except:
                break
            # list format: time, type, payload
            if packetid == 0x02:
                data = self.read("position:position|block:short|damage:byte")
                self.actions.append([timestamp, "place_block", data])
            if packetid == 0x03:
                data = self.read("position:position|block:short|damage:byte")
                self.actions.append([timestamp, "dig_block", data])


class Logger:
    def __init__(self, worldname):
        self.worldName = worldname
        self.queue = {}

    def init(self):
        if not os.path.exists(self.getPath()):
            os.mkdir(self.getPath())
        if not os.path.exists(self.getPath() + "region"):
            os.mkdir(self.getPath() + "region")

    def __del__(self):
        self.flush()

    def cleanup(self):
        pass

    def getPath(self):
        return "%s/SmallBrother/" % self.worldName

    def flush(self):
        for uuid in self.queue:
            path = self.getPath() + "region/%s" % uuid
            with open(path, "a") as f:
                for packet in self.queue[uuid]:
                    f.write(packet)
        self.queue = {}

    def push(self, uuid, payload):
        if uuid not in self.queue:
            self.queue[uuid] = []
        self.queue[uuid].append(self.pack_byte(len(payload)) + payload)

    def write(self, pktid, expressions, payload):
        b = self.pack_byte(pktid)
        b += self.pack_double(time.time())
        for i, v in enumerate(expressions.split("|")):
            datatype, value = v, payload[i]
            if datatype == "byte":
                b += self.pack_byte(value)
            if datatype == "short":
                b += self.pack_short(value)
            if datatype == "ushort":
                b += self.pack_ushort(value)
            if datatype == "int":
                b += self.pack_int(value)
            if datatype == "string":
                b += self.pack_string(value)
            if datatype == "double":
                b += self.pack_double(value)
            if datatype == "bytearray":
                b += self.pack_bytearray(value)
            if datatype == "position":
                b += self.pack_position(value)
        return b

    # packets
    def place_block(self, uuid, x, y, z, blockid, damage):
        self.push(uuid, self.write(0x02, "position|short|byte", ((x, y, z), blockid, damage)))

    def dig_block(self, uuid, x, y, z, blockid, damage):
        self.push(uuid, self.write(0x03, "position|short|byte", ((x, y, z), blockid, damage)))

    def open_chest(self, x, y, z):
        return self.write(0x04, "int|int|int", (x, y, z))

    def close_chest(self, x, y, z):
        return self.write(0x05, "int|int|int", (x, y, z))

    def chest_action(self, x, y, z, action, slot, itemid, damage):
        return self.write(0x04, "position|byte|byte|short|short", ((x, y, z), action, slot, itemid, damage))

    # binary functions
    @staticmethod
    def pack_byte(b):
        return struct.pack("b", b)

    @staticmethod
    def pack_ubyte(b):
        return struct.pack("B", b)

    @staticmethod
    def pack_double(b):
        return struct.pack("d", b)

    @staticmethod
    def pack_short(b):
        return struct.pack("h", b)

    @staticmethod
    def pack_ushort(b):
        return struct.pack("H", b)

    @staticmethod
    def pack_int(b):
        return struct.pack("i", b)

    def pack_bytearray(self, b):
        return self.pack_ushort(len(b)) + b

    def pack_string(self, b):
        return self.pack_ushort(len(b.encode("utf-8"))) + b.encode("utf-8")

    def pack_position(self, b):
        return self.pack_int(b[0]) + self.pack_ubyte(b[1]) + self.pack_int(b[2])
