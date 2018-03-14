# coding=utf-8

# this line is needed to access constants for packet sending/parsing.
from proxy.utils.constants import *

NAME = "Window test"
AUTHOR = "Sasszem"
ID = "com.sas.plugins.win"
VERSION = (1, 2)
SUMMARY = "This plugin opens a window with nothing!"
WEBSITE = ""
DESCRIPTION = """This plugin is just a test. Do /open ingame. 
Updated by SurestTexas to use current Wrapper API, but...
This plugin is untested.

Although probably not working, this plugin does demonstrate
how to send client packets.
"""


class Window:
    def __init__(self):
        pass
        '''  Sample data, I suppose... 
        tag=NbtTag(
            tag_type=10, value=NbtTag(
                tag_type=10, value=(
                    {"display": {"Name": "ASD", "damage": 0, "id": 57}}
                )
            )
        )
        '''


# noinspection PyPep8Naming
class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        self.players = {}
        self.win = {}
        self.players = {}
        self.storage = None

    def onEnable(self):
        # create storage
        self.storage = self.api.getStorage("CommandWindow", True)

        # register commands
        self.api.registerCommand("open", self.openW, "s.open")
        self.api.registerEvent("player.slotClick", self.setSlot)
        self.api.registerPermission("s.open", True)
        self.api.registerCommand("addc", self.addCommand, "s.wop")
        self.api.registerCommand("addw", self.addWindow, "s.wop")
        self.api.registerCommand("remw", self.removeWindow, "s.wop")
        self.api.registerCommand("remc", self.removeCommand, "s.wop")

        # register help
        self.api.registerHelp(
            "WindowMenus", "Commands from the WindowMenus plugin",
            [
                ("/open <WNAME>", "Opens the menu named WNAME", "s.open"),
                ("/addw <WNAME>", "Adds a new menu called WNAME", "s.wop"),
                ("/addc <WNAME>, <COMMAND> [ARG1 [ARG2]]",
                 "Adds a new command to the menu named WNAME for the held "
                 "item with the command COMMAND and args ARG1, ARG2, etc.",
                 "s.wop"),
                ("/remw <WNAME>", "Removes the menu named WNAME", "s.wop"),
                ("/remc <WNAME>", "Removes the command with the icon of the "
                                  "held item from the menu named WNAME")
            ]
        )

    # required onDisable with close/save of storage.
    def onDisable(self):
        self.storage.close()

    def openW(self, player, args):
        # This gets the client-bound packet set from the player object.
        pkt = player.cbpkt
        if len(args) != 0:
            player.openWindow("0", args[0], 9)
            self.win[player.name] = player.client.windowCounter
            inv = self.storage[args[0]]
            self.players[player.name] = inv
            for i in range(len(inv)):
                element = inv[i]
                item = element['item']
                # player.client is the modern way to access the client...
                player.client.packet.sendpkt(
                    pkt.SET_SLOT[PKT],
                    [BYTE, SHORT, SLOT],
                    (player.client.windowCounter, i, item)
                )

        else:  # {tag:{display:{Name:"ASD"}}}
            player.message("Usage: /open <WNAME>")

    def setSlot(self, payload):
        # payload['player'].message(str(payload))

        # This gets server packet set using api.minecraft (player not avail).
        pkt = self.api.minecraft.getServerPackets()
        # Accessing the client using getClient() is deprecated and will
        #  be removed by wrapper 1.5.
        if payload["wid"] == payload["player"].getClient().windowCounter:

            payload['player'].getClient().packet.sendpkt(
                pkt.SET_SLOT[PKT],
                [BYTE, SHORT, RAW],
                (-1, -1, "\xff\xff")
            )
            command = self.players[payload["player"].name]
            command = command[payload["slot"]]
            command = command["command"]
            args = self.players[payload["player"].name][payload["slot"]]["args"]
            # payload["player"].message(command)
            payload["player"].sendCommand(command, args)
        # if payload['wid']==self.win[payload['player'].name]: return False
        return True

    def addWindow(self, player, args):
        if len(args) < 1:
            player.message("USAGE: /addw <WNAME>")
        else:
            self.storage.Data[args[0]] = []

    def addCommand(self, player, args):
        if len(args) < 2:
            player.message("USAGE: /addc <WNAME> <COMMAND> [ARG1[ ARG2]]")
            return
        a = {}
        wname, command, arguments = args[0], args[1], args[2:]
        a['command'] = command
        a['args'] = arguments
        a['item'] = player.getHeldItem()
        self.storage.Data[wname].append(a)

    def removeWindow(self, player, args):
        if len(args) < 1:
            player.message("USAGE: /remw <WNAME>")
        else:
            self.storage.Data[args[0]] = None

    def removeCommand(self, player, args):
        if len(args) < 2:
            player.message("USAGE: /remc <WNAME>")
            return
        w = self.storage.Data[args[0]]
        item = player.getHeldItem()
        for i in range(len(w)):
            if w[i]["item"] == item:
                w[i] = None
        self.storage.Data[args[0]] = w
