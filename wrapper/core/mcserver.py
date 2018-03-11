# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from __future__ import print_function

from api.helpers import getargs, getargsafter, get_int, set_item
from api.helpers import processcolorcodes, chattocolorcodes
from api.helpers import getjsonfile, getfileaslines, config_to_dict_read

from api.base import API
from api.world import World
from api.player import Player

import time
import threading
import subprocess
import os
import json
import ctypes
import platform
import base64
import copy

try:
    import resource
except ImportError:
    resource = False

OFF = 0  # this is the start mode.
STARTING = 1
STARTED = 2
STOPPING = 3
FROZEN = 4
LOBBY = 4


# noinspection PyBroadException,PyUnusedLocal
class MCServer(object):

    def __init__(self, wrapper, servervitals):
        self.log = wrapper.log
        self.config = wrapper.config
        self.vitals = servervitals

        self.encoding = self.config["General"]["encoding"]
        self.stop_message = self.config["Misc"]["stop-message"]
        self.reboot_message = self.config["Misc"]["reboot-message"]
        self.restart_message = self.config["Misc"]["default-restart-message"]

        self.reboot_minutes = self.config["General"]["timed-reboot-minutes"]
        self.reboot_warn_minutes = self.config["General"]["timed-reboot-warning-minutes"]  # noqa

        # These will be used to auto-detect the number of prepend
        # items in the server output.
        self.prepends_offset = 0

        self.wrapper = wrapper
        commargs = self.config["General"]["command"].split(" ")
        self.args = []

        for part in commargs:
            if part[-4:] == ".jar":
                self.args.append("%s/%s" % (self.vitals.serverpath, part))
            else:
                self.args.append(part)

        self.api = API(wrapper, "Server", internal=True)

        if "ServerStarted" not in self.wrapper.storage:
            self._toggle_server_started(False)

        # False/True - whether server will attempt boot
        self.boot_server = self.wrapper.storage["ServerStarted"]
        # whether a stopped server tries rebooting
        self.server_autorestart = self.config["General"]["auto-restart"]
        self.proc = None
        self.lastsizepoll = 0
        self.console_output_data = []

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
        self.world = None

        # get OPs
        self.refresh_ops()

        # This will be redone on server start. However, it
        # has to be done immediately to get worldname; otherwise a
        # "None" folder gets created in the server folder.
        self.reloadproperties()

        # don't reg. an unused event.  The timer still is running, we
        #  just have not cluttered the events holder with another
        #  registration item.

        if self.config["General"]["timed-reboot"]:
            rb = threading.Thread(target=self.reboot_timer, args=())
            rb.daemon = True
            rb.start()

        if self.config["Web"]["web-enabled"]:
            wb = threading.Thread(target=self.eachsecond_web, args=())
            wb.daemon = True
            wb.start()

        # This event is used to allow proxy to make console commands via
        # callevent() without referencing mcserver.py code (the eventhandler
        # is passed as an argument to the proxy).
        self.api.registerEvent("proxy.console", self._console_event)

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
        self.vitals.state = 0

    def accepteula(self):

        if os.path.isfile("%s/eula.txt" % self.vitals.serverpath):
            self.log.debug("Checking EULA agreement...")
            with open("%s/eula.txt" % self.vitals.serverpath) as f:
                eula = f.read()

            # if forced, should be at info level since acceptance
            # is a legal matter.
            if "eula=false" in eula:
                self.log.warning(
                    "EULA agreement was not accepted, accepting on"
                    " your behalf...")
                set_item("eula", "true", "eula.txt", self.vitals.serverpath)

            self.log.debug("EULA agreement has been accepted.")
            return True
        else:
            return False

    def handle_server(self):
        """ Function that handles booting the server, parsing console
        output, and such.
        """
        trystart = 0
        while not self.wrapper.halt.halt:
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

            command = self.args
            self.proc = subprocess.Popen(
                command, cwd=self.vitals.serverpath, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                universal_newlines=True)
            self.wrapper.players = {}
            self.accepteula()  # Auto accept eula

            if self.proc.poll() is None and trystart > 3:
                self.log.error(
                    "Could not start server.  check your server.properties,"
                    " wrapper.properties and this your startup 'command'"
                    " from wrapper.properties:\n'%s'", " ".join(self.args))
                self.changestate(OFF)
                # halt wrapper
                self.wrapper.halt.halt = True
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
                    # break out to `while not self.wrapper.halt.halt:` loop
                    # to (possibly) connect to server again.
                    break

                # is is only reading server console output
                for line in self.console_output_data:
                    try:
                        self.readconsole(line.replace("\r", ""))
                    except Exception as e:
                        self.log.exception(e)
                self.console_output_data = []

        # code ends here on wrapper.halt.halt and execution returns to
        # the end of wrapper.start()

    def _toggle_server_started(self, server_started=True):
        self.wrapper.storage["ServerStarted"] = server_started
        self.wrapper.wrapper_storage.save()

    def start(self):
        """
        Start the Minecraft server
        """
        self.server_autorestart = self.config["General"]["auto-restart"]
        if self.vitals.state in (STARTED, STARTING):
            self.log.warning("The server is already running!")
            return
        if not self.boot_server:
            self.boot_server = True
        else:
            self.handle_server()

        self._toggle_server_started()

    def restart(self, reason=""):
        """Restart the Minecraft server, and kick people with the
        specified reason.  If server was already stopped, restart it.
        """
        if reason == "":
            reason = self.restart_message

        if self.vitals.state in (STOPPING, OFF):
            self.start()
            return
        self.doserversaving()
        self.stop(reason)

    def kick_players(self, reasontext):
        playerlist = copy.copy(self.vitals.players)
        for player in playerlist:
            self.kick_player(player, reasontext)

    def kick_player(self, player, reasontext):
        if self.wrapper.proxymode:
            try:
                playerclient = self.vitals.players[player].client
                playerclient.disconnect(reasontext)
            except AttributeError:
                self.log.warning(
                    "Proxy kick failed - Gould not get client %s.\n"
                    "I'll try using the console..", player)
                self.console("kick %s %s" % (player, reasontext))
            except KeyError:
                self.log.warning(
                    "Kick failed - No proxy player called %s", player)
            except Exception as e:
                self.log.warning(
                    "Kick failed - something else went wrong:"
                    " %s\n%s\n%s", player, e,)
        else:
            self.console("kick %s %s" % (player, reasontext))
            # this sleep is here for Spigot McBans reasons/compatibility.
            time.sleep(2)

    def stop(self, reason="", restart_the_server=True):
        """Stop the Minecraft server from an automatic process.  Allow
        it to restart by default.
        """
        self.doserversaving()
        self.log.info("Stopping Minecraft server with reason: %s", reason)

        self.kick_players(reason)

        self.changestate(STOPPING, reason)
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
        if self.vitals.state == OFF:
            self.log.warning("The server is not running... :?")
            return
        if self.vitals.state == FROZEN:
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
        if self.vitals.state in (STOPPING, OFF):
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
        if self.vitals.state != OFF:
            if os.name == "posix":
                self.log.info("Freezing server with reason: %s", reason)
                self.broadcast("&c%s" % reason)
                time.sleep(0.5)
                self.changestate(FROZEN)
                os.system("kill -STOP %d" % self.proc.pid)
            else:
                raise OSError(
                    "Your current OS (%s) does not support this"
                    " command at this time." % os.name)
        else:
            raise EnvironmentError(
                "Server is not started. You may run '/start' to boot it up.")

    def unfreeze(self):
        """Unfreeze the server with `kill -CONT`. Counterpart
        to .freeze(reason) This command currently only works
        for *NIX based systems.
        """
        if self.vitals.state != OFF:
            if os.name == "posix":
                self.log.info("Unfreezing server (ignore any"
                              " messages to type /start)...")
                self.broadcast("&aServer unfrozen.")
                self.changestate(STARTED)
                os.system("kill -CONT %d" % self.proc.pid)
            else:
                raise OSError(
                    "Your current OS (%s) does not support this command"
                    " at this time." % os.name)
        else:
            raise EnvironmentError(
                "Server is not started. Please run '/start' to boot it up.")

    def broadcast(self, message, who="@a"):
        """Broadcasts the specified message to all clients
        connected. message can be a JSON chat object, or a
        string with formatting codes using the § as a prefix.
        """
        if isinstance(message, dict):
            if self.vitals.version_compute < 10700:
                self.console("say %s %s" % (who, chattocolorcodes(message)))
            else:
                encoding = self.wrapper.encoding
                self.console("tellraw %s %s" % (
                    who, json.dumps(message, ensure_ascii=False)))
        else:
            if self.vitals.version_compute < 10700:
                temp = processcolorcodes(message)
                self.console("say %s %s" % (
                    who, chattocolorcodes(json.loads(temp))))
            else:
                self.console("tellraw %s %s" % (
                    who, processcolorcodes(message)))

    def login(self, username, servereid, position, ipaddr):
        """Called when a player logs in."""

        if username not in self.vitals.players:
            self.vitals.players[username] = Player(username, self.wrapper)
        # store EID if proxy is not fully connected yet (or is not enabled).
        self.vitals.players[username].playereid = servereid
        self.vitals.players[username].loginposition = position
        if self.vitals.players[username].ipaddress == "127.0.0.0":
            self.vitals.players[username].ipaddress = ipaddr

        if self.wrapper.proxy and self.vitals.players[username].client:
            self.vitals.players[username].client.server_eid = servereid
            self.vitals.players[username].client.position = position

        # activate backup status
        self.wrapper.backups.idle = False
        self.wrapper.events.callevent(
            "player.login",
            {"player": self.getplayer(username),
             "playername": username},
            abortable=False
        )

        """ eventdoc
            <group> core/mcserver.py <group>

            <description> When player logs into the java MC server.
            <description>

            <abortable> No <abortable>

            <comments> All events in the core/mcserver.py group are collected
            from the console output, do not require proxy mode, and 
            therefore, also, cannot be aborted.
            <comments>

            <payload>
            "player": player object (if object available -could be False if not)
            "playername": user name of player (string)
            <payload>

        """

    def logout(self, players_name):
        """Called when a player logs out."""

        if players_name in self.vitals.players:
            self.wrapper.events.callevent(
                "player.logout", {"player": self.getplayer(players_name),
                                  "playername": players_name},
                abortable=True
            )
            """ eventdoc
                <group> core/mcserver.py <group>

                <description> When player logs out of the java MC server.
                <description>

                <abortable> No - but This will pause long enough for you to deal with the playerobject. <abortable>

                <comments> All events in the core/mcserver.py group are collected
                from the console output, do not require proxy mode, and 
                therefore, also, cannot be aborted.
                <comments>

                <payload>
                "player": player object (if object available -could be False if not)
                "playername": user name of player (string)
                <payload>

            """  # noqa
            if self.vitals.players[players_name].client.state != LOBBY:
                self.vitals.players[players_name].abort = True
                del self.vitals.players[players_name]
        if len(self.vitals.players) == 0:
            self.wrapper.backups.idle = True

    def getplayer(self, username):
        """Returns a player object with the specified name, or
        False if the user is not logged in/doesn't exist.

        this getplayer only deals with local players on this server.
        api.minecraft.getPlayer will deal in all players, including
        those in proxy and/or other hub servers.
        """
        if username in self.vitals.players:
            player = self.vitals.players[username]
            if player.client.state != LOBBY:
                return player
        return False

    def reloadproperties(self):
        # Read server.properties and extract some information out of it
        # the PY3.5 ConfigParser seems broken.  This way was much more
        # straightforward and works in both PY2 and PY3

        # Load server icon
        if os.path.exists("%s/server-icon.png" % self.vitals.serverpath):
            with open("%s/server-icon.png" % self.vitals.serverpath, "rb") as f:
                theicon = f.read()
                iconencoded = base64.standard_b64encode(theicon)
                self.vitals.serverIcon = b"data:image/png;base64," + iconencoded

        self.vitals.properties = config_to_dict_read(
            "server.properties", self.vitals.serverpath)

        if self.vitals.properties == {}:
            self.log.warning("File 'server.properties' not found.")
            return False

        if "level-name" in self.vitals.properties:
            self.vitals.worldname = self.vitals.properties["level-name"]
        else:
            self.log.warning("No 'level-name=(worldname)' was"
                             " found in the server.properties.")
            return False
        self.vitals.motd = self.vitals.properties["motd"]
        if "max-players" in self.vitals.properties:
            self.vitals.maxPlayers = self.vitals.properties["max-players"]
        else:
            self.log.warning(
                "No 'max-players=(count)' was found in the"
                " server.properties. The default of '20' will be used.")
            self.vitals.maxPlayers = 20
        self.vitals.onlineMode = self.vitals.properties["online-mode"]

    def console(self, command):
        """Execute a console command on the server."""
        if self.vitals.state in (STARTING, STARTED, STOPPING) and self.proc:
            self.proc.stdin.write("%s\n" % command)
            self.proc.stdin.flush()
        else:
            self.log.debug("Attempted to run console command"
                           " '%s' but the Server is not started.", command)

    def changestate(self, state, reason=None):
        """Change the boot state indicator of the server, with a
        reason message.
        """
        self.vitals.state = state
        if self.vitals.state == OFF:
            self.wrapper.events.callevent(
                "server.stopped", {"reason": reason}, abortable=False)
        elif self.vitals.state == STARTING:
            self.wrapper.events.callevent(
                "server.starting", {"reason": reason}, abortable=False)
        elif self.vitals.state == STARTED:
            self.wrapper.events.callevent(
                "server.started", {"reason": reason}, abortable=False)
        elif self.vitals.state == STOPPING:
            self.wrapper.events.callevent(
                "server.stopping", {"reason": reason}, abortable=False)
        self.wrapper.events.callevent(
            "server.state", {"state": state, "reason": reason}, abortable=False)

    def doserversaving(self, desiredstate=True):
        """
        :param desiredstate: True = turn serversaving on
                             False = turn serversaving off
        :return:

        Future expansion to allow config of server saving state glabally in
        config.  Plan to include a global config option for periodic or
        continuous server disk saving of the minecraft server.

        """
        if desiredstate:
            self.console("save-all flush")  # flush argument is required
            self.console("save-on")
        else:
            self.console("save-all flush")  # flush argument is required
            self.console("save-off")
        time.sleep(1)

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
        if self.vitals.state in (STOPPING, OFF):
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
        while not self.wrapper.halt.halt:
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
        while not self.wrapper.halt.halt:
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
        if self.vitals.protocolVersion > 4:
            ops = getjsonfile(
                "ops", self.vitals.serverpath, encodedas=self.encoding
            )
        if not ops:
            # try for an old "ops.txt" file instead.
            ops = []
            opstext = getfileaslines("ops.txt", self.vitals.serverpath)
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
                if eachop["name"] in self.vitals.ownernames:
                    eachop["level"] = self.vitals.ownernames[eachop["name"]]
        return ops

    def refresh_ops(self, read_super_ops=True):
        self.vitals.ownernames = config_to_dict_read("superops.txt", ".")
        if self.vitals.ownernames == {}:
            sample = "<op_player_1>=10\n<op_player_2>=9"
            with open("superops.txt", "w") as f:
                f.write(sample)
        self.vitals.operator_list = self.read_ops_file(read_super_ops)

    def getmemoryusage(self):
        """Returns allocated memory in bytes. This command
        currently only works for *NIX based systems.
        """
        if not resource or not os.name == "posix":
            raise OSError(
                "Your current OS (%s) does not support"
                " this command at this time." % os.name)
        if self.proc is None:
            self.log.debug("There is no running server to getmemoryusage().")
            return 0
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
        # not sure what this is actually removing...
        # this must be legacy code of some kind
        pass
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
            self.vitals.version = getargs(line_words, 4)
            semantics = self.vitals.version.split(".")
            release = get_int(getargs(semantics, 0))
            major = get_int(getargs(semantics, 1))
            minor = get_int(getargs(semantics, 2))
            self.vitals.version_compute = minor + (major * 100) + (release * 10000)  # noqa

            # 1.7.6 (protocol 5) is the cutoff where ops.txt became ops.json
            if self.vitals.version_compute > 10705 and self.vitals.protocolVersion < 0:  # noqa
                self.vitals.protocolVersion = 5
                self.wrapper.api.registerPermission("mc1.7.6", value=True)
            if self.vitals.version_compute < 10702 and self.wrapper.proxymode:
                self.log.warning("\nProxy mode cannot run because the "
                                 "server is a pre-Netty version:\n\n"
                                 "http://wiki.vg/Protocol_version_numbers"
                                 "#Versions_before_the_Netty_rewrite\n\n"
                                 "Server will continue in non-proxy mode.")
                self.wrapper.disable_proxymode()
                return

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
        if "/whitelist <on|off" in buff:
            new_usage = "/whitelist <on|off|list|add|remvove|reload|offline|online>"  # noqa
            message = new_usage
            buff = message

        if "While this makes the game possible to play" in buff:
            prefix = " ".join(buff.split(' ')[:self.prepends_offset])

            if not self.wrapper.wrapper_onlinemode:
                message = (
                    "%s Since you are running Wrapper in OFFLINE mode, THIS "
                    "COULD BE SERIOUS!\n%s Wrapper is not handling any"
                    " authentication.\n%s This is only ok if this wrapper "
                    "is not accessible from either port %s or port %s"
                    " (I.e., this wrapper is a multiworld for a hub server, or"
                    " you are doing your own authorization via a plugin)." % (
                        prefix, prefix, prefix,
                        self.vitals.server_port, self.wrapper.proxy.proxy_port))
            else:
                message = (
                    "%s Since you are running Wrapper in proxy mode, this"
                    " should be ok because Wrapper is handling the"
                    " authentication, PROVIDED no one can access port"
                    " %s from outside your network." % (
                        prefix, self.vitals.server_port))

            if self.wrapper.proxymode:
                buff = message

        # read port of server and display proxy port, if applicable
        if "Starting Minecraft server on" in buff:
            self.vitals.server_port = get_int(buff.split(':')[-1:][0])

        # check for server console spam before printing to wrapper console
        server_spaming = False
        for things in self.vitals.spammy_stuff:
            if things in buff:
                server_spaming = True

        # server_spaming setting does not stop it from being parsed below.
        if not server_spaming:
            if not self.server_muted:
                self.wrapper.write_stdout(buff, "server")
            else:
                self.queued_lines.append(buff)

        first_word = getargs(line_words, 0)
        second_word = getargs(line_words, 1)
        # be careful about how these elif's are handled!
        # confirm server start
        if "Done (" in buff:
            self._toggle_server_started()
            self.changestate(STARTED)
            self.log.info("Server started")
            if self.wrapper.proxymode:
                self.log.info("Proxy listening on *:%s", self.wrapper.proxy.proxy_port)  # noqa

        # Getting world name
        elif "Preparing level" in buff:
            self.vitals.worldname = getargs(line_words, 2).replace('"', "")
            self.world = World(self.vitals.worldname, self)

        # Player Message
        elif first_word[0] == "<":
            # get a name out of <name>
            name = self.stripspecial(first_word[1:-1])
            message = self.stripspecial(getargsafter(line_words, 1))
            original = getargsafter(line_words, 0)
            playerobj = self.getplayer(name)
            if playerobj:
                self.wrapper.events.callevent("player.message", {
                    "player": self.getplayer(name),
                    "message": message,
                    "original": original
                }, abortable=False)
                """ eventdoc
                    <group> core/mcserver.py <group>
    
                    <description> Player chat scrubbed from the console.
                    <description>
    
                    <abortable> No
                    <abortable>
    
                    <comments>
                    This event is triggered by console chat which has already been sent. 
                    This event returns the player object. if used in a string context, 
                    ("%s") it's repr (self.__str__) is self.username (no need to do 
                    str(player) or player.username in plugin code).
                    <comments>
    
                    <payload>
                    "player": playerobject (self.__str__ represents as player.username)
                    "message": <str> type - what the player said in chat. ('hello everyone')
                    "original": The original line of text from the console ('<mcplayer> hello everyone`)
                    <payload>
    
                """  # noqa
            else:
                self.log.debug("Console has chat from '%s', but wrapper has no "
                               "known logged-in player object by that name.", name)  # noqa
        # Player Login
        elif second_word == "logged":
            user_desc = first_word.split("[/")
            name = user_desc[0]
            ip_addr = user_desc[1].split(":")[0]
            eid = get_int(getargs(line_words, 6))
            locationtext = getargs(buff.split(" ("), 1)[:-1].split(", ")
            # spigot versus vanilla
            # SPIGOT - [12:13:19 INFO]: *******[/] logged in with entity id 123 at ([world]316.86789318152546, 67.12426603789697, -191.9069627257038)  # noqa
            # VANILLA - [23:24:34] [Server thread/INFO]: *******[/127.0.0.1:47434] logged in with entity id 149 at (46.29907483845001, 63.0, -270.1293488726086)  # noqa
            if len(locationtext[0].split("]")) > 1:
                x_c = get_int(float(locationtext[0].split("]")[1]))
            else:
                x_c = get_int(float(locationtext[0]))
            y_c = get_int(float(locationtext[1]))
            z_c = get_int(float(locationtext[2]))
            location = x_c, y_c, z_c

            self.login(name, eid, location, ip_addr)

        # Player Logout
        elif "lost connection" in buff:
            name = first_word
            self.logout(name)

        # player action
        elif first_word == "*":
            name = self.stripspecial(second_word)
            message = self.stripspecial(getargsafter(line_words, 2))
            self.wrapper.events.callevent("player.action", {
                "player": self.getplayer(name),
                "action": message
            }, abortable=False)

        # Player Achievement
        elif "has just earned the achievement" in buff:
            name = self.stripspecial(first_word)
            achievement = getargsafter(line_words, 6)
            self.wrapper.events.callevent("player.achievement", {
                "player": name,
                "achievement": achievement
            }, abortable=False)

        # /say command
        elif getargs(
                line_words, 0)[0] == "[" and first_word[-1] == "]":
            if self.getservertype != "vanilla":
                # Unfortunately, Spigot and Bukkit output things
                # that conflict with this.
                return
            name = self.stripspecial(first_word[1:-1])
            message = self.stripspecial(getargsafter(line_words, 1))
            original = getargsafter(line_words, 0)
            self.wrapper.events.callevent("server.say", {
                "player": name,
                "message": message,
                "original": original
            }, abortable=False)

        # Player Death
        elif second_word in self.deathprefixes:
            name = self.stripspecial(first_word)
            self.wrapper.events.callevent("player.death", {
                "player": self.getplayer(name),
                "death": getargsafter(line_words, 1)
            }, abortable=False)

        # server lagged
        elif "Can't keep up!" in buff:
            skipping_ticks = getargs(line_words, 17)
            self.wrapper.events.callevent("server.lagged", {
                "ticks": get_int(skipping_ticks)
            }, abortable=False)

        # player teleport
        elif second_word == "Teleported" and getargs(line_words, 3) == "to":
            playername = getargs(line_words, 2)
            # [SurestTexas00: Teleported SapperLeader to 48.49417131908783, 77.67081086259394, -279.88880690937475]  # noqa
            if playername in self.wrapper.servervitals.players:
                playerobj = self.getplayer(playername)
                playerobj._position = [
                    get_int(float(getargs(line_words, 4).split(",")[0])),
                    get_int(float(getargs(line_words, 5).split(",")[0])),
                    get_int(float(getargs(line_words, 6).split("]")[0])), 0, 0
                ]
                self.wrapper.events.callevent(
                    "player.teleport",
                    {"player": playerobj}, abortable=False)

                """ eventdoc
                    <group> core/mcserver.py <group>

                    <description> When player teleports.
                    <description>

                    <abortable> No <abortable>

                    <comments> driven from console message "Teleported ___ to ....".
                    <comments>

                    <payload>
                    "player": player object
                    <payload>

                """  # noqa
        elif first_word == "Teleported" and getargs(line_words, 2) == "to":
            playername = second_word
            # Teleported SurestTexas00 to 48.49417131908783, 77.67081086259394, -279.88880690937475  # noqa
            if playername in self.wrapper.servervitals.players:
                playerobj = self.getplayer(playername)
                playerobj._position = [
                    get_int(float(getargs(line_words, 3).split(",")[0])),
                    get_int(float(getargs(line_words, 4).split(",")[0])),
                    get_int(float(getargs(line_words, 5))), 0, 0
                ]
                self.wrapper.events.callevent(
                    "player.teleport",
                    {"player": playerobj}, abortable=False)

                """ eventdoc
                    <group> core/mcserver.py <group>
        
                    <description> When player teleports.
                    <description>
        
                    <abortable> No <abortable>
        
                    <comments> driven from console message "Teleported ___ to ....".
                    <comments>
        
                    <payload>
                    "player": player object
                    <payload>
        
                """  # noqa
    # mcserver.py onsecond Event Handlers
    def reboot_timer(self):
        rb_mins = self.reboot_minutes
        rb_mins_warn = self.config["General"]["timed-reboot-warning-minutes"]
        while not self.wrapper.halt.halt:
            time.sleep(1)
            timer = rb_mins - rb_mins_warn
            while self.vitals.state in (STARTED, STARTING):
                timer -= 1
                time.sleep(60)
                if timer > 0:
                    continue
                if timer + rb_mins_warn > 0:
                    if rb_mins_warn + timer > 1:
                        self.broadcast("&cServer will reboot in %d "
                                       "minutes!" % (rb_mins_warn + timer))
                    else:
                        self.broadcast("&cServer will reboot in %d "
                                       "minute!" % (rb_mins_warn + timer))
                        countdown = 59
                        timer -= 1
                        while countdown > 0:
                            time.sleep(1)
                            countdown -= 1
                            if countdown == 0:
                                if self.wrapper.backups_idle():
                                    self.restart(self.reboot_message)
                                else:
                                    self.broadcast(
                                        "&cBackup in progress. Server reboot "
                                        "delayed for one minute..")
                                    countdown = 59
                            if countdown % 15 == 0:
                                self.broadcast("&cServer will reboot in %d "
                                               "seconds" % countdown)
                            if countdown < 6:
                                self.broadcast("&cServer will reboot in %d "
                                               "seconds" % countdown)
                    continue
                if self.wrapper.backups_idle():
                    self.restart(self.reboot_message)
                else:
                    self.broadcast(
                        "&cBackup in progress. Server reboot "
                        "delayed..")
                    timer = rb_mins + rb_mins_warn + 1

    def eachsecond_web(self):
        if time.time() - self.lastsizepoll > 120:
            if self.vitals.worldname is None:
                return True
            self.lastsizepoll = time.time()
            size = 0
            # os.scandir not in standard library on early py2.7.x systems
            for i in os.walk(
                    "%s/%s" % (self.vitals.serverpath, self.vitals.worldname)
            ):
                for f in os.listdir(i[0]):
                    size += os.path.getsize(os.path.join(i[0], f))
            self.vitals.worldsize = size

    def _console_event(self, payload):
        """This function is used in conjunction with event handlers to
        permit a proxy object to make a command call to this server."""

        # make commands pass through the command interface.
        comm_pay = payload["command"].split(" ")
        if len(comm_pay) > 1:
            args = comm_pay[1:]
        else:
            args = [""]
        new_payload = {"player": self.wrapper.xplayer,
                       "command": comm_pay[0],
                       "args": args
                       }
        self.wrapper.commands.playercommand(new_payload)
