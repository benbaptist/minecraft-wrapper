# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import json
import os
import logging
from logging.config import dictConfig

# noinspection PyProtectedMember
from api.helpers import mkdir_p, _use_style

DEFAULT = {
    "wrapperversion": 1.2,
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
            "class": "utils.log.WrapperHandler",
            "level": "INFO",
            "formatter": "file",
            "filters": [],
            "filename": "logs/wrapper/wrapper.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        },
        "error_file_handler": {
            "class": "utils.log.WrapperHandler",
            "level": "ERROR",
            "formatter": "file",
            "filters": [],
            "filename": "logs/wrapper/wrapper.errors.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        }
    },
    "root": {
        "level": "NOTSET",
        "handlers": ["console", "wrapper_file_handler", "error_file_handler"]
    }
}


def configure_logger(betterconsole=False):
    loadconfig(betterconsole=betterconsole)
    logging.getLogger()


def loadconfig(betterconsole=False, configfile="logging.json"):
    dictConfig(DEFAULT)  # Load default config
    try:
        if os.path.isfile(configfile):
            with open(configfile, "r") as f:
                conf = json.load(f)

            # Use newer logging configuration, if the one on disk is too old
            if "wrapperversion" not in conf or \
                    (conf["wrapperversion"] < DEFAULT["wrapperversion"]):
                with open(configfile, "w") as f:
                    f.write(json.dumps(DEFAULT, indent=4,
                                       separators=(',', ': ')))
                logging.warning("Logging configuration updated (%s) -- creat"
                                "ing new logging configuration", configfile)
            else:
                if betterconsole:
                    readcurrent = conf["formatters"]["standard"]["format"]
                    conf["formatters"]["standard"]["format"] = (
                        # go up one line to print - '^[1A' (in hex ASCII)
                        "\x1b\x5b\x31\x41%s\r\n" % readcurrent)
                dictConfig(conf)
                logging.info("Logging configuration file (%s) located and "
                             "loaded, logging configuration set!", configfile)
        else:
            with open(configfile, "w") as f:
                f.write(json.dumps(DEFAULT, indent=4, separators=(',', ': ')))
            logging.warning("Unable to locate %s -- Creating default logging "
                            "configuration", configfile)
    except Exception as e:
        logging.exception("Unable to load or create %s! (%s)", configfile, e)


class ColorFormatter(logging.Formatter):
    """This custom formatter will format console color/option
     (bold, italic, etc) and output based on logging level."""
    def __init__(self, *args, **kwargs):
        super(ColorFormatter, self).__init__(*args, **kwargs)

    # noinspection PyUnusedLocal
    def format(self, record):
        args = record.args
        msg = record.msg

        # Only style on *nix since windows doesn't support ANSI
        if os.name in ("posix", "mac"):
            if record.levelno == logging.INFO:
                info_style = _use_style(foreground="green")
                msg = info_style(msg)
            elif record.levelno == logging.DEBUG:
                debug_style = _use_style(foreground="cyan")
                msg = debug_style(msg)
            elif record.levelno == logging.WARNING:
                warn_style = _use_style(foreground="yellow", options=("bold",))
                msg = warn_style(msg)
            elif record.levelno == logging.ERROR:
                error_style = _use_style(foreground="red", options=("bold",))
                msg = error_style(msg)
            elif record.levelno == logging.CRITICAL:
                crit_style = _use_style(foreground="black", background="red",
                                        options=("bold",))
                msg = crit_style(msg)

        record.msg = msg

        return super(ColorFormatter, self).format(record)


# noinspection PyPep8Naming,PyUnresolvedReferences
class WrapperHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, filename, mode='a', maxBytes=0,
                 backupCount=0, encoding=None, delay=0):
        mkdir_p(os.path.dirname(filename))
        super(WrapperHandler, self).__init__(filename, mode, maxBytes,
                                             backupCount, encoding, delay)
