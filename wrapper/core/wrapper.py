# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

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
from api.helpers import format_bytes, getargs, getargsafter, readout, get_int
from utils import readkey

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
from core.permissions import Permissions
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

# http://wiki.bash-hackers.org/scripting/terminalcodes

# start of escape sequence
ESC = '\x1b'
# Set foreground to color #5 - magenta
FG_MAGENTA = ESC + '\x5b\x33\x35\x6d'  # "[35m"
BOLD = ESC + '\x5b\x31\x6d'
BOLD_MAGENTA = BOLD + FG_MAGENTA

FG_YELLOW = ESC + '\x5b\x33\x33\x6d'
BOLD_YELLOW = BOLD + FG_YELLOW

REVERSED = ESC + '\x5b\x37\x6d'  # '[ 7 m'

# Reset all attributes
RESET = ESC + '\x5b\x30\x6d'  # "[0m"
# move up one line
UP_LINE = ESC + '\x5b\x31\x41'  # "[1A"
# move cursor backwards
BACKSPACE = ESC + '\x5b\x30\x41'  # "[0A"

# clear all text from cursor to End of Line.
CLEAR_EOL = ESC + '\x5b\x4b'
# clear all text from cursor to beginning of Line.
CLEAR_BOL = ESC + '\x5b\x31\x4b'
# clear all text on Line (no cursor position change).
CLEAR_LINE = ESC + '\x5b\x31\x4b'


