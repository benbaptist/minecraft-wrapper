# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import socket
import traceback
import threading
import time
import json
import random
import os
import logging

from api.helpers import getargs, get_req
from api.base import API
from core.storage import Storage

try:
    import pkg_resources
    import requests
except ImportError:
    pkg_resources = False
    requests = False


# Yeah, I know. The code is awful. Probably not even a HTTP-compliant web
# server anyways. I just wrote it at like 3AM in like an hour.


# noinspection PyBroadException,PyUnusedLocal,PyPep8Naming
class Web(object):
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.api = API(wrapper, "Web", internal=True)
        self.log = logging.getLogger('Web')
        self.config = wrapper.config
        self.serverpath = self.config["General"]["server-directory"]
        self.socket = False
        self.data = Storage("web")

        if "keys" not in self.data.Data:
            self.data.Data["keys"] = []
        # if not self.config["Web"]["web-password"] == None:
        #   self.log.info("Changing web-mode password because web-password was changed in wrapper.properties")
        #  ***** change code to hashlib if this gets uncommented
        #   self.data.Data["password"] = md5.md5(self.config["Web"]["web-password"]).hexdigest()
        #   self.config["Web"]["web-password"] = None
        #   self.wrapper.configManager.save()

        self.api.registerEvent("server.consoleMessage", self.onServerConsole)
        self.api.registerEvent("player.message", self.onPlayerMessage)
        self.api.registerEvent("player.login", self.onPlayerJoin)
        self.api.registerEvent("player.logout", self.onPlayerLeave)
        self.api.registerEvent("irc.message", self.onChannelMessage)
        self.consoleScrollback = []
        self.chatScrollback = []
        self.memoryGraph = []
        self.loginAttempts = 0
        self.lastAttempt = 0
        self.disableLogins = 0

        # t = threading.Thread(target=self.updateGraph, args=())
        # t.daemon = True
        # t.start()

    def __del__(self):
            self.data.close()

    def onServerConsole(self, payload):
        while len(self.consoleScrollback) > 1000:
            try:
                del self.consoleScrollback[0]
            except Exception as e:
                break
        self.consoleScrollback.append((time.time(), payload["message"]))

    def onPlayerMessage(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except Exception as e:
                break
        self.chatScrollback.append((time.time(), {
            "type": "player", 
            "payload": {
                "player": payload["player"].username, 
                "message": payload["message"]
            }
        }))

    def onPlayerJoin(self, payload):
        # print(payload)
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except Exception as e:
                break
        self.chatScrollback.append((time.time(), {
            "type": "playerJoin", 
            "payload": {
                "player": payload["player"].username
            }
        }))

    def onPlayerLeave(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except Exception as e:
                break
        self.chatScrollback.append((time.time(), {
            "type": "playerLeave", 
            "payload": {
                "player": payload["player"]
            }
        }))

    def onChannelMessage(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except Exception as e:
                break
        self.chatScrollback.append((time.time(), {"type": "irc", "payload": payload}))

    def updateGraph(self):
        while not self.wrapper.halt:
            while len(self.memoryGraph) > 200:
                del self.memoryGraph[0]
            if self.wrapper.javaserver.getmemoryusage():
                self.memoryGraph.append([time.time(), self.wrapper.javaserver.getmemoryusage()])
            time.sleep(1)

    def checkLogin(self, password):
        if time.time() - self.disableLogins < 60:
            return False  # Threshold for logins
        if password == self.wrapper.config["Web"]["web-password"]:
            return True
        self.loginAttempts += 1
        if self.loginAttempts > 10 and time.time() - self.lastAttempt < 60:
            self.disableLogins = time.time()
            self.log.warning("Disabled login attempts for one minute")
        self.lastAttempt = time.time()

    def makeKey(self, rememberme):
        a = ""
        z = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@-_"
        for i in range(64):  # not enough performance issue to justify xrange
            a += z[random.randrange(0, len(z))]
            # a += chr(random.randrange(97, 122))
        if rememberme:
            print("Will remember!")
        self.data.Data["keys"].append([a, time.time(), rememberme])
        return a

    def validateKey(self, key):
        for i in self.data.Data["keys"]:
            expiretime = 2592000
            if len(i) > 2:
                if not i[2]:
                    expiretime = 21600
            # Validate key and ensure it's under a week old
            if i[0] == key and time.time() - i[1] < expiretime:
                self.loginAttempts = 0
                return True
        return False

    def removeKey(self, key):
        # we dont want to do things like this.  Never delete or insert while iterating over a dictionary
        #  because dictionaries change order as the hashtables are changed during insert and delete operations...
        for i, v in enumerate(self.data.Data["keys"]):
            if v[0] == key:
                del self.data.Data["keys"][i]

    def wrap(self):
        while not self.wrapper.halt:
            try:
                if self.bind():
                    self.listen()
                else:
                    self.log.error("Could not bind web to %s:%d - retrying in 5 seconds",
                                   self.config["Web"]["web-bind"], self.config["Web"]["web-port"])
            except Exception as e:
                self.log.exception(e)
            time.sleep(5)

    def bind(self):
        if self.socket is not False:
            self.socket.close()
        try:
            self.socket = socket.socket()
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.config["Web"]["web-bind"], self.config["Web"]["web-port"]))
            self.socket.listen(5)
            return True
        except Exception as e:
            return False

    def listen(self):
        self.log.info("Web Interface bound to %s:%d",
                      self.config["Web"]["web-bind"], self.config["Web"]["web-port"])
        while not self.wrapper.halt:
            # noinspection PyUnresolvedReferences
            sock, addr = self.socket.accept()
            # self.log.debug("(WEB) Connection %s started", str(addr))
            client = WebClient(sock, addr, self)
            t = threading.Thread(target=client.wrap, args=())
            t.daemon = True
            t.start()


# noinspection PyBroadException,PyUnusedLocal,PyMethodMayBeStatic,PyPep8Naming
class WebClient(object):

    def __init__(self, sock, addr, web):
        self.web = web
        self.wrapper = self.web.wrapper
        self.config = self.web.wrapper.config
        self.serverpath = self.config["General"]["server-directory"]

        self.socket = sock
        self.addr = addr
        self.web = web
        self.request = ""
        self.log = self.wrapper.log
        self.api = self.wrapper.api
        self.socket.setblocking(30)

    def read(self, filename):
        return pkg_resources.resource_stream(__name__, "html/%s" % filename).read()

    def write(self, message):
        self.socket.send(message)

    def headers(self, status="200 Good", contenttype="text/html", location=""):
        self.write("HTTP/1.0 %s\n" % status)
        if len(location) < 1:
            self.write("Content-Type: %s\n" % contenttype)

        if len(location) > 0:
            self.write("Location: %s\n" % location)

        self.write("\n")

    def close(self):
        try:
            self.socket.close_server()
            # self.log.debug("(WEB) Connection %s closed", str(self.addr))
        except Exception as e:
            pass

    def wrap(self):
        try:
            self.handle()
        except Exception as e:
            self.log.exception("Internal error while handling web mode request")
            self.headers(status="300 Internal Server Error")
            self.write("<h1>300 Internal Server Error</h1>")
            self.close()

    def handleAction(self, request):
        info = self.runAction(request)
        if not info:
            return {"status": "error", "payload": "unknown_key"}
        elif info == EOFError:
            return {"status": "error", "payload": "permission_denied"}
        else:
            return {"status": "good", "payload": info}

    def safePath(self, path):
        os.getcwd()

    def runAction(self, request):
        action = request.split("/")[1:][1].split("?")[0]
        if action == "stats":
            if not self.wrapper.config["Web"]["public-stats"]:
                return EOFError  # Why are we returning error objects and not just raising them?
            players = []
            for i in self.wrapper.javaserver.players:
                players.append({"name": i, "loggedIn": self.wrapper.javaserver.players[i].loggedIn,
                                "uuid": self.wrapper.javaserver.players[i].uuid.string})
            return {"playerCount": len(self.wrapper.javaserver.players), "players": players}
        if action == "login":
            password = get_req("password", request)
            rememberme = get_req("remember-me", request)
            if rememberme == "true":
                rememberme = True
            else:
                rememberme = False
            if self.web.checkLogin(password):
                key = self.web.makeKey(rememberme)
                self.log.warning("%s logged in to web mode (remember me: %s)", self.addr[0], rememberme)
                return {"session-key": key}
            else:
                self.log.warning("%s failed to login", self.addr[0])
            return EOFError
        if action == "is_admin":
            if self.web.validateKey(get_req("key", request)):
                return {"status": "good"}
            return EOFError
        if action == "logout":
            if self.web.validateKey(get_req("key", request)):
                self.web.removeKey(get_req("key", request))
                self.log.warning("[%s] Logged out.", self.addr[0])
                return "goodbye"
            return EOFError
        if action == "read_server_props":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            return open("%s/server.properties" % self.serverpath, "r").read()
        if action == "save_server_props":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            props = get_req("props", request)
            if not props:
                return False
            if len(props) < 10:
                return False
            with open("%s/server.properties" % self.serverpath, "w") as f:
                f.write(props)
            return "ok"
        if action == "listdir":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            if not self.wrapper.config["Web"]["web-allow-file-management"]:
                return EOFError
            safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWYXZ0123456789_-/ "
            pathunfiltered = get_req("path", request)
            path = ""
            for i in pathunfiltered:
                if i in safe:
                    path += i
            if path == "":
                path = "."
            files = []
            folders = []
            listdir = os.listdir(path)
            listdir.sort()
            for p in listdir:
                fullpath = path + "/" + p
                if p[-1] == "~":
                    continue
                if p[0] == ".":
                    continue
                if os.path.isdir(fullpath):
                    folders.append({"filename": p, "count": len(os.listdir(fullpath))})
                else:
                    files.append({"filename": p, "size": os.path.getsize(fullpath)})
            return {"files": files, "folders": folders}
        if action == "rename_file":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            if not self.wrapper.config["Web"]["web-allow-file-management"]:
                return EOFError
            workfile = get_req("path", request)
            rename = get_req("rename", request)
            if os.path.exists(workfile):
                try:
                    os.rename(workfile, rename)
                except Exception as e:
                    print(traceback.format_exc())
                    return False
                return True
            return False
        if action == "delete_file":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            if not self.wrapper.config["Web"]["web-allow-file-management"]:
                return EOFError
            workfile = get_req("path", request)
            if os.path.exists(workfile):
                try:
                    if os.path.isdir(workfile):
                        os.removedirs(workfile)
                    else:
                        os.remove(workfile)
                except Exception as e:
                    print(traceback.format_exc())
                    return False
                return True
            return False
        if action == "halt_wrapper":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            self.wrapper.shutdown()
        if action == "get_player_skin":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            if not self.wrapper.proxy:
                return {"error": "Proxy mode not enabled."}
            uuid = get_req("uuid", request)
            if uuid in self.wrapper.proxy.skins:
                skin = self.wrapper.proxy.getskintexture(uuid)
                if skin:
                    return skin
                else:
                    return None
            else:
                return None
        if action == "admin_stats":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            if not self.wrapper.javaserver:
                return
            refreshtime = float(get_req("last_refresh", request))
            players = []
            for i in self.wrapper.javaserver.players:
                player = self.wrapper.javaserver.players[i]
                players.append({
                    "name": i,
                    "loggedIn": player.loggedIn,
                    "uuid": player.uuid.string,
                    "isOp": player.isOp()
                })
            plugins = []
            for pid in self.wrapper.plugins:
                plugin = self.wrapper.plugins[pid]
                if plugin["good"]:
                    if plugin["description"]:
                        description = plugin["description"]
                    else:
                        description = None
                    plugins.append({
                        "name": plugin["name"],
                        "version": plugin["version"],
                        "description": description,
                        "summary": plugin["summary"],
                        "author": plugin["author"],
                        "website": plugin["website"],
                        # "version": (".".join([str(_) for _ in plugin["version"]])),
                        "id": pid,
                        "good": True
                    })
                else:
                    plugins.append({
                        "name": plugin["name"],
                        "good": False
                    })
            consolescrollback = []
            for line in self.web.consoleScrollback:
                if line[0] > refreshtime:
                    consolescrollback.append(line[1])
            chatscrollback = []
            for line in self.web.chatScrollback:
                if line[0] > refreshtime:
                    print(line[1])
                    chatscrollback.append(line[1])
            memorygraph = []
            for line in self.web.memoryGraph:
                if line[0] > refreshtime:
                    memorygraph.append(line[1])
            # totalPlaytime = {}
            # totalPlayers = self.web.api.minecraft.getAllPlayers()
            # for uu in totalPlayers:
            #   if not "logins" in totalPlayers[uu]:
            #       continue
            #   playerName = self.api.lookupbyUUID(uu)
            #   totalPlaytime[playerName] = [0, 0]
            #   for i in totalPlayers[uu]["logins"]:
            #       totalPlaytime[playerName][0] += totalPlayers[uu]["logins"][i] - int(i)
            #       totalPlaytime[playerName][1] += 1

            # secondstohuman was removed from here... a new version is in api.helpers, if needed later.

            topplayers = []
            # for i,username in enumerate(totalPlaytime):
            #   topPlayers.append((totalPlaytime[username][0], secondsToHuman(totalPlaytime[username][0]),
            #                                   totalPlaytime[username][1], username))
            #   if i == 9: break
            #   topPlayers.sort(); topPlayers.reverse()
            return {
                "playerCount": [len(self.wrapper.javaserver.players), self.wrapper.javaserver.maxPlayers],
                "players": players,
                "plugins": plugins,
                "server_state": self.wrapper.javaserver.state,
                "wrapper_build": self.wrapper.getbuildstring(),
                "console": consolescrollback,
                "chat": chatscrollback,
                "level_name": self.wrapper.javaserver.worldname,
                "server_version": self.wrapper.javaserver.version,
                "motd": self.wrapper.javaserver.motd,
                "refresh_time": time.time(),
                "server_name": self.wrapper.config["Web"]["server-name"],
                "server_memory": self.wrapper.javaserver.getmemoryusage(),
                "server_memory_graph": memorygraph,
                "world_size": self.wrapper.javaserver.worldSize,
                "disk_avail": self.wrapper.javaserver.getstorageavailable("."),
                "topPlayers": topplayers
            }
        if action == "console":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            self.wrapper.javaserver.console(get_req("execute", request))
            self.log.warning("[%s] Executed: %s", self.addr[0], get_req("execute", request))
            return True
        if action == "chat":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            message = get_req("message", request)
            self.web.chatScrollback.append((time.time(), {"type": "raw", "payload": "[WEB ADMIN] " + message}))
            self.wrapper.javaserver.broadcast("&c[WEB ADMIN]&r " + message)
            return True
        if action == "kick_player":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            player = get_req("player", request)
            reason = get_req("reason", request)
            self.log.warning("[%s] %s was kicked with reason: %s", self.addr[0], player, reason)
            self.wrapper.javaserver.console("kick %s %s" % (player, reason))
            return True
        if action == "ban_player":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            player = get_req("player", request)
            reason = get_req("reason", request)
            self.log.warning("[%s] %s was banned with reason: %s", self.addr[0], player, reason)
            self.wrapper.javaserver.console("ban %s %s" % (player, reason))
            return True
        if action == "change_plugin":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            plugin = get_req("plugin", request)
            state = get_req("state", request)
            if state == "enable":
                if plugin in self.wrapper.storage["disabled_plugins"]:
                    self.wrapper.storage["disabled_plugins"].remove(plugin)
                    self.log.warning("[%s] Enabled plugin '%s'", self.addr[0], plugin)
                    self.wrapper.reloadplugins()
            else:
                if plugin not in self.wrapper.storage["disabled_plugins"]:
                    self.wrapper.storage["disabled_plugins"].append(plugin)
                    self.log.warning("[%s] Disabled plugin '%s'", self.addr[0], plugin)
                    self.wrapper.reloadplugins()
        if action == "reload_plugins":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            self.wrapper.reloadplugins()
            return True
        if action == "server_action":
            if not self.web.validateKey(get_req("key", request)):
                return EOFError
            atype = get_req("action", request)
            if atype == "stop":
                reason = get_req("reason", request)
                self.wrapper.javaserver.stop_server_command(reason)
                self.log.warning("[%s] Server stop with reason: %s", self.addr[0], reason)
                return "success"
            elif atype == "restart":
                reason = get_req("reason", request)
                self.wrapper.javaserver.restart(reason)
                self.log.warning("[%s] Server restart with reason: %s", self.addr[0], reason)
                return "success"
            elif atype == "start":
                reason = get_req("reason", request)
                self.wrapper.javaserver.start()
                self.log.warning("[%s] Server started", self.addr[0])
                return "success"
            elif atype == "kill":
                self.wrapper.javaserver.kill()
                self.log.warning("[%s] Server killed.", self.addr[0])
                return "success"
            return {"error": "invalid_server_action"}
        return False

    def getcontenttype(self, filename):
        ext = filename[filename.rfind("."):][1:]
        if ext == "js":
            return "application/javascript"
        if ext == "css":
            return "text/css"
        if ext in ("txt", "html"):
            return "text/html"
        if ext == "ico":
            return "image/x-icon"
        return "application/octet-stream"

    def get(self, request):
        print("GET request: %s" % request)
        if request == "/":
            workfile = "index.html"
        elif request.split("/")[1:][0] == "action":
            try:
                self.write(json.dumps(self.handleAction(request)))
            except Exception as e:
                self.headers(status="300 Internal Server Error")
                print(traceback.format_exc())
            self.close()
            return False
        else:
            workfile = request.replace("..", "").replace("%", "").replace("\\", "")
        if workfile == "/admin.html":
            self.headers(status="301 Go Away", location="/admin")
            return False
        if workfile == "/login.html":
            self.headers(status="301 Go Away", location="/login")
            return False
        if workfile == ".":
            self.headers(status="400 Bad Request")
            self.write("<h1>BAD REQUEST</h1>")
            self.close()
            return False
        #try:
        print("\n\nworkfile: %s\n\n" % workfile)
        if workfile == "/admin":
            workfile = "admin.html"
        if workfile == "/login":
            workfile = "login.html"
        print("\n\nworkfile: %s\n\n" % workfile)
        data = self.read(workfile)
        self.headers(contenttype=self.getcontenttype(workfile))
        self.write(data)
        #except Exception as e:
            #self.headers(status="404 Not Found (exception in get)")
            #self.write("<h1>404 Not Found (exception in get)</h4>")
        self.close()

    def handle(self):
        while True:
            try:
                data = self.socket.recv(1024)
                if len(data) < 1:
                    self.close()
                    return
                # self.buffer = data.split("\n")  # TODO replace all new_buffer with self.buffer to restore back
                new_buffer = data.split("\n")
            except Exception as e:
                self.close()
                # self.log.debug("(WEB) Connection %s closed", str(self.addr))
                break
            if len(new_buffer) < 1:
                print("Web connection closed suddenly")
                return False
            for line in new_buffer:
                if getargs(line.split(" "), 0) == "GET":
                    self.get(getargs(line.split(" "), 1))
                if getargs(line.split(" "), 0) == "POST":
                    self.request = getargs(line.split(" "), 1)
                    self.headers(status="400 Bad Request")
                    self.write("<h1>Invalid request. Sorry.</h1>")
