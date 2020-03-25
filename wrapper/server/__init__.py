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

    @property
    def state(self):
        return self.mcserver.state

    @property
    def players(self):
        return self.mcserver.players

    @property
    def world(self):
        return self.mcserver.world

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

    def kill(self):
        self.mcserver.kill()

    def restart(self, reason="Server restarting"):
        return
