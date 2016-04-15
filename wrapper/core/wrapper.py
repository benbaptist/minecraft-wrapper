# -*- coding: utf-8 -*-

import sys
import json
import signal
import hashlib
import traceback
import threading
import time
import os
import logging

import core.globals as globals

import proxy.base as proxy

from management.web import Web as web
from management.dashboard import Web as dashboard
from utils.helpers import get_args, get_argsAfter

from api.base import API

from mcuuid import MCUUID
from config import Config
from irc import IRC
from mcserver import MCServer
from scripts import Scripts
from plugins import Plugins
from commands import Commands
from events import Events
from storage import Storage
from exceptions import UnsupportedOSException, InvalidServerState

try:
    import readline
except ImportError:
    # readline does not exist for windows
    pass

try:
    import requests
    IMPORT_REQUESTS = True
except ImportError:
    IMPORT_REQUESTS = False

class Wrapper:

    def __init__(self):
        self.log = logging.getLogger('Wrapper.py')
        self.configManager = Config()
        self.configManager.loadConfig() # Load initially for storage object
        self.encoding = self.configManager.config["General"]["encoding"] # This was to allow alternate encodings
        self.server = None
        self.proxy = False
        self.halt = False
        self.update = False
        self.storage = Storage("main", encoding=self.encoding)
        self.permissions = Storage("permissions", encoding=self.encoding)
        self.usercache = Storage("usercache", encoding=self.encoding)

        self.plugins = Plugins(self)
        self.commands = Commands(self)
        self.events = Events(self)
        self.permission = {}
        self.help = {}
        # Aliases for compatibility
        self.callEvent = self.events.callEvent

        if not IMPORT_REQUESTS and self.configManager.config["Proxy"]["proxy-enabled"]:
            self.log.error("You must have the requests module installed to run in proxy mode!")
            return

    def isOnlineMode(self):
        """
        :returns: Whether the server OR (for proxy mode) wrapper is in online mode.
        This should normally 'always' render True, unless you want hackers coming on :(
        not sure what circumstances you would want a different confguration...
        """
        if self.config["Proxy"]["proxy-enabled"]:
            # if wrapper is using proxy mode (which should be set to online)
            return self.config["Proxy"]["online-mode"]
        if self.server is not None:
            if self.server.onlineMode:
                return True  # if local server is online-mode
        return False

    @staticmethod
    def formatUUID(playeruuid):
        """
        Takes player's uuid with no dashes and returns it with the dashes
        :param playeruuid: string of player uuid with no dashes (such as you might get back from Mojang)
        :return: string hex format "8-4-4-4-12"
        """
        return MCUUID(bytes=playeruuid.decode("hex")).string

    @staticmethod
    def UUIDFromName(name):
        """
        :param name: should be passed as "OfflinePlayer:<playername>" to get the correct (offline) vanilla server uuid
        :return: a MCUUID object based on the name
        """
        m = hashlib.md5()
        m.update(name)
        d = bytearray(m.digest())
        d[6] &= 0x0f
        d[6] |= 0x30
        d[8] &= 0x3f
        d[8] |= 0x80
        return MCUUID(bytes=str(d))

    def lookupUUIDbyUsername(self, username):
        """
        Lookup users name and update local wrapper usercache. Will check Mojang once per day only.
        :param username:  username as string
        :returns: returns the MCUUID object from the given name. Updates the wrapper usercache.json
                Yields False if failed.
        """
        # frequency = 86400  # check once per day at most for existing players
        for useruuid in self.usercache: # try wrapper cache first
            if username in (self.usercache.key(useruuid)["name"], self.usercache.key(useruuid)["localname"]):
                return MCUUID(useruuid)
        # try mojang  (a new player, likely)
        r = requests.get("https://api.mojang.com/users/profiles/minecraft/%s" % username)
        if r.status_code == 200:
            useruuid = self.formatUUID(r.json()["id"])
            correctcapname = r.json()["name"]
            if username != correctcapname:
                self.log.warn("%s's name is not correctly capitalized (offline name warning!)", correctcapname)
            nameisnow = self.lookupUsernamebyUUID(useruuid)
            if nameisnow:
                return MCUUID(useruuid)
            return False
        else:
            if "uuid-cache" not in self.proxy.storage: # try for any old proxy-data record as a last resort
                return False  # no old proxy uuid-cache exists.
            for useruuid in self.proxy.storage["uuid-cache"]:
                if self.storage["uuid-cache"][useruuid]["name"] == username:
                    return MCUUID(useruuid)
            return False  # if no old proxy record

    def lookupUsernamebyUUID(self, useruuid):
        """
        Lookup users uuid/name and update local wrapper usercache. Will check Mojang once per day only.
        :param useruuid:  UUID - as string with dashes!
        :returns: returns the name from a uuid. Updates the wrapper usercache.json
                Yields False if failed.
        """
        frequency = 86400  # check once per day at most for existing players
        names = self._pollMojangUUID(useruuid)
        numbofnames = len(names)
        if self.usercache.key(useruuid):  # if user is in the cache...
            # and was recently polled...
            if (time.time() - self.usercache.key(useruuid)["time"]) < frequency:
                return self.usercache.key(useruuid)["name"]  # dont re-poll.
            else:
                if not names or names is None:  # not a huge deal, we'll re-poll another time
                    self.usercache.key(useruuid)["time"] = time.time() - frequency + 7200  # delay 2 more hours
                    return self.usercache.key(useruuid)["name"]
        else:  # user is not in cache
            if not names or names is None or numbofnames == 0:  # mojang service failed or UUID not found
                return False
            pastnames = []
            if useruuid not in self.usercache:
                self.usercache[useruuid] = {
                    "time": time.time(),
                    "original": None,
                    "name": None,
                    "online": True,
                    "localname": None,
                    "IP": None,
                    "names": []
                }
            for i in xrange(0, numbofnames):
                if "changedToAt" not in names[i]:  # find the original name
                    self.usercache[useruuid]["original"] = names[i]["name"]
                    self.usercache[useruuid]["online"] = True
                    self.usercache[useruuid]["time"] = time.time()
                    if numbofnames == 1:  # The user has never changed their name
                        self.usercache[useruuid]["name"] = names[i]["name"]
                        if self.usercache[useruuid]["localname"] is None:
                            self.usercache[useruuid]["localname"] = names[i]["name"]
                        break
                else:
                    # Convert java milleseconds to time.time seconds
                    changetime = names[i]["changedToAt"] / 1000
                    oldname = names[i]["name"]
                    if len(pastnames) == 0:
                        pastnames.append({"name": oldname, "date": changetime})
                        continue
                    if changetime > pastnames[0]["date"]:
                        pastnames.insert(0, {"name": oldname, "date": changetime})
                    else:
                        pastnames.append({"name": oldname, "date": changetime})
            self.usercache[useruuid]["names"] = pastnames
            if numbofnames > 1:
                self.usercache[useruuid]["name"] = pastnames[0]["name"]
                if self.usercache[useruuid]["localname"] is None:
                    self.usercache[useruuid]["localname"] = pastnames[0]["name"]
            return self.usercache[useruuid]["localname"]

    def _pollMojangUUID(self, useruuid):
        """
        attempts to poll Mojang with the UUID
        :param useruuid: string uuid with dashes
        :returns:
                None - Most likely a bad UUID
                False - Mojang down or operating in limited fashion
                - otherwise, a list of names...
        """
        r = requests.get("https://api.mojang.com/user/profiles/%s/names" % useruuid.replace("-", ""))
        if r.status_code == 200:
            return r.json()
        else:
            rx = requests.get("https://status.mojang.com/check")
            if rx.status_code == 200:
                rx = rx.json()
                for i in xrange(0, len(rx)):
                    if "account.mojang.com" in rx[i]:
                        if rx[i]["account.mojang.com"] == "green":
                            self.log.error("Mojang accounts is green, but request failed - have you over-polled (large busy server) or supplied an incorrect UUID??")
                            self.log.error("uuid: %s", useruuid)
                            self.log.debug("response: \n%s", str(rx))
                            return None
                        elif rx[i]["account.mojang.com"] in ("yellow", "red"):
                            self.log.error("Mojang accounts is experiencing issues (%s).", rx[i]["account.mojang.com"])
                            return False
                        self.log.error("Mojang Status found, but corrupted or in an unexpected format (status code %s)", r.status_code)
                        return False
                    else:
                        self.log.error("Mojang Status not found - no internet connection, perhaps? (status code %s)", rx.status_code)
                        return self.usercache[useruuid]["name"]
            

    def getUsername(self, useruuid):
        """
        :param useruuid - the string representation with dashes of the uuid.
        used by commands.py in commands-playerstats and in api/minecraft.getAllPlayers
        mostly a wrapper for lookupUsernamebyUUID which also checks the offline server usercache...
        """
        if type(useruuid) not in (str, unicode):
            return False
        if self.isOnlineMode():
            name = self.lookupUsernamebyUUID(useruuid)
            if name:
                return self.usercache[useruuid]["localname"]
            return False
        else:
            # this is the server's usercache.json (not the cache in wrapper-data)
            with open("usercache.json", "r") as f:
                cache = json.loads(f.read())
            for user in cache:
                if user["uuid"] == useruuid:
                    if useruuid not in self.usercache:
                        self.usercache[useruuid] = {
                            "time": time.time(), 
                            "name": None
                        }
                    if user["name"] != self.usercache[useruuid]["name"]:
                        self.usercache[useruuid]["name"] = user["name"]
                        self.usercache[useruuid]["online"] = False
                        self.usercache[useruuid]["time"] = time.time()
                    return user["name"]

    def getUUID(self, username):
        """
        :param username - string of user's name
        :returns a MCUUID object, which means UUIDfromname and lookupUUIDbyUsername must return MCUUID obejcts
        """
        if not self.isOnlineMode():  # both server and wrapper in offline...
            return self.UUIDFromName("OfflinePlayer:%s" % username)

        # proxy mode is off / not working
        if not self.proxy:
            with open("usercache.json", "r") as f: # read offline server cache first
                cache = json.loads(f.read())
            for user in cache:
                if user["name"] == username:
                    return MCUUID(user["uuid"])
        else:
            # proxy mode is on... poll mojang and wrapper cache
            search = self.lookupUUIDbyUsername(username)
            if not search:
                self.log.warn("Server online but unable to getUUID (even by polling!) for username: %s - "
                              "returned an Offline uuid...", username)
                return self.UUIDFromName("OfflinePlayer:%s" % username)
            else:
                return search
        # if both if and else fail to deliver a uuid create offline uuid:
        return self.UUIDFromName("OfflinePlayer:%s" % username)

    def listWrapperPlugins(self):
        self.log.info("List of Wrapper.py plugins installed:")
        for plid in self.plugins:
            plugin = self.plugins[plid]
            if plugin["good"]:
                name = plugin["name"]
                summary = plugin["summary"]
                if summary is None:
                    summary = "No description available for this plugin"

                version = plugin["version"]

                self.log.info("%s v%s - %s", name, ".".join([str(_) for _ in version]), summary)
            else:
                self.log.info("%s failed to load!", plugin)

    def start(self):
        # Reload configuration each time server starts in order to detect changes
        self.configManager.loadConfig()
        self.config = self.configManager.config

        signal.signal(signal.SIGINT, self.SIGINT)
        signal.signal(signal.SIGTERM, self.SIGINT)

        self.api = API(self, "Wrapper.py")
        self.api.registerHelp("Wrapper", "Internal Wrapper.py commands ", [
            ("/wrapper [update/memory/halt]", "If no subcommand is provided, it will show the Wrapper version.", None),
            ("/plugins", "Show a list of the installed plugins", None),
            ("/permissions <groups/users/RESET>", "Command used to manage permission groups and users, add permission nodes, etc.", None),
            ("/playerstats [all]", "Show the most active players. If no subcommand is provided, it'll show the top 10 players.", None),
            ("/reload", "Reload all plugins.", None)
        ])

        self.server = MCServer(sys.argv, self.log, self.configManager.config, self)
        self.server.init()

        self.plugins.loadPlugins()

        if self.config["IRC"]["irc-enabled"]:
            self.irc = IRC(self.server, self.config, self.log, self)
            t = threading.Thread(target=self.irc.init, args=())
            t.daemon = True
            t.start()

        if self.config["Web"]["web-enabled"]:
            if web.IMPORT_SUCCESS:
                self.web = web.Web(self)
                t = threading.Thread(target=self.web.wrap, args=())
                t.daemon = True
                t.start()
            else:
                self.log.error("Web remote could not be started because you do not have the required modules installed: pkg_resources")
                self.log.error("Hint: http://stackoverflow.com/questions/7446187")

        if len(sys.argv) < 2:
            self.server.args = self.configManager.config["General"]["command"].split(" ")
        else:
            self.server.args = sys.argv[1:]

        consoleDaemon = threading.Thread(target=self.console, args=())
        consoleDaemon.daemon = True
        consoleDaemon.start()

        t = threading.Thread(target=self.timer, args=())
        t.daemon = True
        t.start()

        if self.config["General"]["shell-scripts"]:
            if os.name in ("posix", "mac"):
                self.scripts = Scripts(self)
            else:
                self.log.error("Sorry, but shell scripts only work on *NIX-based systems! If you are using a *NIX-based system, please file a bug report.")

        if self.config["Proxy"]["proxy-enabled"]:
            t = threading.Thread(target=self.startProxy, args=())
            t.daemon = True
            t.start()

        if self.config["General"]["auto-update-wrapper"]:
            t = threading.Thread(target=self.checkForUpdates, args=())
            t.daemon = True
            t.start()

        self.server.__handle_server__()

        self.plugins.disablePlugins()

    def startProxy(self):
        if proxy.IMPORT_SUCCESS:
            self.proxy = proxy.Proxy(self)
            proxyThread = threading.Thread(target=self.proxy.host, args=())
            proxyThread.daemon = True
            proxyThread.start()
        else:
            self.log.error("Proxy mode could not be started because you do not have one or more of the following modules installed: pycrypto and requests")

    def SIGINT(self, s, f):
        self.shutdown()

    def shutdown(self, status=0):
        self.halt = True
        self.server.stop(reason="Wrapper.py Shutting Down", save=False)
        time.sleep(1)
        sys.exit(status)

    def rebootWrapper(self):
        self.halt = True
        os.system(" ".join(sys.argv) + "&")

    def getBuildString(self):
        if globals.__branch__ == "dev":
            return "%s (development build #%d)" % (globals.__version__, globals.__build__)
        else:
            return "%s (stable)" % globals.__version__

    def checkForUpdates(self):
        if not IMPORT_REQUESTS:
            self.log.error("Can't automatically check for new Wrapper.py versions because you do not have the requests module installed!")
            return
        while not self.halt:
            time.sleep(3600)
            self.checkForUpdate(True)

    def checkForUpdate(self, auto):
        self.log.info("Checking for new builds...")
        update = self.checkForNewUpdate()
        if update:
            version, build, repotype = update
            if repotype == "dev":
                if auto and not self.config["General"]["auto-update-dev-build"]:
                    self.log.info("New Wrapper.py development build #%d available for download! (currently on #%d)", build, globals.__build__)
                    self.log.info("Because you are running a development build, you must manually update Wrapper.py. To update Wrapper.py manually, please type /update-wrapper.")
                else:
                    self.log.info("New Wrapper.py development build #%d available! Updating... (currently on #%d)", build, globals.__build__)
                self.performUpdate(version, build, repotype)
            else:
                self.log.info("New Wrapper.py stable %s available! Updating... (currently on %s)", \
                    ".".join([str(_) for _ in version]), globals.__version__)
                self.performUpdate(version, build, repotype)
        else:
            self.log.info("No new versions available.")


    def checkForNewUpdate(self, repotype=None):
        if repotype is None:
            repotype = globals.__branch__
        if repotype == "dev":
            r = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/build/version.json")
            if r.status_code == 200:
                data = r.json()
                if self.update:
                    if self.update > data["build"]:
                        return False
                if data["build"] > globals.__build__ and data["repotype"] == "dev":
                    return (data["version"], data["build"], data["repotype"])
                else:
                    return False
            else:
                self.log.warn("Failed to check for updates - are you connected to the internet? (Status Code %d)", r.status_code)
                
        else:
            r = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/build/version.json")
            if r.status_code == 200:
                data = r.json()
                if self.update:
                    if self.update > data["build"]:
                        return False
                if data["build"] > globals.__build__ and data["repotype"] == "stable":
                    return (data["version"], data["build"], data["repotype"])
                else:
                    return False
            else:
                self.log.warn("Failed to check for updates - are you connected to the internet? (Status Code %d)", r.status_code)
        return False

    def performUpdate(self, version, build, repotype):
        if repotype == "dev":
            repo = "development"
        else:
            repo = "master"
        wrapperHash = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/%s/build/Wrapper.py.md5" % repo)
        wrapperFile = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/%s/Wrapper.py" % repo)
        if wrapperHash.status_code == 200 and wrapperFile.status_code == 200:
            self.log.info("Verifying Wrapper.py...")
            if hashlib.md5(wrapperFile.content).hexdigest() == wrapperHash.text:
                self.log.info("Update file successfully verified. Installing...")
                with open(sys.argv[0], "w") as f:
                    f.write(wrapperFile)
                self.log.info("Wrapper.py %s (#%d) installed. Please reboot Wrapper.py.", ".".join([str(_) for _ in version]), build)
                self.update = build
                return True
            else:
                return False
        else:
            self.log.error("Failed to update due to an internal error (%d, %d)", wrapperHash.status_code, wrapperFile.status_code, exc_info=True)
            return False

    def timer(self):
        t = time.time()
        while not self.halt:
            if time.time() - t > 1:
                self.callEvent("timer.second", None)
                t = time.time()
            # self.callEvent("timer.tick", None)
            time.sleep(0.05)

    def console(self):
        while not self.halt:
            try:
                cinput = raw_input("")
            except Exception as e:
                continue

            if len(cinput) < 1:
                continue

            if cinput[0] is not "/":
                try:
                    self.server.console(cinput)
                except Exception as e:
                    break
                continue

            command = get_args(cinput[1:].split(" "), 0)

            if command == "halt":
                self.server.stop("Halting server...", save=False)
                self.halt = True
                sys.exit()
            elif command == "stop":
                self.server.stop("Stopping server...")
            elif command == "start":
                self.server.start()
            elif command == "restart":
                self.server.restart("Server restarting, be right back!")
            elif command == "reload":
                self.plugins.reloadPlugins()
                if self.server.getServerType() != "vanilla":
                    self.log.info("Note: If you meant to reload the server's plugins instead of the Wrapper's plugins, try running 'reload' without any slash OR '/raw /reload'.")
            elif command == "update-wrapper":
                self.checkForUpdate(False)
            elif command == "plugins":
                self.listWrapperPlugins()
            elif command in ("mem", "memory"):
                try:
                    self.log.info("Server Memory Usage: %d bytes", self.server.getMemoryUsage())
                except UnsupportedOSException as e:
                    self.log.error(e)
                except Exception as ex:
                    self.log.exception("Something went wrong when trying to fetch memory usage! (%s)", ex)
            elif command == "raw":
                try:
                    if len(get_argsAfter(cinput[1:].split(" "), 1)) > 0:
                        self.server.console(get_argsAfter(cinput[1:].split(" "), 1))
                    else:
                        self.log.info("Usage: /raw [command]")
                except InvalidServerState as e:
                    self.log.warn(e)
            elif command == "freeze":
                try:
                    self.server.freeze()
                except InvalidServerState as e:
                    self.log.warn(e)
                except UnsupportedOSException as ex:
                    self.log.error(ex)
                except Exception as exc:
                    self.log.exception("Something went wrong when trying to freeze the server! (%s)", exc)
            elif command == "unfreeze":
                try:
                    self.server.unfreeze()
                except InvalidServerState as e:
                    self.log.warn(e)
                except UnsupportedOSException as ex:
                    self.log.error(ex)
                except Exception as exc:
                    self.log.exception("Something went wrong when trying to unfreeze the server! (%s)", exc)
            elif command == "help":
                self.log.info("/reload - Reload Wrapper.py plugins.")
                self.log.info("/plugins - Lists Wrapper.py plugins.")
                self.log.info("/update-wrapper - Checks for new Wrapper.py updates, and will install them automatically if one is available.")
                self.log.info("/start - Start the minecraft server.")
                self.log.info("/stop - Stop the minecraft server without auto-restarting and without shutting down Wrapper.py.")
                self.log.info("/restart - Restarts the minecraft server.")
                self.log.info("/halt - Shutdown Wrapper.py completely.")
                self.log.info("/freeze - Temporarily locks the server up until /unfreeze is executed (Only works on *NIX servers).")
                self.log.info("/unfreeze - Unlocks the server from a frozen state (Only works on *NIX servers).")
                self.log.info("/mem - Get memory usage of the server (Only works on *NIX servers).")
                self.log.info("/raw [command] - Send command to the Minecraft Server. Useful for Forge commands like '/fml confirm'.")
                self.log.info("Wrapper.py Version %s", self.getBuildString())
            else:
                self.log.error("Invalid command -- %s", command)
