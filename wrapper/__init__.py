import os
import time
import threading

from wrapper.config import Config
from wrapper.storify import Storify
from wrapper.log_manager import LogManager
from wrapper.server import Server
from wrapper.console import Console

CONFIG_TEMPLATE = {
    "server": {
        "jar": "server.jar",
        "arguments": "",
        "auto-restart": True
    },
    # "dashboard": {
    #     "bind": "127.0.0.1",
    #     "port": 8025
    # },
    # "scripts": {
    #     "enable": False
    # },
    "backups": {
        "compression": {
            "enable": True,
            "format": "gzip" # Only gzip is supported for now
        },
        "history": 50,
        "interval-seconds": 600,
        "destination": None,
        "notification": {
            "enable": True,
            "only-ops": False,
            "verbose": False
        }
    }
}

class Wrapper:
    def __init__(self):
        self.log_manager = LogManager()
        self.log = self.log_manager.get_logger("main")

        # Check if wrapper-data folder exists before continuing
        if not os.path.exists("wrapper-data"):
            os.mkdir("wrapper-data")

        # Configuration manager
        self.config = Config(path="wrapper-data/config.json",
            template=CONFIG_TEMPLATE,
            log=self.log_manager.get_logger("config")
        )
        self.config.save()

        # Database manager
        self.storify = Storify(log=self.log_manager.get_logger("storify"))
        self.db = self.storify.getDB("main")

        # Other
        self.server = Server(self)
        self.console = Console(self)

        self.abort = False

    def start(self):
        self.log.info("Wrapper starting")

        t = threading.Thread(target=self.console.read_console)
        t.daemon = True
        t.start()

        self.run()
        self.cleanup()

    def shutdown(self):
        self.log.info("Shutting down Wrapper.py")
        self.abort = True

    def cleanup(self):
        self.server.stop()

    def run(self):
        while not self.abort:
            self.server.tick()
            time.sleep(1 / 20.0) # 20 ticks per second
