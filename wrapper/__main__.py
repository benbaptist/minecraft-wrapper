# -*- coding: utf-8 -*-

import os

from core.wrapper import Wrapper
from utils.log import configure_logger

if __name__ == "__main__":
    configure_logger()
    wrapper = Wrapper()
    log = wrapper.log
    log.info("Wrapper.py started - Version %s", wrapper.getbuildstring())

    try:
        wrapper.start()
    except SystemExit as e:
        if not wrapper.configManager.exit:
            os.system("reset")
        wrapper.plugins.disableplugins()
        wrapper.server.console("save-all flush")  # required to have a flush argument
        wrapper.server.stop("Wrapper.py received shutdown signal - bye", save=False)
        wrapper.halt = True
    except Exception as ex:
        log.critical("Wrapper.py crashed - stopping server to be safe (%s)", ex, exc_info=True)
        wrapper.halt = True
        wrapper.plugins.disableplugins()
        try:
            wrapper.server.stop("Wrapper.py crashed - please contact the server host as soon as possible", save=False)
        except AttributeError as exc:
            log.critical("Wrapper has no server instance. Server is likely killed but could still be running, or it "
                         "might be corrupted! (%s)", exc, exc_info=True)