class Wrapper(object):

    def __init__(self):
        # setup log and config
        # needs a false setting on first in case config does not
        # load (like after changes).
        self.storage = False
        self.log = logging.getLogger('Wrapper.py')
        self.configManager = Config()
        self.configManager.loadconfig()
        # set up config
        self.config = self.configManager.config

        # Read Config items
        # hard coded cursor for non-readline mode
        self.cursor = ">"
        self.wrapper_ban_system = False
        # This was to allow alternate encodings
        self.encoding = self.config["General"]["encoding"]
        self.proxymode = self.config["Proxy"]["proxy-enabled"]
        self.wrapper_onlinemode = self.config["Proxy"]["online-mode"]
        self.wrapper_ban_system = self.proxymode and self.wrapper_ban_system
        self.auto_update_wrapper = self.config[
            "Updates"]["auto-update-wrapper"]
        self.auto_update_branch = self.config[
            "Updates"]["auto-update-branch"]
        self.use_timer_tick_event = self.config[
            "Gameplay"]["use-timer-tick-event"]
        self.command_prefix = self.config["Misc"]["command-prefix"]
        self.use_readline = self.config["Misc"]["use-readline"]

        # Storages
        self.wrapper_storage = Storage("wrapper", encoding=self.encoding)

        self.wrapper_permissions = Storage(
            "permissions", encoding=self.encoding, pickle=False)

        self.wrapper_usercache = Storage(
            "usercache", encoding=self.encoding, pickle=False)

        # storage Data objects
        self.storage = self.wrapper_storage.Data
        self.permissions = self.wrapper_permissions.Data
        self.usercache = self.wrapper_usercache.Data

        # core functions and datasets
        self.perms = Permissions(self)
        self.uuids = UUIDS(self)
        self.plugins = Plugins(self)
        self.commands = Commands(self)
        self.events = Events(self)
        self.registered_permissions = {}
        self.help = {}
        self.input_buff = ""
        self.sig_int = False
        self.command_hist = ['/help', 'help']
        self.command_index = 1

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
        # future plan to expose this to api
        self.xplayer = ConsolePlayer(self)
        # define the slot once here and not at each clients Instantiation:
        self.inv_slots = range(46)

        # Error messages for non-standard import failures.
        if not readline and self.use_readline:
            self.log.warning(
                "'readline' not imported.  This is needed for proper"
                " console functioning. Press <Enter> to acknowledge...")
            sys.stdin.readline()

        # requests is just being used in too many places to try
        # and track its usages piece-meal.
        if not requests:
            self.log.error(
                "You must have the requests module installed to use wrapper!"
                " console functioning. Press <Enter> to Exit...")
            sys.stdin.readline()
            self._halt()

    def __del__(self):
        """prevent error message on very first wrapper starts when
        wrapper exits after creating new wrapper.properties file.
        """
        if self.storage:
            self.wrapper_storage.close()
            self.wrapper_permissions.close()
            self.wrapper_usercache.close()

    def start(self):
        """wrapper execution starts here"""

        self.signals()

        self.backups = Backups(self)

        self.api = API(self, "Wrapper.py")
        self._registerwrappershelp()

        # This is not the actual server... the MCServer
        # class is a console wherein the server is started
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
                self.log.error(
                    "Web remote could not be started because you do not have"
                    " the required modules installed: pkg_resources\n"
                    "Hint: http://stackoverflow.com/questions/7446187")

        # Console Daemon runs while not wrapper.halt (here; self.halt)
        consoledaemon = threading.Thread(
            target=self.parseconsoleinput, args=())
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
                self.log.error(
                    "Sorry, but shell scripts only work on *NIX-based systems!"
                    " If you are using a  *NIX-based system, please file a "
                    "bug report.")

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
        self.wrapper_storage.close()
        self.wrapper_permissions.close()
        self.wrapper_usercache.close()
        self.log.info("Wrapper Storages closed and saved.")

        # wrapper execution ends here.  handle_server ends when
        # wrapper.halt is True.
        if self.sig_int:
            self.log.info("Ending threads, please wait...")
            time.sleep(5)
            os.system("reset")

    def signals(self):
        signal.signal(signal.SIGINT, self.sigint)
        signal.signal(signal.SIGTERM, self.sigterm)
        # noinspection PyBroadException
        try:
            # lacking in Windows
            signal.signal(signal.SIGTSTP, self.sigtstp)
        except:
            pass

    def sigint(*args):
        self = args[0]  # We are only interested in the self component
        self.log.info("Wrapper.py received SIGINT; halting...\n")
        self.sig_int = True
        self._halt()

    def sigterm(*args):
        self = args[0]  # We are only interested in the self component
        self.log.info("Wrapper.py received SIGTERM; halting...\n")
        self._halt()

    def sigtstp(*args):
        # We are only interested in the 'self' component
        self = args[0]
        self.log.info("Wrapper.py received SIGTSTP; NO sleep support!"
                      " Wrapper halting...\n")
        os.system("kill -CONT %d" % self.javaserver.proc.pid)
        self._halt()

    def _halt(self):
        self.javaserver.stop("Halting server...", restart_the_server=False)
        self.halt = True

    def shutdown(self):
        self._halt()

    def write_stdout(self, message="", source="print"):
        """
        :param message: desired output line.  Default is wrapper.
        :param source: "server", "wrapper", "print" or "log".  Default is
         print.

        """
        cursor = self.cursor

        if self.use_readline:
            print(message)
            return

        def _wrapper(msg):
            """_wrapper is normally displaying a live typing buffer.
            Therefore, there is no cr/lf at end because it is 
            constantly being re-printed in the same spot as the
            user types."""
            if msg != "":
                # re-print what the console user was typing right below that.
                # /wrapper commands receive special magenta coloring
                if msg[0:1] == '/':
                    print("{0}{1}{2}{3}{4}{5}".format(
                        UP_LINE, cursor, FG_YELLOW,
                        msg, RESET, CLEAR_EOL))
                else:
                    print("{0}{1}{2}{3}".format(
                        BACKSPACE, cursor,
                        msg, CLEAR_EOL))

        def _server(msg):
            # print server lines
            print("{0}{1}{2}\r\n".format(UP_LINE, CLEAR_LINE, msg, CLEAR_EOL))

        def _print(msg):
            _server(msg)

        parse = {
            "server": _server,
            "wrapper": _wrapper,
            "print": _print,
        }

        # if this fails due to key error, we WANT that raised, as it is
        #  a program code error, not a run-time error.
        parse[source](message)

    def getconsoleinput(self):
        """If wrapper is NOT using readline (self.use_readline == False),
        then getconsoleinput manually implements our own character 
        reading, parsing, arrow keys, command history, etc.  This 
        is desireable because it allows the user to continue to see
        their input and modify it, even if the server is producing
        console line messages that would normally "carry away" the 
        user's typing.
        
        Implemented in response to issue 326:
        'Command being typed gets carried off by console every time
         server generates output #326' by @Darkness3840:
        https://github.com/benbaptist/minecraft-wrapper/issues/326 
        """
        if self.use_readline:
            # Obtain a line of console input
            try:
                consoleinput = sys.stdin.readline().strip()
            except Exception as e:
                self.log.error(
                    "[continue] variable 'consoleinput' in 'console()' did"
                    " not evaluate \n%s" % e)
                consoleinput = ""

        else:
            arrow_index = 0
            # working buffer allows arrow use to restore what they
            # were typing but did not enter as a command yet
            working_buff = ''
            while not self.halt:
                keypress = readkey.getcharacter()
                keycode = readkey.convertchar(keypress)
                length = len(self.input_buff)

                if keycode == "right":
                    arrow_index += 1
                    if arrow_index > length:
                        arrow_index = length

                if keycode == "left":
                    arrow_index -= 1
                    if arrow_index < 1:
                        arrow_index = 0

                if keycode == "up":
                    # goes 'back' in command history time
                    self.command_index -= 1
                    if self.command_index < 1:
                        self.command_index = 0
                    self.input_buff = self.command_hist[self.command_index]
                    arrow_index = len(self.input_buff)

                if keycode == "down":
                    # goes forward in command history time
                    self.command_index += 1

                    if self.command_index + 1 > len(self.command_hist):
                        # These actions happen when at most recent typing
                        self.command_index = len(self.command_hist)
                        self.input_buff = '%s' % working_buff
                        self.write_stdout(
                            "%s " % self.input_buff, source="wrapper")
                        arrow_index = len(self.input_buff)
                        continue

                    self.input_buff = self.command_hist[self.command_index]
                    arrow_index = len(self.input_buff)

                buff_left = "%s" % self.input_buff[:arrow_index]
                buff_right = "%s" % self.input_buff[arrow_index:]

                if keycode == "backspace":
                    if len(buff_left) > 0:
                        buff_left = buff_left[:-1]
                        self.input_buff = "%s%s" % (buff_left, buff_right)
                        working_buff = "%s" % self.input_buff
                        arrow_index -= 1

                if keycode == "delete":
                    if len(buff_right) > 0:
                        buff_right = buff_right[1:]
                    self.input_buff = "%s%s" % (buff_left, buff_right)
                    working_buff = "%s" % self.input_buff

                if keycode in ("enter", "cr", "lf"):
                    # scroll up (because cr is not added to buffer)
                    # print("")
                    break

                if keycode in ("ctrl-c", "ctrl-x"):
                    self.sigterm()
                    break

                # hide special key codes like PAGE_UP, etc if not used
                if not keycode:
                    buff_left = "%s%s" % (buff_left, keypress)
                    self.input_buff = "%s%s" % (buff_left, buff_right)
                    working_buff = "%s" % self.input_buff
                    arrow_index += 1

                # with open('readout.txt', "w") as f:
                #     f.write("left: '%s'\nright: '%s'\nbuff: '%s'" % (
                #         buff_left, buff_right, self.input_buff))

                if len(buff_right) > 0:
                    self.write_stdout("{0}{1}{2}{3}".format(
                        REVERSED, buff_left, RESET, buff_right),
                        "wrapper")
                else:
                    self.write_stdout(
                        "%s " % self.input_buff, source="wrapper")

            consoleinput = "%s" % self.input_buff
            self.input_buff = ""

            if consoleinput in self.command_hist:
                # if the command is already in the history somewhere,
                # remove it and re-append to the end (most recent)
                self.command_hist.remove(consoleinput)
                self.command_hist.append(consoleinput)
            else:
                # or just add it.
                self.command_hist.append(consoleinput)
            self.command_index = len(self.command_hist)

            # print the finished command to console
            self.write_stdout(
                "%s\r\n" % self.input_buff, source="wrapper")

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

            # this can be passed to runwrapperconsolecommand() command for args
            allargs = wholecommandline[1:]

            # Console only commands (not accessible in-game)
            if command.lower() in ("/halt", "halt"):
                self._halt()
            elif command.lower() in ("/stop", "stop"):
                self.javaserver.stop_server_command("Stopping server...")
            # "kill" (with no slash) is a server command.
            elif command.lower() == "/kill":
                self.javaserver.kill("Server killed at Console...")
            elif command.lower() in ("/start", "start"):
                self.javaserver.start()
            elif command.lower() in ("/restart", "restart"):
                self.javaserver.restart("Server restarting, be right back!")
            elif command.lower()in ("/update-wrapper", "update-wrapper"):
                self._checkforupdate(True)
            # "plugins" command (with no slash) reserved for server commands
            elif command.lower() == "/plugins":
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
                readout("/version", self.getbuildstring(),
                        usereadline=self.use_readline)
            elif command.lower() in ("/mute", "/pause", "/cm", "/m", "/p"):
                self._mute_console(allargs)

            # Commands that share the commands.py in-game interface

            # "reload" (with no slash) may be used by bukkit servers
            elif command.lower() == "/reload":
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

            elif command in ("/perm", "/perms", "/super", "/permissions",
                             "perm", "perms", "super", "permissions"):
                self.runwrapperconsolecommand("perms", allargs)

            elif command in ("/playerstats", "/stats", "playerstats", "stats"):
                self.runwrapperconsolecommand("playerstats", allargs)

            elif command in ("/ent", "/entity", "/entities", "ent",
                             "entity", "entities"):
                self.runwrapperconsolecommand("ent", allargs)

            elif command.lower() in ("/config", "/con", "/prop",
                                     "/property", "/properties"):
                self.runwrapperconsolecommand("config", allargs)

            elif command.lower() in ("op", "/op"):
                self.runwrapperconsolecommand("op", allargs)

            elif command.lower() in ("deop", "/deop"):
                self.runwrapperconsolecommand("deop", allargs)

            # TODO Add more commands below here, below the original items:
            # TODO __________________

            # more commands here...

            # TODO __________________
            # TODO add more commands above here, above the help-related items:

            # minecraft help command
            elif command == "help":
                readout("/help", "Get wrapper.py help.",
                        separator=" (with a slash) - ",
                        usereadline=self.use_readline)
                self.javaserver.console(consoleinput)

            # wrapper's help (console version)
            elif command == "/help":
                self._show_help_console()

            # wrapper ban help
            elif command == "/bans":
                self._show_help_bans()

            # Commmand not recognized by wrapper
            else:
                try:
                    self.javaserver.console(consoleinput)
                except Exception as e:
                    self.log.error("[BREAK] Console input exception"
                                   " (nothing passed to server) \n%s" % e)
                    break
                continue

    def _registerwrappershelp(self):
        # All commands listed herein are accessible in-game
        # Also require player.isOp()
        new_usage = "<player> [-s SUPER-OP] [-o OFFLINE] [-l <level>]"
        self.api.registerHelp(
            "Wrapper", "Internal Wrapper.py commands ",
            [
                ("/wrapper [update/memory/halt]",
                 "If no subcommand is provided, it will"
                 " show the Wrapper version.", None),
                ("/playerstats [all]",
                 "Show the most active players. If no subcommand"
                 " is provided, it'll show the top 10 players.",
                 None),
                ("/plugins",
                 "Show a list of the installed plugins", None),
                ("/reload", "Reload all plugins.", None),
                ("/op %s" % new_usage, "This and deop are Wrapper commands.",
                 None),
                ("/permissions <groups/users/RESET>",
                 "Command used to manage permission groups and"
                 " users, add permission nodes, etc.",
                 None),
                ("/entity <count/kill> [eid] [count]",
                 "/entity help/? for more help.. ", None),
                ("/config", "Change wrapper.properties (type"
                            " /config help for more..)", None),

                # Minimum server version for commands to appear is
                # 1.7.6 (registers perm later in serverconnection.py)
                # These won't appear if proxy mode is not on (since
                # serverconnection is part of proxy).
                ("/ban <name> [reason..] [d:<days>/h:<hours>]",
                 "Ban a player. Specifying h:<hours> or d:<days>"
                 " creates a temp ban.", "mc1.7.6"),
                ("/ban-ip <ip> [<reason..> <d:<number of days>]",
                 "- Ban an IP address. Reason and days"
                 " (d:) are optional.", "mc1.7.6"),
                ("/pardon <player> [False]",
                 " - pardon a player. Default is byuuidonly."
                 "  To unban a specific "
                 "name (without checking uuid), use `pardon"
                 " <player> False`", "mc1.7.6"),
                ("/pardon-ip <address>", "Pardon an IP address.", "mc1.7.6"),
                ("/banlist [players|ips] [searchtext]",
                 "search and display the banlist (warning -"
                 " displays on single page!)", "mc1.7.6")
            ])

    def runwrapperconsolecommand(self, wrappercommand, argslist):
        xpayload = {
            'player': self.xplayer,
            'command': wrappercommand,
            'args': argslist
        }
        self.commands.playercommand(xpayload)

    def isonlinemode(self):
        """
        :returns: Whether the server OR (for proxy mode) wrapper
        is in online mode.  This should normally 'always' render
        True. Under rare circumstances it could be false, such
        as when this wrapper and its server are the target for
        a wrapper lobby with player.connect().
        """
        if self.proxymode:
            # if wrapper is using proxy mode (which should be set to online)
            return self.config["Proxy"]["online-mode"]
        if self.javaserver is not None:
            if self.javaserver.onlineMode:
                # if local server is online-mode
                return True
        return False

    def listplugins(self):
        readout("",
                "List of Wrapper.py plugins installed:", separator="", pad=4,
                usereadline=self.use_readline)
        for plid in self.plugins:
            plugin = self.plugins[plid]
            if plugin["good"]:
                name = plugin["name"]
                summary = plugin["summary"]
                if summary is None:
                    summary = "No description available for this plugin"

                version = plugin["version"]
                readout(name, summary,
                        separator=(
                            " - v%s - " % ".".join([str(_) for _ in version])),
                        usereadline=self.use_readline)
            else:
                readout("failed to load plugin", plugin, pad=25,
                        usereadline=self.use_readline)

    def _startproxy(self):
        self.proxy = proxy.Proxy(self)
        # requests will be set to False if requests or cryptography is missing.
        if proxy.requests:
            proxythread = threading.Thread(target=self.proxy.host, args=())
            proxythread.daemon = True
            proxythread.start()
        else:
            self.disable_proxymode()
            self.log.error(
                "Proxy mode has been disabled because you do not have one"
                " or more of the following modules installed:"
                " \npycrypto and requests")

    def disable_proxymode(self):
        self.proxymode = False
        self.configManager.config["Proxy"]["proxy-enabled"] = False
        self.configManager.save()
        self.config = self.configManager.config
        self.log.warning(
            "\nProxy mode is now turned off in wrapper.properties.json.\n")

    @staticmethod
    def getbuildstring():
        if core_buildinfo_version.__branch__ == "dev":
            return "%s (development build #%d)" % (
                core_buildinfo_version.__version__,
                core_buildinfo_version.__build__)

        elif core_buildinfo_version.__branch__ == "stable":
            return "%s (stable)" % core_buildinfo_version.__build__
        else:
            return "Version: %s (%s build #%d)" % (
                core_buildinfo_version.__version__,
                core_buildinfo_version.__branch__,
                core_buildinfo_version.__build__)

    def _auto_update_process(self):
        while not self.halt:
            time.sleep(3600)
            if self.updated:
                self.log.info(
                    "An update for wrapper has been loaded,"
                    " Please restart wrapper.")
            else:
                self._checkforupdate()

    def _checkforupdate(self, update_now=False):
        """ checks for update """
        self.log.info("Checking for new builds...")
        update = self.get_wrapper_update_info()
        if update:
            version, build, repotype, reponame = update
            self.log.info(
                "New Wrapper.py %s build #%d is available!"
                " (current build is #%d)",
                repotype, build, core_buildinfo_version.__build__)

            if self.auto_update_wrapper or update_now:
                self.log.info("Updating...")
                self.performupdate(version, build, reponame)
            else:
                self.log.info(
                    "Because you have 'auto-update-wrapper' set to False,"
                    " you must manually update Wrapper.py. To update"
                    " Wrapper.py manually, please type /update-wrapper.")
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
            if data["__build__"] > core_buildinfo_version.__build__:
                if repotype == "dev":
                    reponame = "development"
                elif repotype == "stable":
                    reponame = "master"
                else:
                    reponame = data["__branch__"]
                if "__version__" not in data:
                    data["__version__"] = data["version"]
                return data["__version__"],\
                    data["__build__"],\
                    data["__branch__"], reponame

        else:
            self.log.warning(
                "Failed to check for updates - are you connected to the"
                " internet? (Status Code %d)", r.status_code)
            return False

    def performupdate(self, version, build, reponame):
        """
        Perform update; returns True if update succeeds.  User must
        still restart wrapper manually.

        :param version: first argument from get_wrapper_update_info()
        :param build: second argument from get_wrapper_update_info()
        :param reponame: 4th argument from get_wrapper_update_info()
             - not the '__branch__'!
        :return: True if update succeeds
        """
        repo = reponame
        wraphash = requests.get(
            "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper"
            "/%s/build/Wrapper.py.md5" % repo)
        wrapperfile = requests.get(
            "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper"
            "/%s/Wrapper.py" % repo)

        if wraphash.status_code == 200 and wrapperfile.status_code == 200:
            self.log.info("Verifying Wrapper.py...")
            if hashlib.md5(wrapperfile.content).hexdigest() == wraphash.text:
                self.log.info(
                    "Update file successfully verified. Installing...")
                with open(sys.argv[0], "wb") as f:
                    f.write(wrapperfile.content)
                self.log.info(
                    "Wrapper.py %s (#%d) installed. Please reboot Wrapper.py.",
                    ".".join([str(_) for _ in version]), build)
                self.updated = True
                return True
            else:
                return False
        else:
            self.log.error(
                "Failed to update due to an internal error (%d, %d)",
                wraphash.status_code,
                wrapperfile.status_code, exc_info=True)
            return False

    def event_timer(self):
        t = time.time()
        while not self.halt:
            if time.time() - t > 1:
                self.events.callevent("timer.second", None)
                """ eventdoc
                    <group> wrapper <group>

                    <description> a timer that is called each second.
                    <description>

                    <abortable> No <abortable>

                """
                t = time.time()
            if self.use_timer_tick_event:
                # don't really advise the use of this timer
                self.events.callevent("timer.tick", None)
                """ eventdoc
                    <group> wrapper <group>

                    <description> a timer that is called each 1/20th
                    <sp> of a second, like a minecraft tick.
                    <description>

                    <abortable> No <abortable>

                    <comments>
                    Use of this timer is not suggested and is turned off
                    <sp> by default in the wrapper.config.json file
                    <comments>

                """
            time.sleep(0.05)

    def _pause_console(self, pause_time):
        if not self.javaserver:
            readout("ERROR - ",
                    "There is no running server instance to mute.",
                    separator="", pad=10, usereadline=self.use_readline)
            return
        self.javaserver.server_muted = True
        readout("Server is now muted for %d seconds." % pause_time, "",
                separator="", command_text_fg="yellow",
                usereadline=self.use_readline)
        time.sleep(pause_time)
        readout("Server now unmuted.", "", separator="",
                usereadline=self.use_readline)
        self.javaserver.server_muted = False
        for lines in self.javaserver.queued_lines:
            readout("Q\\", "", lines, pad=3, usereadline=self.use_readline)
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
            self.log.exception(
                "Something went wrong when trying to freeze the"
                " server! (%s)", exc)

    def _memory(self):
        try:
            get_bytes = self.javaserver.getmemoryusage()
        except UnsupportedOSException as e:
            self.log.error(e)
        except Exception as ex:
            self.log.exception(
                "Something went wrong when trying to fetch"
                " memory usage! (%s)", ex)
        else:
            amount, units = format_bytes(get_bytes)
            self.log.info(
                "Server Memory Usage: %s %s (%s bytes)" % (
                    amount, units, get_bytes))

    def _raw(self, console_input):
        try:
            if len(getargsafter(console_input[1:].split(" "), 1)) > 0:
                self.javaserver.console(
                    getargsafter(console_input[1:].split(" "), 1))
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
            self.log.exception(
                "Something went wrong when trying to unfreeze"
                " the server! (%s)", exc)

    def _show_help_console(self):
        # This is the console help command display.
        readout("", "Get Minecraft help.",
                separator="help (no slash) - ", pad=0,
                usereadline=self.use_readline)
        readout("/reload", "Reload Wrapper.py plugins.",
                usereadline=self.use_readline)
        readout("/plugins", "Lists Wrapper.py plugins.",
                usereadline=self.use_readline)
        readout("/update-wrapper",
                "Checks for new Wrapper.py updates, and will install\n"
                "them automatically if one is available.",
                usereadline=self.use_readline)
        readout("/stop",
                "Stop the minecraft server without"
                " auto-restarting and without\n"
                "                  shuttingdown Wrapper.py.",
                usereadline=self.use_readline)
        readout("/start", "Start the minecraft server.",
                usereadline=self.use_readline)
        readout("/restart", "Restarts the minecraft server.",
                usereadline=self.use_readline)
        readout("/halt", "Shutdown Wrapper.py completely.",
                usereadline=self.use_readline)
        readout("/cm [seconds]",
                "Mute server output (Wrapper console"
                " logging still happens)",
                usereadline=self.use_readline)
        readout("/kill", "Force kill the server without saving.",
                usereadline=self.use_readline)
        readout("/freeze",
                "Temporarily locks the server up"
                " until /unfreeze is executed\n"
                "                  (Only works on *NIX servers).",
                usereadline=self.use_readline)
        readout("/unfreeze", "Unlocks a frozen state server"
                             " (Only works on *NIX servers).",
                usereadline=self.use_readline)
        readout("/mem", "Get memory usage of the server"
                        " (Only works on *NIX servers).",
                usereadline=self.use_readline)
        readout("/raw [command]",
                "Send command to the Minecraft"
                " Server. Useful for Forge\n"
                "                  commands like '/fml confirm'.",
                usereadline=self.use_readline)
        readout("/perms", "/perms for more...)",
                usereadline=self.use_readline)
        readout("/config", "Change wrapper.properties (type"
                           " /config help for more..)",
                usereadline=self.use_readline)
        readout("/version", self.getbuildstring(),
                usereadline=self.use_readline)
        readout("/entity",
                "Work with entities (run /entity for more...)",
                usereadline=self.use_readline)
        readout("/bans", "Display the ban help page.",
                usereadline=self.use_readline)

    def _show_help_bans(self):
        # ban commands help.
        if not self.proxymode:
            readout(
                "ERROR - ",
                "Wrapper proxy-mode bans are not enabled "
                "(proxy mode is not on).", separator="",
                pad=10,
                usereadline=self.use_readline)
            return

        readout(
            "",
            "Bans - To use the server's versions, do not type a slash.",
            separator="", pad=5,
            usereadline=self.use_readline)
        readout(
            "", "", separator="-----1.7.6 and later ban commands-----",
            pad=10,
            usereadline=self.use_readline)
        readout(
            "/ban",
            " - Ban a player. Specifying h:<hours> or d:<days>"
            " creates a temp ban.",
            separator="<name> [reason..] [d:<days>/h:<hours>] ",
            pad=12,
            usereadline=self.use_readline)
        readout(
            "/ban-ip",
            " - Ban an IP address. Reason and days (d:) are optional.",
            separator="<ip> [<reason..> <d:<number of days>] ", pad=12,
            usereadline=self.use_readline)
        readout(
            "/pardon",
            " - pardon a player. Default is byuuidonly.  To unban a"
            "specific name (without checking uuid), use"
            " `pardon <player> False`",
            separator="<player> [byuuidonly(true/false)]", pad=12,
            usereadline=self.use_readline)
        readout(
            "/pardon-ip", " - Pardon an IP address.",
            separator="<address> ", pad=12,
            usereadline=self.use_readline)
        readout(
            "/banlist",
            " - search and display the banlist (warning -"
            " displays on single page!)",
            separator="[players|ips] [searchtext] ", pad=12,
            usereadline=self.use_readline)
