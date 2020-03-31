import re
import json
import uuid
import time
import os

from wrapper.server.process import Process
from wrapper.server.player import Player
from wrapper.server.uuid_cache import UUID_Cache
from wrapper.commons import *
from wrapper.exceptions import *

class MCServer:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.events = wrapper.events
        self.config = wrapper.config
        self.log = wrapper.log_manager.get_logger("mcserver")

        self.process = None

        self.state = SERVER_STOPPED
        self.target_state = (SERVER_STOPPED, time.time())

        self.uuid_cache = UUID_Cache()
        self._reset()

    def _reset(self):
        self.players = []
        self.world = None
        self.server_version = None
        self.server_port = None

        self.process = None
        self.dirty = False

    def start(self):
        if self.state != SERVER_STOPPED:
            raise StartingException("Server is already running")

        self.log.info("Starting server")

        # Call event
        self.events.call("server.starting")

        # Check EULA
        agree_eula = False
        if os.path.exists("eula.txt"):
            with open("eula.txt", "r") as f:
                if not "eula=true" in f.read():
                    agree_eula = True
        else:
            agree_eula = True

        if agree_eula:
            with open("eula.txt", "w") as f:
                f.write("eula=true")

        self._reset()

        # Start process
        self.process = Process()
        self.process.start(self.config["server"]["jar"])
        self.state = SERVER_STARTING

        self.target_state = (SERVER_STARTED, time.time())

    def stop(self, reason):
        self.target_state = (SERVER_STOPPED, time.time())

    def freeze(self):
        return

    def unfreeze(self):
        return

    def kill(self):
        self.process.kill()

    # Commands

    def run_command(self, cmd):
        if not self.process:
            raise ServerStopped()

        self.process.write("%s\n" % cmd)

    def broadcast(self, msg):
        if type(msg) == dict:
            json_blob = json.dumps(msg)
        else:
            json_blob = json.dumps({
                "text": msg
            })
        self.run_command("tellraw @a %s" % json_blob)

    # Players
    def list_players(self):
        players = []

        for player in self.players:
            # Filters go here

            players.append(player)

        return players

    def get_player(self, username=None, mcuuid=None, ip_address=None):
        for player in self.players:
            if username:
                if username == player.username:
                    return player

            if mcuuid:
                if player.uuid == mcuuid:
                    return player

            if ip_address:
                if player.ip_address == ip_address:
                    return player

    # Tick
    def tick(self):
        # Check if server process is stopped
        if self.process:
            if not self.process.process:
                self._reset()

        if not self.process and self.state != SERVER_STOPPED:
            print("self.process is dead, state == server-stopped")
            self.log.info("Server stopped")
            self.state = SERVER_STOPPED
            self.events.call("server.stopped")

        # Check target state, and do accordingly
        target_state, target_state_time = self.target_state
        if target_state == SERVER_STOPPED:

            # Start server shutdown, if it hasn't already started
            if self.state not in (SERVER_STOPPING, SERVER_STOPPED):
                self.run_command("stop")
                self.state = SERVER_STOPPING

            # Check if server stop has been going for too long, and kill server
            if self.state == SERVER_STOPPING:
                if time.time() - target_state_time > 60:
                    self.kill()

        # Don't go further unless a server process exists
        if not self.process:
            return

        # Check if server is 'dirty'
        if len(self.players) > 0:
            self.dirty = True

        # Regex new lines
        for std, line in self.process.console_output:
            # Print line to console
            print(line)

            # Compatible with most recent versions of Minecraft server
            r = re.search("(\[[0-9:]*\]) \[([A-z #]*)\/([A-z #]*)\](.*)", line)

            # If regex did not match, continue to prevent issues
            if r == None:
                continue

            log_time = r.group(1)
            server_thread = r.group(2)
            log_level = r.group(3)
            output = r.group(4)

            # Parse output
            if self.state == SERVER_STARTING:
                # Grab server version
                if "Starting minecraft" in output:
                    r = re.search(": Starting minecraft server version (.*)", output)
                    server_version = r.group(1)

                # Grab server port
                if "Starting Minecraft server on" in output:
                    r = re.search(": Starting Minecraft server on \*:([0-9]*)", output)
                    server_port = r.group(1)

                # Grab world name
                if "Preparing level" in output:
                    r = re.search(": Preparing level \"(.*)\"", output)
                    self.world = r.group(1)

                # Server started
                if "Done" in output:
                    self.state = SERVER_STARTED
                    self.run_command("gamerule sendCommandFeedback false")
                    self.run_command("gamerule logAdminCommands false")
                    self.events.call("server.started")

            if self.state == SERVER_STARTED:
                # UUID catcher
                if "User Authenticator" in server_thread:
                    r = re.search(": UUID of player (.*) is (.*)", output)

                    if r:
                        username, uuid_string = r.group(1), r.group(2)
                        uuid_obj = uuid.UUID(hex=uuid_string)

                        self.uuid_cache.add(username, uuid_obj)

                # Player Join
                r = re.search(": (.*)\[\/(.*):(.*)\] logged in with entity id (.*) at \((.*), (.*), (.*)\)", output)
                if r:
                    username = r.group(1)
                    ip_address = r.group(2)
                    entity_id = r.group(4)
                    position = [
                        float(r.group(5)),
                        float(r.group(6)),
                        float(r.group(7))
                    ]

                    uuid_obj = self.uuid_cache.get(username)

                    player = Player(username=username, mcuuid=uuid_obj)

                    self.players.append(player)

                    self.dirty = True
                    self.events.call("server.player.join", player=player)

                    print(username, ip_address, entity_id, position)

                # Player Part
                r = re.search(": (.*) lost connection: (.*)", output)
                if r:
                    username = r.group(1)
                    server_disconnect_reason = r.group(2)

                    player = self.get_player(username=username)
                    if player:
                        self.events.call("server.player.join", player=player)

                        print("Removing %s from players" % player)
                        self.players.remove(player)

                # Chat messages
                r = re.search(": <(.*)> (.*)", output)
                if r:
                    username, message = r.group(1), r.group(2)
                    print(username, message)

        # Dirty hack, let's make this better later using process.read_console()
        self.process.console_output = []
