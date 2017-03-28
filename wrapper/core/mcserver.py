# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from __future__ import print_function

from api.helpers import getargs, getargsafter, get_int, set_item
from api.helpers import processcolorcodes, chattocolorcodes
from api.helpers import getjsonfile, getfileaslines, config_to_dict_read

from api.base import API
from api.player import Player
from api.world import World
from api.entity import EntityControl

from core.exceptions import UnsupportedOSException, InvalidServerStartedError

import time
import threading
import subprocess
import os
import json
import ctypes
import platform
import base64

try:
    import resource
except ImportError:
    resource = False

OFF = 0  # this is the start mode.
STARTING = 1
STARTED = 2
STOPPING = 3
FROZEN = 4


# noinspection PyBroadException,PyUnusedLocal
class MCServer(object):

    def __init__(self, wrapper):
        self.log = wrapper.log
        self.config = wrapper.config
        self.encoding = self.config["General"]["encoding"]
        self.serverpath = self.config["General"]["server-directory"]

        self.stop_message = self.config["Misc"]["stop-message"]
        self.reboot_message = self.config["Misc"]["reboot-message"]
        self.restart_message = self.config["Misc"]["default-restart-message"]

        self.reboot_minutes = self.config[
            "General"]["timed-reboot-minutes"]
        self.reboot_warning_minutes = self.config[
            "General"]["timed-reboot-warning-minutes"]

        # These will be used to auto-detect the number of prepend
        # items in the server output.
        self.prepends_offset = 0

        self.wrapper = wrapper
        commargs = self.config["General"]["command"].split(" ")
        self.args = []

        for part in commargs:
            if part[-4:] == ".jar":
                self.args.append("%s/%s" % (self.serverpath, part))
            else:
                self.args.append(part)

        self.api = API(wrapper, "Server", internal=True)

        if "ServerStarted" not in self.wrapper.storage:
            self._toggle_server_started(False)

        self.state = OFF
        self.bootTime = time.time()
        # False/True - whether server will attempt boot
        self.boot_server = self.wrapper.storage["ServerStarted"]
        # whether a stopped server tries rebooting
        self.server_autorestart = self.config["General"]["auto-restart"]
        self.proc = None
        self.rebootWarnings = 0
        self.lastsizepoll = 0
        self.console_output_data = []
        self.spammy_stuff = ["found nothing", "vehicle of", "Wrong location!",
                             "Tried to add entity"]
        self.server_muted = False
        self.queued_lines = []
        self.server_stalled = False
        self.deathprefixes = ["fell", "was", "drowned", "blew", "walked",
                              "went", "burned", "hit", "tried", "died", "got",
                              "starved", "suffocated", "withered", "shot"]

        if not self.wrapper.storage["ServerStarted"]:
            self.log.warning(
                "NOTE: Server was in 'STOP' state last time  Wrapper.py was"
                " running. To start the server, run /start.")

        # Server Information
        self.players = {}
        self.player_eids = {}
        self.worldname = None
        self.worldSize = 0
        self.maxPlayers = 20
        # -1 until proxy mode checks the server's MOTD on boot
        self.protocolVersion = -1
        # this is string name of the version, collected by console output
        self.version = None
        # a comparable number = x0y0z, where x, y, z = release,
        #  major, minor, of version.
        self.version_compute = 0
        # this port should be hidden from outside traffic.
        self.server_port = "25564"

        self.world = None
        self.entity_control = None
        self.motd = None
        # -1 until a player logs on and server sends a time update
        self.timeofday = -1
        self.onlineMode = True
        self.serverIcon = None

        # get OPs
        self.ownernames = {}
        self.operator_list = []
        self.refresh_ops()

        self.properties = {}

        # This will be redone on server start. However, it
        # has to be done immediately to get worldname; otherwise a
        # "None" folder gets created in the server folder.
        self.reloadproperties()

        # don't reg. an unused event.  The timer still is running, we
        #  just have not cluttered the events holder with another
        #  registration item.
        if self.config["General"]["timed-reboot"] or self.config[
                "Web"]["web-enabled"]:
            self.api.registerEvent("timer.second", self.eachsecond)

    def init(self):
        """ Start up the listen threads for reading server console
        output.
        """
        capturethread = threading.Thread(target=self.__stdout__, args=())
        capturethread.daemon = True
        capturethread.start()

        capturethread = threading.Thread(target=self.__stderr__, args=())
        capturethread.daemon = True
        capturethread.start()

    def __del__(self):
        self.state = 0

    def accepteula(self):

        if os.path.isfile("%s/eula.txt" % self.serverpath):
            self.log.debug("Checking EULA agreement...")
            with open("%s/eula.txt" % self.serverpath) as f:
                eula = f.read()

            # if forced, should be at info level since acceptance
            # is a legal matter.
            if "eula=false" in eula:
                self.log.warning(
                    "EULA agreement was not accepted, accepting on"
                    " your behalf...")
                set_item("eula", "true", "eula.txt", self.serverpath)

            self.log.debug("EULA agreement has been accepted.")
            return True
        else:
            return False

    def handle_server(self):
        """ Function that handles booting the server, parsing console
        output, and such.
        """
        trystart = 0
        while not self.wrapper.halt:
            trystart += 1
            self.proc = None

            # endless loop for not booting the server (while still
            # allowing handle to run).
            if not self.boot_server:
                time.sleep(0.2)
                trystart = 0
                continue

            self.changestate(STARTING)
            self.log.info("Starting server...")
            self.reloadproperties()

            # stuff I was trying to get colorized output to come through
            # for non-vanilla servers.
            command = '-fdiagnostics-color=always'
            self.args.append(command)
            command2 = self.args
            # print("args:\n%s\n" % command2)

            self.proc = subprocess.Popen(
                command2, cwd=self.serverpath, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                universal_newlines=True)
            self.players = {}
            self.accepteula()  # Auto accept eula

            if self.proc.poll() is None and trystart > 3:
                self.log.error(
                    "Could not start server.  check your server.properties,"
                    " wrapper.properties and this your startup 'command'"
                    " from wrapper.properties:\n'%s'", " ".join(self.args))
                self.changestate(OFF)
                # halt wrapper
                self.wrapper.halt = True
                # exit server_handle
                break

            # The server loop
            while True:
                # Loop runs continously as long as server console is running
                time.sleep(0.1)
                if self.proc.poll() is not None:
                    self.changestate(OFF)
                    trystart = 0
                    self.boot_server = self.server_autorestart
                    # break back out to `while not self.wrapper.halt:` loop
                    # to (possibly) connect to server again.
                    break

                # is is only reading server console output
                for line in self.console_output_data:
                    try:
                        self.readconsole(line.replace("\r", ""))
                    except Exception as e:
                        self.log.exception(e)
                self.console_output_data = []

        # code ends here on wrapper.halt and execution returns to
        # the end of wrapper.start()

    def _toggle_server_started(self, server_started=True):
        self.wrapper.storage["ServerStarted"] = server_started
        self.wrapper.wrapper_storage.save()

    def start(self):
        """
        Start the Minecraft server
        """
        self.server_autorestart = self.config["General"]["auto-restart"]
        if self.state in (STARTED, STARTING):
            self.log.warning("The server is already running!")
            return
        if not self.boot_server:
            self.boot_server = True
        else:
            self.handle_server()

        self._toggle_server_started()

    def restart(self, reason=""):
        """Restart the Minecraft server, and kick people with the
        specified reason
        """
        if reason == "":
            reason = self.restart_message
        if self.state in (STOPPING, OFF):
            self.log.warning(
                "The server is not already running... Just use '/start'.")
            return
        self.stop(reason)

    def stop(self, reason="", restart_the_server=True):
        """Stop the Minecraft server from an automatic process.  Allow
        it to restart by default.
        """
        self.log.info("Stopping Minecraft server with reason: %s", reason)
        self.changestate(STOPPING, reason)
        for player in self.players:
            self.console("kick %s %s" % (player, reason))
        self.console("stop")

        # False will allow this loop to run with no server (and
        # reboot if permitted).
        self.boot_server = restart_the_server

    def stop_server_command(self, reason="", restart_the_server=False):
        """
        Stop the Minecraft server (as a command).  By default, do not restart.
        """
        if reason == "":
            reason = self.stop_message
        if self.state == OFF:
            self.log.warning("The server is not running... :?")
            return
        if self.state == FROZEN:
            self.log.warning("The server is currently frozen.\n"
                             "To stop it, you must /unfreeze it first")
            return
        self.server_autorestart = False
        self.stop(reason, restart_the_server)
        self._toggle_server_started(restart_the_server)

    def kill(self, reason="Killing Server"):
        """Forcefully kill the server. It will auto-restart if set
        in the configuration file.
        """
        if self.state in (STOPPING, OFF):
            self.log.warning("The server is already dead, my friend...")
            return
        self.log.info("Killing Minecraft server with reason: %s", reason)
        self.changestate(OFF, reason)
        self.proc.kill()

    def freeze(self, reason="Server is now frozen. You may disconnect."):
        """Freeze the server with `kill -STOP`. Can be used to
        stop the server in an emergency without shutting it down,
        so it doesn't write corrupted data - e.g. if the disk is
        full, you can freeze the server, free up some disk space,
        and then unfreeze 'reason' argument is printed in the
        chat for all currently-connected players, unless you
        specify None.  This command currently only works for
        *NIX based systems.
        """
        if self.state != OFF:
            if os.name == "posix":
                self.log.info("Freezing server with reason: %s", reason)
                self.broadcast("&c%s" % reason)
                time.sleep(0.5)
                self.changestate(FROZEN)
                os.system("kill -STOP %d" % self.proc.pid)
            else:
                raise UnsupportedOSException(
                    "Your current OS (%s) does not support this"
                    " command at this time." % os.name)
        else:
            raise InvalidServerStartedError(
                "Server is not started. You may run '/start' to boot it up.")

    def unfreeze(self):
        """Unfreeze the server with `kill -CONT`. Counterpart
        to .freeze(reason) This command currently only works
        for *NIX based systems.
        """
        if self.state != OFF:
            if os.name == "posix":
                self.log.info("Unfreezing server (ignore any"
                              " messages to type /start)...")
                self.broadcast("&aServer unfrozen.")
                self.changestate(STARTED)
                os.system("kill -CONT %d" % self.proc.pid)
            else:
                raise UnsupportedOSException(
                    "Your current OS (%s) does not support this command"
                    " at this time." % os.name)
        else:
            raise InvalidServerStartedError(
                "Server is not started. Please run '/start' to boot it up.")

    def broadcast(self, message, who="@a"):
        """Broadcasts the specified message to all clients
        connected. message can be a JSON chat object, or a
        string with formatting codes using the § as a prefix.
        """
        if isinstance(message, dict):
            if self.version_compute < 10700:
                self.console("say %s %s" % (who, chattocolorcodes(message)))
            else:
                encoding = self.wrapper.encoding
                self.console("tellraw %s %s" % (
                    who, json.dumps(message, ensure_ascii=False)))
        else:
            if self.version_compute < 10700:
                temp = processcolorcodes(message)
                self.console("say %s %s" % (
                    who, chattocolorcodes(json.loads(temp))))
            else:
                self.console("tellraw %s %s" % (
                    who, processcolorcodes(message)))

    def login(self, username, eid, location):
        """Called when a player logs in."""

        # place to store EID if proxy is not fully connected yet.
        self.player_eids[username] = [eid, location]
        if username not in self.players:
            self.players[username] = Player(username, self.wrapper)
        if self.wrapper.proxy:
            playerclient = self.getplayer(username).getClient()
            if playerclient:
                playerclient.server_connection.eid = eid
                playerclient.position = location
        self.players[username].loginposition = self.player_eids[username][1]
        self.wrapper.events.callevent(
            "player.login",
            {"player": self.getplayer(username)})

    def logout(self, players_name):
        """Called when a player logs out."""

        # self.wrapper.callEvent(
        #    "player.logout", {"player": self.getPlayer(username)})
        self.wrapper.events.callevent(
            "player.logout", self.getplayer(players_name))
        if self.wrapper.proxy:
            self.wrapper.proxy.removestaleclients()

        # remove a hub player or not??
        if players_name in self.players:
            self.players[players_name].abort = True
            del self.players[players_name]

    def getplayer(self, username):
        """Returns a player object with the specified name, or
        False if the user is not logged in/doesn't exist.
        """
        if username in self.players:
            return self.players[username]
        return False

    def reloadproperties(self):
        # Load server icon
        if os.path.exists("%s/server-icon.png" % self.serverpath):
            with open("%s/server-icon.png" % self.serverpath, "rb") as f:
                theicon = f.read()
                iconencoded = base64.standard_b64encode(theicon)
                self.serverIcon = b"data:image/png;base64," + iconencoded

        # Read server.properties and extract some information out of it
        # the PY3.5 ConfigParser seems broken.  This way was much more
        # straightforward and works in both PY2 and PY3
        self.properties = config_to_dict_read(
            "server.properties", self.serverpath)

        if self.properties == {}:
            self.log.warning("File 'server.properties' not found.")
            return False

        if "level-name" in self.properties:
            self.worldname = self.properties["level-name"]
        else:
            self.log.warning("No 'level-name=(worldname)' was"
                             " found in the server.properties.")
            return False
        self.motd = self.properties["motd"]
        if "max-players" in self.properties:
            self.maxPlayers = self.properties["max-players"]
        else:
            self.log.warning(
                "No 'max-players=(count)' was found in the"
                " server.properties. The default of '20' will be used.")
            self.maxPlayers = 20
        self.onlineMode = self.properties["online-mode"]

    def console(self, command):
        """Execute a console command on the server."""
        if self.state in (STARTING, STARTED, STOPPING) and self.proc:
            self.proc.stdin.write("%s\n" % command)
            self.proc.stdin.flush()
        else:
            self.log.debug("Attempted to run console command"
                           " '%s' but the Server is not started.", command)

    def changestate(self, state, reason=None):
        """Change the boot state indicator of the server, with a
        reason message.
        """
        self.state = state
        if self.state == OFF:
            self.wrapper.events.callevent(
                "server.stopped", {"reason": reason})
        elif self.state == STARTING:
            self.wrapper.events.callevent(
                "server.starting", {"reason": reason})
        elif self.state == STARTED:
            self.wrapper.events.callevent(
                "server.started", {"reason": reason})
        elif self.state == STOPPING:
            self.wrapper.events.callevent(
                "server.stopping", {"reason": reason})
        self.wrapper.events.callevent(
            "server.state", {"state": state, "reason": reason})

    def getservertype(self):
        if "spigot" in self.config["General"]["command"].lower():
            return "spigot"
        elif "bukkit" in self.config["General"]["command"].lower():
            return "bukkit"
        else:
            return "vanilla"

    def server_reload(self):
        """This is not used yet.. intended to restart a server
        without kicking players restarts the server quickly.
        Wrapper "auto-restart" must be set to True. If wrapper
        is in proxy mode, it will reconnect all clients to the
        serverconnection.
        """
        if self.state in (STOPPING, OFF):
            self.log.warning(
                "The server is not already running... Just use '/start'.")
            return
        if self.wrapper.proxymode:
            # discover who all is playing and store that knowledge

            # tell the serverconnection to stop processing play packets
            self.server_stalled = True

        # stop the server.

        # Call events to "do stuff" while server is down (write
        # whilelists, OP files, server properties, etc)

        # restart the server.

        if self.wrapper.proxymode:
            pass
            # once server is back up,  Reconnect stalled/idle
            # clients back to the serverconnection process.

            # Do I need to create a new serverconnection,
            # or can the old one be tricked into continuing??

        self.stop_server_command()

    def __stdout__(self):
        """handles server output, not lines typed in console."""
        while not self.wrapper.halt:
            # noinspection PyBroadException,PyUnusedLocal

            # this reads the line and puts the line in the
            # 'self.data' buffer for processing by
            # readconsole() (inside handle_server)
            try:
                data = self.proc.stdout.readline()
                for line in data.split("\n"):
                    if len(line) < 1:
                        continue
                    self.console_output_data.append(line)
            except Exception as e:
                time.sleep(0.1)
                continue

    def __stderr__(self):
        """like __stdout__, handles server output (not lines
        typed in console)."""
        while not self.wrapper.halt:
            try:
                data = self.proc.stderr.readline()
                if len(data) > 0:
                    for line in data.split("\n"):
                        self.console_output_data.append(line.replace("\r", ""))
            except Exception as e:
                time.sleep(0.1)
                continue

    def read_ops_file(self, read_super_ops=True):
        """Keep a list of ops in the server instance to stop
        reading the disk for it.
        :rtype: Dictionary
        """
        ops = False
        # (4 = PROTOCOL_1_7 ) - 1.7.6 or greater use ops.json
        if self.protocolVersion > 4:
            ops = getjsonfile("ops", self.serverpath, encodedas=self.encoding)
        if not ops:
            # try for an old "ops.txt" file instead.
            ops = []
            opstext = getfileaslines("ops.txt", self.serverpath)
            if not opstext:
                return False
            for op in opstext:
                # create a 'fake' ops list from the old pre-1.8
                # text line name list notice that the level (an
                # option not the old list) is set to 1 This will
                # pass as true, but if the plugin is also
                # checking op-levels, it may not pass truth.
                indivop = {"uuid": op,
                           "name": op,
                           "level": 1}
                ops.append(indivop)

        # Grant "owner" an op level above 4. required for some wrapper commands
        if read_super_ops:
            for eachop in ops:
                if eachop["name"] in self.ownernames:
                    eachop["level"] = self.ownernames[eachop["name"]]
        return ops

    def refresh_ops(self, read_super_ops=True):
        self.ownernames = config_to_dict_read("superops.txt", ".")
        if self.ownernames == {}:
            sample = "<op_player_1>=10\n<op_player_2>=9"
            with open("superops.txt", "w") as f:
                f.write(sample)
        self.operator_list = self.read_ops_file(read_super_ops)

    def getmemoryusage(self):
        """Returns allocated memory in bytes. This command
        currently only works for *NIX based systems.
        """
        if not resource or not os.name == "posix" or self.proc is None:
            raise UnsupportedOSException(
                "Your current OS (%s) does not support"
                " this command at this time." % os.name)
        try:
            with open("/proc/%d/statm" % self.proc.pid) as f:
                getbytes = int(f.read().split(" ")[1]) * resource.getpagesize()
            return getbytes
        except Exception as e:
            raise e

    @staticmethod
    def getstorageavailable(folder):
        """Returns the disk space for the working directory
        in bytes.
        """
        if platform.system() == "Windows":
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(folder), None, None,
                ctypes.pointer(free_bytes))
            return free_bytes.value
        else:
            st = os.statvfs(folder)
            return st.f_bavail * st.f_frsize

    @staticmethod
    def stripspecial(text):
        a = ""
        it = iter(range(len(text)))
        for i in it:
            char = text[i]
            if char == "\xc2":
                try:
                    next(it)
                    next(it)
                except Exception as e:
                    pass
            else:
                a += char
        return a

    def readconsole(self, buff):
        """Internally-used function that parses a particular
        console line.
        """
        if not self.wrapper.events.callevent(
                "server.consoleMessage", {"message": buff}):
            return False

        if len(buff) < 1:
            return
        # Standardize the line to only include the text (removing
        # time and log pre-pends)
        line_words = buff.split(' ')[self.prepends_offset:]

        # find the actual offset is where server output line
        # starts (minus date/time and info stamps).
        # .. and load the proper ops file
        if "Starting minecraft server version" in buff and \
                self.prepends_offset == 0:

            for place in range(len(line_words)-1):
                self.prepends_offset = place
                if line_words[place] == "Starting":
                    break

            line_words = buff.split(' ')[self.prepends_offset:]
            self.version = getargs(line_words, 4)
            semantics = self.version.split(".")
            release = get_int(getargs(semantics, 0))
            major = get_int(getargs(semantics, 1))
            minor = get_int(getargs(semantics, 2))
            self.version_compute = minor + (major * 100) + (release * 10000)

            # 1.7.6 (protocol 5) is the cutoff where ops.txt became ops.json
            if self.version_compute > 10705 and self.protocolVersion < 0:
                self.protocolVersion = 5
            self.refresh_ops()

        if len(line_words) < 1:
            return

        # the server attempted to print a blank line
        if len(line_words[0]) < 1:
            print('')
            return

        # parse or modify the server output section
        #
        #

        # Over-ride OP help console display
        if "/op <player>" in buff:
            new_usage = "player> [-s SUPER-OP] [-o OFFLINE] [-l <level>]"
            message = buff.replace("player>", new_usage)
            buff = message

        if "While this makes the game possible to play" in buff:
            prefix = " ".join(buff.split(' ')[:self.prepends_offset])

            if not self.wrapper.wrapper_onlinemode:
                message = (
                    "%s Since you are running Wrapper in OFFLINE mode, THIS "
                    "COULD BE SERIOUS!\n%s Wrapper is not handling any"
                    " authenication.\n%s This is only ok if this wrapper "
                    "is not accessible from either port %s or port %s"
                    " (I.e., this wrapper is a multiworld for a hub server, or"
                    " you are doing your own authorization via a plugin)." % (
                        prefix, prefix, prefix,
                        self.server_port, self.wrapper.proxy.proxy_port))
            else:
                message = (
                    "%s Since you are running Wrapper in proxy mode, this"
                    " should be ok because Wrapper is handling the"
                    " authenication, PROVIDED no one can access port"
                    " %s from outside your network." % (
                        prefix, self.server_port))

            if self.wrapper.proxymode:
                buff = message

        # check for server console spam before printing to wrapper console
        server_spaming = False
        for things in self.spammy_stuff:
            if things in buff:
                server_spaming = True

        # server_spaming setting does not stop it from being parsed below.
        if not server_spaming:
            if not self.server_muted:
                self.wrapper.write_stdout(buff, "server")
            else:
                self.queued_lines.append(buff)

        # region server console parsing section

        # read port of server
        if "Starting Minecraft server" in buff:
            self.server_port = get_int(buff.split('on *:')[1])

        # confirm server start
        elif "Done (" in buff:
            self._toggle_server_started()
            self.changestate(STARTED)
            self.log.info("Server started")
            self.bootTime = time.time()

        # Getting world name
        elif "Preparing level" in buff:
            self.worldname = getargs(line_words, 2).replace('"', "")
            self.world = World(self.worldname, self)
            if self.wrapper.proxymode:
                self.entity_control = EntityControl(self)
        # Player Message
        if getargs(line_words, 0)[0] == "<":
            name = self.stripspecial(getargs(line_words, 0)[1:-1])
            message = self.stripspecial(getargsafter(line_words, 1))
            original = getargsafter(line_words, 0)
            self.wrapper.events.callevent("player.message", {
                "player": self.getplayer(name),
                "message": message,
                "original": original
            })

        # Player Login
        elif getargs(line_words, 1) == "logged":
            name = self.stripspecial(
                getargs(line_words, 0)[0:getargs(line_words, 0).find("[")])
            eid = get_int(getargs(line_words, 6))
            locationtext = getargs(buff.split(" ("), 1)[:-1].split(", ")
            location = get_int(
                float(locationtext[0])), get_int(
                float(locationtext[1])), get_int(
                float(locationtext[2]))
            self.login(name, eid, location)

        # Player Logout
        elif "lost connection" in buff:
            name = getargs(line_words, 0)
            self.logout(name)

        # player action
        elif getargs(line_words, 0) == "*":
            name = self.stripspecial(getargs(line_words, 1))
            message = self.stripspecial(getargsafter(line_words, 2))
            self.wrapper.events.callevent("player.action", {
                "player": self.getplayer(name),
                "action": message
            })

        # Player Achievement
        elif "has just earned the achievement" in buff:
            name = self.stripspecial(getargs(line_words, 0))
            achievement = getargsafter(line_words, 6)
            self.wrapper.events.callevent("player.achievement", {
                "player": name,
                "achievement": achievement
            })

        # /say command
        elif getargs(
                line_words, 0)[0] == "[" and getargs(line_words, 0)[-1] == "]":
            if self.getservertype != "vanilla":
                # Unfortunately, Spigot and Bukkit output things
                # that conflict with this.
                return
            name = self.stripspecial(getargs(line_words, 0)[1:-1])
            message = self.stripspecial(getargsafter(line_words, 1))
            original = getargsafter(line_words, 0)
            self.wrapper.events.callevent("server.say", {
                "player": name,
                "message": message,
                "original": original
            })

        # Player Death
        elif getargs(line_words, 1) in self.deathprefixes:
            name = self.stripspecial(getargs(line_words, 0))
            self.wrapper.events.callevent("player.death", {
                "player": self.getplayer(name),
                "death": getargsafter(line_words, 1)
            })

        # server lagged
        elif "Can't keep up!" in buff:
            skipping_ticks = getargs(line_words, 17)
            self.wrapper.events.callevent("server.lagged", {
                "ticks": get_int(skipping_ticks)
            })

    # mcserver.py onsecond Event Handler
    def eachsecond(self, payload):
        if self.config["General"]["timed-reboot"]:
            if time.time() - self.bootTime > (self.reboot_minutes * 60):
                if self.config["General"]["timed-reboot-warning-minutes"] > 0:
                    if self.rebootWarnings <= self.reboot_warning_minutes:
                        l = (time.time()
                             - self.bootTime
                             - self.reboot_minutes * 60)
                        if l > self.rebootWarnings:
                            self.rebootWarnings += 1
                            if int(self.reboot_warning_minutes - l + 1) > 0:
                                self.broadcast(
                                    "&cServer will reboot in %d minute(s)!" %
                                    int(self.reboot_warning_minutes - l + 1))
                        return
                self.restart(self.reboot_message)
                self.bootTime = time.time()
                self.rebootWarnings = 0

        # only used by web management module
        if self.config["Web"]["web-enabled"]:
            if time.time() - self.lastsizepoll > 120:
                if self.worldname is None:
                    return True
                self.lastsizepoll = time.time()
                size = 0
                # os.scandir not in standard library on early py2.7.x systems
                for i in os.walk("%s/%s" % (self.serverpath, self.worldname)):
                    for f in os.listdir(i[0]):
                        size += os.path.getsize(os.path.join(i[0], f))
                self.worldSize = size
