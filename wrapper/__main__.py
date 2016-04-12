# -*- coding: utf-8 -*-

from core.wrapper import Wrapper
from utils.log import configure_logger

if __name__ == "__main__":
    configure_logger()
    wrapper = Wrapper()
    log = wrapper.log
    log.info("Wrapper.py started - Version %s", wrapper.getBuildString())

    try:
        wrapper.start()
    except SystemExit as e:
        if not wrapper.configManager.exit:
            os.system("reset")
        wrapper.plugins.disablePlugins()
        wrapper.halt = True
        wrapper.server.console("save-all")
        wrapper.server.stop("Wrapper.py received shutdown signal - bye", save=False)
    except Exception as ex:
        log.critical("Wrapper.py crashed - stopping server to be safe (%s)", ex, exc_info=True)
        wrapper.halt = True
        wrapper.plugins.disablePlugins()
        try:
            wrapper.server.stop("Wrapper.py crashed - please contact the server host as soon as possible", save=False)
        except Exception as exc:
            log.critical("Failure to shut down server cleanly! Server could still be running, or it might rollback/corrupt! (%s)", exc, exc_info=True)
