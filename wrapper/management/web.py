# -*- coding: utf-8 -*-

# Copyright (C) 2014 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.
from __future__ import print_function
from __future__ import absolute_import

import copy
import traceback
import threading
import time
import json
import random
import os
import logging
import socket

from api.helpers import getargs, mkdir_p
from core.storage import Storage
from core.consoleuser import ConsolePlayer
from utils.py23 import py_str, py_bytes

try:
    from shutil import disk_usage
except ImportError:
    disk_usage = False

try:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import unquote as urllib_unquote
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib import unquote as urllib_unquote

try:
    import requests
except ImportError:
    requests = False

try:
    import pkg_resources
except ImportError:
    pkg_resources = False

DISCLAIMER = "Web mode is a beta feature and does not use HTTPS to send your " \
             "password to the server (just uses a plain-text HTTP GET).  " \
             "Besides password protection, we also have a setting in the " \
             "'Web' section to    only allow only certain IPs to connect.  If " \
             "you need to use web remotely, it is recommended to turn this " \
             "feature on and add the IP address from where you will be using " \
             "the web interface into the 'safe-ips' config item.  That said" \
             "... never use the same password for Web that you use anywhere " \
             "else (like your banking or email accounts).  This password " \
             "is passed over the connection unencrypted, exactly as you " \
             "typed it into the browser password field.."


