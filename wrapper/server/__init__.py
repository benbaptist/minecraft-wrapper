from wrapper.server.mcserver import MCServer
from wrapper.commons import *

class Server(object):
    def __init__(self, wrapper):
        self.wrapper = wrapper

        self.log = wrapper.log_manager.get_logger("server")
        self.mcserver = MCServer(wrapper)
        self.db = wrapper.db

        if "server" not in self.db:
            self.db["server"] = {
                "state": SERVER_STARTED # SERVER_STARTED/SERVER_STOPPED
            }
    def __getattr__(self, name):
        if name == "state":
            return self.mcserver.state
        elif name == "players":
            return self.mcserver.players
        else:
            return super(Server, self).__getattr__(name)

    def tick(self):
        if self.mcserver.state == SERVER_STOPPED:
            if self.db["server"]["state"] == SERVER_STARTED:
                self.mcserver.start()

        self.mcserver.tick()

    def run_command(self, cmd):
        self.mcserver.run_command(cmd)

    def start(self):
        self.db["server"]["state"] = SERVER_STARTED

    def stop(self, reason="Server stopping", save=True):
        self.mcserver.stop(reason)

        if save:
            self.db["server"]["state"] = SERVER_STOPPED

    def restart(self, reason="Server restarting"):
        return
