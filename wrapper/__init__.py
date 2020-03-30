import os
import time
import threading
import logging

from wrapper.config import Config
from wrapper.storify import Storify
from wrapper.log_manager import LogManager
from wrapper.server import Server
from wrapper.console import Console
from wrapper.backups import Backups
from wrapper.events import Events
from wrapper.scripts import Scripts
from wrapper.dashboard import Dashboard
from wrapper.commons import *

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
        self.storify = Storify(
            root="wrapper-data",
            log=self.log_manager.get_logger("storify")
        )
        self.db = self.storify.getDB("main")

        # Core functionality
        self.events = Events()
        self.server = Server(self)
        self.console = Console(self)
        self.backups = Backups(self)
        self.scripts = Scripts(self)
        self.dashboard = Dashboard(self)

        self.abort = False
        self.initiate_shutdown = False

    @property
    def debug(self):
        """ Returns True if debug-mode is enabled, otherwise False. """
        return self.config["general"]["debug-mode"]

    def start(self):
        """ Starts wrapper. """

        # Alert user if config was changed from an update, and shutdown
        if self.config.updated_from_template:
            self.log.info(
                "Configuration file has been updated with new entries. Open "
                "config.json, and make sure your settings are good "
                "before running."
            )
            return

        # Set logging level if debug mode is enabled
        if self.debug:
            self.log_manager.level = logging.DEBUG

        self.log.info("Wrapper starting")
        self.log.debug("Debug?")

        # Start thread that reads console input
        t = threading.Thread(target=self.console.read_console)
        t.daemon = True
        t.start()

        # Run dashboard
        t = threading.Thread(target=self.dashboard.run)
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
        self.storify.flush()

    def run(self):
        while not self.abort:
            if self.initiate_shutdown and self.server.state != SERVER_STOPPING:
                self.server.stop(save=False)

            if self.initiate_shutdown and self.server.state == SERVER_STOPPED:
                self.abort = True
                break

            self.server.tick()
            self.backups.tick()
            self.storify.tick()
            time.sleep(1 / 20.0) # 20 ticks per second
