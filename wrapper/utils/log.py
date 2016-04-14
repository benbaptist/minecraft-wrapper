# -*- coding: utf-8 -*-

import json
import os
import errno
import logging
from logging.config import dictConfig

import termcolors

DEFAULT_CONFIG = dict({
    "version": 1,              
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "()": "utils.log.ColorFormatter",
            "format": "[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s",
            "datefmt": "%H:%M:%S"
        },
        "file": {
            "format": "[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "trace": {
            "format": "[%(asctime)s] [%(name)s/%(levelname)s] [THREAD:%(threadName)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "filters": [],
            "stream": "ext://sys.stdout"
        },
        "wrapper_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "file",
            "filters": [],
            "filename": "logs/wrapper/wrapper.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        },
        "error_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "file",
            "filters": [],
            "filename": "logs/wrapper/wrapper.errors.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        },
        "trace_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "TRACE",
            "formatter": "trace",
            "filters": [],
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


def configure_logger():
    # We need to setup each log file since the default file
    # handlers will not do this for us
    setupLog("logs/wrapper/wrapper.log")
    setupLog("logs/wrapper/wrapper.errors.log")
    setupLog("logs/wrapper/wrapper.trace.log")
    setCustomLevels()
    loadConfig()

    logger = logging.getLogger()

def setupLog(filename):
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

def setCustomLevels():
    # Create a TRACE level
    # We should probably not do this, but for wrappers use case this is non-impacting.
    # See: https://docs.python.org/2/howto/logging.html#custom-levels
    logging.TRACE = 5 # lower than DEBUG
    logging.addLevelName(logging.TRACE, "TRACE")
    logging.Logger.trace = lambda inst, msg, *args, **kwargs: inst.log(logging.TRACE, msg, *args, **kwargs)

def loadConfig(file="logging.json"):
    dictConfig(DEFAULT_CONFIG) # Load default config
    try:
        if os.path.isfile(file):
            with open(file, "r") as f:
                conf = json.load(f)
            dictConfig(conf)
            logging.info("Logging configuration file %s located and loaded, logging configuration set!", file)
        else:
            with open(file, "w") as f:
                f.write(json.dumps(DEFAULT_CONFIG, indent=4, separators=(',', ': ')))
            logging.warn("Unable to locate %s -- Using default logging configuration", file)
    except Exception as e:
        logging.exception("Unable to load or create %s! (%s)", file, e)

class ColorFormatter(logging.Formatter):
    """
    This custom formatter will colorize console output based on logging level
    """
    def __init__(self, *args, **kwargs):
        super(ColorFormatter, self).__init__(*args, **kwargs)

    def format(self, record):
        args = record.args
        msg = record.msg

        if os.name in ("posix", "mac"): # Only style on *nix since windows doesn't support ANSI
            if record.levelno == logging.INFO:
                info_style = termcolors.make_style(fg="green")
                msg = info_style(msg)
            elif record.levelno == logging.DEBUG:
                debug_style = termcolors.make_style(fg="cyan")
                msg = debug_style(msg)
            elif record.levelno == logging.WARNING:
                warn_style = termcolors.make_style(fg="yellow", opts=("bold",))
                msg = warn_style(msg)
            elif record.levelno == logging.ERROR:
                error_style = termcolors.make_style(fg="red", opts=("bold",))
                msg = error_style(msg)
            elif record.levelno == logging.CRITICAL:
                crit_style = termcolors.make_style(fg="black", bg="red", opts=("bold",))
                msg = crit_style(msg)
            elif record.levelno == logging.TRACE:
                trace_style  = termcolors.make_style(fg="black", bg="white")
                msg = trace_style(msg)

        record.msg = msg

        return super(ColorFormatter, self).format(record)
