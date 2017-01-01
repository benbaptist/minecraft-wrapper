# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

from __future__ import print_function

# system imports
import signal
import hashlib
import threading
import time
import os
import logging
import sys  # used to pass sys.argv to server

# non standard library imports
try:
    import readline
except ImportError:
    readline = False

try:
    import requests
except ImportError:
    requests = False

# small feature and helpers
# noinspection PyProtectedMember
from api.helpers import _format_bytes, getargs, getargsafter, _readout, get_int
from utils import readchar

# core items
from core.mcserver import MCServer
from core.plugins import Plugins
from core.commands import Commands
from core.events import Events
from core.storage import Storage
from core.irc import IRC
from core.scripts import Scripts
import core.buildinfo as core_buildinfo_version
from core.mcuuid import UUIDS
from core.config import Config
from core.backups import Backups
from core.consoleuser import ConsolePlayer
from core.exceptions import UnsupportedOSException, InvalidServerStartedError

# optional API type stuff
import proxy.base as proxy
from api.base import API
import management.web as manageweb
# from management.dashboard import Web as Managedashboard  # presently unused

# javaserver state constants
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
        self.cursor = "\033[5m>\033[0m"  # hard coded cursor for non-readline mode
        self.wrapper_ban_system = False
        self.encoding = self.config["General"]["encoding"]  # This was to allow alternate encodings
        self.proxymode = self.config["Proxy"]["proxy-enabled"]
        self.wrapper_onlinemode = self.config["Proxy"]["online-mode"]
        self.wrapper_ban_system = self.proxymode and self.wrapper_ban_system
        self.auto_update_wrapper = self.config["Updates"]["auto-update-wrapper"]
        self.auto_update_branch = self.config["Updates"]["auto-update-branch"]
        self.use_timer_tick_event = self.config["Gameplay"]["use-timer-tick-event"]
        self.command_prefix = self.config["Misc"]["command-prefix"]
        self.use_readline = self.config["Misc"]["use-readline"]

        # Storages
        self.storage = Storage("wrapper", encoding=self.encoding)
        self.permissions = Storage("permissions", encoding=self.encoding)
        self.usercache = Storage("usercache", encoding=self.encoding)

        # core functions and datasets
        self.uuids = UUIDS(self)
        self.plugins = Plugins(self)
        self.commands = Commands(self)
        self.events = Events(self)
        self.registered_permissions = {}
        self.help = {}
        self.input_buff = ""
        self.last_input_line = ["/help", ]
        self.last_input_line_index = 0

        # init items that are set up later (or opted out of/ not set up.)
        self.javaserver = None
        self.api = None
        self.irc = None
        self.scripts = None
        self.web = None
        self.proxy = None
        self.backups = None
        self.halt = False
        self.updated = False
        self.xplayer = ConsolePlayer(self)  # future plan to expose this to api

        # Error messages for non-standard import failures.
        if not readline and self.use_readline:
            self.log.warning("'readline' not imported.  This is needed for proper console functioning")

        # requests is just being used in too many places to try and track its usages piece-meal.
        if not requests:
            self.log.error("You must have the requests module installed to use wrapper!")
            self._halt()

    def __del__(self):
        if self.storage:  # prevent error message on very first wrapper starts when wrapper exits after creating
            # new wrapper.properties file.
            self.storage.close()
            self.permissions.close()
            self.usercache.close()

    def start(self):
        """ wrapper should only start ONCE... old code made it restart over when only a server needed restarting"""
        # Configuration is loaded on __init__ each time wrapper starts in order to detect changes

        self.signals()

        self.backups = Backups(self)

        self.api = API(self, "Wrapper.py")
        self._registerwrappershelp()

        # This is not the actual server... the MCServer class is a console wherein the server is started
        self.javaserver = MCServer(self)
        self.javaserver.init()

        # load plugins
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
            t = threading.Thread(target=self._startproxy, args=())
            t.daemon = True
            t.start()

        if self.auto_update_wrapper:
            t = threading.Thread(target=self._auto_update_process, args=())
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

        # wrapper execution ends here.  handle_server ends when wrapper.halt is True.

    def signals(self):
        signal.signal(signal.SIGINT, self.sigint)  # CTRL-C
        signal.signal(signal.SIGTERM, self.sigint)  # (I dont think wrapper will actually be allowed to stop SIGTERM)

    def sigint(*args):
        self = args[0]  # We are only interested in the self component
        self._halt()

    def _halt(self):
        self.javaserver.stop("Halting server...")
        self.halt = True

    def shutdown(self):
        self._halt()

    def getconsoleinput(self):
        if self.use_readline:
            # Obtain a line of console input
            try:
                consoleinput = sys.stdin.readline().strip()
            except Exception as e:
                self.log.error("[continue] variable 'consoleinput' in 'console()' did not evaluate \n%s" % e)
                consoleinput = ""

        else:
            while not self.halt:
                keypress = readchar.readkey()

                if keypress == readchar.key.BACKSPACE:
                    self.input_buff = self.input_buff[:-1]
                    print("\033[0A%s         " % self.input_buff)
                    continue

                if keypress != readchar.key.CR and len(keypress) < 2:
                    self.input_buff = "%s%s" % (self.input_buff, keypress)
                    if self.input_buff[0:1] == '/':  # /wrapper commands receive special magenta coloring
                        print("%s\033[0A\033[33m%s\033[0m" % (self.cursor, self.input_buff))
                    else:
                        print("%s\033[0A%s" % (self.cursor, self.input_buff))
                    continue

                if keypress in (readchar.key.CR, readchar.key.CTRL_C):
                    break

            consoleinput = "%s" % self.input_buff
            self.input_buff = ""
            # print a line so last typed line is not covered by new output
            print("")
        return consoleinput

    def parseconsoleinput(self):
        while not self.halt:
            consoleinput = self.getconsoleinput()
            # No command (perhaps just a line feed or spaces?)
            if len(consoleinput) < 1:
                continue

            # for use with runwrapperconsolecommand() command
            wholecommandline = consoleinput[0:].split(" ")
            command = getargs(wholecommandline, 0)
            allargs = wholecommandline[1:]  # this can be passed to runwrapperconsolecommand() command for args

            # Console only commands (not accessible in-game)
            if command.lower() in ("/halt", "halt"):
                self._halt()
            elif command.lower() in ("/stop", "stop"):
                self.javaserver.stop_server_command("Stopping server...")
            elif command.lower() == "/kill":  # "kill" (with no slash) is a server command.
                self.javaserver.kill("Server killed at Console...")
            elif command.lower() in ("/start", "start"):
                self.javaserver.start()
            elif command.lower() in ("/restart", "restart"):
                self.javaserver.restart("Server restarting, be right back!")
            elif command.lower()in ("/update-wrapper", "update-wrapper"):
                self._checkforupdate(True)
            elif command.lower() == "/plugins":  # "plugins" command (with no slash) reserved for server commands
                self.listplugins()
            elif command.lower() in ("/mem", "/memory", "mem", "memory"):
                self._memory()
            elif command.lower() in ("/raw", "raw"):
                self._raw(consoleinput)
            elif command.lower() in ("/freeze", "freeze"):
                self._freeze()
            elif command.lower() in ("/unfreeze", "unfreeze"):
                self._unfreeze()
            elif command.lower() == "/version":
                _readout("/version", self.getbuildstring(), usereadline=self.use_readline)
            elif command.lower() in ("/mute", "/pause", "/cm", "/m", "/p"):
                self._mute_console(allargs)

            # Commands that share the commands.py in-game interface
            elif command.lower() == "/reload":  # "reload" (with no slash) may be used by bukkit servers
                self.runwrapperconsolecommand("reload", [])

            # proxy mode ban system
            elif self.proxymode and command == "/ban":
                self.runwrapperconsolecommand("ban", allargs)

            elif self.proxymode and command == "/ban-ip":
                self.runwrapperconsolecommand("ban-ip", allargs)

            elif self.proxymode and command == "/pardon-ip":
                self.runwrapperconsolecommand("pardon-ip", allargs)

            elif self.proxymode and command == "/pardon":
                self.runwrapperconsolecommand("pardon", allargs)

            elif command in ("/perm", "/perms", "/super", "/permissions", "perm", "perms", "super", "permissions"):
                self.runwrapperconsolecommand("perms", allargs)

            elif command in ("/playerstats", "/stats", "playerstats", "stats"):
                self.runwrapperconsolecommand("playerstats", allargs)

            elif command in ("/ent", "/entity", "/entities", "ent", "entity", "entities"):
                self.runwrapperconsolecommand("ent", allargs)

            elif command.lower() in ("/config", "/con", "/prop", "/property", "/properties"):
                self.runwrapperconsolecommand("config", allargs)

            # TODO Add more commands below here, below the original items:
            # TODO __________________

            # more commands here...

            # TODO __________________
            # TODO add more commands above here, above the help-related items:

            elif command == "help":
                _readout("/help", "Get wrapper.py help.", separator=" (with a slash) - ", usereadline=self.use_readline)
                self.javaserver.console(consoleinput)
            elif command == "/help":
                # This is the console help commands.  Below this in _registerwrappershelp is the in-game help
                _readout("", "Get Minecraft help.", separator="help (no slash) - ", pad=0,
                         usereadline=self.use_readline)
                _readout("/reload", "Reload Wrapper.py plugins.", usereadline=self.use_readline)
                _readout("/plugins", "Lists Wrapper.py plugins.", usereadline=self.use_readline)
                _readout("/update-wrapper", "Checks for new Wrapper.py updates, and will install\n"
                                            "                  them automatically if one is available.",
                         usereadline=self.use_readline)
                _readout("/stop", "Stop the minecraft server without auto-restarting and without\n"
                                  "                  shuttingdown Wrapper.py.", usereadline=self.use_readline)
                _readout("/start", "Start the minecraft server.", usereadline=self.use_readline)
                _readout("/restart", "Restarts the minecraft server.", usereadline=self.use_readline)
                _readout("/halt", "Shutdown Wrapper.py completely.", usereadline=self.use_readline)
                _readout("/cm [seconds]", "Mute server output (Wrapper console logging still happens)",
                         usereadline=self.use_readline)
                _readout("/kill", "Force kill the server without saving.", usereadline=self.use_readline)
                _readout("/freeze", "Temporarily locks the server up until /unfreeze is executed\n"
                                    "                  (Only works on *NIX servers).", usereadline=self.use_readline)
                _readout("/unfreeze", "Unlocks a frozen state server (Only works on *NIX servers).",
                         usereadline=self.use_readline)
                _readout("/mem", "Get memory usage of the server (Only works on *NIX servers).",
                         usereadline=self.use_readline)
                _readout("/raw [command]", "Send command to the Minecraft Server. Useful for Forge\n"
                                           "                  commands like '/fml confirm'.",
                         usereadline=self.use_readline)
                _readout("/perms", "/perms for more...)", usereadline=self.use_readline)
                _readout("/config", "Change wrapper.properties (type /config help for more..)",
                         usereadline=self.use_readline)
                _readout("/version", self.getbuildstring(), usereadline=self.use_readline)
                _readout("/entity", "Work with entities (run /entity for more...)", usereadline=self.use_readline)
                _readout("/bans", "Display the ban help page.", usereadline=self.use_readline)
            elif command == "/bans":
                # ban commands help.
                if self.proxymode:
                    _readout("", "Bans - To use the server's versions, do not type a slash.", separator="", pad=5,
                             usereadline=self.use_readline)
                    _readout("", "", separator="-----1.7.6 and later ban commands-----", pad=10,
                             usereadline=self.use_readline)
                    _readout("/ban", " - Ban a player. Specifying h:<hours> or d:<days> creates a temp ban.",
                             separator="<name> [reason..] [d:<days>/h:<hours>] ", pad=12,
                             usereadline=self.use_readline)
                    _readout("/ban-ip", " - Ban an IP address. Reason and days (d:) are optional.",
                             separator="<ip> [<reason..> <d:<number of days>] ", pad=12,
                             usereadline=self.use_readline)
                    _readout("/pardon", " - pardon a player. Default is byuuidonly.  To unban a"
                                        "specific name (without checking uuid), use `pardon <player> False`",
                             separator="<player> [byuuidonly(true/false)]", pad=12,
                             usereadline=self.use_readline)
                    _readout("/pardon-ip", " - Pardon an IP address.",
                             separator="<address> ", pad=12,
                             usereadline=self.use_readline)
                    _readout("/banlist", " - search and display the banlist (warning - displays on single page!)",
                             separator="[players|ips] [searchtext] ", pad=12,
                             usereadline=self.use_readline)
                else:
                    _readout("ERROR - ", "Wrapper proxy-mode bans are not enabled "
                                         "(proxy mode is not on).", separator="", pad=10,
                             usereadline=self.use_readline)

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
        This should normally 'always' render True. Under rare circumstances it could be false,
        such as when this wrapper and its server are the target for a wrapper lobby with player.connect().
        """
        if self.proxymode:
            # if wrapper is using proxy mode (which should be set to online)
            return self.config["Proxy"]["online-mode"]
        if self.javaserver is not None:
            if self.javaserver.onlineMode:
                return True  # if local server is online-mode
        return False

    def listplugins(self):
        _readout("", "List of Wrapper.py plugins installed:", separator="", pad=4,
                 usereadline=self.use_readline)
        for plid in self.plugins:
            plugin = self.plugins[plid]
            if plugin["good"]:
                name = plugin["name"]
                summary = plugin["summary"]
                if summary is None:
                    summary = "No description available for this plugin"

                version = plugin["version"]
                _readout(name, summary, separator=(" - v%s - " % ".".join([str(_) for _ in version])),
                         usereadline=self.use_readline)
                # self.log.info("%s v%s - %s", name, ".".join([str(_) for _ in version]), summary)
            else:
                _readout("failed to load plugin", plugin, " - ", pad=25,
                         usereadline=self.use_readline)

    def _startproxy(self):
        self.proxy = proxy.Proxy(self)
        if proxy.requests:  # requests will be set to False if requests or any crptography is missing.
            proxythread = threading.Thread(target=self.proxy.host, args=())
            proxythread.daemon = True
            proxythread.start()
        else:
            self.disable_proxymode()
            self.log.error("Proxy mode has been disabled because you do not have one or more "
                           "of the following modules installed: \npycrypto and requests")

    def disable_proxymode(self):
        self.proxymode = False
        self.configManager.config["Proxy"]["proxy-enabled"] = False
        self.configManager.save()
        self.config = self.configManager.config
        self.log.warning("\nProxy mode is now turned off in wrapper.properties.json.\n")

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

    def _auto_update_process(self):
        while not self.halt:
            time.sleep(3600)
            if self.updated:
                self.log.info("An update for wrapper has been loaded, Please restart wrapper.")
            else:
                self._checkforupdate()

    def _checkforupdate(self, update_now=False):
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
        if self.auto_update_branch:
            branch_key = self.auto_update_branch
        else:
            branch_key = "%s-branch" % repotype
        r = requests.get(self.config["Updates"][branch_key])
        if r.status_code == 200:
            data = r.json()
            print(data)
            if data["__build__"] > core_buildinfo_version.__build__:
                if repotype == "dev":
                    reponame = "development"
                elif repotype == "stable":
                    reponame = "master"
                else:
                    reponame = data["__branch__"]
                if "__version__" not in data:
                    data["__version__"] = data["version"]
                return data["__version__"], data["__build__"], data["__branch__"], reponame

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
                with open(sys.argv[0], "wb") as f:
                    f.write(wrapperfile.content)
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

    def _pause_console(self, pause_time):
        if not self.javaserver:
            _readout("ERROR - ", "There is no running server instance to mute.", separator="", pad=10,
                     usereadline=self.use_readline)
            return
        self.javaserver.server_muted = True
        _readout("Server is now nuted for %d seconds." % pause_time, "", separator="", command_text_fg="yellow",
                 usereadline=self.use_readline)
        time.sleep(pause_time)
        _readout("Server now unmuted.", "", separator="", usereadline=self.use_readline)
        self.javaserver.server_muted = False
        for lines in self.javaserver.queued_lines:
            _readout("Q\\", "", lines, pad=3, usereadline=self.use_readline)
            time.sleep(.1)
        self.javaserver.queued_lines = []

    def _mute_console(self, all_args):
        pausetime = 30
        if len(all_args) > 0:
            pausetime = get_int(all_args[0])
        # spur off a pause thread
        cm = threading.Thread(target=self._pause_console, args=(pausetime,))
        cm.daemon = True
        cm.start()

    def _freeze(self):
        try:
            self.javaserver.freeze()
        except InvalidServerStartedError as e:
            self.log.warning(e)
        except UnsupportedOSException as ex:
            self.log.error(ex)
        except Exception as exc:
            self.log.exception("Something went wrong when trying to freeze the server! (%s)", exc)

    def _memory(self):
        try:
            get_bytes = self.javaserver.getmemoryusage()
        except UnsupportedOSException as e:
            self.log.error(e)
        except Exception as ex:
            self.log.exception("Something went wrong when trying to fetch memory usage! (%s)", ex)
        else:
            amount, units = _format_bytes(get_bytes)
            self.log.info("Server Memory Usage: %s %s (%s bytes)" % (amount, units, get_bytes))

    def _raw(self, console_input):
        try:
            if len(getargsafter(console_input[1:].split(" "), 1)) > 0:
                self.javaserver.console(getargsafter(console_input[1:].split(" "), 1))
            else:
                self.log.info("Usage: /raw [command]")
        except InvalidServerStartedError as e:
            self.log.warning(e)

    def _unfreeze(self):
        try:
            self.javaserver.unfreeze()
        except InvalidServerStartedError as e:
            self.log.warning(e)
        except UnsupportedOSException as ex:
            self.log.error(ex)
        except Exception as exc:
            self.log.exception("Something went wrong when trying to unfreeze the server! (%s)", exc)