# noinspection PyBroadException
class Web(object):
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.api = wrapper.api
        self.log = logging.getLogger('Web')
        self.config = wrapper.config
        self.serverpath = self.config["General"]["server-directory"]
        self.pass_handler = self.wrapper.cipher
        self.socket = False
        self.storage = Storage("web", pickle=False)
        self.data = self.storage.Data
        self.xplayer = ConsolePlayer(self.wrapper, self.console_output)

        self.adminname = "Web Admin"
        self.xplayer.username = self.adminname

        self.onlyusesafe_ips = self.config["Web"]["safe-ips-use"]
        self.safe_ips = self.config["Web"]["safe-ips"]

        if "keys" not in self.data:
            self.data["keys"] = []

        # Register events
        self.api.registerEvent("server.consoleMessage", self.on_server_console)
        self.api.registerEvent("player.message", self.on_player_message)
        self.api.registerEvent("player.login", self.on_player_join)
        self.api.registerEvent("player.logout", self.on_player_leave)
        self.api.registerEvent("irc.message", self.on_channel_message)

        self.consoleScrollback = []
        self.chatScrollback = []
        self.memoryGraph = []
        self.loginAttempts = 0
        self.lastAttempt = 0
        self.disableLogins = 0
        self.props = ""
        self.propsCount = 0
        # t = threading.Thread(target=self.update_graph, args=())
        # t.daemon = True
        # t.start()

    # ================ Start  and Run code section ================
    # ordered by the time they are referenced in the code.

    # def update_graph(self):
    #     while not self.wrapper.haltsig.halt:
    #         while len(self.memoryGraph) > 200:
    #             del self.memoryGraph[0]
    #         if self.wrapper.javaserver.getmemoryusage():
    #             self.memoryGraph.append(
    #                 [time.time(), self.wrapper.javaserver.getmemoryusage()])
    #        time.sleep(1)

    def wrap(self):
        """ Wrapper starts excution here (via a thread). """
        if not pkg_resources:
            self.log.error("`pkg_resources` is not installed.  It is usually "
                           "distributed with setuptools. Check https://stackov"
                           "erflow.com/questions/7446187/no-module-named-pkg-r"
                           "esources for possible solutions")
            return 
        
        while not self.wrapper.haltsig.halt:
            try:
                if self.bind():
                    # cProfile.run("self.listen()", "cProfile-debug")
                    self.listen()
                else:
                    self.log.error(
                        "Could not bind web to %s:%d - retrying in 5"
                        " seconds" % (
                            self.config["Web"]["web-bind"],
                            self.config["Web"]["web-port"]
                        )
                    )
            except:
                for line in traceback.format_exc().split("\n"):
                    self.log.error(line)
            time.sleep(5)
        # closing also calls storage.save().
        self.storage.close()

    def bind(self):
        """ Started by self.wrap() to bind socket. """
        if self.socket is not False:
            self.socket.close()
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.config["Web"]["web-bind"],
                              self.config["Web"]["web-port"]))
            self.socket.listen(5)
            return True
        except:
            return False

    def listen(self):
        """ Excuted by self.wrap() to listen for client(s). """
        self.log.info("Web Interface bound to %s:%d" % (
            self.config["Web"]["web-bind"], self.config["Web"]["web-port"]))
        while not self.wrapper.haltsig.halt:
            # noinspection PyUnresolvedReferences
            sock, addr = self.socket.accept()
            if self.onlyusesafe_ips:
                if addr[0] not in self.safe_ips:
                    sock.close()
                    self.log.info(
                        "Sorry charlie (an unathorized IP %s attempted "
                        "connection)", addr[0]
                    )
                    continue
            client = Client(self.wrapper, sock, addr, self)

            t = threading.Thread(target=client.wrap, args=())
            t.daemon = True
            t.start()
        self.storage.save()

    def console_output(self, message):
        display = str(message)
        if type(message) is dict:
            if "text" in message:
                display = message["text"]
        self.on_server_console({"message": display})

    # ========== EVENTS SECTION ==========================

    def on_server_console(self, payload):
        while len(self.consoleScrollback) > 1000:
            try:
                self.consoleScrollback.pop()
            except:
                break
        self.consoleScrollback.append((time.time(), payload["message"]))

    def on_player_message(self, payload):
        while len(self.chatScrollback) > 200:
            try:
                self.chatScrollback.pop()
            except:
                break
        self.chatScrollback.append(
            [time.time(), {"type": "player",
                           "payload": {"player": payload["player"].username,
                                       "message": payload["message"]}}])

    def on_player_join(self, payload):
        # abrupt disconnections can cause player on-join although player is
        # not on...
        if not payload["player"]:
            return
        while len(self.chatScrollback) > 200:
            self.chatScrollback.pop()
        self.chatScrollback.append([
            time.time(), {"type": "playerJoin",
                          "payload": {"player": payload["player"].username}}])

    def on_player_leave(self, payload):
        while len(self.chatScrollback) > 200:
            self.chatScrollback.pop()
        self.chatScrollback.append([
            time.time(), {"type": "playerLeave",
                          "payload": {"player": payload["player"].username}}])

    def on_channel_message(self, payload):
        while len(self.chatScrollback) > 200:
            self.chatScrollback.pop()
        self.chatScrollback.append([
            time.time(), {"type": "irc", "payload": payload}])

    # ========== Externally-called Methods section ==========================

    def check_login(self, password):
        """
        Returns True or False to indicate login success.
         - Called by client.run_action, action="login"
        """

        # Threshold for logins
        if time.time() - self.disableLogins < 60:
            self.loginAttempts = 0
            return None

        # check password validity
        if self.pass_handler.check_pw(password, self.config["Web"]["web-password"]):  # noqa
            return True

        # unsuccessful password attempt
        self.loginAttempts += 1
        if self.loginAttempts > 4 and time.time() - self.lastAttempt < 60:
            self.disableLogins = time.time()
            self.log.warning("Disabled login attempts for one minute")
        self.lastAttempt = time.time()
        return False

    def make_key(self, remember_me, username):
        a = ""
        z = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        for i in range(64):
            a += z[random.randrange(0, len(z))]
        # a += chr(random.randrange(97, 122))
        self.data["keys"].append([a, time.time(), remember_me, username])
        return a

    def validate_key(self, key):
        # day = 86400
        week = 604800
        curr_time = int(time.time())
        old_keys = []
        success = False

        for i in self.data["keys"]:
            if len(i) > 2:
                expire_time = int(i[1])
                remembered = i[2]
                user = getargs(i, 3)
                if user != "":
                    self.adminname = user

                # even "remembereds" should expire after a week after last use
                if remembered:
                    expire_time += week

                if curr_time - expire_time > week:  # or day or whatever
                    # remove expired keys
                    old_keys.append(i[0])
                else:
                    if i[0] == key:  # Validate key
                        if remembered:
                            # remembereds are reset at each successful login:
                            self.update_key(i, 1, curr_time)
                        self.loginAttempts = 0
                        success = True
            else:
                # remove bad malformed keys
                old_keys.append(i[0])

        for oldkey in old_keys:
            self.remove_key(oldkey)
        self.storage.save()
        return success

    def update_key(self, key, field_number, data):
        for i, v in enumerate(self.data["keys"]):
            if v[0] == key:
                self.data["keys"][i][field_number] = data

    def remove_key(self, key):
        for i, v in enumerate(self.data["keys"]):
            if v[0] == key:
                del self.data["keys"][i]

    def getdisk_usage(self):
        """only works on Python 3.  returns 0 for Python 2"""
        if disk_usage:
            # noinspection PyCallingNonCallable
            spaces = disk_usage(self.serverpath)
            frsp = spaces.free
            return frsp
        return int(0)


