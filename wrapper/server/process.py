import threading
import time
import traceback

from subprocess import Popen, PIPE

from wrapper.exceptions import *

class Process:
    def __init__(self):
        self.process = None
        self.threads = {}
        self.console_output = []

    def start(self, jar_name, java_args=[], java_bin="java", jar_args=["nogui"]):
        if self.process:
            raise StartingException("Cannot start java process, because it is already running.")

        command = [java_bin] + java_args + ["-jar", jar_name] + jar_args
        # command = ["python", "/home/benbaptist/Documents/Programming/minecraft-wrapper/tools/fake_minecraft_server.py"]

        self.process = Popen(command, stdout=PIPE, stderr=PIPE, stdin=PIPE, universal_newlines=True, bufsize=1)

        self.threads["__stdout__"] = threading.Thread(target=self.__stread__, args=("stdout", ))
        self.threads["__stdout__"].daemon = True
        self.threads["__stdout__"].start()

        self.threads["__stderr__"] = threading.Thread(target=self.__stread__, args=("stderr", ))
        self.threads["__stderr__"].daemon = True
        self.threads["__stderr__"].start()

    def read_console(self):
        i = 0
        while i < len(self.console_output):
            line = self.console_output[i]
            yield line

            del self.console_output[i]
            i += 1

    def kill(self):
        if self.process:
            self.process.kill()
            self.process = None

    def write(self, cmd):
        if not self.process:
            raise ServerStopped("Can't write to server process because it is stopped")

        self.process.stdin.write(cmd)
        self.process.stdin.flush()

    def __stread__(self, read):
        try:
            assert read in ["stdout", "stderr"]

            if read == "stdout":
                std = self.process.stdout
            elif read == "stderr":
                std = self.process.stderr

            # print("__stread__ start // %s" % read)
            while self.process:
                blob = std.readline()

                if len(blob) < 1:
                    break

                for line in blob.split("\n"):
                    # Ignore empty lines
                    if len(line) < 1:
                        continue

                    # Strip line of \r
                    line = line.replace("\r", "")

                    self.console_output.append([read, line])

            # After loop is killed, ensure process is cleaned up
            self.kill()

            # print("__stread__ end // %s" % read)
        except:
            # If a fatal error occurs, print traceback and ensure process is cleaned up
            traceback.print_exc()
            self.kill()

# For experimentaion purposes, this module can be called directly
# This will be removed later
# from builtins import input
if __name__ == "__main__":
    proc = Process()
    proc.start("server.jar")

    while True:
        data = input("> ")
        proc.write(data)
