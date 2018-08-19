# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from __future__ import print_function

# system imports
import copy
import signal
import hashlib
import threading
import time
import os
import logging
# import smtplib
import sys  # used to pass sys.argv to server

try:
    from concurrent.futures import ProcessPoolExecutor
except ImportError:
    ProcessPoolExecutor = False

# non standard library imports
try:
    import readline
except ImportError:
    readline = False

try:
    import requests
except ImportError:
    requests = False

try:
    import resource
except ImportError:
    resource = False

# small feature and helpers
# noinspection PyProtectedMember
from api.helpers import format_bytes, getargs, getargsafter, readout, get_int
from api.helpers import putjsonfile
from utils import readkey
from utils import version as version_mod

# core items
from core.mcserver import MCServer
from core.plugins import Plugins
from core.commands import Commands
from core.events import Events
from core.storage import Storage
from core.irc import IRC
from core.scripts import Scripts
import core.buildinfo as buildinfo
from proxy.utils.mcuuid import UUIDS, MCUUID
from core.config import Config
from core.backups import Backups
from core.consoleuser import ConsolePlayer
from core.permissions import Permissions
from core.alerts import Alerts
from utils.crypt import Crypt, phrase_to_url_safebytes, gensalt

# optional API type stuff
from proxy.base import Proxy
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
    def __init__(self, secret_passphrase):
        # setup log and config
        # needs a false setting on first in case config does not
        # load (like after changes).
        self.storage = False
        self.log = logging.getLogger('Wrapper.py')
        self.configManager = Config()
        self.configManager.loadconfig()
        self.config = self.configManager.config
        self.encoding = self.config["General"]["encoding"]
        self.serverpath = self.config["General"]["server-directory"]
        self.api = API(self, "Wrapper.py")
        self.alerts = Alerts(self)
        self.alerts_on = self.config["Alerts"]["enabled"]

        # Read Config items
        # hard coded cursor for non-readline mode
        self.cursor = ">"
        # This was to allow alternate encodings

        self.proxymode = self.config["Proxy"]["proxy-enabled"]
        self.wrapper_onlinemode = self.config["Proxy"]["online-mode"]
        self.halt_message = self.config["Misc"]["halt-message"]

        # encryption items (for passwords and sensitive user data)
        # salt is generated and stored in wrapper.properties.json
        config_changes = False
        salt = self.config["General"]["salt"]
        if not salt:
            salt = gensalt(self.encoding)
            self.config["General"]["salt"] = salt
            config_changes = True
        # passphrase is provided at startup by the wrapper operator or script (not stored)  # noqa
        passphrase = phrase_to_url_safebytes(secret_passphrase, self.encoding, salt)  # noqa
        self.cipher = Crypt(passphrase, self.encoding)

        # Update passwords (hash any plaintext passwords)
        for groups in self.config:
            for cfg_items in self.config[groups]:
                if cfg_items[-10:] == "-plaintext":
                    # i.e., cfg_items ===> like ["web-password-plaintext"]
                    hash_item = cfg_items[:-10]
                    # hash_item ===> i.e., ["web-password"]
                    if hash_item in self.config[groups] and self.config[groups][cfg_items]:  # noqa
                        # encrypt contents of (i.e.) ["web-password-plaintext"]
                        hashed_item = self.cipher.encrypt(
                            self.config[groups][cfg_items])
                        # store in "" ["Web"]["web-password"]
                        self.config[groups][hash_item] = hashed_item
                        # set plaintext item to false (successful digest)
                        self.config[groups][cfg_items] = False
                        config_changes = True

        # Patch any old update paths "..wrapper/development/build/version.json"
        # new paths are: "..wrapper/development"
        for entries in self.config["Updates"]:
            if "/build/version.json" in str(self.config["Updates"][entries]):
                oldentry = copy.copy(self.config["Updates"][entries])
                self.config["Updates"][entries] = oldentry.split("/build/version.json")[0]  # noqa
                config_changes = True

        # save changes made to config file
        if config_changes:
            self.configManager.save()

        # reload branch update info.
        self.auto_update_wrapper = self.config["Updates"]["auto-update-wrapper"]
        self.auto_update_branch = self.config["Updates"]["auto-update-branch"]
        if not self.auto_update_branch:
            self.update_url = "https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development"  # noqa
        else:
            self.update_url = self.config["Updates"][self.auto_update_branch]

        # load some general options
        self.use_timer_tick_event = self.config[
            "Gameplay"]["use-timer-tick-event"]
        self.use_readline = not(self.config["Misc"]["use-betterconsole"])
        self.trap_ctrlz = self.config["Misc"]["trap-ctrl-z"]

        #  HaltSig - Why? ... because if self.haltsig was just `False`, passing
        #  a self.haltsig would simply be passing `False` (immutable).  Changing
        # the value of self.haltsig would not necessarily change the value of
        # the passed parameter (unless it was specifically referenced back as
        # `wrapper.haltsig`). Since the halt signal needs to be passed, possibly
        # several layers deep, and into other modules , using a HaltSig object
        # is required to ensure we are actually sharing the same value between
        # different objects.
        self.haltsig = HaltSig()

        # Storages
        self.wrapper_storage = Storage("wrapper", pickle=False)
        self.wrapper_permissions = Storage("permissions", pickle=False)
        self.wrapper_usercache = Storage("usercache", pickle=False)

        # storage Data objects
        self.storage = self.wrapper_storage.Data
        self.usercache = self.wrapper_usercache.Data
        # self.wrapper_permissions accessed only by permissions module

        # core functions and datasets
        self.perms = Permissions(self)
        self.uuids = UUIDS(self.log, self.usercache)
        self.mcuuid = MCUUID
        self.plugins = Plugins(self)
        self.commands = Commands(self)
        self.events = Events(self)
        self.players = {}
        self.registered_permissions = {}
        self.help = {}
        self.input_buff = ""
        self.sig_int = False
        self.command_hist = ['/help', 'help']
        self.command_index = 1

        # init items that are set up later (or opted out of/ not set up.)
        self.javaserver = None
        self.irc = None
        self.scripts = None
        self.web = None
        self.proxy = None
        self.backups = None

        self.updated = False
        # future plan to expose this to api
        self.xplayer = ConsolePlayer(self)

        # Error messages for non-standard import failures.
        if not readline and self.use_readline:
            self.log.warning(
                "'readline' not imported.  This is needed for proper"
                " console functioning. Press <Enter> to acknowledge...")
            sys.stdin.readline()

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

        # requests is just being used in too many places to try
        # and track its usages piece-meal.
        if not requests:
            self.log.error(
                "You must have the requests module installed to use wrapper!"
                " console functioning. Press <Enter> to Exit...")
            sys.stdin.readline()
            raise ImportWarning

        self.signals()
        self.backups = Backups(self)
        self._registerwrappershelp()

        # The MCServerclass is a console wherein the server is started
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
            if manageweb.pkg_resources:
                self.log.warning(manageweb.DISCLAIMER)
                self.web = manageweb.Web(self)
                t = threading.Thread(target=self.web.wrap, args=())
                t.daemon = True
                t.start()
            else:
                self.log.error(
                    "Web remote could not be started because you do not have"
                    " the pkg_resources module installed: \n"
                    "Hint: http://stackoverflow.com/questions/7446187")

        # Console Daemon runs while not wrapper.halt.halt
        consoledaemon = threading.Thread(
            target=self.parseconsoleinput, args=())
        consoledaemon.daemon = True
        consoledaemon.start()

        # Timer runs while not wrapper.halt.halt
        ts = threading.Thread(target=self.event_timer_second, args=())
        ts.daemon = True
        ts.start()

        if self.use_timer_tick_event:
            # Timer runs while not wrapper.halt.halt
            tt = threading.Thread(target=self.event_timer_tick, args=())
            tt.daemon = True
            tt.start()

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

        # Alert sent by daemonized thread to prevent wrapper execution blocking
        if self.alerts_on:
            self.alerts.ui_process_alerts(
                "Wrapper.py started at %s" % time.time()
            )

        self.javaserver.handle_server()
        # handle_server always runs, even if the actual server is not started

        self.plugins.disableplugins()
        self.log.info("Plugins disabled")
        self.wrapper_storage.close()
        self.wrapper_permissions.close()
        self.wrapper_usercache.close()
        self.log.info("Wrapper Storages closed and saved.")

        # use non-daemon thread to ensure alert gets sent before wrapper closes
        if self.alerts_on:
            self.alerts.ui_process_alerts(
                "Wrapper.py stopped at %s" % time.time(), blocking=True
            )

        # wrapper execution ends here.  handle_server ends when
        # wrapper.halt.halt is True.
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
            if self.trap_ctrlz:
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
        # this continues a frozen server, if it was frozen...
        os.system("kill -CONT %d" % self.javaserver.proc.pid)
        self._halt()

    def _halt(self):
        if self.javaserver.state in (1, 2):
            self.javaserver.stop(self.halt_message, restart_the_server=False)
        self.haltsig.halt = True

    def shutdown(self):
        self._halt()

    def write_stdout(self, message="", source="print"):
        """
        :param message: desired output line.  Default is wrapper.
        :param source: "server", "wrapper", "print" or "log".  Default is
         print.

        """
        cursor = self.cursor

        def _console_event():
            self.events.callevent("server.consoleMessage",
                                  {"message": message}, abortable=False)
            """ eventdoc
                <group> core/wrapper.py <group>

                <description> a line of Console output.
                <description>

                <abortable> No
                <abortable>

                <comments>
                This event is triggered by console output which has already been sent. 
                <comments>

                <payload>
                "message": <str> type - The line of buffered output.
                <payload>

            """  # noqa

        if self.use_readline:
            _console_event()
            print(message)
            return

        def _wrapper_line():
            _console_event()
            _wrapper()

        def _wrapper():
            """_wrapper is normally displaying a live typing buffer.
            Therefore, there is no cr/lf at end because it is 
            constantly being re-printed in the same spot as the
            user types."""
            if message != "":
                # re-print what the console user was typing right below that.
                # /wrapper commands receive special magenta coloring
                if message[0:1] == '/':
                    print("{0}{1}{2}{3}{4}{5}".format(
                        UP_LINE, cursor, FG_YELLOW,
                        message, RESET, CLEAR_EOL))
                else:
                    print("{0}{1}{2}{3}".format(
                        BACKSPACE, cursor,
                        message, CLEAR_EOL))

        def _server():
            # print server lines
            _console_event()
            print("{0}{1}{2}\r\n".format(UP_LINE, CLEAR_LINE, message, CLEAR_EOL))  # noqa

        def _print():
            _server()

        parse = {
            "server": _server,
            "wrapper": _wrapper,
            "wrapper_line": _wrapper_line,
            "print": _print,
        }

        # if this fails due to key error, we WANT that raised, as it is
        #  a program code error, not a run-time error.
        parse[source]()

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
            while not self.haltsig.halt:
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
                "%s\r\n" % self.input_buff, source="wrapper_line")

        return consoleinput

    def parseconsoleinput(self):
        while not self.haltsig.halt:
            consoleinput = self.getconsoleinput()
            # No command (perhaps just a line feed or spaces?)
            if len(consoleinput) < 1:
                continue
            self.process_command(consoleinput)

    def process_command(self, commandline, player=None):
            if player is None:
                player = self.xplayer
            # for use with runwrapperconsolecommand() command
            wholecommandline = commandline[0:].split(" ")
            command = str(getargs(wholecommandline, 0)).lower()

            # this can be passed to runwrapperconsolecommand() command for args
            allargs = wholecommandline[1:]

            # Console only commands (not accessible in-game)
            if command in ("/halt", "halt"):
                self._halt()
            elif command in ("/stop", "stop"):
                self.javaserver.stop_server_command()
            # "kill" (with no slash) is a server command.
            elif command == "/kill":
                self.javaserver.kill("Server killed at Console...")
            elif command in ("/start", "start"):
                self.javaserver.start()
            elif command in ("/restart", "restart"):
                self.javaserver.restart()
            elif command in ("/update-wrapper", "update-wrapper"):
                self._checkforupdate(True)
            # "plugins" command (with no slash) reserved for server commands
            elif command == "/plugins":
                self.listplugins(player)
            elif command in ("/mem", "/memory", "mem", "memory"):
                self._memory()
            elif command in ("/raw", "raw"):
                self._raw(commandline)
            elif command in ("/freeze", "freeze"):
                self._freeze()
            elif command in ("/unfreeze", "unfreeze"):
                self._unfreeze()
            elif command == "/version":
                readout("/version", self.getbuildstring(),
                        usereadline=self.use_readline, player=player)
            elif command in ("/mute", "/pause", "/cm", "/m", "/p"):
                self._mute_console(allargs, player)

            # Commands that share the commands.py in-game interface

            # "reload" (with no slash) may be used by bukkit servers
            elif command == "/reload":
                self.runwrapperconsolecommand("reload", [], player)

            # proxy mode ban system
            elif self.proxymode and command == "/ban":
                self.runwrapperconsolecommand("ban", allargs, player)

            elif self.proxymode and command == "/ban-ip":
                self.runwrapperconsolecommand("ban-ip", allargs, player)

            elif self.proxymode and command == "/pardon-ip":
                self.runwrapperconsolecommand("pardon-ip", allargs, player)

            elif self.proxymode and command == "/pardon":
                self.runwrapperconsolecommand("pardon", allargs, player)

            elif command in ("/perm", "/perms", "/super", "/permissions",
                             "perm", "perms", "super", "permissions"):
                self.runwrapperconsolecommand("perms", allargs, player)

            elif command in ("/playerstats", "/stats", "playerstats", "stats"):
                self.runwrapperconsolecommand("playerstats", allargs, player)

            elif command in ("/ent", "/entity", "/entities", "ent",
                             "entity", "entities"):
                self.runwrapperconsolecommand("ent", allargs, player)

            elif command in ("/config", "/con", "/prop",
                             "/property", "/properties"):
                self.runwrapperconsolecommand("config", allargs, player)

            elif command in ("whitelist", "/whitelist"):
                self.runwrapperconsolecommand("whitelist", allargs, player)

            elif command in ("op", "/op"):
                self.runwrapperconsolecommand("op", allargs, player)

            elif command in ("kick", "/kick"):
                self.runwrapperconsolecommand("kick", allargs, player)

            elif command in ("deop", "/deop"):
                self.runwrapperconsolecommand("deop", allargs, player)

            elif command in ("pass", "/pass", "pw", "/pw", "password", "/password"):  # noqa
                self.runwrapperconsolecommand("password", allargs, player)

            # minecraft help command
            elif command == "help":
                readout("/help", "Get wrapper.py help.",
                        separator=" (with a slash) - ",
                        usereadline=self.use_readline, player=player)
                self.javaserver.console(commandline)

            # wrapper's help (console version)
            elif command == "/help":
                self._show_help_console(player)

            # wrapper ban help
            elif command == "/bans":
                self._show_help_bans(player)

            # Commmand not recognized by wrapper
            else:
                try:
                    self.javaserver.console(commandline)
                except Exception as e:
                    self.log.error("Console input exception"
                                   " (nothing passed to server) \n%s" % e)

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
                ("/password", "Sample usage: /pw IRC control-irc-pass <new"
                              "password>", None),

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

    def runwrapperconsolecommand(self, wrappercommand, argslist, player=None):
        if player is None:
            player = self.xplayer
        xpayload = {
            'player': player,
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
        if self.javaserver:
            try:
                return self.javaserver.properties["online-mode"]
            except KeyError:
                pass
        return False

    def listplugins(self, player):
        readout("",
                "List of Wrapper.py plugins installed:", separator="", pad=4,
                usereadline=self.use_readline, player=player)
        for plid in self.plugins:
            plugin = self.plugins[plid]
            if plugin["good"]:
                name = plugin["name"]
                summary = plugin["summary"]
                if summary is None:
                    summary = "No description available for this plugin"

                plugin_version = plugin["version"]
                sep = " - v%s - " % ".".join([str(_) for _ in plugin_version])
                readout(name, summary, separator=sep,
                        usereadline=self.use_readline, player=player)
            else:
                readout("failed to load plugin", plugin, pad=25,
                        usereadline=self.use_readline, player=player)

    def _start_emailer(self):
        alerts = self.config["Alerts"]["enabled"]
        if alerts:
            self.config["Alerts"] = "alerts true"

    def _startproxy(self):
        try:
            self.proxy = Proxy(self)
        except ImportError:
            self.log.error("Proxy mode not started because of missing "
                           "dependencies for encryption!")
            self.disable_proxymode()
            return

        # wait for server to start
        timer = 0
        while self.javaserver.state < STARTED:
            timer += 1
            time.sleep(.1)
            if timer > 1200:
                self.log.warning(
                    "Proxy mode did not detect a started server within 2"
                    " minutes.  Disabling proxy mode because something is"
                    " wrong.")
                self.disable_proxymode()
                return

        if self.proxy.proxy_port == self.javaserver.server_port:
            self.log.warning("Proxy mode cannot start because the wrapper"
                             " port is identical to the server port.")
            self.disable_proxymode()
            return

        if not ProcessPoolExecutor:
            proxythread = threading.Thread(target=self.proxy.host, args=())
            proxythread.daemon = True
            proxythread.start()
        else:
            with ProcessPoolExecutor(max_workers=2) as executor:
                executor.submit(self.proxy.host())

    def disable_proxymode(self):
        self.proxymode = False
        self.config["Proxy"]["proxy-enabled"] = False
        self.configManager.save()
        self.log.warning(
            "\nProxy mode is now turned off in wrapper.properties.json.\n")

    def enable_proxymode(self):
        self.proxymode = True
        self.config["Proxy"]["proxy-enabled"] = True
        self.configManager.save()
        self.log.warning(
            "\nProxy mode is now back on in wrapper.properties.json.\n")
        self.log.debug("attempting a restart of proxy mode...")
        self._startproxy()

    @staticmethod
    def getbuildstring():

        thisversion = version_mod.get_complete_version()
        vers_string = "%d.%d.%d - %s (%s build #%d)" % (
            thisversion[0], thisversion[1], thisversion[2],  # 3 part semantic
            thisversion[3],                                  # release type
            buildinfo.__branch__,                            # branch
            thisversion[4],                                  # build number
        )
        return vers_string

    def _auto_update_process(self):
        while not self.haltsig.halt:
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
            version, repotype, reponame = update
            build = version[4]
            self.log.info(
                "New Wrapper.py %s build #%d is available!"
                " (current build is #%d)",
                repotype, build, buildinfo.__version__[4])

            if self.auto_update_wrapper or update_now:
                self.log.info("Updating...")
                self.performupdate(version, reponame)
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
            repotype = buildinfo.__branch__

        # develop updates location
        if self.auto_update_branch:
            branch_key = self.auto_update_branch
        else:
            branch_key = "%s-branch" % repotype

        # get the update information
        r = requests.get("%s/build/version.json" % self.config["Updates"][branch_key])  # noqa
        if r.status_code == 200:
            data = r.json()
        else:
            self.log.warning(
                "Failed to check for updates - are you connected to the"
                " internet? (Status Code %d)", r.status_code)
            return False
        # do some renaming for humans (maintain consistent branch namings)
        if repotype == "dev":
            reponame = "development"
        elif repotype == "stable":
            reponame = "master"
        else:
            reponame = data["__branch__"]

        # should not happen unless someone points to a very old repo.
        if "__version__" not in data:
            self.log.warning("corrupted repo data. Saved debug data to disk!")
            putjsonfile(data, "repo_update_failure_debug")
            return False

        release_mapping = {'alpha': 0, 'beta': 1, 'rc': 2, "final": 3}
        this_wrapper_rel = release_mapping[buildinfo.__version__[3]]
        found_wrapper_rel = release_mapping[data["__version__"][3]]
        versionisbetter = data["__version__"][0] > buildinfo.__version__[0]
        versionissame = data["__version__"][0] = buildinfo.__version__[0]
        subversionhigher = data["__version__"][1] > buildinfo.__version__[1]
        subversionsame = data["__version__"][1] = buildinfo.__version__[1]
        miniversionhigher = data["__version__"][2] > buildinfo.__version__[2]
        buildishigher = data["__version__"][4] > buildinfo.__version__[4]

        ''' 
        version[__build__] is deprecated and remains in version.json solely
        for older wrapper builds before (old build number) 265.  Since the 
        new version tuple includes build as the fifth element, we use that.
        Of course really old versions (0.8.x and older) still use the old
        `"build"` item... 
        
        Build numbers are now unique to a given release and version.  So
        [1, 0, 0, 'rc', <build>] will have a different build number sequence
        from both [0, 16, 1, 'beta', <build>] and [1, 0, 0, 'final', <build>]
        '''

        update = False
        if found_wrapper_rel > this_wrapper_rel:
            update = True
        elif versionisbetter:
            update = True
        elif buildishigher:
            update = True
        elif versionissame:
            if subversionhigher:
                update = True
            elif subversionsame and miniversionhigher:
                update = True

        if update:
            return data["__version__"], data[
                "__branch__"], reponame
        else:
            return False

    def performupdate(self, version, repo):
        """
        Perform update; returns True if update succeeds.  User must
        still restart wrapper manually.

        :param version: first argument from get_wrapper_update_info()
        :param repo: get_wrapper_update_info().__branch__
        :return: True if update succeeds
        """

        if self.updated:
            return True
        wraphash = requests.get("%s/build/Wrapper.py.md5" % self.update_url)
        wrapperfile = requests.get("%s/Wrapper.py" % self.update_url)

        if wraphash.status_code == 200 and wrapperfile.status_code == 200:
            self.log.info("Verifying Wrapper.py...")
            if hashlib.md5(wrapperfile.content).hexdigest() == wraphash.text:
                self.log.info(
                    "Update file successfully verified. Installing...")
                with open(sys.argv[0], "wb") as f:
                    f.write(wrapperfile.content)
                self.log.info(
                    "Wrapper.py %s (%s) installed. Please reboot Wrapper.py.",
                    version_mod.get_main_version(version), repo
                )
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

    def event_timer_second(self):
        while not self.haltsig.halt:
            time.sleep(1)
            self.events.callevent("timer.second", None, abortable=False)
            """ eventdoc
                <group> wrapper <group>

                <description> a timer that is called each second.  Do
                <sp> not rely on these events to happen 'on-time'!  They
                <sp> can be delayed based on their position the queue, as 
                <sp> well as the total number of timer.second events being 
                <sp> called.                
                <description>

                <abortable> No <abortable>

            """

    def event_timer_tick(self):
        while not self.haltsig.halt:
            self.events.callevent("timer.tick", None, abortable=False)
            time.sleep(0.05)
            """ eventdoc
                <group> wrapper <group>

                <description> a timer that is called each 1/20th
                <sp> of a second, like a minecraft tick.
                <description>

                <abortable> No <abortable>

                <comments>
                Use of this timer is deprecated and is turned off
                <sp> by default in the wrapper.config.json file.  the final 
                <sp> wrapper version 1.0 final will not support this timer. Its
                <sp> use in wrapper has always been a bad idea. Starting with
                <sp> wrapper 1.0.9 RC 12, this timer will be somewhat buggy,
                <sp> running two or more ticks behind.
                <comments>

            """

    def backups_running(self):
        return self._backup_progress()

    def backups_idle(self):
        return not self._backup_progress()

    def _backup_progress(self):
        if self.backups:
            if self.backups.inprogress:
                self.log.info(
                    "backup_progress reporting: A backup is in progress."
                )
                return True
            else:
                return False
        else:
            return False

    def _pause_console(self, pause_time, player):
        if not self.javaserver:
            readout("ERROR - ",
                    "There is no running server instance to mute.",
                    separator="", pad=10,
                    usereadline=self.use_readline, player=player)
            return
        self.javaserver.server_muted = True
        readout("Server is now muted for %d seconds." % pause_time, "",
                separator="", command_text_fg="yellow",
                usereadline=self.use_readline, player=player)
        time.sleep(pause_time)
        readout("Server now unmuted.", "", separator="",
                usereadline=self.use_readline, player=player)
        self.javaserver.server_muted = False
        for lines in self.javaserver.queued_lines:
            readout("Q\\", "", lines, pad=3,
                    usereadline=self.use_readline, player=player)
            time.sleep(.1)
        self.javaserver.queued_lines = []

    def _mute_console(self, all_args, player):
        pausetime = 30
        if len(all_args) > 0:
            pausetime = get_int(all_args[0])
        # spur off a pause thread
        cm = threading.Thread(
            target=self._pause_console, args=(pausetime, player)
        )
        cm.daemon = True
        cm.start()

    def _freeze(self):
        try:
            self.javaserver.freeze()
        except OSError as ex:
            self.log.error(ex)
        except EnvironmentError as e:
            self.log.warning(e)
        except Exception as exc:
            self.log.exception(
                "Something went wrong when trying to freeze the"
                " server! (%s)", exc)

    # noinspection PyBroadException
    @staticmethod
    def memory_usage():
        """Memory usage of the current process in kilobytes.
        returns dict {'peak': 0, 'rss': 0}"""

        def _memory_usage():
            """Memory usage of the current process in kilobytes."""
            status = None
            result = {'peak': 0, 'rss': 0}
            try:
                # This will only work on systems with a /proc file system
                # (like Linux).
                status = open('/proc/self/status')
                for line in status:
                    parts = line.split()
                    key = parts[0][2:-1].lower()
                    if key in result:
                        result[key] = int(parts[1])
            finally:
                if status is not None:
                    status.close()
            return result
        try:
            totmem = _memory_usage()
        except:
            try:
                # this might be cross-platform
                if resource:
                    temp = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    totmem = {'peak': temp, 'rss': temp}
                else:
                    totmem = {'peak': 0, 'rss': 0}
            except:
                # all efforts fail...
                totmem = {'peak': 0, 'rss': 0}
        return totmem

    def _memory(self):
        try:
            get_bytes = self.javaserver.getmemoryusage()
        except OSError as e:
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
        except EnvironmentError as e:
            self.log.warning(e)

    def _unfreeze(self):
        try:
            self.javaserver.unfreeze()
        except OSError as ex:
            self.log.error(ex)
        except EnvironmentError as e:
            self.log.warning(e)
        except Exception as exc:
            self.log.exception(
                "Something went wrong when trying to unfreeze"
                " the server! (%s)", exc)

    def _show_help_console(self, player):
        # This is the console help command display.
        readout("", "Get Minecraft help.",
                separator="help (no slash) - ", pad=0,
                usereadline=self.use_readline, player=player)
        readout("/reload", "Reload Wrapper.py plugins.",
                usereadline=self.use_readline, player=player)
        readout("/plugins", "Lists Wrapper.py plugins.",
                usereadline=self.use_readline, player=player)
        readout("/update-wrapper",
                "Checks for new Wrapper.py updates, and will install\n"
                "them automatically if one is available.",
                usereadline=self.use_readline, player=player)
        readout("/stop",
                "Stop the minecraft server without"
                " auto-restarting and without\n"
                "                  shuttingdown Wrapper.py.",
                usereadline=self.use_readline, player=player)
        readout("/start", "Start the minecraft server.",
                usereadline=self.use_readline, player=player)
        readout("/restart", "Restarts the minecraft server.",
                usereadline=self.use_readline, player=player)
        readout("/halt", "Shutdown Wrapper.py completely.",
                usereadline=self.use_readline, player=player)
        readout("/cm [seconds]",
                "Mute server output (Wrapper console"
                " logging still happens)",
                usereadline=self.use_readline, player=player)
        readout("/kill", "Force kill the server without saving.",
                usereadline=self.use_readline, player=player)
        readout("/freeze",
                "Temporarily locks the server up"
                " until /unfreeze is executed\n"
                "                  (Only works on *NIX servers).",
                usereadline=self.use_readline, player=player)
        readout("/unfreeze", "Unlocks a frozen state server"
                             " (Only works on *NIX servers).",
                usereadline=self.use_readline, player=player)
        readout("/mem", "Get memory usage of the server"
                        " (Only works on *NIX servers).",
                usereadline=self.use_readline, player=player)
        readout("/raw [command]",
                "Send command to the Minecraft"
                " Server. Useful for Forge\n"
                "                  commands like '/fml confirm'.",
                usereadline=self.use_readline, player=player)
        readout("/password",
                "run `/password help` for more...)",
                usereadline=self.use_readline, player=player)
        readout("/perms", "/perms for more...)",
                usereadline=self.use_readline, player=player)
        readout("/config", "Change wrapper.properties (type"
                           " /config help for more..)",
                usereadline=self.use_readline, player=player)
        readout("/version", self.getbuildstring(),
                usereadline=self.use_readline, player=player)
        readout("/entity",
                "Work with entities (run /entity for more...)",
                usereadline=self.use_readline, player=player)
        readout("/bans", "Display the ban help page.",
                usereadline=self.use_readline, player=player)

    def _show_help_bans(self, player):
        # ban commands help.
        if not self.proxymode:
            readout(
                "ERROR - ",
                "Wrapper proxy-mode bans are not enabled "
                "(proxy mode is not on).", separator="",
                pad=10,
                usereadline=self.use_readline, player=player)
            return

        readout(
            "",
            "Bans - To use the server's versions, do not type a slash.",
            separator="", pad=5,
            usereadline=self.use_readline, player=player)
        readout(
            "", "", separator="-----1.7.6 and later ban commands-----",
            pad=10,
            usereadline=self.use_readline, player=player)
        readout(
            "/ban",
            " - Ban a player. Specifying h:<hours> or d:<days>"
            " creates a temp ban.",
            separator="<name> [reason..] [d:<days>/h:<hours>] ",
            pad=12,
            usereadline=self.use_readline, player=player)
        readout(
            "/ban-ip",
            " - Ban an IP address. Reason and days (d:) are optional.",
            separator="<ip> [<reason..> <d:<number of days>] ", pad=12,
            usereadline=self.use_readline, player=player)
        readout(
            "/pardon",
            " - pardon a player. Default is byuuidonly.  To unban a"
            "specific name (without checking uuid), use"
            " `pardon <player> False`",
            separator="<player> [byuuidonly(true/false)]", pad=12,
            usereadline=self.use_readline, player=player)
        readout(
            "/pardon-ip", " - Pardon an IP address.",
            separator="<address> ", pad=12,
            usereadline=self.use_readline, player=player)
        readout(
            "/banlist",
            " - search and display the banlist (warning -"
            " displays on single page!)",
            separator="[players|ips] [searchtext] ", pad=12,
            usereadline=self.use_readline, player=player)


class HaltSig(object):
    """
    HaltSig is simply a sort of dummy class created for the
    proxy.  proxy expects this object with a self.halt property
    that tells proxy to shutdown.  The caller maintains control
    of the Haltsig object and uses it to signal the proxy to
    shut down.  The caller will import this class, instantiate
    it, and then pass the object to proxy as the argument for
    termsignal."""
    def __init__(self):
        self.halt = False
