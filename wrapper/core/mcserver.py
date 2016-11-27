# -*- coding: utf-8 -*-
from __future__ import print_function

from utils.helpers import getargs, getargsafter, get_int, processcolorcodes
from utils.helpers import getjsonfile, getfileaslines, config_to_dict_read, set_item

from api.base import API
from api.player import Player
from api.world import World
from api.entity import EntityControl

from core.backups import Backups
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
class MCServer:

    def __init__(self, wrapper):
        self.log = wrapper.log
        self.config = wrapper.config
        self.encoding = self.config["General"]["encoding"]
        self.serverpath = self.config["General"]["server-directory"]
        self.stop_message = self.config["Misc"]["stop-message"]
        self.reboot_message = self.config["Misc"]["reboot-message"]
        self.restart_message = self.config["Misc"]["default-restart-message"]

        self.wrapper = wrapper
        commargs = self.config["General"]["command"].split(" ")
        self.args = []

        for part in commargs:
            if part[-4:] == ".jar":
                self.args.append("%s/%s" % (self.serverpath, part))
            else:
                self.args.append(part)

        self.api = API(wrapper, "Server", internal=True)
        self.backups = Backups(wrapper)

        if "ServerStarted" not in self.wrapper.storage:
            self.wrapper.storage["ServerStarted"] = True
            self.wrapper.storage.save()

        self.state = OFF
        self.bootTime = time.time()
        self.serverbooted = self.wrapper.storage["ServerStarted"]
        self.server_handle_on = False
        self.proc = None
        self.rebootWarnings = 0
        self.lastsizepoll = 0
        self.console_output_data = []
        self.spammy_stuff = ["found nothing", "vehicle of"]
        self.server_muted = False
        self.queued_lines = []
        self.server_stalled = False

        if not self.wrapper.storage["ServerStarted"]:
            self.log.warning("NOTE: Server was in 'STOP' state last time Wrapper.py was running. "
                             "To start the server, run /start.")
            time.sleep(5)

        # Server Information
        self.players = {}
        self.player_eids = {}
        self.worldname = None
        self.worldSize = 0
        self.maxPlayers = 20
        self.protocolVersion = -1  # -1 until proxy mode checks the server's MOTD on boot
        self.version = None  # this is string name of the server version, collected by console output
        self.world = None
        self.entity_control = None
        self.motd = None
        self.timeofday = -1  # -1 until a player logs on and server sends a time update
        self.onlineMode = True
        self.serverIcon = None
        self.operatordict = self.read_ops_file()

        self.properties = {}

        # has to be done immediately to get worldname; otherwise a "None" folder gets created in the server folder.
        self.reloadproperties()  # This will be redone on server start

        if self.config["General"]["timed-reboot"] or self.config["Web"]["web-enabled"]:  # don't reg. an unused event
            self.api.registerEvent("timer.second", self.eachsecond)

        # self.api.backups.init_backups()

    def init(self):
        """
        Start up the listen threads for reading server console output
        """
        capturethread = threading.Thread(target=self.__stdout__, args=())
        capturethread.daemon = True
        capturethread.start()

        capturethread = threading.Thread(target=self.__stderr__, args=())
        capturethread.daemon = True
        capturethread.start()

    def __del__(self):
        self.state = 0  # OFF use hard-coded number in case Class MCSState is GC'ed

    def handle_server(self):
        """
        Function that handles booting the server, parsing console output, and such.
        """

        trystart = 0
        if self.server_handle_on:
            return
        while not self.wrapper.halt:
            trystart += 1
            self.proc = None
            self.server_handle_on = True
            if not self.serverbooted:
                time.sleep(0.1)
                trystart = 0
                continue
            self.changestate(STARTING)
            self.log.info("Starting server...")
            self.reloadproperties()
            self.proc = subprocess.Popen(self.args, cwd=self.serverpath, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         stdin=subprocess.PIPE, universal_newlines=True)
            self.players = {}
            self.accepteula()  # Auto accept eula
            if self.proc.poll() is None and trystart > 3:
                self.log.error("Could not start server.  check your server.properties, wrapper.properties and this"
                               " startup 'command' from wrapper.properties:\n'%s'", " ".join(self.args))
                self.changestate(OFF)
                self.server_handle_on = False
                break

            # The server loop
            while True:
                time.sleep(0.1)
                if self.proc.poll() is not None:
                    self.changestate(OFF)
                    if not self.config["General"]["auto-restart"]:
                        self.wrapper.halt = True
                    break

                # This level runs continously once server console starts
                # is is only reading server console output
                for line in self.console_output_data:
                    try:
                        self.readconsole(line.replace("\r", ""))
                    except Exception as e:
                        self.log.exception(e)
                self.console_output_data = []
            self.server_handle_on = False

    def start(self, save=True):
        """
        Start the Minecraft server
        """
        if self.state in (STARTED, STARTING):
            self.log.warning("The server is already running!")
            return
        if not self.serverbooted:
            self.serverbooted = True
        else:
            self.handle_server()
        if save:
            self.wrapper.storage["ServerStarted"] = True
            self.wrapper.storage.save()

    def restart(self, reason=""):
        """
        Restart the Minecraft server, and kick people with the specified reason
        """
        if reason == "":
            reason = self.restart_message
        if self.state in (STOPPING, OFF):
            self.log.warning("The server is not already running... Just use '/start'.")
            return
        self.log.info("Restarting Minecraft server with reason: %s", reason)
        self.changestate(STOPPING, reason)
        for player in self.players:
            self.console("kick %s %s" % (player, reason))
        self.console("stop")

    def accepteula(self):

        if os.path.isfile("%s/eula.txt" % self.serverpath):
            self.log.debug("Checking EULA agreement...")
            with open("%s/eula.txt" % self.serverpath, "r") as f:
                eula = f.read()

            if "false" in eula:
                # if forced, should be at info level since acceptance is a legal matter.
                self.log.warning("EULA agreement was not accepted, accepting on your behalf...")
                set_item("eula", "true", "eula.txt", self.serverpath)

            self.log.debug("EULA agreement has been accepted.")
            return True
        else:
            return False

    def stop(self, reason="", save=True):
        """
        Stop the Minecraft server, prevent it from auto-restarting.
        """
        if reason == "":
            reason = self.stop_message
        if self.state in (STOPPING, OFF):
            self.log.warning("The server is not running... :?")
            return
        if self.state == FROZEN:
            self.log.warning("The server is currently frozen.\n"
                             "To stop it, you must /unfreeze it first")
            return
        self.log.info("Stopping Minecraft server with reason: %s", reason)
        self.changestate(STOPPING, reason)
        self.serverbooted = False
        if save:
            self.wrapper.storage["ServerStarted"] = False
            self.wrapper.storage.save()
        self.console("stop")  # really no reason to kick the players.  Stop will do it

    def kill(self, reason="Killing Server"):
        """ 
        Forcefully kill the server. It will auto-restart if set in the configuration file
        """
        if self.state in (STOPPING, OFF):
            self.log.warning("The server is already dead, my friend...")
            return
        self.log.info("Killing Minecraft server with reason: %s", reason)
        self.changestate(OFF, reason)
        self.proc.kill()

    def freeze(self, reason="Server is now frozen. You may disconnect momentarily."):
        """ 
        Freeze the server with `kill -STOP`. Can be used to stop the server in an emergency without shutting it down, 
        so it doesn't write corrupted data - e.g. if the disk is full, you can freeze the server, free up some disk
        space, and then unfreeze
        'reason' argument is printed in the chat for all currently-connected players, unless you specify None.
        This command currently only works for *NIX based systems
        """
        if self.state != OFF:
            if os.name == "posix":
                self.log.info("Freezing server with reason: %s", reason)
                self.broadcast("&c%s" % reason)
                time.sleep(0.5)
                self.changestate(FROZEN)
                os.system("kill -STOP %d" % self.proc.pid)
            else:
                raise UnsupportedOSException("Your current OS (%s) does not support this command at this time."
                                             % os.name)
        else:
            raise InvalidServerStartedError("Server is not started. You may run '/start' to boot it up.")

    def unfreeze(self):
        """
        Unfreeze the server with `kill -CONT`. Counterpart to .freeze(reason)
        This command currently only works for *NIX based systems
        """
        if self.state != OFF:
            if os.name == "posix":
                self.log.info("Unfreezing server (ignore any messages to type /start)...")
                self.broadcast("&aServer unfrozen.")
                self.changestate(STARTED)
                os.system("kill -CONT %d" % self.proc.pid)
            else:
                raise UnsupportedOSException("Your current OS (%s) does not support this command at this time."
                                             % os.name)
        else:
            raise InvalidServerStartedError("Server is not started. Please run '/start' to boot it up.")

    def broadcast(self, message=""):
        """
        Broadcasts the specified message to all clients connected. message can be a JSON chat object, 
        or a string with formatting codes using the & as a prefix 
        """
        if isinstance(message, dict):
            if self.config["General"]["pre-1.7-mode"]:
                self.console("say %s" % self.chattocolorcodes(message))
            else:
                self.console("tellraw @a %s" % json.dumps(message, encoding=self.encoding, ensure_ascii=False))
        else:
            if self.config["General"]["pre-1.7-mode"]:
                self.console("say %s" %
                             self.chattocolorcodes(json.loads(processcolorcodes(message)).decode(self.encoding)))
            else:
                self.console("tellraw @a %s" % processcolorcodes(message))

    def chattocolorcodes(self, jsondata):
        def getcolorcode(color):
            for code in API.colorcodes:
                if API.colorcodes[code] == color:
                    return "\xa7\xc2" + code
            return ""

        def handlechunk(chunk):
            extras = ""
            if "color" in chunk:
                extras += getcolorcode(chunk["color"])
            if "text" in chunk:
                extras += chunk["text"]
            if "string" in chunk:
                extras += chunk["string"]
            return extras

        total = handlechunk(jsondata)

        if "extra" in jsondata:
            for extra in jsondata["extra"]:
                total += handlechunk(extra)
        return total.encode(self.encoding)

    def login(self, username, eid, location):
        """
        Called when a player logs in
        """
        if username not in self.players:
            self.players[username] = Player(username, self.wrapper)
        if self.wrapper.proxy:
            playerclient = self.getplayer(username).getClient()
            if playerclient:
                playerclient.servereid = eid
                playerclient.position = location
            self.player_eids[username] = [eid, location]  # palce to store EID if proxy is not fully connected yet.

        self.wrapper.events.callevent("player.login", {"player": self.getplayer(username)})

    def logout(self, players_name):
        """
        Called when a player logs out
        """
        # player object is defunct at this point.  All we can pass to the plugin is a name
        nameduser = "%s" % players_name
        x = MiniPlayer(nameduser)  # create a new simple object describing the logged off player.

        # self.wrapper.callEvent("player.logout", {"player": self.getPlayer(username)})
        self.wrapper.events.callevent("player.logout", {"player": x})
        if self.wrapper.proxy:
            self.wrapper.proxy.removestaleclients()

        if players_name in self.players:
            self.players[players_name].abort = True
            del self.players[players_name]

    def getplayer(self, username):
        """
        Returns a player object with the specified name, or False if the user is not logged in/doesn't exist
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
        # the PY3.5 ConfigParser seems broken.  This way was much more straightforward and works in both PY2 and PY3
        self.properties = config_to_dict_read("server.properties", self.serverpath)

        if self.properties == {}:
            self.log.warning("File 'server.properties' not found.")
            return False

        if "level-name" in self.properties:
            self.worldname = self.properties["level-name"]
        else:
            self.log.warning("No 'level-name=(worldname)' was found in the server.properties.")
            return False
        self.motd = self.properties["motd"]
        if "max-players" in self.properties:
            self.maxPlayers = self.properties["max-players"]
        else:
            self.log.warning("No 'max-players=(count)' was found in the server.properties."
                             "The default of '20' will be used.")
            self.maxPlayers = 20
        self.onlineMode = self.properties["online-mode"]

    def console(self, command):
        """
        Execute a console command on the server
        """
        if self.state in (STARTING, STARTED, STOPPING):
            self.proc.stdin.write("%s\n" % command)
        else:
            self.log.info("Server is not started. Please run '/start' to boot it up.")

    def changestate(self, state, reason=None):
        """
        Change the boot state of the server, with a reason message
        """
        self.state = state
        if self.state == OFF:
            self.wrapper.events.callevent("server.stopped", {"reason": reason})
        elif self.state == STARTING:
            self.wrapper.events.callevent("server.starting", {"reason": reason})
        elif self.state == STARTED:
            self.wrapper.events.callevent("server.started", {"reason": reason})
        elif self.state == STOPPING:
            self.wrapper.events.callevent("server.stopping", {"reason": reason})
        self.wrapper.events.callevent("server.state", {"state": state, "reason": reason})

    def getservertype(self):
        if "spigot" in self.config["General"]["command"].lower():
            return "spigot"
        elif "bukkit" in self.config["General"]["command"].lower():
            return "bukkit"
        else:
            return "vanilla"

    def server_reload(self):
        """
        Restarts the server quickly.  Wrapper "auto-restart" must be set to True.
        If wrapper is in proxy mode, it will reconnect all clients to the serverconnection.
        """
        if self.state in (STOPPING, OFF):
            self.log.warning("The server is not already running... Just use '/start'.")
            return
        if self.wrapper.proxymode:
            # discover who all is playing and store that knowledge

            # tell the serverconnection to stop processing play packets
            self.server_stalled = True

        # stop the server.

        # Call events to "do stuff" while server is down (write whilelists, OP files, server properties, etc)

        # restart the server.

        if self.wrapper.proxymode:
            pass
            # once server is back up,  Reconnect stalled/idle clients back to the serverconnection process.
            #   #  do I need to create a new serverconnection, or can the old one be tricked into continuing??

        reason = None
        self.log.info("Restarting Minecraft server with reason:")
        self.changestate(STOPPING, reason)
        for player in self.players:
            self.console("kick %s %s" % (player, reason))
        self.console("stop")

    def __stdout__(self):
        # handles server output, not lines typed in console.
        while not self.wrapper.halt:
            # noinspection PyBroadException,PyUnusedLocal

            # this reads the line and puts the line in the 'self.data' buffer for processing by
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
        # like __stdout__, handles server output (not lines typed in console)
        while not self.wrapper.halt:
            try:
                data = self.proc.stderr.readline()
                if len(data) > 0:
                    for line in data.split("\n"):
                        self.console_output_data.append(line.replace("\r", ""))
            except Exception as e:
                time.sleep(0.1)
                continue

    def read_ops_file(self):
        """
        Keep a list of ops in the server instance to stop reading the disk for it
        :rtype: Dictionary
        """
        ops = False
        if self.protocolVersion > 4:  # (4 = PROTOCOL_1_7 ) - 1.7.6 or greater use ops.json
            ops = getjsonfile("ops", self.serverpath, encodedas=self.encoding)
        if not ops:
            # try for an old "ops.txt" file instead.
            ops = []
            opstext = getfileaslines("ops.txt", self.serverpath)
            if not opstext:
                return False
            for op in opstext:
                # create a 'fake' ops list from the old pre-1.8 text line name list
                # notice that the level (an option not the old list) is set to 1
                #   This will pass as true, but if the plugin is also checking op-levels, it
                #   may not pass truth.
                indivop = {"uuid": op,
                           "name": op,
                           "level": 1}
                ops.append(indivop)

        return ops

    def refresh_ops(self):
        self.operatordict = self.read_ops_file()

    def getmemoryusage(self):
        """
        Returns allocated memory in bytes
        This command currently only works for *NIX based systems
        """
        if not resource or not os.name == "posix" or self.proc is None:
            raise UnsupportedOSException("Your current OS (%s) does not support this command at this time." % os.name)
        try:
            with open("/proc/%d/statm" % self.proc.pid, "r") as f:
                getbytes = int(f.read().split(" ")[1]) * resource.getpagesize()
            return getbytes
        except Exception as e:
            raise e

    @staticmethod
    def getstorageavailable(folder):
        """
        Returns the disk space for the working directory in bytes
        """
        if platform.system() == "Windows":
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None,
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
        """
        Internally-used function that parses a particular console line
        """
        if not self.wrapper.events.callevent("server.consoleMessage", {"message": buff}):
            return False

        # remove time stamp and server labeling pre-pends.
        if self.getservertype() == "spigot":
            line = " ".join(buff.split(" ")[2:])
        else:
            line = " ".join(buff.split(" ")[3:])

        # check for server console spam before printing to wrapper console
        server_spaming = False
        for things in self.spammy_stuff:
            if things in buff:
                server_spaming = True

        # server_spaming setting does not stop it from being parsed below.
        if not server_spaming:
            if not self.server_muted:

                if self.wrapper.use_readline:
                    print(buff)
                else:
                    # Format the output to prevent a command that is in-process of being typed get carried away.
                    if self.wrapper.input_buff == "":  # input_buff is built by parseconsoleinput() of core.wrapper.
                        print("\033[1A%s" % buff)
                        print(self.wrapper.cursor)
                    else:
                        # print the server lines above and re-print what the console user was typing right below that.
                        print("\033[1A%s" % buff)
                        if self.wrapper.input_buff[0:1] == '/':  # /wrapper commands receive special magenta coloring
                            print("%s\033[35m%s\033[0m" % (self.wrapper.cursor, self.wrapper.input_buff))
                        else:
                            print("%s%s" % (self.wrapper.cursor, self.wrapper.input_buff))

            else:
                self.queued_lines.append(buff)

        # server console parsing section
        line_words = line.split(" ")
        deathprefixes = ["fell", "was", "drowned", "blew", "walked", "went", "burned", "hit", "tried",
                         "died", "got", "starved", "suffocated", "withered"]
        if not self.config["General"]["pre-1.7-mode"]:
            if len(getargs(line.split(" "), 0)) < 1:
                return

            # confirm server start
            if "Done (" in line:
                self.changestate(STARTED)
                self.log.info("Server started")
                self.bootTime = time.time()

            # Getting world name
            elif "Preparing level" in line:
                self.worldname = getargs(line.split(" "), 2).replace('"', "")
                self.world = World(self.worldname, self)
                self.entity_control = EntityControl(self)

            elif getargs(line_words, 0)[0] == "<":  # Player Message
                name = self.stripspecial(getargs(line_words, 0)[1:-1])
                message = self.stripspecial(getargsafter(line_words, 1))
                original = getargsafter(line_words, 0)
                self.wrapper.events.callevent("player.message", {
                    "player": self.getplayer(name), 
                    "message": message, 
                    "original": original
                })
            elif getargs(line_words, 1) == "logged":  # Player Login
                name = self.stripspecial(getargs(line_words, 0)[0:getargs(line_words, 0).find("[")])
                eid = int(getargs(line_words, 6))
                locationtext = getargs(line.split(" ("), 1)[:-1].split(", ")
                location = int(float(locationtext[0])), int(float(locationtext[1])), int(float(locationtext[2]))
                self.login(name, eid, location)
            elif getargs(line_words, 1) == "left":  # Player Logout
                name = getargs(line_words, 0)
                self.logout(name)
            elif getargs(line_words, 0) == "*":
                name = self.stripspecial(getargs(line_words, 1))
                message = self.stripspecial(getargsafter(line_words, 2))
                self.wrapper.events.callevent("player.action", {
                    "player": self.getplayer(name),
                    "action": message
                })
            elif getargs(line_words, 0)[0] == "[" and getargs(line_words, 0)[-1] == "]":  # /say command
                if self.getservertype != "vanilla":
                    return  # Unfortunately, Spigot and Bukkit output things that conflict with this
                name = self.stripspecial(getargs(line_words, 0)[1:-1])
                message = self.stripspecial(getargsafter(line_words, 1))
                original = getargsafter(line_words, 0)
                self.wrapper.events.callevent("server.say", {
                    "player": name, 
                    "message": message, 
                    "original": original
                })
            # Player Achievement
            elif getargs(line_words, 1) == "has" and getargs(line_words, 5) == "achievement":
                name = self.stripspecial(getargs(line_words, 0))
                achievement = getargsafter(line_words, 6)
                self.wrapper.events.callevent("player.achievement", {
                    "player": name, 
                    "achievement": achievement
                })
            elif getargs(line_words, 1) in deathprefixes:  # Player Death
                name = self.stripspecial(getargs(line_words, 0))
                self.wrapper.events.callevent("player.death", {
                    "player": self.getplayer(name), 
                    "death": getargsafter(line_words, 4)
                })
            elif "minecraft server version" in line:  # Starting minecraft server version 1.11
                self.version = getargs(line_words, 4)
                semanitics = self.version.split(".")
                release = get_int(getargs(semanitics, 0))
                major = get_int(getargs(semanitics, 1))
                minor = get_int(getargs(semanitics, 2))
                if release > 1 and major > 6 and minor > 4 and self.protocolVersion < 0:
                    self.protocolVersion = 5
                self.refresh_ops()

        else:  # pre 1.7 mode
            if len(getargs(line_words, 3)) < 1:
                return
            if getargs(line_words, 3) == "Done":  # Confirmation that the server finished booting
                self.changestate(STARTED)
                self.log.info("Server started")
                self.bootTime = time.time()
            elif getargs(line_words, 3) == "Preparing" and getargs(line_words, 4) == "level":
                # Getting world name
                self.worldname = getargs(line_words, 5).replace('"', "")
                self.world = World(self.worldname, self)
                self.entity_control = EntityControl(self)
            elif getargs(line_words, 3)[0] == "<":  # Player Message
                name = self.stripspecial(getargs(line_words, 3)[1:-1])
                message = self.stripspecial(getargsafter(line_words, 4))
                original = getargsafter(line_words, 3)
                self.wrapper.events.callevent("player.message", {
                    "player": self.getplayer(name), 
                    "message": message, 
                    "original": original
                })
            elif getargs(line_words, 4) == "logged":  # Player Login
                name = self.stripspecial(getargs(line_words, 3)[0:getargs(line_words, 3).find("[")])
                self.login(name, None, (0, 0, 0))
            elif getargs(line_words, 4) == "lost":  # Player Logout
                name = getargs(line_words, 3)
                self.logout(name)
            elif getargs(line_words, 3) == "*":
                name = self.stripspecial(getargs(line_words, 4))
                message = self.stripspecial(getargsafter(line_words, 5))
                self.wrapper.events.callevent("player.action", {
                    "player": self.getplayer(name), 
                    "action": message
                })
            elif getargs(line_words, 3)[0] == "[" and getargs(line_words, 3)[-1] == "]":  # /say command
                name = self.stripspecial(getargs(line_words, 3)[1:-1])
                message = self.stripspecial(getargsafter(line_words, 4))
                original = getargsafter(line_words, 3)
                if name == "Server":
                    return
                self.wrapper.events.callevent("server.say", {
                    "player": name, 
                    "message": message, 
                    "original": original
                })
            elif getargs(line_words, 4) == "has" and getargs(line_words, 8) == "achievement":
                # Player Achievement
                name = self.stripspecial(getargs(line_words, 3))
                achievement = getargsafter(line_words, 9)
                self.wrapper.events.callevent("player.achievement", {
                    "player": name, 
                    "achievement": achievement
                })
            elif getargs(line_words, 4) in deathprefixes:  # Pre- 1.7 Player Death
                name = self.stripspecial(getargs(line_words, 3))
                # No such config items!
                # deathmessage = self.config["Death"]["death-kick-messages"][random.randrange(
                #     0, len(self.config["Death"]["death-kick-messages"]))]
                # if self.config["Death"]["kick-on-death"] and name in self.config["Death"]["users-to-kick"]:
                #     self.console("kick %s %s" % (name, deathmessage))
                self.wrapper.events.callevent("player.death", {
                    "player": self.getplayer(name), 
                    "death": getargsafter(line_words, 4)
                })
            self.version = "Pre-1.7"
            self.refresh_ops()

    # mcserver.py onsecond Event Handler
    def eachsecond(self, payload):
        if self.config["General"]["timed-reboot"]:
            if time.time() - self.bootTime > self.config["General"]["timed-reboot-seconds"]:
                if self.config["General"]["timed-reboot-warning-minutes"] > 0:
                    if self.rebootWarnings - 1 < self.config["General"]["timed-reboot-warning-minutes"]:
                        l = (time.time() - self.bootTime - self.config["General"]["timed-reboot-seconds"]) / 60
                        if l > self.rebootWarnings:
                            self.rebootWarnings += 1
                            if int(self.config["General"]["timed-reboot-warning-minutes"] - l + 1) > 0:
                                self.broadcast("&cServer will be rebooting in %d minute(s)!"
                                               % int(self.config["General"]["timed-reboot-warning-minutes"] - l + 1))
                        return
                self.restart(self.reboot_message)
                self.bootTime = time.time()
                self.rebootWarnings = 0
        if self.config["Web"]["web-enabled"]:  # only used by web management module
            if time.time() - self.lastsizepoll > 120:
                if self.worldname is None:
                    return True
                self.lastsizepoll = time.time()
                size = 0
                # os.scandir not in standard library even on early py2.7.x systems
                for i in os.walk("%s/%s" % (self.serverpath, self.worldname)):
                    for f in os.listdir(i[0]):
                        size += os.path.getsize(os.path.join(i[0], f))
                self.worldSize = size


class MiniPlayer:
    """ a shell of the original player, who is now logged off and real player object is defunct.
    Only used to pass some info to the player payload for event player.Logout, mostly for back-wards
    compatibility to plugins."""
    def __init__(self, playername):
        self.username = playername
