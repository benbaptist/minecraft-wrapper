# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

import os
import sys
from core.wrapper import Wrapper
from api.helpers import getjsonfile, config_to_dict_read
from utils.log import configure_logger

BOOT_OPTIONS = "ENCODING=UTF-8\n"

bootoption_count = 1

PY3 = sys.version_info[0] > 2
SUBVER = sys.version_info[1]
print(SUBVER)


def main():
    # determine immediate need-to-know options for wrapper start
    better_console = False  # same as 'use-readline = True'
    encoding = 'UTF-8'
    bootoptions = config_to_dict_read("boot.txt", '.')
    if len(bootoptions) < bootoption_count:
        with open("boot.txt", "w") as f:
            f.write(BOOT_OPTIONS)
    if "ENCODING" in bootoptions:
        encoding = bootoptions["ENCODING"]

    # noinspection PyBroadException
    try:
        configuration = getjsonfile("wrapper.properties", ".", encodedas=encoding)
    except:
        configuration = False
    if configuration:
        if "Misc" in configuration:
            # noinspection PyUnresolvedReferences
            if "use-readline" in configuration["Misc"]:
                # noinspection PyUnresolvedReferences
                better_console = not(configuration["Misc"]["use-readline"])  # use readline = not using better_console

    configure_logger(betterconsole=better_console)

    # check python version compatibilities\
    wrapper = Wrapper()
    log = wrapper.log
    log.info("Wrapper.py started - Version %s", wrapper.getbuildstring())
    if not PY3 and SUBVER < 7:
        log.warning("You are using python 2.%s.  wrapper uses 2.7.x contructs and imports that may not be"
                    " backwards compatible.  You may encounter errors", SUBVER)
    if PY3 and SUBVER < 4:
        log.warning("You are using python 3.%s.  wrapper only supports 3.4 and later."
                    "  You may encounter errors", SUBVER)

    # start wrapper
    try:
        wrapper.start()
    except SystemExit:
        if not wrapper.configManager.exit:
            os.system("reset")
        wrapper.plugins.disableplugins()
        wrapper.javaserver.console("save-all flush")  # required to have a flush argument
        wrapper.javaserver.stop("Wrapper.py received shutdown signal - bye")
        wrapper.halt = True
    except Exception as ex:
        log.critical("Wrapper.py crashed - stopping server to be safe (%s)", ex, exc_info=True)
        wrapper.halt = True
        wrapper.plugins.disableplugins()
        try:
            wrapper.javaserver.stop("Wrapper.py crashed - please contact the server host as soon as possible")
        except AttributeError as exc:
            log.critical("Wrapper has no server instance. Server is likely killed but could still be running, or it "
                         "might be corrupted! (%s)", exc, exc_info=True)

if __name__ == "__main__":
    main()
