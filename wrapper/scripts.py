import subprocess
import threading

class Scripts:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.events = wrapper.events
        self.config = wrapper.config["scripts"]

        @self.events.hook("server.started")
        def server_started():
            self.call_script("server-started")

        @self.events.hook("server.stopped")
        def server_stopped():
            self.call_script("server-stopped")

        @self.events.hook("backups.start")
        def backup_start():
            self.call_script("backup-start")

        @self.events.hook("backups.complete")
        def backup_complete(details):
            path = details["path"]

            self.call_script("backup-complete", [path])

        @self.events.hook("server.player.join")
        def player_join(player):
            username = player.username
            mcuuid = player.mcuuid
            ip_address = player.ip_address

            self.call_script("player-join", [username, mcuuid, ip_address])

        @self.events.hook("server.player.part")
        def player_part(player):
            username = player.username
            mcuuid = player.mcuuid
            ip_address = player.ip_address

            self.call_script("player-join", [username, mcuuid, ip_address])

    def call_script(self, script, args=[]):
        path = self.config["scripts"][script]

        if not self.config["enable"]:
            return

        if not path:
            return

        cmd = [path] + args

        t = threading.Thread(target=self._call_script, args=(cmd))
        t.start()

    def _call_script(self, cmd):
        status_code = subprocess.call(cmd)
