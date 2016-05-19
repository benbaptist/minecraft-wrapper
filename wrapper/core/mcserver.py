# -*- coding: utf-8 -*-

# p2 and py3 compliant (no PyCharm IDE-flagged errors)
# (has warnings in both versions due to the manner of import)

from utils.helpers import getargs, getargsafter, processcolorcodes
from api.base import API
from api.player import Player
from api.world import World

from core.backups import Backups
from core.exceptions import UnsupportedOSException, InvalidServerStateError

import time
import threading
import random
import subprocess
import os
import json
import ctypes
import platform
import base64

# Py3-2
import sys
PY3 = sys.version_info > (3,)

try:
    import resource
except ImportError:
    resource = False


# noinspection PyBroadException,PyUnusedLocal
class MCServer:

    def __init__(self, args, log, config, wrapper):
        self.log = log
        self.config = config
        self.wrapper = wrapper
        self.args = args
        self.api = API(wrapper, "Server", internal=True)
        self.backups = Backups(wrapper)

        if "serverState" not in self.wrapper.storage:
            self.wrapper.storage["serverState"] = True

        self.players = {}
        self.state = MCSState.OFF
        self.bootTime = time.time()
        self.boot = self.wrapper.storage["serverState"]
        self.proc = None
        self.rebootWarnings = 0
        self.lastsizepoll = 0
        self.data = []

        if not self.wrapper.storage["serverState"]:
            self.log.warning("NOTE: Server was in 'STOP' state last time Wrapper.py was running. "
                             "To start the server, run /start.")
            time.sleep(5)

        # Server Information
        self.worldName = None
        self.worldSize = 0
        self.maxPlayers = 20
        self.protocolVersion = -1  # -1 until proxy mode checks the server's MOTD on boot
        self.version = None
        self.world = None
        self.motd = None
        self.timeofday = -1  # -1 until a player logs on and server sends a time update
        self.onlineMode = True
        self.serverIcon = None

        self.properties = {}
        self.reloadproperties()

        self.api.registerEvent("irc.message", self.onchannelmessage)
        self.api.registerEvent("irc.action", self.onchannelaction)
        self.api.registerEvent("irc.join", self.onchanneljoin)
        self.api.registerEvent("irc.part", self.onchannelpart)
        self.api.registerEvent("irc.quit", self.onchannelquit)
        self.api.registerEvent("timer.second", self.eachsecond)

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

    def start(self, save=True):
        """
        Start the Minecraft server
        """
        self.boot = True
        if save:
            self.wrapper.storage["serverState"] = True

    def restart(self, reason="Restarting Server"):
        """
        Restart the Minecraft server, and kick people with the specified reason
        """
        self.log.info("Restarting Minecraft server with reason: %s", reason)
        self.changestate(MCSState.STOPPING, reason)
        for player in self.players:
            self.console("kick %s %s" % (player, reason))
        self.console("stop")

    def stop(self, reason="Stopping Server", save=True):
        """
        Stop the Minecraft server, prevent it from auto-restarting and kick people with the specified reason
        """
        self.log.info("Stopping Minecraft server with reason: %s", reason)
        self.changestate(MCSState.STOPPING, reason)
        self.boot = False
        if save:
            self.wrapper.storage["serverState"] = False
        for player in self.players:
            self.console("kick %s %s" % (player, reason))
        self.console("stop")

    def kill(self, reason="Killing Server"):
        """ 
        Forcefully kill the server. It will auto-restart if set in the configuration file
        """
        self.log.info("Killing Minecraft server with reason: %s", reason)
        self.changestate(MCSState.OFF, reason)
        self.proc.kill()

    def freeze(self, reason="Server is now frozen. You may disconnect momentarily."):
        """ 
        Freeze the server with `kill -STOP`. Can be used to stop the server in an emergency without shutting it down, 
        so it doesn't write corrupted data - e.g. if the disk is full, you can freeze the server, free up some disk
        space, and then unfreeze
        'reason' argument is printed in the chat for all currently-connected players, unless you specify None.
        This command currently only works for *NIX based systems
        """
        if self.state != MCSState.OFF:
            if os.name == "posix":
                self.log.info("Freezing server with reason: %s", reason)
                self.broadcast("&c%s" % reason)
                time.sleep(0.5)
                self.changestate(MCSState.FROZEN)
                os.system("kill -STOP %d" % self.proc.pid)
            else:
                raise UnsupportedOSException("Your current OS (%s) does not support this command at this time."
                                             % os.name)
        else:
            raise InvalidServerStateError("Server is not started. You may run '/start' to boot it up.")

    def unfreeze(self):
        """
        Unfreeze the server with `kill -CONT`. Counterpart to .freeze(reason)
        This command currently only works for *NIX based systems
        """
        if self.state != MCSState.OFF:
            if os.name == "posix":
                self.log.info("Unfreezing server...")
                self.broadcast("&aServer unfrozen.")
                self.changestate(MCSState.STARTED)
                os.system("kill -CONT %d" % self.proc.pid)
            else:
                raise UnsupportedOSException("Your current OS (%s) does not support this command at this time."
                                             % os.name)
        else:
            raise InvalidServerStateError("Server is not started. Please run '/start' to boot it up.")

    def broadcast(self, message=""):
        """
        Broadcasts the specified message to all clients connected. message can be a JSON chat object, 
        or a string with formatting codes using the & as a prefix 
        """
        if isinstance(message, dict):
            if self.config["General"]["pre-1.7-mode"]:
                self.console("say %s" % self.chattocolorcodes(message))
            else:
                self.console("tellraw @a %s" % json.dumps(message))
        else:
            if self.config["General"]["pre-1.7-mode"]:
                self.console("say %s" %
                             self.chattocolorcodes(json.loads(processcolorcodes(message)).decode('utf-8')))
            else:
                self.console("tellraw @a %s" % processcolorcodes(message))

    @staticmethod
    def chattocolorcodes(jsondata):
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
        return total.encode("utf8")

    def login(self, username):
        """
        Called when a player logs in
        """
        try:
            if username not in self.players:
                self.players[username] = Player(username, self.wrapper)
            self.wrapper.events.callevent("player.login", {"player": self.getplayer(username)})
        except Exception as e:
            self.log.exception(e)

    def logout(self, username):
        """
        Called when a player logs out
        """
        self.wrapper.events.callevent("player.logout", {"player": self.getplayer(username)})
        # if self.wrapper.proxy:
        #     for client in self.wrapper.proxy.clients:
        #         uuid = self.players[username].uuid # This is not used
        if username in self.players:
            self.players[username].abort = True
            del self.players[username]

    def getplayer(self, username):
        """
        Returns a player object with the specified name, or False if the user is not logged in/doesn't exist
        """
        if username in self.players:
            return self.players[username]
        return False

    def reloadproperties(self):
        # Load server icon
        if os.path.exists("server-icon.png"):
            with open("server-icon.png", "rb") as f:
                theicon = f.read()
                iconencoded = base64.standard_b64encode(theicon)
                self.serverIcon = b"data:image/png;base64," + iconencoded
        # Read server.properties and extract some information out of it
        # the PY3.5 ConfigParser seems broken.  This way was much more straightforward and works in both PY2 and PY3
        if os.path.exists("server.properties"):
            with open("server.properties", "r") as f:
                configfile = f.read()
            self.worldName = configfile.split("level-name=")[1].split("\n")[0]
            self.motd = configfile.split("motd=")[1].split("\n")[0]
            self.maxPlayers = configfile.split("max-players=")[1].split("\n")[0]
            self.onlineMode = configfile.split("online-mode=")[1].split("\n")[0]
            if self.onlineMode == "false":
                self.onlineMode = False
            else:
                self.onlineMode = True

    def console(self, command):
        """
        Execute a console command on the server
        """
        if self.state in (MCSState.STARTING, MCSState.STARTED, MCSState.STOPPING):
            self.proc.stdin.write("%s\n" % command)
        else:
            raise InvalidServerStateError("Server is not started. Please run '/start' to boot it up.")

    def changestate(self, state, reason=None):
        """
        Change the boot state of the server, with a reason message
        """
        self.state = state
        if self.state == MCSState.OFF:
            self.wrapper.events.callevent("server.stopped", {"reason": reason})
        elif self.state == MCSState.STARTING:
            self.wrapper.events.callevent("server.starting", {"reason": reason})
        elif self.state == MCSState.STARTED:
            self.wrapper.events.callevent("server.started", {"reason": reason})
        elif self.state == MCSState.STOPPING:
            self.wrapper.events.callevent("server.stopping", {"reason": reason})
        self.wrapper.events.callevent("server.state", {"state": state, "reason": reason})

    def getservertype(self):
        if "spigot" in self.config["General"]["command"].lower():
            return "spigot"
        elif "bukkit" in self.config["General"]["command"].lower():
            return "bukkit"
        else:
            return "vanilla"

    def __stdout__(self):
        while not self.wrapper.halt:
            # noinspection PyBroadException,PyUnusedLocal
            try:
                data = self.proc.stdout.readline()
                for line in data.split("\n"):
                    if len(line) < 1:
                        continue
                    self.data.append(line)
            except Exception as e:
                time.sleep(0.1)
                continue

    def __stderr__(self):
        while not self.wrapper.halt:
            try:
                data = self.proc.stderr.readline()
                if len(data) > 0:
                    for line in data.split("\n"):
                        self.data.append(line.replace("\r", ""))
            except Exception as e:
                time.sleep(0.1)
                continue

    def __handle_server__(self):
        """
        Internally-used function that handles booting the server, parsing console output, and etc.
        """
        while not self.wrapper.halt:
            self.proc = None
            if not self.boot:
                time.sleep(0.1)
                continue
            self.changestate(MCSState.STARTING)
            self.log.info("Starting server...")
            self.reloadproperties()
            self.proc = subprocess.Popen(self.args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         stdin=subprocess.PIPE, universal_newlines=True)
            self.players = {}
            self.wrapper.accepteula()  # Auto accept eula
            while True:
                time.sleep(0.1)
                if self.proc.poll() is not None:
                    self.changestate(MCSState.OFF)
                    if not self.config["General"]["auto-restart"]:
                        self.wrapper.halt = True
                    self.log.info("Server stopped")
                    break
                for line in self.data:
                    try:
                        self.readconsole(line.replace("\r", ""))
                    except Exception as e:
                        self.log.exception(e)
                self.data = []

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
        if self.getservertype() == "spigot":
            line = " ".join(buff.split(" ")[2:])
        else:
            line = " ".join(buff.split(" ")[3:])
        print(buff)
        deathprefixes = ["fell", "was", "drowned", "blew", "walked", "went", "burned", "hit", "tried",
                         "died", "got", "starved", "suffocated", "withered"]
        if not self.config["General"]["pre-1.7-mode"]:
            if len(getargs(line.split(" "), 0)) < 1:
                return
            if getargs(line.split(" "), 0) == "Done":  # Confirmation that the server finished booting
                self.changestate(MCSState.STARTED)
                self.log.info("Server started")
                self.bootTime = time.time()
            # Getting world name
            elif getargs(line.split(" "), 0) == "Preparing" and getargs(line.split(" "), 1) == "level":
                self.worldName = getargs(line.split(" "), 2).replace('"', "")
                self.world = World(self.worldName, self)
            elif getargs(line.split(" "), 0)[0] == "<":  # Player Message
                name = self.stripspecial(getargs(line.split(" "), 0)[1:-1])
                message = self.stripspecial(getargsafter(line.split(" "), 1))
                original = getargsafter(line.split(" "), 0)
                self.wrapper.events.callevent("player.message", {
                    "player": self.getplayer(name), 
                    "message": message, 
                    "original": original
                })
            elif getargs(line.split(" "), 1) == "logged":  # Player Login
                name = self.stripspecial(getargs(line.split(" "), 0)[0:getargs(line.split(" "), 0).find("[")])
                self.login(name)
            elif getargs(line.split(" "), 1) == "lost":  # Player Logout
                name = getargs(line.split(" "), 0)
                self.logout(name)
            elif getargs(line.split(" "), 0) == "*":
                name = self.stripspecial(getargs(line.split(" "), 1))
                message = self.stripspecial(getargsafter(line.split(" "), 2))
                self.wrapper.events.callevent("player.action", {
                    "player": self.getplayer(name),
                    "action": message
                })
            elif getargs(line.split(" "), 0)[0] == "[" and getargs(line.split(" "), 0)[-1] == "]":  # /say command
                if self.getservertype != "vanilla":
                    return  # Unfortunately, Spigot and Bukkit output things that conflict with this
                name = self.stripspecial(getargs(line.split(" "), 0)[1:-1])
                message = self.stripspecial(getargsafter(line.split(" "), 1))
                original = getargsafter(line.split(" "), 0)
                self.wrapper.events.callevent("server.say", {
                    "player": name, 
                    "message": message, 
                    "original": original
                })
            # Player Achievement
            elif getargs(line.split(" "), 1) == "has" and getargs(line.split(" "), 5) == "achievement":
                name = self.stripspecial(getargs(line.split(" "), 0))
                achievement = getargsafter(line.split(" "), 6)
                self.wrapper.events.callevent("player.achievement", {
                    "player": name, 
                    "achievement": achievement
                })
            elif getargs(line.split(" "), 1) in deathprefixes:  # Player Death
                name = self.stripspecial(getargs(line.split(" "), 0))
                self.wrapper.events.callevent("player.death", {
                    "player": self.getplayer(name), 
                    "death": getargsafter(line.split(" "), 4)
                })
        else:
            if len(getargs(line.split(" "), 3)) < 1:
                return
            if getargs(line.split(" "), 3) == "Done":  # Confirmation that the server finished booting
                self.changestate(MCSState.STARTED)
                self.log.info("Server started")
                self.bootTime = time.time()
            elif getargs(line.split(" "), 3) == "Preparing" and getargs(line.split(" "), 4) == "level":
                # Getting world name
                self.worldName = getargs(line.split(" "), 5).replace('"', "")
                self.world = World(self.worldName, self)
            elif getargs(line.split(" "), 3)[0] == "<":  # Player Message
                name = self.stripspecial(getargs(line.split(" "), 3)[1:-1])
                message = self.stripspecial(getargsafter(line.split(" "), 4))
                original = getargsafter(line.split(" "), 3)
                self.wrapper.events.callevent("player.message", {
                    "player": self.getplayer(name), 
                    "message": message, 
                    "original": original
                })
            elif getargs(line.split(" "), 4) == "logged":  # Player Login
                name = self.stripspecial(getargs(line.split(" "), 3)[0:getargs(line.split(" "), 3).find("[")])
                self.login(name)
            elif getargs(line.split(" "), 4) == "lost":  # Player Logout
                name = getargs(line.split(" "), 3)
                self.logout(name)
            elif getargs(line.split(" "), 3) == "*":
                name = self.stripspecial(getargs(line.split(" "), 4))
                message = self.stripspecial(getargsafter(line.split(" "), 5))
                self.wrapper.events.callevent("player.action", {
                    "player": self.getplayer(name), 
                    "action": message
                })
            elif getargs(line.split(" "), 3)[0] == "[" and getargs(line.split(" "), 3)[-1] == "]":  # /say command
                name = self.stripspecial(getargs(line.split(" "), 3)[1:-1])
                message = self.stripspecial(getargsafter(line.split(" "), 4))
                original = getargsafter(line.split(" "), 3)
                if name == "Server":
                    return
                self.wrapper.events.callevent("server.say", {
                    "player": name, 
                    "message": message, 
                    "original": original
                })
            elif getargs(line.split(" "), 4) == "has" and getargs(line.split(" "), 8) == "achievement":
                # Player Achievement
                name = self.stripspecial(getargs(line.split(" "), 3))
                achievement = getargsafter(line.split(" "), 9)
                self.wrapper.events.callevent("player.achievement", {
                    "player": name, 
                    "achievement": achievement
                })
            elif getargs(line.split(" "), 4) in deathprefixes:  # Player Death
                name = self.stripspecial(getargs(line.split(" "), 3))
                deathmessage = self.config["Death"]["death-kick-messages"][random.randrange(
                    0, len(self.config["Death"]["death-kick-messages"]))]
                if self.config["Death"]["kick-on-death"] and name in self.config["Death"]["users-to-kick"]:
                    self.console("kick %s %s" % (name, deathmessage))
                self.wrapper.events.callevent("player.death", {
                    "player": self.getplayer(name), 
                    "death": getargsafter(line.split(" "), 4)
                })

    # Event Handlers

    def messagefromchannel(self, channel, message):
        if self.config["IRC"]["show-channel-server"]:
            self.broadcast("&6[%s] %s" % (channel, message))
        else:
            self.broadcast(message)

    def onchanneljoin(self, payload):
        channel, nick = payload["channel"], payload["nick"]
        if not self.config["IRC"]["show-irc-join-part"]:
            return
        self.messagefromchannel(channel, "&a%s &rjoined the channel" % nick)

    def onchannelpart(self, payload):
        channel, nick = payload["channel"], payload["nick"]
        if not self.config["IRC"]["show-irc-join-part"]:
            return
        self.messagefromchannel(channel, "&a%s &rparted the channel" % nick)

    def onchannelmessage(self, payload):
        channel, nick, message = payload["channel"], payload["nick"], payload["message"]
        final = ""
        for i, chunk in enumerate(message.split(" ")):
            if not i == 0:
                final += " "
            try:
                if chunk[0:7] in ("http://", "https://"):
                    final += "&b&n&@%s&@&r" % chunk
                else:
                    final += chunk
            except Exception as e:
                final += chunk
        self.messagefromchannel(channel, "&a<%s> &r%s" % (nick, final))

    def onchannelaction(self, payload):
        channel, nick, action = payload["channel"], payload["nick"], payload["action"]
        self.messagefromchannel(channel, "&a* %s &r%s" % (nick, action))

    def onchannelquit(self, payload):
        channel, nick, message = payload["channel"], payload["nick"], payload["message"]
        if not self.config["IRC"]["show-irc-join-part"]:
            return
        self.messagefromchannel(channel, "&a%s &rquit: %s" % (nick, message))

    def eachsecond(self, payload):
        """
        Called every second, and used for handling cron-like jobs
        """
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
                self.restart("Server is conducting a scheduled reboot. The server will be back momentarily!")
                self.bootTime = time.time()
                self.rebootWarnings = 0
        if self.config["Web"]["web-enabled"]:  # only used by web management module
            if time.time() - self.lastsizepoll > 120:
                if self.worldName is None:
                    return True
                self.lastsizepoll = time.time()
                size = 0
                for i in os.walk(self.worldName):
                    for f in os.listdir(i[0]):
                        size += os.path.getsize(os.path.join(i[0], f))
                self.worldSize = size


class MCSState:
    """
    This class represents Minecraft Console Server states
    """

    OFF = 0  # this is the start mode.
    STARTING = 1
    STARTED = 2
    STOPPING = 3
    FROZEN = 4

    def __init__(self):
        pass
