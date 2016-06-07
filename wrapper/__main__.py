# -*- coding: utf-8 -*-

import os
import sys

PY3 = sys.version_info[0] > 2
SUBVER = sys.version_info[1:1]


from core.wrapper import Wrapper
from utils.log import configure_logger

if __name__ == "__main__":
    configure_logger()
    if PY3:
        print("Sorry, but Wrapper is only working for Python 2")
    wrapper = Wrapper()
    log = wrapper.log
    log.info("Wrapper.py started - Version %s", wrapper.getbuildstring())
    if not PY3 and SUBVER < 6:
        log.warning("You are using python 2.%s.  wrapper uses several 2.6 - 2.7.x contructs."
                    "  You may encounter errors", SUBVER)
    if PY3 and SUBVER < 4:
        log.warning("You are using python 3.%s.  wrapper only supports 3.4 and later."
                    "  You may encounter errors", SUBVER)
    try:
        wrapper.start()
    except SystemExit as e:
        if not wrapper.configManager.exit:
            os.system("reset")
        wrapper.plugins.disableplugins()
        wrapper.javaserver.console("save-all flush")  # required to have a flush argument
        wrapper.javaserver.stop("Wrapper.py received shutdown signal - bye", save=False)
        wrapper.halt = True
    except Exception as ex:
        log.critical("Wrapper.py crashed - stopping server to be safe (%s)", ex, exc_info=True)
        wrapper.halt = True
        wrapper.plugins.disableplugins()
        try:
            wrapper.javaserver.stop("Wrapper.py crashed - please contact the server host as soon as possible", save=False)
        except AttributeError as exc:
            log.critical("Wrapper has no server instance. Server is likely killed but could still be running, or it "
                         "might be corrupted! (%s)", exc, exc_info=True)
