from builtins import input

from wrapper.exceptions import *
from wrapper.commons import *

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

            def args_after(i):
                try:
                    return " ".join(data.split(" ")[i:])
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

                    continue

                if command == "broadcast":
                    message = args_after(1)
                    self.server.broadcast(message)

                    continue

                if command == "backups":
                    subcommand = args(1)
                    if subcommand == "start":
                        self.wrapper.backups.start()
                    elif subcommand == "list":
                        for index, backup in enumerate(self.wrapper.backups.list()):
                            self.log.info("%s: %s | %s"
                                % (
                                    index,
                                    backup["name"],
                                    bytes_to_human(backup["filesize"])
                                )
                            )
                    elif subcommand == "cancel":
                        self.wrapper.backups.cancel()
                    elif subcommand == "delete":
                        try:
                            backup_index = int(args(2))
                        except:
                            self.log.error(
                                "Usage: /backups delete <index>"
                            )
                            self.log.error(
                                "Use /backups list` to see a list of backups."
                            )
                            continue

                        backup = self.wrapper.backups.list()[backup_index]

                        self.wrapper.backups.delete(backup)
                    else:
                        self.log.info("Usage: /backups <start/list/delete/cancel>")

                    continue

                if command == "stop":
                    self.wrapper.server.stop()
                    continue

                if command == "wrapper":
                    subcommand = args(1)
                    if subcommand in ("halt", "stop"):
                        self.log.info("Wrapper.py shutdown initiated from console")
                        self.wrapper.shutdown()
                    elif subcommand == "about":
                        self.log.info("Wrapper.py")
                    else:
                        self.log.info("Usage: /wrapper <stop/about>")

                    continue

            try:
                self.server.run_command(data)
            except ServerStopped:
                self.log.info("Failed to run command, because server is currently stopped")