# noinspection PyBroadException
class Client(object):
    """ Client socket handler- Web and Client function together as a server. """
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

    @staticmethod
    def read(filename):
        ret_object = pkg_resources.resource_stream(__name__,
                                                   "html/%s" % filename).read()
        return ret_object

    def write(self, message):
        if type(message) is str:
            message = py_bytes(message, self.wrapper.encoding)
        self.socket.send(message)

    # noinspection PyBroadException
    def close(self):
        try:
            self.socket.close()
        except:
            pass

    def headers(self, status="200 Good", content_type="text/html", location=""):
        self.write("HTTP/1.1 %s\r\n" % status)
        self.write("Content-Type: %s\r\n" % content_type)
        if len(location) > 0:
            self.write("Location: %s\r\n" % location)
        self.write("\r\n")

    @staticmethod
    def get_content_type(filename):
        ext = filename.split(".")[-1]
        if ext == "js":
            return "application/javascript"
        if ext == "css":
            return "text/css"
        if ext in ("txt", "html"):
            return "text/html"
        if ext in ("ico",):
            return"image/x-icon"
        return "application/octet-stream"

    def wrap(self):
        try:
            self.handle()
        except:
            error_is = traceback.format_exc()
            self.log.error("Internal error while handling web mode request:")
            self.log.error(error_is)
            self.headers(status="300 Internal Server Error")
            self.write("<h1>300 Internal Server Error</h1>\r\n%s" % error_is)
            self.close()

    def handle(self):
        while not self.wrapper.haltsig.halt:

            # read data from socket
            try:
                data = self.socket.recv(1024)
                if len(data) < 1:
                    self.close()
                    return

                str_data = py_str(data, self.wrapper.encoding)
                buff = str_data.split("\r\n")
            except:
                self.close()
                break

            if len(buff) < 1:
                self.log.debug("Connection closed abnormally")
                return False

            for line in buff:
                args = line.split(" ")

                if getargs(args, 0) == "GET":
                    self.get(getargs(args, 1))

                if getargs(args, 0) == "POST":
                    self.request = getargs(args, 1)
                    self.headers(status="400 Bad Request")
                    self.write("<h1>Invalid request. Sorry.</h1>")
        self.close()

    def get(self, request):

        if request in ("/", "index"):
            request = "/index.html"
        elif request == "/admin":
            request = "/admin.html"
        elif request == ".":
            self.headers(status="400 Bad Request")
            self.write("<h1>BAD REQUEST</h1>")
            self.close()
            return
        # Process actions
        elif request[0:7] == "/action":
            try:
                raw_dump = json.dumps(self.handle_action(request))
                self.headers()
                self.write(raw_dump)
                self.close()
            except:
                self.headers(status="300 Internal Server Error")
                print(traceback.format_exc())
                self.close()
            return

        try:
            data = self.read(request)
            contenttype = self.get_content_type(request)
            self.headers(content_type=contenttype, location=request)
            self.write(data)
        except:
            self.headers(status="404 Not Found")
            self.write("<h1>404 Not Found</h4>")
        self.close()

    def handle_action(self, request):

        info = self.run_action(request)
        if not info:
            return {"status": "error", "payload": "unknown_key"}
        elif info == EOFError:
            return {"status": "error", "payload": "permission_denied"}
        elif info == LookupError:
            return {"status": "error", "payload": "timed_out"}
        else:
            return {"status": "good", "payload": info}

    def run_action(self, request):
        # Entire requested action
        request_action = request.split("/")[2] or ""

        # split the action into two parts - action and args
        action_parts = request_action.split("?")

        # get the action - read_server_props, halt_wrapper, server_action, etc
        action = action_parts[0]

        # develop args into a dictionary for later
        action_arg_list = action_parts[1].split("&")
        argdict = {"key": ""}
        for argument in action_arg_list:
            argparts = argument.split("=")
            argname = argument.split("=")[0]
            if len(argparts) > 1:
                value = argparts[1]
                value = value.replace("%2F", "/").replace("+", " ")
            else:
                value = ""
            argdict[argname] = value

        # convert %xx items from argument values
        scrubs = {
            "+": " ",
            "%20": " ",
            "%21": "!",
            '%23': "#",
            '%24': "$",
            "%26": "&",
            "%27": "'",
            "%28": "(",
            "%29": ")",
            "%2B": "+",
            "%2F": "/",
            "%3D": "=",
            "%3A": ":",
            "%3B": ";",
            "%40": "@",
            "%7E": "~",
            "%22": "\"",
            "%25": "%",
            "%3C": "<",
            "%3E": ">",
            "%3F": "?",
            "%5B": "[",
            "%5C": "\\",
            "%5E": "^",
            "%7C": "|",
            "%7B": "{",
            "%7D": "}",
        }
        for arguments in argdict:
            temparg = copy.copy(argdict[arguments])
            for scrub in scrubs:
                temparg = temparg.replace(scrub, scrubs[scrub])
            argdict[arguments] = temparg

        if action == "login":
            password = argdict["password"]
            remember_me = argdict["remember-me"]
            user = argdict["username"]
            if remember_me == "true":
                remember_me = True
            else:
                remember_me = False
            log_status = self.web.check_login(password)
            if log_status:
                key = self.web.make_key(remember_me, user)
                self.log.info(
                    "%s/%s logged in to web mode (remember me: %s)" % (
                     self.addr[0], user, remember_me))
                return {"session-key": key}
            elif log_status is None:
                return LookupError
            else:
                self.log.warning("%s failed to login" % self.addr[0])
                return EOFError

        if action == "is_admin":
            if self.web.validate_key(argdict["key"]):
                return {"status": "good"}
            return EOFError

        if action == "logout":
            if self.web.validate_key(argdict["key"]):
                self.web.remove_key(argdict["key"])
                self.web.storage.save()
                self.log.info("[%s] Logged out." % self.addr[0])
                return "goodbye"
            return EOFError

        if action == "read_server_props":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            with open("%s/server.properties" % self.web.serverpath, 'r') as f:
                file_contents = f.read()
            return file_contents

        if action == "send_server_props":
            # no need for this
            # if not self.web.validate_key(argdict["key"]):
            #     return EOFError
            prop = argdict["prop"]
            if self.web.props == "":
                self.web.props += prop
            else:
                self.web.props += '\n' + prop
            self.web.propsCount += 1
            return "ok"

        if action == "save_server_props":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            prop_count = int(argdict["propCount"])
            if prop_count != self.web.propsCount:
                return False
            props = copy.copy(self.web.props)
            self.web.props = ""
            self.web.propsCount = 0
            with open("%s/server.properties" % self.web.serverpath, 'w') as f:
                f.write(props)
            return "ok"

        if action == "listdir":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            if not self.config["Web"]["web-allow-file-management"]:
                return EOFError
            safe = ".abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWYXZ0123456789_-/ "  # noqa
            path_unfiltered = argdict["path"]
            path = ""
            for i in path_unfiltered:
                if i in safe:
                    path += i
            if path == "":
                path = "."
            files = []
            folders = []
            try:
                listdir = os.listdir(path)
            except:
                return EOFError

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

        if action == "add_directory":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            if not self.config["Web"]["web-allow-file-management"]:
                return EOFError
            sourcefolder = argdict["source_dir"]
            newfolder = argdict["new_dir"]
            mkdir_p(sourcefolder + "/" + newfolder)
            return "ok"

        if action == "rename_file":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            if not self.config["Web"]["web-allow-file-management"]:
                return EOFError
            ren_file = argdict["path"]
            rename = argdict["rename"]
            if os.path.exists(ren_file):
                try:
                    os.rename(ren_file, rename)
                except:
                    print(traceback.format_exc())
                    return False
                return "ok"
            return False

        if action == "delete_file":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            if not self.config["Web"]["web-allow-file-management"]:
                return EOFError
            del_file = argdict["path"]
            if os.path.exists(del_file):
                try:
                    if os.path.isdir(del_file):
                        os.removedirs(del_file)
                    else:
                        os.remove(del_file)
                except Exception as ex:
                    print(traceback.format_exc())
                    return str(ex)
                return "ok"
            return False

        if action == "halt_wrapper":
            # if not self.web.validate_key(argdict["key"]):
            #    return EOFError
            self.wrapper.shutdown()

        if action == "get_player_skin":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            if not self.wrapper.proxymode:
                return {"error": "Proxy mode not enabled."}
            uuid = argdict["uuid"]
            if uuid in self.wrapper.proxy.skins:
                skin = self.wrapper.proxy.getskintexture(uuid)
                if skin:
                    return skin
                else:
                    return None
            else:
                return None

        if action == "admin_stats":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            if not self.wrapper.javaserver:
                return
            try:
                last_refresh = float(argdict["last_refresh"])
            except ValueError:
                last_refresh = time.time()
            players = []
            refresh_time = time.time()
            for i in self.wrapper.players:
                player = self.wrapper.players[i]
                players.append({
                    "name": i,
                    "loggedIn": player.loggedIn,
                    "uuid": str(player.mojangUuid),
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
                if line[0] > last_refresh:
                    console_scrollback.append(line[1])
            chat_scrollback = []
            for line in self.web.chatScrollback:
                if line[0] > last_refresh:
                    chat_scrollback.append(line[1])
            memory_graph = []
            for line in self.web.memoryGraph:
                if line[0] > last_refresh:
                    memory_graph.append(line[1])

            mem_use = self.wrapper.memory_usage()
            wrapper_peak_mem = mem_use["peak"] * 1000
            wrapper_rss_mem = mem_use["rss"] * 1000
            stats = {"playerCount": (len(self.wrapper.players),
                                     self.wrapper.proxy.maxplayers),
                     "players": players,
                     "plugins": plugins,
                     "server_state": self.wrapper.javaserver.state,
                     "wrapper_build": self.wrapper.getbuildstring(),
                     "console": console_scrollback,
                     "chat": chat_scrollback,
                     "level_name": self.wrapper.javaserver.worldname,
                     "server_version": self.wrapper.javaserver.version,
                     "motd": self.wrapper.javaserver.motd,
                     "last_refresh": refresh_time,
                     "disk_avail": self.web.getdisk_usage(),
                     "server_name": self.config["Web"]["server-name"],
                     "server_memory": self.wrapper.javaserver.getmemoryusage(),
                     "wrapper_memory_rss": wrapper_rss_mem,
                     "wrapper_memory_peak": wrapper_peak_mem,
                     "server_memory_graph": memory_graph,
                     "world_size": self.wrapper.javaserver.worldsize
                     }
            return stats

        if action == "console":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            command = argdict["execute"]
            self.wrapper.process_command(command, self.web.xplayer)
            self.log.info("[%s] Executed: %s" % (self.addr[0], argdict["execute"]))  # noqa
            return True

        if action == "chat":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            message = argdict["message"]
            self.web.chatScrollback.append(
                (time.time(),
                 {"type": "raw", "payload": "[%s] %s" % (
                     self.web.adminname, message)})
            )
            self.wrapper.javaserver.broadcast("&c[%s]&r %s" % (
                self.web.adminname, message))
            return True

        if action == "kick_player":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            player = argdict["player"]
            reason = argdict["reason"].split("%20")
            args = [player]
            args += reason
            payload = {"player": self.web.xplayer, "args": args, "command": "kick"}  # noqa
            self.wrapper.commands.playercommand(payload)
            self.log.info("[WEB][%s] kicked %s with reason: %s"
                          "" % (self.addr[0], player, " ".join(reason)))
            return True

        if action == "ban_player":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            player = argdict["player"]
            reason = argdict["reason"].split("%20")
            args = [player]
            args += reason

            self.log.info(
                "[%s] %s was banned with reason: %s" % (
                    self.addr[0], player, " ".join(reason))
            )
            payload = {"player": self.web.xplayer,
                       "args": args,
                       "command": "ban"}
            self.wrapper.commands.playercommand(payload)
            return True

        if action == "change_plugin":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            plugin = argdict["plugin"]
            state = argdict["state"]
            payload = {"player": self.web.xplayer,
                       "args": "",
                       "command": "reload"}

            if state == "enable":
                if plugin in self.wrapper.storage["disabled_plugins"]:
                    for thisone in self.wrapper.storage["disabled_plugins"]:
                        if plugin == self.wrapper.storage["disabled_plugins"][thisone]:  # noqa
                            del self.wrapper.storage["disabled_plugins"][thisone]  # noqa
                            break
                    self.wrapper.wrapper_storage.save()
                    self.log.info(
                        "[%s] Set plugin enabled: '%s'" % (
                            self.addr[0], plugin)
                    )
                    self.wrapper.commands.playercommand(payload)
            else:
                if plugin not in self.wrapper.storage["disabled_plugins"]:
                    self.wrapper.storage["disabled_plugins"].append(plugin)
                    self.wrapper.wrapper_storage.save()
                    self.log.info(
                        "[%s] Set plugin disabled: '%s'" % (
                            self.addr[0], plugin)
                    )
                    self.wrapper.commands.playercommand(payload)

        if action == "reload_plugins":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            payload = {"player": self.web.xplayer,
                       "args": "",
                       "command": "reload"}
            self.wrapper.commands.playercommand(payload)
            return True

        if action == "reload_disabled_plugins":
            self.wrapper.storage["disabled_plugins"] = []
            self.wrapper.wrapper_storage.save()
            payload = {"player": self.web.xplayer,
                       "args": "",
                       "command": "reload"}
            self.wrapper.commands.playercommand(payload)
            return True

        if action == "server_action":
            if not self.web.validate_key(argdict["key"]):
                return EOFError
            command = argdict["action"]
            if command == "stop":
                reason = argdict["reason"]
                self.wrapper.javaserver.stop_server_command(reason)
                self.log.info(
                    "[%s] Server stop with reason: %s" % (self.addr[0], reason))
                return "success"
            elif command == "restart":
                reason = argdict["reason"]
                self.wrapper.javaserver.restart(reason)
                self.log.info(
                    "[%s] Server restart with reason: %s" % (
                        self.addr[0], reason)
                )
                return "success"
            elif command == "start":
                self.wrapper.javaserver.start()
                self.log.info("[%s] Server started" % (self.addr[0]))
                return "success"
            elif command == "kill":
                self.wrapper.javaserver.kill("Server killed by Web module...")
                self.log.info("[%s] Server killed." % self.addr[0])
                return "success"
            return {"error": "invalid_server_action"}
        return False


if __name__ == "__main__":
    pass
