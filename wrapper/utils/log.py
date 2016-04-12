# -*- coding: utf-8 -*-

import json
import os.path
import logging
from logging.config import dictConfig

import termcolors

from core.config import Config

DEFAULT_CONFIG = dict({
    "version": 1,              
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] [%(plugin)s/%(levelname)s]: %(message)s",
            "datefmt": "%H:%M:%S"
        },
        "file": {
            "format": "[%(asctime)s] [%(plugin)s/%(levelname)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "trace": {
            "format": "[%(asctime)s] [%(plugin)s/%(levelname)s] [THREAD:%(threadName)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard"
        },
        "wrapper_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "NOTSET",
            "formatter": "file",
            "filename": "logs/wrapper/wrapper.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        },
        "error_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "file",
            "filename": "logs/wrapper/wrapper.errors.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        },
        "trace_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "TRACE",
            "formatter": "trace",
            "filename": "logs/wrapper/wrapper.trace.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        }
    },
    "root": {
        "level": "NOTSET",
        "handlers": ["console", "wrapper_file_handler", "error_file_handler", "trace_file_handler"]
    }
})

class Log:
    """
    This class is an instance of a wrapped logging.Logger.
    Theoretically this could be changed in the future to subclass logging.Logger,
    but that work effort is non-trivial. As a result, an individual logger is spun up for every
    plugin and module that initializes it.
    """

    def __init__(self, plugin="Wrapper.py"):
        self.plugin = plugin
        self.setupLogger()

    def info(self, message, *args, **kwargs):
        """
        Confirmation that things are working as expected.
        """
        self.logger.info(message, *args, **dict(extra={"plugin": self.plugin}, **kwargs))

    def debug(self, message, *args, **kwargs):
        """
        Detailed information, typically of interest only when diagnosing problems.
        """
        if Config.debug:
            debug_style = termcolors.make_style(fg="cyan")
            self.logger.debug(debug_style(message), *args, **dict(extra={"plugin": self.plugin}, **kwargs))

    def trace(self, message, *args, **kwargs):
        """
        Low level information like proxy packets
        """
        if Config.trace:
            trace_style  = termcolors.make_style(fg="green")
            self.logger.trace(trace_style(message), *args, **dict(extra={"plugin": self.plugin}, **kwargs))

    def warn(self, message, *args, **kwargs):
        """
        An indication that something unexpected happened, or indicative of some problem in the near future (e.g. "disk space low"). 
        The software is still working as expected.
        """
        warn_style = termcolors.make_style(fg="yellow", opts=("bold",))
        self.logger.warning(warn_style(message), *args, **dict(extra={"plugin": self.plugin}, **kwargs))

    def error(self, message, *args, **kwargs):
        """
        Due to a more serious problem, the software has not been able to perform some function.
        """
        error_style = termcolors.make_style(fg="red", opts=("bold",))
        self.logger.error(error_style(message), *args, **dict(extra={"plugin": self.plugin}, **kwargs))

    def exception(self, message, *args, **kwargs):
        """ 
        Creates a log message similar to Logger.error(). 
        The difference is that Logger.exception() dumps a stack trace along with it.
        Call this method only from an exception handler.
        """
        except_style = termcolors.make_style(fg="red", opts=("bold",))
        self.logger.exception(except_style(message), *args, **dict(extra={"plugin": self.plugin}, **kwargs))

    def critical(self, message, *args, **kwargs):
        """
        A serious error, indicating that the program itself may be unable to continue running.
        """
        crit_style = termcolors.make_style(fg="black", bg="red", opts=("bold",))
        self.logger.critical(crit_style(message), *args, **dict(extra={"plugin": self.plugin}, **kwargs))

    def setCustomLevels(self):
        # Create a TRACE level
        # We should probably not do this, but for wrappers use case this is non-impacting.
        # See: https://docs.python.org/2/howto/logging.html#custom-levels
        logging.TRACE = 51
        logging.addLevelName(logging.TRACE, "TRACE")
        logging.Logger.trace = lambda inst, msg, *args, **kwargs: inst.log(logging.TRACE, msg, *args, **kwargs)

    def loadConfig(self, file="logging.json"):
        dictConfig(DEFAULT_CONFIG) # Load default config
        try:
            if os.path.isfile(file):
                with open(file, "r") as f:
                    conf = json.load(f)
                dictConfig(conf)
                self.info("Logging configuration file %s located and loaded, logging configuration set!", file)
            else:
                with open(file, "w") as f:
                    f.write(json.dumps(DEFAULT_CONFIG, indent=4, separators=(',', ': ')))
                self.warn("Unable to locate %s -- Using default logging configuration", file)
        except Exception as e:
            self.exception("Unable to load or create %s! (%s)", file, e)

    def setupLogger(self):
        self.setCustomLevels()
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())
        self.loadConfig()