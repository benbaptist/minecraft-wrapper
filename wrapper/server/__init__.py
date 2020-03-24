from wrapper.server.mcserver import MCServer
from wrapper.commons import *

class Server:
    def __init__(self, wrapper):
        self.wrapper = wrapper

        self.log = wrapper.log_manager.get_logger("server")
        self.mcserver = MCServer(wrapper)
        self.db = wrapper.db

        if "server" not in self.db:
            self.db["server"] = {
                "state": SERVER_STARTED # SERVER_STARTED/SERVER_STOPPED
            }

    def tick(self):
        if self.mcserver.state == SERVER_STOPPED:
            if self.db["server"]["state"] == SERVER_STARTED:
                self.mcserver.start()

        self.mcserver.tick()

    def run_command(self, cmd):
        self.mcserver.run_command(cmd)

    def start(self):
        return

    def stop(self):
        return

    def restart(self):
        return
