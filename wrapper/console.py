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

            def args(i):
                try:
                    return data.split(" ")[i]
                except:
                    pass

            if len(data) > 1:
                command = args(0)

                # Remove preceeding slash before processing
                if command[0] == "/":
                    command = command[1:]

                # Commands

                if command == "restart":
                    self.log.info("Restart initiated from console")
                    self.server.restart()

                if command == "wrapper":
                    subcommand = args(1)
                    if subcommand in ("halt", "stop"):
                        self.log.info("Wrapper.py shutdown initiated from console")
                        self.wrapper.shutdown()
                    elif subcommand == "about":
                        self.log.info("Wrapper.py")
                    else:
                        self.log.info("Usage: /wrapper [stop/about]")


            try:
                self.server.run_command(data)
            except ServerStopped:
                self.log.info("Failed to run command, because server is currently stopped")
