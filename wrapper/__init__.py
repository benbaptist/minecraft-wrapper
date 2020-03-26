import os
import time
import threading

from wrapper.config import Config
from wrapper.storify import Storify
from wrapper.log_manager import LogManager
from wrapper.server import Server
from wrapper.console import Console
from wrapper.backups import Backups
from wrapper.commons import *

CONFIG_TEMPLATE = {
    "general": {
        "debug-mode": True
    },
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
        "enable": False,
        "archive-format": {
            "format": "auto",
            "compression": {
                "enable": True
            }
        },
        "history": 50,
        "interval-seconds": 600,
        "only-backup-if-player-joins": True,
        "destination": "backups",
        "ingame-notification": {
            "enable": True,
            "only-ops": False,
            "verbose": False
        },
        "backup-mode": "auto",
        "include": {
            "world": True,
            "logs": False,
            "server-properties": False,
            "wrapper-data": True,
            "whitelist-ops-banned": True
        },
        "include-paths": ["wrapper-data"]
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

        # Database manager
        self.storify = Storify(log=self.log_manager.get_logger("storify"))
        self.db = self.storify.getDB("main")

        # Other
        self.server = Server(self)
        self.console = Console(self)
        self.backups = Backups(self)

        self.abort = False
        self.initiate_shutdown = False

    def start(self):
        if self.config.updated_from_template:
            self.log.info(
                "Configuration file has been updated with new entries. Open "
                "config.json, and make sure your settings are good "
                "before running."
            )
            return

        self.log.info("Wrapper starting")

        t = threading.Thread(target=self.console.read_console)
        t.daemon = True
        t.start()

        try:
            self.run()
        except KeyboardInterrupt:
            self.log.info("Wrapper caught KeyboardInterrupt, shutting down")
        except:
            self.log.traceback("Fatal error, shutting down")
            self.server.kill()
            # This won't properly wait for the server to stop. This needs to be fixed.

        self.cleanup()

    def shutdown(self):
        self.initiate_shutdown = True

    def cleanup(self):
        self.server.stop(save=False)

    def run(self):
        while not self.abort:
            if self.initiate_shutdown and self.server.state != SERVER_STOPPING:
                self.server.stop(save=False)

            if self.initiate_shutdown and self.server.state == SERVER_STOPPED:
                self.abort = True
                break

            self.server.tick()
            self.backups.tick()
            time.sleep(1 / 20.0) # 20 ticks per second
