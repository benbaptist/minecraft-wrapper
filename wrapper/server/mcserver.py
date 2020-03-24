import re
import json

from wrapper.server.process import Process
from wrapper.commons import *
from wrapper.exceptions import *

class MCServer:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        self.log = wrapper.log_manager.get_logger("mcserver")

        self.process = None

        self.state = SERVER_STOPPED

    def start(self):
        if self.state != SERVER_STOPPED:
            raise StartingException("Server is already running")

        self.log.info("Starting server")

        self.process = Process()
        self.process.start(self.config["server"]["jar"])
        self.state = SERVER_STARTING

    def stop(self):
        return

    def run_command(self, cmd):
        self.process.write("%s\n" % cmd)

    def broadcast(self, msg):
        if type(msg) == dict:
            json_blob = json.dumps(msg)
        else:
            json_blob = json.dumps({
                "text": msg
            })
        self.run_command("tellraw @a %s" % json_blob)

    def tick(self):
        # Check if server process is stopped
        if not self.process.process and self.state != SERVER_STOPPED:
            self.log.info("Server stopped")
            self.state = SERVER_STOPPED

        # Regex new lines
        for std, line in self.process.console_output:
            # Print line to console
            print(line)

            # Compatible with most recent versions of Minecraft server
            m = re.search("(\[[0-9:]*\]) \[([A-z -]*)\/([A-z -]*)\]: (.*)", line)

            # If regex did not match, continue to prevent issues
            if m == None:
                continue

            time = m.group(1)
            server_thread = m.group(2)
            log_level = m.group(3)
            output = m.group(4)

            # Parse output
            if self.state == SERVER_STARTING:
                # Grab server version
                if "Starting minecraft" in output:
                    r = re.search("Starting minecraft server version (.*)", output)
                    server_version = r.group(1)
                    print(server_version)

                # Grab server port
                if "Starting Minecraft server on" in output:
                    r = re.search("Starting Minecraft server on \*:([0-9]*)", output)
                    server_port = r.group(1)
                    print(server_port)

                # Grab world name
                if "Preparing level" in output:
                    r = re.search("Preparing level \"(.*)\"", output)
                    world_name = r.group(1)
                    print(world_name)

                # Server started
                if "Done" in output:
                    self.state = SERVER_STARTED

        # Dirty hack, let's make this better later using process.read_console()
        self.process.console_output = []
