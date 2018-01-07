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

from api.helpers import getargs, getargsafter
from core.storage import Storage

import urllib

try:
    import pkg_resources
    import requests
except ImportError:
    pkg_resources = False
    requests = False


# noinspection PyBroadException
class Web(object):
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.api = wrapper.api
        self.log = logging.getLogger('Web')
        self.config = wrapper.config
        self.pass_handler = self.wrapper.cipher
        self.socket = False
        self.storage = Storage("web", pickle=False)
        self.data = self.storage.Data
        if "keys" not in self.data:
            self.data["keys"] = []

        self.api.registerEvent("server.consoleMessage", self.on_server_console)
        self.api.registerEvent("player.message", self.on_player_message)
        self.api.registerEvent("player.join", self.on_player_join)
        self.api.registerEvent("player.leave", self.on_player_leave)
        self.api.registerEvent("irc.message", self.on_channel_message)
        self.consoleScrollback = []
        self.chatScrollback = []
        self.memoryGraph = []
        self.loginAttempts = 0
        self.lastAttempt = 0
        self.disableLogins = 0

        # t = threading.Thread(target=self.update_graph, args=())
        # t.daemon = True
        # t.start()

    def on_server_console(self, payload):
        while len(self.consoleScrollback) > 1000:
            try:
                del self.consoleScrollback[0]
            except:
                break
        self.consoleScrollback.append((time.time(), payload["message"]))

    def on_player_message(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except:
                break
        self.chatScrollback.append((time.time(), {"type": "player",
                                                  "payload": {
                                                      "player": payload[
                                                          "player"].username,
                                                      "message": payload[
                                                          "message"]}}))

    def on_player_join(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except:
                break
        self.chatScrollback.append((time.time(), {"type": "playerJoin",
                                                  "payload": {
                                                      "player": payload[
                                                          "player"].username}}))

    def on_player_leave(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except:
                break
        self.chatScrollback.append((time.time(), {"type": "playerLeave",
                                                  "payload": {
                                                      "player": payload[
                                                          "player"].username}}))

    def on_channel_message(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                del self.chatScrollback[0]
            except:
                break
        self.chatScrollback.append(
            (time.time(), {"type": "irc", "payload": payload}))

    def update_graph(self):
        while not self.wrapper.halt.halt:
            while len(self.memoryGraph) > 200:
                del self.memoryGraph[0]
            if self.wrapper.javaserver.getmemoryusage():
                self.memoryGraph.append(
                    [time.time(), self.wrapper.javaserver.getmemoryusage()])
            time.sleep(1)

    def check_login(self, password):
        if time.time() - self.disableLogins < 60:
            return False  # Threshold for logins
        if self.pass_handler.check_pw(password, self.config["Web"]["web-password"]):
            return True
        self.loginAttempts += 1
        if self.loginAttempts > 10 and time.time() - self.lastAttempt < 60:
            self.disableLogins = time.time()
            self.log.warn("Disabled login attempts for one minute")
        self.lastAttempt = time.time()

    def make_key(self, remember_me):
        a = ""
        z = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@-_"
        for i in range(64):
            a += z[random.randrange(0, len(z))]
        # a += chr(random.randrange(97, 122))
        self.data["keys"].append([a, time.time(), remember_me])
        return a

    def validate_key(self, key):
        for i in self.data["keys"]:
            expire_time = 2592000
            if len(i) > 2:
                if i[2]:
                    expire_time = 21600
            if i[0] == key and time.time() - i[1] < expire_time:  # Validate key and ensure it's under a week old
                self.loginAttempts = 0
                return True
        return False

    def remove_key(self, key):
        for i, v in enumerate(self.data["keys"]):
            if v[0] == key:
                del self.data["keys"][i]

    def wrap(self):
        while not self.wrapper.halt.halt:
            try:
                if self.bind():
                    # cProfile.run("self.listen()", "cProfile-debug")
                    self.listen()
                else:
                    self.log.error(
                        "Could not bind web to %s:%d - retrying in 5 seconds" % (
                            self.config["Web"]["web-bind"],
                            self.config["Web"]["web-port"]))
            except:
                for line in traceback.format_exc().split("\n"):
                    self.log.error(line)
            time.sleep(5)

    def bind(self):
        if self.socket is not False:
            self.socket.close()
        try:
            self.socket = socket.socket()
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.config["Web"]["web-bind"],
                              self.config["Web"]["web-port"]))
            self.socket.listen(5)
            return True
        except:
            return False

    def listen(self):
        self.log.info("Web Interface bound to %s:%d" % (
            self.config["Web"]["web-bind"], self.config["Web"]["web-port"]))
        while not self.wrapper.halt.halt:
            sock, addr = self.socket.accept()
            # self.log.debug("(WEB) Connection %s started" % str(addr))
            client = Client(self.wrapper, sock, addr, self)
            # t = threading.Thread(target=cProfile.runctx, args=("client.wrap()", globals(), locals(), "cProfile-debug"))
            # t.daemon = True
            # t.start()
            t = threading.Thread(target=client.wrap, args=())
            t.daemon = True
            t.start()


# noinspection PyBroadException
class Client(object):
    def __init__(self, wrapper, socket_conn, addr, web):
        self.wrapper = wrapper
        self.config = wrapper.config
        self.socket = socket_conn
        self.addr = addr
        self.web = web
        self.request = ""
        self.log = wrapper.log
        self.api = wrapper.api
        self.socket.setblocking(30)
        self.command_payload = {"args": ""}
        self.web_admin = self.wrapper.xplayer

    def read(self, filename):
        return pkg_resources.resource_stream(__name__,
                                             "html/%s" % filename).read()

    def write(self, message):
        self.socket.send(message)

    def headers(self, status="200 Good", content_type="text/html", location=""):
        self.write("HTTP/1.0 %s\n" % status)
        if len(location) < 1:
            self.write("Content-Type: %s\n" % content_type)

        if len(location) > 0:
            self.write("Location: %s\n" % location)

        self.write("\n")

    def close(self):
        try:
            self.socket.close()
        # self.log.debug("(WEB) Connection %s closed" % str(self.addr))
        except:
            pass

    def wrap(self):
        try:
            self.handle()
        except:
            error_is = traceback.format_exc()
            self.log.error("Internal error while handling web mode request:")
            self.log.error(error_is)
            self.headers(status="300 Internal Server Error")
            self.write("<h1>300 Internal Server Error</h1>\n\n%s" % error_is)
            self.close()

    def handle_action(self, request):
        # def args(i):
        #    try:
        #        return request.split("/")[1:][i]
        #    except:
        #        return ""

        # def get(i):
        #    for a in args(1).split("?")[1].split("&"):
        #        if a[0:a.find("=")]:
        #            return urllib.unquote(a[a.find("=") + 1:])
        #    return ""

        info = self.run_action(request)
        if not info:
            return {"status": "error", "payload": "unknown_key"}
        elif info == EOFError:
            return {"status": "error", "payload": "permission_denied"}
        else:
            return {"status": "good", "payload": info}

    def run_action(self, request):
        def args(index):
            try:
                return request.split("/")[1:][index]
            except:
                return ""

        def get(index):
            for a in args(1).split("?")[1].split("&"):
                if a[0:a.find("=")] == index:
                    return urllib.unquote(a[a.find("=") + 1:])
            return ""

        action = args(1).split("?")[0]
        if action == "stats":
            if not self.config["Web"]["public-stats"]:
                return EOFError
            players = []
            for i in self.wrapper.servervitals.players:
                players.append(
                    {"name": i,
                     "loggedIn": self.wrapper.servervitals.players[i].loggedIn,
                     "uuid": str(self.wrapper.servervitals.players[i].mojangUuid)
                     })
            return {"playerCount": len(self.wrapper.servervitals.players),
                    "players": players}
        if action == "login":
            password = get("password")
            remember_me = get("remember-me")
            if remember_me == "true":
                remember_me = True
            else:
                remember_me = False
            if self.web.check_login(password):
                key = self.web.make_key(remember_me)
                self.log.warn("%s logged in to web mode (remember me: %s)" % (
                    self.addr[0], remember_me))
                return {"session-key": key}
            else:
                self.log.warn("%s failed to login" % self.addr[0])
            return EOFError
        if action == "is_admin":
            if self.web.validate_key(get("key")):
                return {"status": "good"}
            return EOFError
        if action == "logout":
            if self.web.validate_key(get("key")):
                self.web.remove_key(get("key"))
                self.log.warn("[%s] Logged out." % self.addr[0])
                return "goodbye"
            return EOFError
        if action == "read_server_props":
            if not self.web.validate_key(get("key")):
                return EOFError
            return open("server.properties", "r").read()
        if action == "save_server_props":
            if not self.web.validate_key(get("key")):
                return EOFError
            props = get("props")
            if not props:
                return False
            if len(props) < 10:
                return False
            with open("server.properties", "w") as f:
                f.write(props)
            return "ok"
        if action == "listdir":
            if not self.web.validate_key(get("key")):
                return EOFError
            if not self.config["Web"]["web-allow-file-management"]:
                return EOFError
            safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWYXZ0123456789_-/ "
            path_unfiltered = get("path")
            path = ""
            for i in path_unfiltered:
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
                    folders.append(
                        {"filename": p, "count": len(os.listdir(fullpath))})
                else:
                    files.append(
                        {"filename": p, "size": os.path.getsize(fullpath)})
            return {"files": files, "folders": folders}
        if action == "rename_file":
            if not self.web.validate_key(get("key")):
                return EOFError
            if not self.config["Web"]["web-allow-file-management"]:
                return EOFError
            ren_file = get("path")
            rename = get("rename")
            if os.path.exists(ren_file):
                try:
                    os.rename(ren_file, rename)
                except:
                    print(traceback.format_exc())
                    return False
                return True
            return False
        if action == "delete_file":
            if not self.web.validate_key(get("key")):
                return EOFError
            if not self.config["Web"]["web-allow-file-management"]:
                return EOFError
            del_file = get("path")
            if os.path.exists(del_file):
                try:
                    if os.path.isdir(del_file):
                        os.removedirs(del_file)
                    else:
                        os.remove(del_file)
                except:
                    print(traceback.format_exc())
                    return False
                return True
            return False
        if action == "halt_wrapper":
            if not self.web.validate_key(get("key")):
                return EOFError
            self.wrapper.shutdown()
        if action == "get_player_skin":
            if not self.web.validate_key(get("key")):
                return EOFError
            if not self.wrapper.proxymode:
                return {"error": "Proxy mode not enabled."}
            uuid = get("uuid")
            if uuid in self.wrapper.proxy.skins:
                skin = self.wrapper.proxy.getSkinTexture(uuid)
                if skin:
                    return skin
                else:
                    return None
            else:
                return None
        if action == "admin_stats":
            if not self.web.validate_key(get("key")):
                return EOFError
            if not self.wrapper.javaserver:
                return
            refresh_time = float(get("last_refresh"))
            players = []
            for i in self.wrapper.servervitals.players:
                player = self.wrapper.servervitals.players[i]
                players.append({
                    "name": i,
                    "loggedIn": player.loggedIn,
                    "uuid": str(player.uuid),
                    "isOp": player.isOp()
                })
            plugins = []
            for plugid in self.wrapper.plugins:
                plugin = self.wrapper.plugins[plugid]
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
                        "id": plugid,
                        "good": True
                    })
                else:
                    plugins.append({
                        "name": plugin["name"],
                        "good": False
                    })
            console_scrollback = []
            for line in self.web.consoleScrollback:
                if line[0] > refresh_time:
                    console_scrollback.append(line[1])
            chat_scrollback = []
            for line in self.web.chatScrollback:
                if line[0] > refresh_time:
                    chat_scrollback.append(line[1])
            memory_graph = []
            for line in self.web.memoryGraph:
                if line[0] > refresh_time:
                    memory_graph.append(line[1])
            return {"playerCount": len(self.wrapper.servervitals.players),
                    "players": players,
                    "plugins": plugins,
                    "server_state": self.wrapper.servervitals.state,
                    "wrapper_build": self.wrapper.getbuildstring(),
                    "console": console_scrollback,
                    "chat": chat_scrollback,
                    "level_name": self.wrapper.servervitals.worldName,
                    "server_version": self.wrapper.servervitals.version,
                    "motd": self.wrapper.servervitals.motd,
                    "refresh_time": time.time(),
                    "server_name": self.config["Web"]["server-name"],
                    "server_memory": self.wrapper.server.getmemoryusage(),
                    "server_memory_graph": memory_graph,
                    "world_size": self.wrapper.server.worldSize}
        if action == "console":
            if not self.web.validate_key(get("key")):
                return EOFError
            self.wrapper.javaserver.console(get("execute"))
            self.log.warn("[%s] Executed: %s" % (self.addr[0], get("execute")))
            return True
        if action == "chat":
            if not self.web.validate_key(get("key")):
                return EOFError
            message = get("message")
            self.web.chatScrollback.append((time.time(), {"type": "raw",
                                                          "payload": "[WEB ADMIN] " + message}))
            self.wrapper.javaserver.broadcast("&c[WEB ADMIN]&r " + message)
            return True
        if action == "kick_player":
            if not self.web.validate_key(get("key")):
                return EOFError
            player = get("player")
            reason = get("reason")
            self.log.warn("[%s] %s was kicked with reason: %s" % (self.addr[0], player, reason))
            self.wrapper.javaserver.console("kick %s %s" % (player, reason))
            return True
        if action == "ban_player":
            if not self.web.validate_key(get("key")):
                return EOFError
            player = get("player")
            reason = get("reason")
            self.log.warn("[%s] %s was banned with reason: %s" % (self.addr[0], player, reason))
            self.wrapper.javaserver.console("ban %s %s" % (player, reason))
            return True
        if action == "change_plugin":
            if not self.web.validate_key(get("key")):
                return EOFError
            plugin = get("plugin")
            state = get("state")
            if state == "enable":
                if plugin in self.wrapper.storage["disabled_plugins"]:
                    self.wrapper.storage["disabled_plugins"].remove(plugin)
                    self.log.warn("[%s] Set plugin enabled: '%s'" % (self.addr[0], plugin))
                    self.wrapper.commands.command_reload(self.web_admin,
                                                         self.command_payload)
            else:
                if plugin not in self.wrapper.storage["disabled_plugins"]:
                    self.wrapper.storage["disabled_plugins"].append(plugin)
                    self.log.warn("[%s] Set plugin disabled: '%s'" % (self.addr[0], plugin))
                    self.wrapper.commands.command_reload(self.web_admin,
                                                         self.command_payload)
        if action == "reload_plugins":
            if not self.web.validate_key(get("key")):
                return EOFError
            self.wrapper.commands.command_reload(self.web_admin,
                                                 self.command_payload)
            return True
        if action == "server_action":
            if not self.web.validate_key(get("key")):
                return EOFError
            command = get("action")
            if command == "stop":
                reason = get("reason")
                self.wrapper.javaserver.stop(reason)
                self.log.warn("[%s] Server stop with reason: %s" % (self.addr[0], reason))
                return "success"
            elif command == "restart":
                reason = get("reason")
                self.wrapper.javaserver.restart(reason)
                self.log.warn("[%s] Server restart with reason: %s" % (self.addr[0], reason))
                return "success"
            elif command == "start":
                self.wrapper.javaserver.start()
                self.log.warn("[%s] Server started" % (self.addr[0]))
                return "success"
            elif command == "kill":
                self.wrapper.javaserver.kill()
                self.log.warn("[%s] Server killed." % self.addr[0])
                return "success"
            return {"error": "invalid_server_action"}
        return False

    def get_content_type(self, filename):
        ext = filename[filename.rfind("."):][1:]
        if ext == "js":
            return "application/javascript"
        if ext == "css":
            return "text/css"
        if ext in ("txt", "html"):
            return "text/html"
        if ext in ("ico",):
            return"image/x-icon"
        return "application/octet-stream"

    def get(self, request):
        # print("GET request: %s" % request)

        def args(i):
            try:
                return request.split("/")[1:][i]
            except:
                return ""
        fn_path = request.split(" ")
        if fn_path[0] == "/":
            filename = "index.html"
        elif args(0) == "action":
            try:
                self.write(json.dumps(self.handle_action(request)))
            except:
                self.headers(status="300 Internal Server Error")
                print(traceback.format_exc())
            self.close()
            return False
        else:
            filename = fn_path[0]
            #filename = request.replace("..", "").replace("%", "").replace("\\", "")
        # print(filename)
        if filename == "/admin":
            filename = "/admin.html"  # alias /admin as /admin.html
        if filename == ".":
            self.headers(status="400 Bad Request")
            self.write("<h1>BAD REQUEST</h1>")
            self.close()
            return False
        try:
            data = self.read(filename)
            self.headers(content_type=self.get_content_type(filename))
            self.write(data)
        except:
            self.headers(status="404 Not Found")
            self.write("<h1>404 Not Found</h4>")
        self.close()

    def handle(self):
        while True:
            try:
                data = self.socket.recv(1024)
                if len(data) < 1:
                    self.close()
                    return
                buff = data.split("\n")
            except:
                self.close()
                # self.log.debug("(WEB) Connection %s closed" % str(self.addr))
                break
            if len(buff) < 1:
                print("Web connection closed suddenly")
                return False
            for line in buff:
                args = line.split(" ")
                # def args(i):
                #    try:
                #        return line.split(" ")[i]
                #    except:
                #        return ""

                # def argsAfter(i):
                #    try:
                #        return " ".join(line.split(" ")[i:])
                #    except:
                #        return ""

                if getargs(args, 0) == "GET":
                    # intent not clear to me in original code:
                    #  #self.get(args(1))

                    # self.get(getargs(args, 1)) or (as I am guessing):
                    self.get(getargsafter(args, 1))

                if getargs(args, 0) == "POST":
                    self.request = getargsafter(args, 1)
                    self.headers(status="400 Bad Request")
                    self.write("<h1>Invalid request. Sorry.</h1>")
