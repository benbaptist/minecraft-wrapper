import os

from wrapper.config import Config
from wrapper.storify import Storify
from wrapper.log_manager import LogManager

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
        self.log = self.log_manager.getLogger("main")

        # Check if wrapper-data folder exists before continuing
        if not os.path.exists("wrapper-data"):
            os.mkdir("wrapper-data")

        # Configuration manager
        self.config = Config(path="wrapper-data/config.json",
            template=CONFIG_TEMPLATE,
            log=self.log_manager.getLogger("config")
        )
        self.config.save()

        # Database manager
        self.storify = Storify(log=self.log_manager.getLogger("storify"))
		self.db = self.storify.getDB("main")

    def start(self):
        self.log.info("Hello world. I'm just some placeholder code, just to let you know that I'm doing something.")
