from builtins import input

from wrapper.exceptions import *

class Console:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.server = wrapper.server
        self.log = wrapper.log_manager.get_logger("console")

    def run(self):
        try:
            self.read_console()
        except:
            self.log.traceback("Console input error")
            raise ConsoleError()

    def read_console(self):
        while not self.wrapper.abort:
            data = input("> ")

            try:
                self.server.run_command(data)
            except ServerStopped:
                self.log.info("Failed to run command, because server is currently stopped")
