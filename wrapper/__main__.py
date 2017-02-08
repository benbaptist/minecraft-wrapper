# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import os
import sys
from core.wrapper import Wrapper
from api.helpers import getjsonfile
from utils.log import configure_logger
import argparse

parser = argparse.ArgumentParser(
    description='Wrapper.py startup arguments',
    epilog='Created by SurestTexas00')

parser.add_argument('--encoding', "-e", default='utf-8',
                    action='store_true', help=' Specify an encoding'
                                              ' (other than utf-8')
parser.add_argument('--betterconsole', "-b", default=False,
                    action='store_true', help='Use "better '
                    ' console" feature to anchor your imput at'
                    ' the bottom of the console (anti- scroll-away'
                    ' feature)')

args = parser.parse_args()

version = sys.version_info
VERSION = version[0]
SUBVER = version[1]

PY3 = VERSION > 2
MINSUB = 7
if PY3:
    MINSUB = 4


def main(wrapper_start_args):
    # same as 'use-readline = True'
    better_console = wrapper_start_args.betterconsole
    encoding = wrapper_start_args.encoding

    config = getjsonfile("wrapper.properties", ".", encodedas=encoding)

    if config and "Misc" in config:
        if "use-readline" in config["Misc"]:
            # use readline = not using better_console
            better_console = not(config["Misc"]["use-readline"])

    configure_logger(betterconsole=better_console)

    # __init__ wrapper and set up logging
    wrapper = Wrapper()
    log = wrapper.log

    # start first wrapper log entry
    log.info("Wrapper.py started - Version %s", wrapper.getbuildstring())
    log.debug("Wrapper is using Python %s.%s.", sys.version_info[0], SUBVER)

    # flag python version problems
    if SUBVER < MINSUB:
        log.warning(
            "You are using Python %s.%s.  There are Wrapper dependencies"
            " and methods that may require a minimum version of %s.%s."
            " Please press <y> and <Enter> to acknowledge and continue"
            " (anything else to exit)..." %
            (VERSION, SUBVER, VERSION, MINSUB))
        userstdin = sys.stdin.readline().strip()
        if userstdin.lower() != "y":
            print("bye..")
            sys.exit(1)

    # start wrapper
    # noinspection PyBroadException
    try:
        wrapper.start()
    except SystemExit:
        if not wrapper.configManager.exit:
            os.system("reset")
        wrapper.plugins.disableplugins()

        # save-all is required to have a flush argument
        wrapper.javaserver.console("save-all flush")
        wrapper.javaserver.stop("Wrapper.py received shutdown signal - bye")
        wrapper.halt = True
    except Exception as ex:
        log.critical("Wrapper.py crashed - stopping server to be safe (%s)",
                     ex, exc_info=True)
        wrapper.halt = True
        wrapper.plugins.disableplugins()
        try:
            wrapper.javaserver.stop("Wrapper.py crashed - please contact"
                                    " the server host as soon as possible")
        except AttributeError as exc:
            log.critical("Wrapper has no server instance. Server is likely "
                         "killed but could still be running, or it "
                         "might be corrupted! (%s)", exc, exc_info=True)

if __name__ == "__main__":
    main(args)
