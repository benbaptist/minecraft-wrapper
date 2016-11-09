# -*- coding: utf-8 -*-

# py3 non-compliant at runtime

# system imports
import signal
import hashlib
import threading
import time
import os
import logging
import socket
import sys  # used to pass sys.argv to server

# small feature and helpers
from utils.helpers import format_bytes, getargs, getargsafter, readout
import core.buildinfo as core_buildinfo_version
from core.mcuuid import MCUUID
from core.config import Config
from core.exceptions import UnsupportedOSException, InvalidServerStartedError

# big ticket items
import proxy.base as proxy
from api.base import API
from core.mcserver import MCServer

from core.plugins import Plugins
from core.commands import Commands
from core.events import Events
from core.storage import Storage

# extra feature imports
import management.web as manageweb
# from management.dashboard import Web as Managedashboard  # presently unused
from core.irc import IRC
from core.scripts import Scripts

# non standard library imports
try:
    import readline
except ImportError:
    readline = False

try:
    import requests
except ImportError:
    requests = False

# javaserver constants
OFF = 0  # this is the start mode.
STARTING = 1
STARTED = 2
STOPPING = 3
FROZEN = 4


class Wrapper:

    def __init__(self):
        # setup log and config
        self.storage = False    # needs a false setting on first in case config does not load (like after changes).
        self.log = logging.getLogger('Wrapper.py')
        self.configManager = Config()
        self.configManager.loadconfig()
        self.config = self.configManager.config  # set up config

        # Read Config items
        self.wrapper_ban_system = False
        self.encoding = self.config["General"]["encoding"]  # This was to allow alternate encodings
        self.proxymode = self.config["Proxy"]["proxy-enabled"]
        self.wrapper_onlinemode = self.config["Proxy"]["online-mode"]
        self.wrapper_ban_system = self.proxymode and self.wrapper_ban_system
        self.auto_update_wrapper = self.config["General"]["auto-update-wrapper"]
        self.use_timer_tick_event = self.config["Gameplay"]["use-timer-tick-event"]

        # Storages
        self.storage = Storage("wrapper", encoding=self.encoding)
        self.permissions = Storage("permissions", encoding=self.encoding)
        self.usercache = Storage("usercache", encoding=self.encoding)

        # core functions and datasets
        self.plugins = Plugins(self)
        self.commands = Commands(self)
        self.events = Events(self)
        self.registered_permissions = {}
        self.help = {}
        self.xplayer = ConsolePlayer(self)  # future plan to expose this to api

        # init items that are set up later (or opted out of/ not set up.)
        self.javaserver = None
        self.api = None
        self.irc = None
        self.scripts = None
        self.web = None
        self.proxy = None
        self.halt = False
        self.updated = False

        # Error messages for non-standard import failures.
        if not readline:
            self.log.warning("'readline' not imported.  This is needed for proper console functioning")

        if not requests:
            if self.auto_update_wrapper:
                self.log.error("You must have the requests module installed to enable auto-updates for wrapper!")
                return
            if self.proxymode:
                self.log.error("You must have the requests module installed to run in proxy mode!")
                return

    def __del__(self):
        if self.storage:  # prevent error message on very first wrapper starts when wrapper exits after creating
            # new wrapper.properties file.
            self.storage.close()
            self.permissions.close()
            self.usercache.close()

    def start(self):
        """ wrapper should only start ONCE... old code made it restart over when only a server needed restarting"""
        # Configuration is loaded on __init__ each time wrapper starts in order to detect changes

        signal.signal(signal.SIGINT, self.sigint)
        signal.signal(signal.SIGTERM, self.sigint)

        self.api = API(self, "Wrapper.py")
        self._registerwrappershelp()

        # This is not the actual server... the MCServer class is a console wherein the server is started
        self.javaserver = MCServer(self)
        self.javaserver.init()

        self.plugins.loadplugins()

        if self.config["IRC"]["irc-enabled"]:  # this should be a plugin
            self.irc = IRC(self.javaserver, self.log, self)
            t = threading.Thread(target=self.irc.init, args=())
            t.daemon = True
            t.start()

        if self.config["Web"]["web-enabled"]:  # this should be a plugin
            if manageweb.pkg_resources and manageweb.requests:
                self.web = manageweb.Web(self)
                t = threading.Thread(target=self.web.wrap, args=())
                t.daemon = True
                t.start()
            else:
                self.log.error("Web remote could not be started because you do not have the required modules "
                               "installed: pkg_resources")
                self.log.error("Hint: http://stackoverflow.com/questions/7446187")

        # Console Daemon runs while not wrapper.halt (here; self.halt)
        consoledaemon = threading.Thread(target=self.parseconsoleinput, args=())
        consoledaemon.daemon = True
        consoledaemon.start()

        # Timer also runs while not wrapper.halt
        t = threading.Thread(target=self.event_timer, args=())
        t.daemon = True
        t.start()

        if self.config["General"]["shell-scripts"]:
            if os.name in ("posix", "mac"):
                self.scripts = Scripts(self)
            else:
                self.log.error("Sorry, but shell scripts only work on *NIX-based systems! If you are using a "
                               "*NIX-based system, please file a bug report.")

        if self.proxymode:
            t = threading.Thread(target=self.startproxy, args=())
            t.daemon = True
            t.start()

        if self.auto_update_wrapper:
            t = threading.Thread(target=self.auto_update_process, args=())
            t.daemon = True
            t.start()

        self.javaserver.handle_server()
        # handle_server always runs, even if the actual server is not started

        self.plugins.disableplugins()
        self.log.info("Plugins disabled")
        self.storage.close()
        self.permissions.close()
        self.usercache.close()
        self.log.info("Wrapper Storages closed and saved.")

        # wrapper execution ends here.

    def parseconsoleinput(self):
        while not self.halt:

            # Obtain a line of console input
            try:
                consoleinput = sys.stdin.readline()
            except Exception as e:
                print("[continue] variable 'consoleinput' in 'console()' did not evaluate \n%s" % e)
                continue

            # No command (perhaps just a line feed or spaces?)
            if len(consoleinput) < 1:
                continue

            # for use with runwrapperconsolecommand() command
            wholecommandline = consoleinput[0:].split(" ")
            command = getargs(wholecommandline, 0)
            allargs = wholecommandline[1:]  # this can be passed to runwrapperconsolecommand() command for args

            # Most of these are too small to use the runwrapperconsolecommand command (or work better here)
            if command in ("/halt", "halt"):
                self.javaserver.stop("Halting server...", save=False)
                self.halt = True
                sys.exit()
            elif command in ("/stop", "stop"):
                self.javaserver.stop("Stopping server...")
            elif command == "/kill":  # "kill" (with no slash) is a server command.
                self.javaserver.kill("Server killed at Console...")
            elif command in ("/start", "start"):
                self.javaserver.start()
            elif command in ("/restart", "restart"):
                self.javaserver.restart("Server restarting, be right back!")
            elif command == "/reload":  # "reload" (with no slash) may be used by bukkit servers
                self.runwrapperconsolecommand("reload", [])
            elif command in ("/update-wrapper", "update-wrapper"):
                self.checkforupdate(True)
            elif command == "/plugins":  # "plugins" command (with no slash) reserved for possible server commands
                self.listplugins()
            elif command in ("/mem", "/memory", "mem", "memory"):
                try:
                    get_bytes = self.javaserver.getmemoryusage()
                except UnsupportedOSException as e:
                    self.log.error(e)
                except Exception as ex:
                    self.log.exception("Something went wrong when trying to fetch memory usage! (%s)", ex)
                else:
                    amount, units = format_bytes(get_bytes)
                    self.log.info("Server Memory Usage: %s %s (%s bytes)" % (amount, units, get_bytes))
            elif command in ("/raw", "raw"):
                try:
                    if len(getargsafter(consoleinput[1:].split(" "), 1)) > 0:
                        self.javaserver.console(getargsafter(consoleinput[1:].split(" "), 1))
                    else:
                        self.log.info("Usage: /raw [command]")
                except InvalidServerStartedError as e:
                    self.log.warning(e)
            elif command in ("/freeze", "freeze"):
                try:
                    self.javaserver.freeze()
                except InvalidServerStartedError as e:
                    self.log.warning(e)
                except UnsupportedOSException as ex:
                    self.log.error(ex)
                except Exception as exc:
                    self.log.exception("Something went wrong when trying to freeze the server! (%s)", exc)
            elif command in ("/unfreeze", "unfreeze"):
                try:
                    self.javaserver.unfreeze()
                except InvalidServerStartedError as e:
                    self.log.warning(e)
                except UnsupportedOSException as ex:
                    self.log.error(ex)
                except Exception as exc:
                    self.log.exception("Something went wrong when trying to unfreeze the server! (%s)", exc)
            elif command == "/version":
                readout("/version", self.getbuildstring())

            # Ban commands MUST over-ride the server version in proxy mode; otherwise, the server will re-write
            #       Its version from memory, undoing wrapper's changes to the disk file version.
            elif self.proxymode and command in ("/ban", "ban"):
                self.runwrapperconsolecommand("ban", allargs)

            elif self.proxymode and command in ("/ban-ip", "ban-ip"):
                self.runwrapperconsolecommand("ban-ip", allargs)

            elif self.proxymode and command in ("/pardon-ip", "pardon-ip"):
                self.runwrapperconsolecommand("pardon-ip", allargs)

            elif self.proxymode and command in ("/pardon", "pardon"):
                self.runwrapperconsolecommand("pardon", allargs)

            elif command in ("/perm", "/perms", "/super", "/permissions", "perm", "perms", "super", "permissions"):
                self.runwrapperconsolecommand("perms", allargs)

            elif command in ("/playerstats", "/stats", "playerstats", "stats"):
                self.runwrapperconsolecommand("playerstats", allargs)

            elif command in ("/ent", "/entity", "/entities", "ent", "entity", "entities"):
                if self.proxymode:
                    self.runwrapperconsolecommand("ent", allargs)
                else:
                    readout("ERROR - ", "Entity tracking requires proxy mode. "
                                        "(proxy mode is not on).", separator="", pad=10)
            elif command.lower() in ("/config", "/con", "/prop", "/property", "/properties"):
                self.runwrapperconsolecommand("config", allargs)

            # TODO Add more commands below here, below the original items:
            # TODO __________________

            # more commands here...

            # TODO __________________
            # TODO add more commands above here, above the help-related items:

            elif command == "help":
                readout("/help", "Get wrapper.py help.", separator=" (with a slash) - ")
                self.javaserver.console(consoleinput)
            elif command == "/help":
                # This is the console help commands.  Below this in _registerwrappershelp is the in-game help
                readout("", "Get Minecraft help.", separator="help (no slash) - ", pad=0)
                readout("/reload", "Reload Wrapper.py plugins.")
                readout("/plugins", "Lists Wrapper.py plugins.")
                readout("/update-wrapper", "Checks for new Wrapper.py updates, and will install\n"
                                           "                  them automatically if one is available.")
                readout("/stop", "Stop the minecraft server without auto-restarting and without\n"
                                 "                  shuttingdown Wrapper.py.")
                readout("/start", "Start the minecraft server.")
                readout("/restart", "Restarts the minecraft server.")
                readout("/halt", "Shutdown Wrapper.py completely.")
                readout("/kill", "Force kill the server without saving.")
                readout("/freeze", "Temporarily locks the server up until /unfreeze is executed\n"
                                   "                  (Only works on *NIX servers).")
                readout("/unfreeze", "Unlocks a frozen state server (Only works on *NIX servers).")
                readout("/mem", "Get memory usage of the server (Only works on *NIX servers).")
                readout("/raw [command]", "Send command to the Minecraft Server. Useful for Forge\n"
                                          "                  commands like '/fml confirm'.")
                readout("/config (/properties)", "Change wrapper.properties (type /config help for more..)")
                readout("/version", self.getbuildstring())
                readout("/entity", "Work with entities (run /entity for more...)")
                readout("/bans", "Display the ban help page.")
            elif command == "/bans":
                # ban commands help.
                if self.proxymode:
                    readout("", "Bans - To use the server's versions, do not type a slash.", separator="", pad=5)
                    readout("", "", separator="-----1.7.6 and later ban commands-----", pad=10)
                    readout("/ban", " - Ban a player. Specifying h:<hours> or d:<days> creates a temp ban.",
                            separator="<name> [reason..] [d:<days>/h:<hours>] ", pad=12)
                    readout("/ban-ip", " - Ban an IP address. Reason and days (d:) are optional.",
                            separator="<ip> [<reason..> <d:<number of days>] ", pad=12)
                    readout("/pardon", " - pardon a player. Default is byuuidonly.  To unban a"
                                       "specific name (without checking uuid), use `pardon <player> False`",
                            separator="<player> [byuuidonly(true/false)]", pad=12)
                    readout("/pardon-ip", " - Pardon an IP address.",
                            separator="<address> ", pad=12)
                    readout("/banlist", " - search and display the banlist (warning - displays on single page!)",
                            separator="[players|ips] [searchtext] ", pad=12)
                else:
                    readout("ERROR - ", "Wrapper proxy-mode bans are not enabled "
                                        "(proxy mode is not on).", separator="", pad=10)

            else:
                try:
                    self.javaserver.console(consoleinput)
                except Exception as e:
                    print("[BREAK] Console input exception (nothing passed to server) \n%s" % e)
                    break
                continue

    def _registerwrappershelp(self):
        # All commands listed herein are accessible in-game
        # Also require player.isOp()
        self.api.registerHelp(
            "Wrapper", "Internal Wrapper.py commands ",
            [
                ("/wrapper [update/memory/halt]",
                 "If no subcommand is provided, it will show the Wrapper version.", None),
                ("/playerstats [all]",
                 "Show the most active players. If no subcommand is provided, it'll show the top 10 players.",
                 None),
                ("/plugins",
                 "Show a list of the installed plugins", None),
                ("/reload", "Reload all plugins.", None),
                ("/permissions <groups/users/RESET>",
                 "Command used to manage permission groups and users, add permission nodes, etc.",
                 None),
                ("/entity <count/kill> [eid] [count]", "/entity help/? for more help.. ", None),
                ("/config", "Change wrapper.properties (type /config help for more..)", None),

                # Minimum server version for commands to appear is 1.7.6 (registers perm later in serverconnection.py)
                # These won't appear if proxy mode is not on (since serverconnection is part of proxy).
                ("/ban <name> [reason..] [d:<days>/h:<hours>]",
                 "Ban a player. Specifying h:<hours> or d:<days> creates a temp ban.", "mc1.7.6"),
                ("/ban-ip <ip> [<reason..> <d:<number of days>]",
                 "- Ban an IP address. Reason and days (d:) are optional.", "mc1.7.6"),
                ("/pardon <player> [False]",
                 " - pardon a player. Default is byuuidonly.  To unban a specific "
                 "name (without checking uuid), use `pardon <player> False`", "mc1.7.6"),
                ("/pardon-ip <address>", "Pardon an IP address.", "mc1.7.6"),
                ("/banlist [players|ips] [searchtext]",
                 "search and display the banlist (warning - displays on single page!)", "mc1.7.6")
            ])

    def runwrapperconsolecommand(self, wrappercommand, argslist):
        xpayload = {'player': self.xplayer, 'command': wrappercommand, 'args': argslist}
        self.commands.playercommand(xpayload)

    def isonlinemode(self):
        """
        :returns: Whether the server OR (for proxy mode) wrapper is in online mode.
        This should normally 'always' render True, unless you want hackers coming on :(
        not sure what circumstances you would want a different confguration...
        """
        if self.proxymode:
            # if wrapper is using proxy mode (which should be set to online)
            return self.config["Proxy"]["online-mode"]
        if self.javaserver is not None:
            if self.javaserver.onlineMode:
                return True  # if local server is online-mode
        return False

    @staticmethod
    def isipv4address(addr):
        try:
            socket.inet_aton(addr)  # Attempts to convert to an IPv4 address
        except socket.error:  # If it fails, the ip is not in a valid format
            return False
        return True

    @staticmethod
    def formatuuid(playeruuid):
        """
        Takes player's uuid with no dashes and returns it with the dashes
        :param playeruuid: string of player uuid with no dashes (such as you might get back from Mojang)
        :return: string hex format "8-4-4-4-12"
        """
        return MCUUID(bytes=playeruuid.decode("hex")).string

    @staticmethod
    def getuuidfromname(name):
        """
        Get the offline vanilla server UUID

        :param name: The playername  (gets hashed as "OfflinePlayer:<playername>")
        :return: a MCUUID object based on the name
        """
        playername = "OfflinePlayer:%s" % name
        m = hashlib.md5()
        m.update(playername)
        d = bytearray(m.digest())
        d[6] &= 0x0f
        d[6] |= 0x30
        d[8] &= 0x3f
        d[8] |= 0x80
        return MCUUID(bytes=str(d))

    def getuuidbyusername(self, username, forcepoll=False):
        """
        Lookup user's UUID using the username. Primarily searches the wrapper usercache.  If record is
        older than 30 days (or cannot be found in the cache), it will poll Mojang and also attempt a full
        update of the cache using getusernamebyuuid as well.

        :param username:  username as string
        :param forcepoll:  force polling even if record has been cached in past 30 days
        :returns: returns the online/Mojang MCUUID object from the given name. Updates the wrapper usercache.json
                Yields False if failed.
        """
        frequency = 2592000  # 30 days.
        if forcepoll:
            frequency = 3600  # do not allow more than hourly
        user_uuid_matched = None
        for useruuid in self.usercache:  # try wrapper cache first
            if username == self.usercache[useruuid]["localname"]:
                # This search need only be done by 'localname', which is always populated and is always
                # the same as the 'name', unless a localname has been assigned on the server (such as
                # when "falling back' on an old name).'''
                if (time.time() - self.usercache[useruuid]["time"]) < frequency:
                    return MCUUID(useruuid)
                # if over the time frequency, it needs to be updated by using actual last polled name.
                username = self.usercache[useruuid]["name"]
                user_uuid_matched = useruuid  # cache for later in case multiple name changes require a uuid lookup.

        # try mojang  (a new player or player changed names.)
        # requests seems to =have a builtin json() method
        r = requests.get("https://api.mojang.com/users/profiles/minecraft/%s" % username)
        if r.status_code == 200:
            useruuid = self.formatuuid(r.json()["id"])  # returns a string uuid with dashes
            correctcapname = r.json()["name"]
            if username != correctcapname:  # this code may not be needed if problems with /perms are corrected.
                self.log.warning("%s's name is not correctly capitalized (offline name warning!)", correctcapname)
            # This should only run subject to the above frequency (hence use of forcepoll=True)
            nameisnow = self.getusernamebyuuid(useruuid, forcepoll=True)
            if nameisnow:
                return MCUUID(useruuid)
            return False
        elif r.status_code == 204:  # try last matching UUID instead.  This will populate current name back in 'name'
            if user_uuid_matched:
                nameisnow = self.getusernamebyuuid(user_uuid_matched, forcepoll=True)
                if nameisnow:
                    return MCUUID(user_uuid_matched)
                return False
        else:
            return False  # No other options but to fail request

    def getusernamebyuuid(self, useruuid, forcepoll=False):
        """
        Returns the username from the specified UUID.
        If the player has never logged in before and isn't in the user cache, it will poll Mojang's API.
        Polling is restricted to once per day.
        Updates will be made to the wrapper usercache.json when this function is executed.

        :param useruuid:  string UUID
        :param forcepoll:  force polling even if record has been cached in past 30 days.

        :returns: returns the username from the specified uuid, else returns False if failed.
        """
        frequency = 2592000  # if called directly, can update cache daily (refresh names list, etc)
        if forcepoll:
            frequency = 600  # 10 minute limit

        theirname = None
        if useruuid in self.usercache:  # if user is in the cache...
            theirname = self.usercache[useruuid]["localname"]
            if int((time.time() - self.usercache[useruuid]["time"])) < frequency:
                return theirname  # dont re-poll if same time frame (daily = 86400).
        # continue on and poll... because user is not in cache or is old record that needs re-polled
        # else:  # user is not in cache
        names = self._pollmojanguuid(useruuid)
        numbofnames = 0
        if names is not False:  # service returned data
            numbofnames = len(names)

        if numbofnames == 0:
            if theirname is not None:
                self.usercache[useruuid]["time"] = time.time() - frequency + 7200  # may try again in 2 hours
                return theirname
            return False  # total FAIL

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

        for nameitem in names:
            if "changedToAt" not in nameitem:  # find the original name
                self.usercache[useruuid]["original"] = nameitem["name"]
                self.usercache[useruuid]["online"] = True
                self.usercache[useruuid]["time"] = time.time()
                if numbofnames == 1:  # The user has never changed their name
                    self.usercache[useruuid]["name"] = nameitem["name"]
                    if self.usercache[useruuid]["localname"] is None:
                        self.usercache[useruuid]["localname"] = nameitem["name"]
                    break
            else:
                # Convert java milleseconds to time.time seconds
                changetime = nameitem["changedToAt"] / 1000
                oldname = nameitem["name"]
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

    def _pollmojanguuid(self, useruuid):
        """
        attempts to poll Mojang with the UUID
        :param useruuid: string uuid with dashes
        :returns:
                False - could not resolve the uuid
                - otherwise, a list of names...
        """

        r = requests.get("https://api.mojang.com/user/profiles/%s/names" % useruuid.replace("-", ""))
        if r.status_code == 200:
            return r.json()
        if r.status_code == 204:
            return False
        else:
            rx = requests.get("https://status.mojang.com/check")
            if rx.status_code == 200:
                rx = rx.json()
                for entry in rx:
                    if "account.mojang.com" in entry:
                        if entry["account.mojang.com"] == "green":
                            self.log.warning("Mojang accounts is green, but request failed - have you "
                                             "over-polled (large busy server) or supplied an incorrect UUID??")
                            self.log.warning("uuid: %s", useruuid)
                            self.log.warning("response: \n%s", str(rx))
                            return False
                        elif entry["account.mojang.com"] in ("yellow", "red"):
                            self.log.warning("Mojang accounts is experiencing issues (%s).",
                                             entry["account.mojang.com"])
                            return False
                        self.log.warning("Mojang Status found, but corrupted or in an unexpected format (status "
                                         "code %s)", r.status_code)
                        return False
                    else:
                        self.log.warning("Mojang Status not found - no internet connection, perhaps? "
                                         "(status code may not exist)")
                        try:
                            return self.usercache[useruuid]["name"]
                        except TypeError:
                            return False

    def listplugins(self):
        readout("", "List of Wrapper.py plugins installed:", separator="", pad=4)
        for plid in self.plugins:
            plugin = self.plugins[plid]
            if plugin["good"]:
                name = plugin["name"]
                summary = plugin["summary"]
                if summary is None:
                    summary = "No description available for this plugin"

                version = plugin["version"]
                readout(name, summary, separator=(" - v%s - " % ".".join([str(_) for _ in version])))
                # self.log.info("%s v%s - %s", name, ".".join([str(_) for _ in version]), summary)
            else:
                readout("failed to load plugin", plugin, " - ", pad=25)

    def startproxy(self):
        self.proxy = proxy.Proxy(self)
        if proxy.requests:  # requests will be set to False if requests or any crptography is missing.
            proxythread = threading.Thread(target=self.proxy.host, args=())
            proxythread.daemon = True
            proxythread.start()
        else:
            self.proxymode = False
            self.configManager.config["Proxy"]["proxy-enabled"] = False
            self.configManager.save()
            self.config = self.configManager.config
            self.log.error("Proxy mode is disabled because you do not have one or more of the following "
                           "modules installed: pycrypto and requests")

    def sigint(*args):  # doing this allows the calling function to pass extra args without defining/using them here
        self = args[0]  # .. as we are only interested in the self component
        self.shutdown()

    def shutdown(self, status=0):
        self.storage.close()
        self.permissions.close()
        self.usercache.close()
        self.halt = True
        self.javaserver.stop(reason="Wrapper.py Shutting Down", save=False)
        time.sleep(1)
        sys.exit(status)

    def reboot(self):
        self.halt = True
        os.system(" ".join(sys.argv) + "&")

    @staticmethod
    def getbuildstring():
        if core_buildinfo_version.__branch__ == "dev":
            return "%s (development build #%d)" % (core_buildinfo_version.__version__, core_buildinfo_version.__build__)
        elif core_buildinfo_version.__branch__ == "stable":
            return "%s (stable)" % core_buildinfo_version.__build__
        else:
            return "Version: %s (%s build #%d)" % (core_buildinfo_version.__version__,
                                                   core_buildinfo_version.__branch__,
                                                   core_buildinfo_version.__build__)

    def auto_update_process(self):
        while not self.halt:
            time.sleep(3600)
            if self.updated:
                self.log.info("An update for wrapper has been loaded, Please restart wrapper.")
            else:
                self.checkforupdate()

    def checkforupdate(self, update_now=False):
        """ checks for update """
        self.log.info("Checking for new builds...")
        update = self.get_wrapper_update_info()
        if update:
            version, build, repotype, reponame = update
            self.log.info("New Wrapper.py %s build #%d is available! (current build is #%d)",
                          repotype, build, core_buildinfo_version.__build__)
            if self.auto_update_wrapper or update_now:
                self.log.info("Updating...")
                self.performupdate(version, build, reponame)
            else:
                self.log.info("Because you have 'auto-update-wrapper' set to False, you must manually update "
                              "Wrapper.py. To update Wrapper.py manually, please type /update-wrapper.")
        else:
            self.log.info("No new versions available.")

    def get_wrapper_update_info(self, repotype=None):
        """get the applicable branch wrapper update"""
        # read the installed branch info
        if repotype is None:
            repotype = core_buildinfo_version.__branch__
        branch_key = "%s-branch" % repotype
        r = requests.get(self.config["General"][branch_key])
        if r.status_code == 200:
            data = r.json()
            if data("__build__") > core_buildinfo_version.__build__:
                if repotype == "dev":
                    reponame = "development"
                elif repotype == "stable":
                    reponame = "master"
                else:
                    reponame = data["__branch__"]
                return data["__version__"], data["__build__"], data["__branch__", reponame]

        else:
            self.log.warning("Failed to check for updates - are you connected to the internet? "
                             "(Status Code %d)", r.status_code)
            return False

    def performupdate(self, version, build, reponame):
        """
        Perform update; returns True if update succeeds.  User must still restart wrapper manually.

        :param version: first argument from get_wrapper_update_info()
        :param build: second argument from get_wrapper_update_info()
        :param reponame: 4th argument from get_wrapper_update_info() - not the '__branch__'!
        :return: True if update succeeds
        """
        repo = reponame
        wrapperhash = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/%s/build"
                                   "/Wrapper.py.md5" % repo)
        wrapperfile = requests.get("https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/%s/Wrapper.py"
                                   % repo)
        if wrapperhash.status_code == 200 and wrapperfile.status_code == 200:
            self.log.info("Verifying Wrapper.py...")
            if hashlib.md5(wrapperfile.content).hexdigest() == wrapperhash.text:
                self.log.info("Update file successfully verified. Installing...")
                with open(sys.argv[0], "w") as f:
                    # requests object is the binary/Wrapper.py file.
                    # noinspection PyTypeChecker
                    f.write(wrapperfile)
                self.log.info("Wrapper.py %s (#%d) installed. Please reboot Wrapper.py.",
                              ".".join([str(_) for _ in version]), build)
                self.updated = True
                return True
            else:
                return False
        else:
            self.log.error("Failed to update due to an internal error (%d, %d)", wrapperhash.status_code,
                           wrapperfile.status_code, exc_info=True)
            return False

    def event_timer(self):
        t = time.time()
        while not self.halt:
            if time.time() - t > 1:
                self.events.callevent("timer.second", None)
                t = time.time()
            time.sleep(0.05)
            if self.use_timer_tick_event:
                self.events.callevent("timer.tick", None)  # don't really advise the use of this timer


