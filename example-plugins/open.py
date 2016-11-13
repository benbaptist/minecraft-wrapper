NAME = "Window test"
AUTHOR = "Sasszem"
ID = "com.sas.plugins.win"
VERSION = (1, 2)
SUMMARY = "This plugin opens a window with nothing!"
WEBSITE = ""
DESCRIPTION = """This plugin is just a test. Do /open ingame"""


class Window:
    def __init__(self):
        pass
# tag=NbtTag(tag_type=10, value=NbtTag(tag_type=10, value=("display": {"Name": "ASD"}}}, "damage": 0, "id": 57))


class Main:
    def __init__(self, api, log):
        self.api = api
        self.minecraft = api.minecraft
        self.log = log
        self.players = {}
        self.win = {}
        self.players = {}

    def openW(self, player, args):
        if len(args) != 0:
            player.openWindow("0", args[0], 9)
            self.win[player.name] = player.getClient().windowCounter
            inv = self.storage[args[0]]
            self.players[player.name] = inv
            for i in range(len(inv)):
                element = inv[i]
                item = element['item']
                player.getClient().send(0x2f, "byte|short|slot", (player.getClient().windowCounter, i, item))
        else:  # {tag:{display:{Name:"ASD"}}}
            player.message("Usage: /open <WNAME>")

    def onEnable(self):
        self.storage = self.api.getStorage("CommandWindow", True)
        self.api.registerCommand("open", self.openW, "s.open")
        self.api.registerEvent("player.slotClick", self.setSlot)
        self.api.registerPermission("s.open", True)
        self.api.registerCommand("addc", self.addCommand, "s.wop")
        self.api.registerCommand("addw", self.addWindow, "s.wop")
        self.api.registerCommand("remw", self.removeWindow, "s.wop")
        self.api.registerCommand("remc", self.removeCommand, "s.wop")
        self.api.registerHelp("WindowMenus", "Commans from the WindowMenus plugin",
                              [
                                  ("/open <WNAME>", "Opens the menu named WNAME", "s.open"),
                                  ("/addw <WNAME>", "Adds a new menu called WNAME", "s.wop"),
                                  ("/addc <WNAME>, <COMMAND> [ARG1 [ARG2]]",
                                   "Adds a new command to the menu named WNAME for the held item "
                                   "with the command COMMAND and args ARG1, ARG2, etc.", "s.wop"),
                                  ("/remw <WNAME>", "Removes the menu named WNAME", "s.wop"),
                                  ("/remc <WNAME>", "Removes the command with the icon of the "
                                                    "held item from the menu named WNAME")])

    def onDisable(self):
        self.storage.close()

    def setSlot(self, payload):
        # payload['player'].message(str(payload))
        if payload["wid"] == payload["player"].getClient().windowCounter:

            payload['player'].getClient().send(0x2f, "byte|short|raw", (-1, -1, "\xff\xff"))
            command = self.players[payload["player"].name]
            command = command[payload["slot"]]
            command = command["command"]
            args = self.players[payload["player"].name][payload["slot"]]["args"]
            # payload["player"].message(command)
            pay = {"player": payload["player"], "command": command, "args": args}
            self.api.callEvent("player.runCommand", pay)
        # if payload['wid']==self.win[payload['player'].name]: return False
        return True

    def addWindow(self, player, args):
        if len(args) < 1:
            player.message("USAGE: /addw <WNAME>")
        else:
            self.storage[args[0]] = []

    def addCommand(self, player, args):
        if len(args) < 2:
            player.message("USAGE: /addc <WNAME> <COMMAND> [ARG1[ ARG2]]")
            return
        a = {}
        wname, command, arguments = args[0], args[1], args[2:]
        a['command'] = command
        a['args'] = arguments
        a['item'] = player.getHeldItem()
        self.storage[wname].append(a)

    def removeWindow(self, player, args):
        if len(args) < 1:
            player.message("USAGE: /remw <WNAME>")
        else:
            self.storage[args[0]] = None

    def removeCommand(self, player, args):
        if len(args) < 2:
            player.message("USAGE: /remc <WNAME>")
            return
        w = self.storage[args[0]]
        item = player.getHeldItem()
        for i in range(len(w)):
            if w[i]["item"] == item:
                w[i] = None
        self.storage[args[0]] = w
