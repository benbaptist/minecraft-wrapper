NAME = "Bookmarks"
AUTHOR = "Cougar"
ID = "net.version6.minecraft.plugins.bookmarks"
SUMMARY = "Bookmark commands"
DESCRIPTION = """Bookmarks plugin.
Permissions:
bookmarks - use bookmark commands"""
WEBSITE = ""
VERSION = (0, 1)


class Main:
        def __init__(self, api, log):
                self.api = api
                self.minecraft = api.minecraft
                self.log = log

        def onEnable(self):
                self.data = self.api.getStorage("bookmarks", True)

                self.api.registerHelp("Bookmarks", "Commands from the Bookmarks plugin", [
                        ("/bmset <name>", "Save current position as bookmark", "bookmarks"),
                        ("/bmgo <name>", "Teleports you to your bookmark", "bookmarks"),
                        ("/bmdel <name>", "Delete your existing bookmark", "bookmarks"),
                        ("/bmlist", "List bookmark names", "bookmarks"),
                ])

                self.api.registerCommand("bmset", self.bookmarkset)
                self.api.registerCommand("bmgo", self.bookmarkgo)
                self.api.registerCommand("bmdel", self.bookmarkdel)
                self.api.registerCommand("bmlist", self.bookmarklist)

        def onDisable(self):
                self.data.save()

        def _isallowed(self, cmd, player, args):
                """ Essential tests before accepting command """
                if len(args) != 1:
                        player.message({"text": "Use ", "color": "gray", "extra":[
                                {"text": "/%s" % cmd, "color": "gold", "clickEvent": {"action": "suggest_command", "value": "/"+cmd}},
                                {"text": " <name>", "color": "gold", "italic": True}
                        ]})
                        return False
                if not player.getDimension() == 0:
                        player.message("&cSorry, but you can't do this from the Nether or End.")
                        return False
                if not player.isOp() and not player.getGamemode() == 0:
                        player.message("&cSorry, but you can do this only in Surival gamemode.")
                        return False
                bmname = args[0]
                if player.username not in self.data:
                        if cmd in ["bmgo", "bmdel"]:
                                player.message({"text": "You haven't used bookmarks yet.\n", "color": "red", "extra":[
                                        {"text": " Use ", "color": "gray"},
                                        {"text": "/bmset", "color": "gold", "clickEvent": {"action": "suggest_command", "value": "/bmset"}},
                                        {"text": " <name>", "color": "gold", "italic": True}
                                ]})
                                return False
                        elif cmd in ["bmset"]:
                                self.data[player.username] = {}
                                return True
                        else:
                                return False
                else:
                        if bmname in self.data[player.username]:
                                if cmd in ["bmgo", "bmdel"]:
                                        return True
                                elif cmd in ["bmset"]:
                                        player.message({"text": "Bookmark ", "color": "red", "extra":[
                                                {"text": bmname, "color": "dark_red"},
                                                {"text": " is already saved.\n", "color": "red"},
                                                {"text": " Use ", "color": "gray"},
                                                {"text": "/bmdel %s" % bmname, "color": "gold", "clickEvent": {"action": "run_command", "value": "/bmdel %s" % bmname}},
                                                {"text": " to delete it first.", "color": "gray"},
                                        ]})
                                        return False
                                else:
                                        return False
                        else:
                                if cmd in ["bmgo", "bmdel"]:
                                        player.message({"text": "Bookmark ", "color": "red", "extra":[
                                                {"text": bmname, "color": "dark_red"},
                                                {"text": " is not set.\n", "color": "red"},
                                                {"text": " Use ", "color": "gray"},
                                                {"text": "/bmset", "color": "gold", "clickEvent": {"action": "suggest_command", "value": "/bmset"}},
                                                {"text": " <name>", "color": "gold", "italic": True}
                                        ]})
                                        return False
                                elif cmd in ["bmset"]:
                                        if len(self.data[player.username]) >= 5:
                                                player.message({"text": "Maximum number of bookmarks already in use.\n", "color": "red", "extra":[
                                                        {"text": " Remove some of them with ", "color": "gray"},
                                                        {"text": "/bmdel", "color": "gold", "clickEvent": {"action": "suggest_command", "value": "/bmdel"}},
                                                        {"text": " <name>", "color": "gold", "italic": True},
                                                        {"text": " first.\n Use ", "color": "gray"},
                                                        {"text": "/bmlist", "color": "gold", "clickEvent": {"action": "run_command", "value": "/bmlist"}},
                                                        {"text": " to see their names.", "color": "gray"},
                                                ]})
                                                return False
                                        else:
                                                return True
                                else:
                                        return False

        def bookmarkset(self, player, args):
                """ Save new bookmark """
                if not self._isallowed("bmset", player, args):
                        return
                bmname = args[0]
                self.data[player.username][bmname] = player.getPosition()
                player.message({"text": "Bookmark ", "color": "green", "extra":[
                        {"text": bmname, "color": "dark_green"},
                        {"text": " set.\n", "color": "green"},
                        {"text": " Use ", "color": "gray"},
                        {"text": "/bmgo %s" % bmname, "color": "gold", "clickEvent": {"action": "run_command", "value": "/bmgo %s" % bmname}},
                        {"text": " to return here.", "color": "gray"},
                ]})
                self.data.save()

        def bookmarkgo(self, player, args):
                """ Teleport to saved bookmark """
                if not self._isallowed("bmgo", player, args):
                        return
                bmname = args[0]
                player.message({"text": "Teleporting you to your bookmark ", "color": "green", "extra":[
                        {"text": bmname, "color": "dark_green"},
                        {"text": ".", "color": "green"},
                ]})
                self.api.minecraft.console("tp %s %d %d %d" % (player.username, self.data[player.username][bmname][0], self.data[player.username][bmname][1], self.data[player.username][bmname][2]))

        def bookmarkdel(self, player, args):
                """ Delete existing bookmark """
                if not self._isallowed("bmdel", player, args):
                        return
                bmname = args[0]
                del self.data[player.username][bmname]
                player.message({"text": "Bookmark ", "color": "green", "extra":[
                        {"text": bmname, "color": "dark_green"},
                        {"text": " deleted.", "color": "green"},
                ]})
                self.data.save()

        def bookmarklist(self, player, args):
                """ List all bookmark names """
                if len(args) != 0:
                        player.message({"text": "Use ", "color": "gray", "extra":[
                                {"text": "/bmlist", "color": "gold", "clickEvent": {"action": "run_command", "value": "/bmlist"}},
                        ]})
                        return
                if player.username not in self.data:
                        player.message({"text": "You haven't used bookmarks yet.\n", "color": "red", "extra":[
                                {"text": " Use ", "color": "gray"},
                                {"text": "/bmset", "color": "gold", "clickEvent": {"action": "suggest_command", "value": "/bmset"}},
                                {"text": " <name>", "color": "gold", "italic": True}
                        ]})
                        return
                if len(self.data[player.username]) == 0:
                        player.message({"text": "You don't have any bookmarks.\n", "color": "red", "extra":[
                                {"text": " Use ", "color": "gray"},
                                {"text": "/bmset", "color": "gold", "clickEvent": {"action": "suggest_command", "value": "/bmset"}},
                                {"text": " <name>", "color": "gold", "italic": True}
                        ]})
                        return
                bmlist = []
                for bmname in self.data[player.username].keys():
                        bmlist.append({"text": " %s" % bmname, "color": "gold", "clickEvent": {"action": "run_command", "value": "/bmgo %s" % bmname}})
                player.message({"text": "Your bookmarks are:" , "color": "green", "extra": bmlist})
