# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import socket
import time
import threading
import random
import math

import core.buildinfo as version_info

from api.helpers import getargs, getargsafter
from api.base import API

# Py3-2
import sys
PY3 = sys.version_info > (3,)
if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range


# due to self.socket being ducktyped as boolean when it is used later as a socket.
# also, api uses mixedCase
# noinspection PyUnresolvedReferences,PyPep8Naming,PyUnusedLocal
class IRC(object):

    def __init__(self, mcserver, log, wrapper):
        self.socket = False
        self.state = False
        self.javaserver = mcserver
        self.config = wrapper.config
        self.configmgr = wrapper.configManager
        self.wrapper = wrapper
        self.address = self.config["IRC"]["server"]
        self.port = self.config["IRC"]["port"]
        self.nickname = self.config["IRC"]["nick"]
        self.originalNickname = self.nickname[0:]
        self.nickAttempts = 0
        self.channels = self.config["IRC"]["channels"]
        self.log = log
        self.timeout = False
        self.ready = False
        self.msgQueue = []
        self.authorized = {}
        self.line = ""

        self.api = API(self.wrapper, "IRC", internal=True)

        self.api.registerEvent("irc.message", self.onchannelmessage)
        self.api.registerEvent("irc.action", self.onchannelaction)
        self.api.registerEvent("irc.join", self.onchanneljoin)
        self.api.registerEvent("irc.part", self.onchannelpart)
        self.api.registerEvent("irc.quit", self.onchannelquit)

        self.api.registerEvent("server.starting", self.onServerStarting)
        self.api.registerEvent("server.started", self.onServerStarted)
        self.api.registerEvent("server.stopping", self.onServerStopping)
        self.api.registerEvent("server.stopped", self.onServerStopped)
        self.api.registerEvent("player.login", self.onPlayerLogin)
        self.api.registerEvent("player.message", self.onPlayerMessage)
        self.api.registerEvent("player.action", self.onPlayerAction)
        self.api.registerEvent("player.logout", self.onPlayerLogout)
        self.api.registerEvent("player.achievement", self.onPlayerAchievement)
        self.api.registerEvent("player.death", self.onPlayerDeath)
        self.api.registerEvent("wrapper.backupBegin", self.onBackupBegin)
        self.api.registerEvent("wrapper.backupEnd", self.onBackupEnd)
        self.api.registerEvent("wrapper.backupFailure", self.onBackupFailure)
        self.api.registerEvent("server.say", self.onPlayerSay)

    def init(self):
        while not self.wrapper.halt:
            try:
                self.log.info("Connecting to IRC...")
                self.connect()
                t = threading.Thread(target=self.queue, args=())
                t.daemon = True
                t.start()
                self.handle()
            except Exception as e:
                self.log.exception(e)
                self.disconnect("Error in Wrapper.py - restarting")
            self.log.info("Disconnected from IRC")
            time.sleep(5)

    def connect(self):
        self.nickname = self.originalNickname[0:]
        self.socket = socket.socket()
        self.socket.connect((self.address, self.port))
        self.socket.setblocking(120)

        self.auth()

    def auth(self):
        if self.config["IRC"]["password"]:
            self.send("PASS %s" % self.config["IRC"]["password"])
        self.send("NICK %s" % self.nickname)
        self.send("USER %s 0 * :%s" % (self.nickname, self.nickname))

    def disconnect(self, message):
        try:
            self.send("QUIT :%s" % message)
            self.socket.close()
            self.socket = False
        except Exception as e:
            self.log.debug("Exception in IRC disconnect: \n%s", e)

    def send(self, payload):
        if self.socket:
            self.socket.send("%s\n" % payload)
        else:
            return False

    # Event Handlers

    def messagefromchannel(self, channel, message):
        if self.config["IRC"]["show-channel-server"]:
            self.javaserver.broadcast("&6[%s] %s" % (channel, message))
        else:
            self.javaserver.broadcast(message)

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
                self.log.debug("Exception in IRC onchannelmessage: \n%s", e)
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

    def onPlayerLogin(self, payload):
        player = self.filterName(payload["player"])
        self.msgQueue.append("[%s connected]" % player)

    def onPlayerLogout(self, payload):
        player = payload["player"]
        self.msgQueue.append("[%s disconnected]" % player)

    def onPlayerMessage(self, payload):
        player = self.filterName(payload["player"])
        message = payload["message"]
        self.msgQueue.append("<%s> %s" % (player, message))

    def onPlayerAction(self, payload):
        player = self.filterName(payload["player"])
        action = payload["action"]
        self.msgQueue.append("* %s %s" % (player, action))

    def onPlayerSay(self, payload):
        player = self.filterName(payload["player"])
        message = payload["message"]
        self.msgQueue.append("[%s] %s" % (player, message))

    def onPlayerAchievement(self, payload):
        player = self.filterName(payload["player"])
        achievement = payload["achievement"]
        self.msgQueue.append("%s has just earned the achievement %s" % (player, achievement))

    def onPlayerDeath(self, payload):
        player = self.filterName(payload["player"])
        death = payload["death"]
        self.msgQueue.append("%s %s" % (player, death))

    def onBackupBegin(self, payload):
        self.msgQueue.append("Backing up... lag may occur!")

    def onBackupEnd(self, payload):
        time.sleep(1)
        self.msgQueue.append("Backup complete!")

    def onBackupFailure(self, payload):
        if "reasonText" in payload:
            self.msgQueue.append("ERROR: %s" % payload["reasonText"])
        else:
            self.msgQueue.append("An unknown error occurred while trying to backup.")

    def onServerStarting(self, payload):
        self.msgQueue.append("Server starting...")

    def onServerStarted(self, payload):
        self.msgQueue.append("Server started!")

    def onServerStopping(self, payload):
        self.msgQueue.append("Server stopping...")

    def onServerStopped(self, payload):
        self.msgQueue.append("Server stopped!")

    def handle(self):
        while self.socket:
            try:
                irc_buffer = self.socket.recv(1024)  # more duck typing
                if irc_buffer == "":
                    self.log.error("Disconnected from IRC")
                    self.socket = False
                    self.ready = False
                    break
            except socket.timeout:
                if self.timeout:
                    self.socket = False
                    break
                else:
                    self.send("PING :%s" % str(random.randint()))
                    self.timeout = True
                irc_buffer = ""
            except Exception as e:
                self.log.debug("Exception in IRC handle: \n%s", e)
                irc_buffer = ""
            for line in irc_buffer.split("\n"):
                self.line = line
                self.parse()

    def queue(self):
        while self.socket:
            if not self.ready:
                time.sleep(0.1)
                continue
            for i, message in enumerate(self.msgQueue):
                for channel in self.channels:
                    if len(message) > 400:
                        for l in xrange(int(math.ceil(len(message) / 400.0))):
                            chunk = message[l * 400:(l + 1) * 400]
                            self.send("PRIVMSG %s :%s" % (channel, chunk))
                    else:
                        self.send("PRIVMSG %s :%s" % (channel, message))
                del self.msgQueue[i]
            self.msgQueue = []
            time.sleep(0.1)

    def filterName(self, name):
        if self.config["IRC"]["obstruct-nicknames"]:
            return "_" + str(name)[1:]
        else:
            return name

    def rawConsole(self, payload):
        self.javaserver.console(payload)

    def console(self, channel, payload):
        if self.config["IRC"]["show-channel-server"]:
            self.rawConsole({"text": "[%s] " % channel, "color": "gold", "extra": payload})
        else:
            self.rawConsole({"extra": payload})

    def parse(self):
        if getargs(self.line.split(" "), 1) == "001":
            for command in self.config["IRC"]["autorun-irc-commands"]:
                self.send(command)
            for channel in self.channels:
                self.send("JOIN %s" % channel)
            self.ready = True
            self.log.info("Connected to IRC!")
            self.state = True
            self.nickAttempts = 0
        if getargs(self.line.split(" "), 1) == "433":
            self.log.info("Nickname '%s' already in use.", self.nickname)
            self.nickAttempts += 1
            if self.nickAttempts > 2:
                name = bytearray(self.nickname)
                for i in xrange(3):
                    name[len(self.nickname) / 3 * i] = chr(random.randrange(97, 122))
                self.nickname = str(name)
            else:
                self.nickname += "_"
            self.auth()
            self.log.info("Attemping to use nickname '%s'.", self.nickname)
        if getargs(self.line.split(" "), 1) == "JOIN":
            nick = getargs(self.line.split(" "), 0)[1:getargs(self.line.split(" "), 0).find("!")]
            channel = getargs(self.line.split(" "), 2)[1:][:-1]
            self.log.info("%s joined %s", nick, channel)
            self.wrapper.events.callevent("irc.join", {"nick": nick, "channel": channel})
        if getargs(self.line.split(" "), 1) == "PART":
            nick = getargs(self.line.split(" "), 0)[1:getargs(self.line.split(" "), 0).find("!")]
            channel = getargs(self.line.split(" "), 2)
            self.log.info("%s parted %s", nick, channel)
            self.wrapper.events.callevent("irc.part", {"nick": nick, "channel": channel})
        if getargs(self.line.split(" "), 1) == "MODE":
            try:
                nick = getargs(self.line.split(" "), 0)[1:getargs(self.line.split(" "), 0).find('!')]
                channel = getargs(self.line.split(" "), 2)
                modes = getargs(self.line.split(" "), 3)
                user = getargs(self.line.split(" "), 4)[:-1]
                self.console(channel, [{
                    "text": user, 
                    "color": "green"
                }, {
                    "text": " received modes %s from %s" % (modes, nick), 
                    "color": "white"
                }])
            except Exception as e:
                self.log.debug("Exception in IRC in parse (MODE): \n%s", e)
                pass
        if getargs(self.line.split(" "), 0) == "PING":
            self.send("PONG %s" % getargs(self.line.split(" "), 1))
        if getargs(self.line.split(" "), 1) == "QUIT":
            nick = getargs(self.line.split(" "), 0)[1:getargs(self.line.split(" "), 0).find("!")]
            message = getargsafter(self.line.split(" "), 2)[1:].strip("\n").strip("\r")

            self.wrapper.events.callevent("irc.quit", {"nick": nick, "message": message, "channel": None})
        if getargs(self.line.split(" "), 1) == "PRIVMSG":
            channel = getargs(self.line.split(" "), 2)
            nick = getargs(self.line.split(" "), 0)[1:getargs(self.line.split(" "), 0).find("!")]
            message = getargsafter(self.line.split(" "), 3)[1:].strip("\n").strip("\r")

            if channel[0] == "#":
                if message.strip() == ".players":
                    users = ""
                    for user in self.javaserver.players:
                        users += "%s " % user
                    self.send("PRIVMSG %s :There are currently %s users on the server: %s" %
                              (channel, len(self.javaserver.players), users))
                elif message.strip() == ".about":
                    self.send("PRIVMSG %s :Wrapper.py Version %s" % (channel, self.wrapper.getbuildstring()))
                else:
                    message = message.decode("utf-8", "ignore")
                    if getargs(message.split(" "), 0) == "\x01ACTION":
                        self.wrapper.events.callevent("irc.action", {"nick": nick,
                                                                     "channel": channel,
                                                                     "action":
                                                                         getargsafter(message.split(" "), 1)[:-1]})
                        self.log.info("[%s] * %s %s", channel, nick, getargsafter(message.split(" "), 1)[:-1])
                    else:
                        self.wrapper.events.callevent("irc.message", {"nick": nick,
                                                                      "channel": channel,
                                                                      "message": message})
                        self.log.info("[%s] <%s> %s", channel, nick, message)
            elif self.config["IRC"]["control-from-irc"]:
                self.log.info("[PRIVATE] (%s) %s", nick, message)

                def msg(string):
                    self.log.info("[PRIVATE] (%s) %s", self.nickname, string)
                    self.send("PRIVMSG %s :%s" % (nick, string))
                if self.config["IRC"]["control-irc-pass"] == "password":
                    msg("A new password is required in wrapper.properties. Please change it.")
                    return
                if "password" in self.config["IRC"]["control-irc-pass"]:
                    msg("Please choose a password that doesn't contain the term 'password'.")
                    return
                if nick in self.authorized:
                    if int(time.time()) - self.authorized[nick] < 900:
                        if getargs(message.split(" "), 0) == 'hi':
                            msg('Hey there!')
                        elif getargs(message.split(" "), 0) == 'help':
                            # eventually I need to make help only one or two
                            # lines, to prevent getting kicked/banned for spam
                            msg("run [command] - run command on server")
                            msg("togglebackups - temporarily turn backups on or off. this setting is not permanent "
                                "and will be lost on restart")
                            msg("halt - shutdown server and Wrapper.py, will not auto-restart")
                            msg("kill - force server restart without clean shutdown - only use when server "
                                "is unresponsive")
                            msg("start/restart/stop - start the server/automatically stop and start server/stop "
                                "the server without shutting down Wrapper")
                            msg("status - show status of the server")
                            msg("check-update - check for new Wrapper.py updates, but don't install them")
                            msg("update-wrapper - check and install new Wrapper.py updates")
                            msg("Wrapper.py Version %s by benbaptist" %
                                self.wrapper.getbuildstring())
                            # msg('console - toggle console output to this private message')
                        elif getargs(message.split(" "), 0) == 'togglebackups':
                            self.config["Backups"]["enabled"] = not self.config["Backups"]["enabled"]
                            if self.config["Backups"]["enabled"]:
                                msg('Backups are now on.')
                            else:
                                msg('Backups are now off.')
                            self.configmgr.save()  # 'config' is just the json dictionary of items, not the Config class
                        elif getargs(message.split(" "), 0) == 'run':
                            if getargs(message.split(" "), 1) == '':
                                msg('Usage: run [command]')
                            else:
                                command = " ".join(message.split(' ')[1:])
                                self.javaserver.console(command)
                        elif getargs(message.split(" "), 0) == 'halt':
                            self.wrapper.halt = True
                            self.javaserver.console("stop")
                            self.javaserver.changestate(3)
                        elif getargs(message.split(" "), 0) == 'restart':
                            self.javaserver.restart("Restarting server from IRC remote")
                            self.javaserver.changestate(3)
                        elif getargs(message.split(" "), 0) == 'stop':
                            self.javaserver.console('stop')
                            self.javaserver.stop_server_command("Stopped from IRC remote")
                            msg("Server stopping")
                        elif getargs(message.split(" "), 0) == 'start':
                            self.javaserver.start()
                            msg("Server starting")
                        elif getargs(message.split(" "), 0) == 'kill':
                            self.javaserver.kill("Killing server from IRC remote")
                            msg("Server terminated.")
                        elif getargs(message.split(" "), 0) == 'status':
                            if self.javaserver.state == 2:
                                msg("Server is running.")
                            elif self.javaserver.state == 1:
                                msg("Server is currently starting/frozen.")
                            elif self.javaserver.state == 0:
                                msg("Server is stopped. Type 'start' to fire it back up.")
                            elif self.javaserver.state == 3:
                                msg("Server is in the process of shutting down/restarting.")
                            else:
                                msg("Server is in unknown state. This is probably a Wrapper.py bug - report it! "
                                    "(state #%d)" % self.javaserver.state)
                            if self.wrapper.javaserver.getmemoryusage():
                                msg("Server Memory Usage: %d bytes" % self.wrapper.javaserver.getmemoryusage())
                        elif getargs(message.split(" "), 0) == 'check-update':
                            msg("Checking for new updates...")
                            update = self.wrapper.get_wrapper_update_info()
                            if update:
                                version, build, repotype = update
                                if repotype == "stable":
                                    msg("New Wrapper.py Version %s available! (you have %s)" %
                                        (".".join([str(_) for _ in version]), self.wrapper.getbuildstring()))
                                elif repotype == "dev":
                                    msg("New Wrapper.py development build %s #%d available! (you have %s #%d)" % 
                                        (".".join([str(_) for _ in version]), build, version_info.__version__,
                                         version_info.__build__))
                                else:
                                    msg("Unknown new version: %s | %d | %s" % (version, build, repotype))
                                msg("To perform the update, type update-wrapper.")
                            else:
                                if version_info.__branch__ == "stable":
                                    msg("No new stable Wrapper.py versions available.")
                                elif version_info.__branch__ == "dev":
                                    msg("No new development Wrapper.py versions available.")
                        elif getargs(message.split(" "), 0) == 'update-wrapper':
                            msg("Checking for new updates...")
                            update = self.wrapper.get_wrapper_update_info()
                            if update:
                                version, build, repotype = update
                                if repotype == "stable":
                                    msg("New Wrapper.py Version %s available! (you have %s)" %
                                        (".".join([str(_) for _ in version]), self.wrapper.getbuildstring()))
                                elif repotype == "dev":
                                    msg("New Wrapper.py development build %s #%d available! (you have %s #%d)" %
                                        (".".join(version), build, version_info.__version__, version_info.__build__))
                                else:
                                    msg("Unknown new version: %s | %d | %s" % (version, build, repotype))
                                msg("Performing update..")
                                if self.wrapper.performupdate(version, build, repotype):
                                    msg("Update completed! Version %s #%d (%s) is now installed. Please reboot "
                                        "Wrapper.py to apply changes." % (version, build, repotype))
                                else:
                                    msg("An error occured while performing update.")
                                    msg("Please check the Wrapper.py console as soon as possible for an explanation "
                                        "and traceback.")
                                    msg("If you are unsure of the cause, please file a bug report on http://github.com"
                                        "/benbaptist/minecraft-wrapper.")
                            else:
                                if version_info.__branch__ == "stable":
                                    msg("No new stable Wrapper.py versions available.")
                                elif version_info.__branch__ == "dev":
                                    msg("No new development Wrapper.py versions available.")
                        elif getargs(message.split(" "), 0) == "about":
                            msg("Wrapper.py by benbaptist - Version %s (build #%d)" % (version_info.__version__,
                                                                                       version_info.__branch__))
                        else:
                            msg('Unknown command. Type help for more commands')
                    else:
                        msg("Session expired, re-authorize.")
                        del self.authorized[nick]
                else:
                    if getargs(message.split(" "), 0) == 'auth':
                        if getargs(message.split(" "), 1) == self.config["IRC"]["control-irc-pass"]:
                            msg("Authorization success! You'll remain logged in for 15 minutes.")
                            self.authorized[nick] = int(time.time())
                        else:
                            msg("Invalid password.")
                    else:
                        msg('Not authorized. Type "auth [password]" to login.')