# - due to being refrerenced by the external wrapper API that is camelCase
# noinspection PyUnresolvedReferences,PyPep8Naming,PyBroadException
class ConsolePlayer:
    """
    This class minimally represents the console as a player so that the console can use wrapper/plugin commands.
    """

    def __init__(self, wrapper):
        self.username = "*Console*"
        self.loggedIn = time.time()
        self.wrapper = wrapper
        self.permissions = wrapper.permissions
        self.log = wrapper.log
        self.abort = False

        self.mojangUuid = "00000000-0000-0000-0000-000000000000"
        self.clientUuid = self.mojangUuid
        self.offlineUuid = "00000000-0000-0000-0000-000000000000"
        self.serverUuid = self.offlineUuid

        self.ipaddress = "127.0.0.1"

        self.client = None
        self.clientboundPackets = None
        self.serverboundPackets = None

        self.field_of_view = float(1)
        self.godmode = 0x00
        self.creative = 0x00
        self.fly_speed = float(1)

        # these map minecraft color codes to "approximate" ANSI terminal color used by our color formatter.
        self.message_number_coders = {'0': 'black',
                                      '1': 'blue',
                                      '2': 'green',
                                      '3': 'cyan',
                                      '4': 'red',
                                      '5': 'magenta',
                                      '6': 'yellow',
                                      '7': 'white',
                                      '8': 'black',
                                      '9': 'blue',
                                      'a': 'green',
                                      'b': 'cyan',
                                      'c': 'red',
                                      'd': 'magenta',
                                      'e': 'yellow',
                                      'f': 'white'
                                      }

        # these do the same for color names (things like 'red', 'white', 'yellow, etc, not needing conversion...
        self.messsage_color_coders = {'dark_blue': 'blue',
                                      'dark_green': 'green',
                                      'dark_aqua': 'cyan',
                                      'dark_red': 'red',
                                      'dark_purple': 'magenta',
                                      'gold': 'yellow',
                                      'gray': 'white',
                                      'dark_gray': 'black',
                                      'aqua': 'cyan',
                                      'light_purple': 'magenta'
                                      }

    @staticmethod
    def isOp():
        return 4

    @staticmethod
    def isOp_fast():
        return 4

    def message(self, message):
        displaycode, displaycolor = "5", "magenta"
        display = str(message)
        if type(message) is dict:
            jsondisplay = message
        else:
            jsondisplay = False
        if display[0:1] == "&":  # format "&c" type color (roughly) to console formatters color
            displaycode = display[1:1]
            display = display[2:]
        if displaycode in self.message_number_coders:
            displaycolor = self.message_number_coders[displaycode]
        if jsondisplay:  # or use json formatting, if available
            if "text" in jsondisplay:
                display = jsondisplay["text"]
            if "color" in jsondisplay:
                displaycolor = jsondisplay["color"]
                if displaycolor in self.messsage_color_coders:
                    displaycolor = self.messsage_color_coders[displaycolor]
        readout(display, "", "", 15, displaycolor)

    @staticmethod
    def hasPermission(*args):
        if args:
            return True
