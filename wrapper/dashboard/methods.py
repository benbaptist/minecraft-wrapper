from flask import g
from flask_socketio import Namespace, send, emit, join_room, leave_room

class Methods(Namespace):
    def __init__(self, wrapper, socketio, auth):
        self.wrapper = wrapper
        self.socketio = socketio
        self.verify_token = auth.verify_token
        self.events = wrapper.events

        # Server state
        @self.events.hook("server.starting")
        def server_starting():
            self.socketio.emit("server.starting", room="server")

        @self.events.hook("server.started")
        def server_started():
            self.socketio.emit("server.started", room="server")

        @self.events.hook("server.stopping")
        def server_stopping():
            self.socketio.emit("server.stopping", room="server")

        @self.events.hook("server.stopped")
        def server_stopped():
            self.socketio.emit("server.stopped", room="server")

        # Server status
        @self.events.hook("server.status.ram")
        def server_status_ram(usage):
            self.socketio.emit("server.status.ram", {"usage": usage}, room="server")

        @self.events.hook("server.status.cpu")
        def server_status_cpu(usage):
            self.socketio.emit("server.status.cpu", {"usage": usage}, room="server")

        # Players #

        @self.events.hook("server.player.join")
        def server_player_join(player):
            self.socketio.emit(
                "server.player.join",
                {
                    "player": self._serialize_player(player)
                },
                room="chat"
            )

        @self.events.hook("server.player.message")
        def server_player_message(player, message):
            print("emit", player, message)
            self.socketio.emit(
                "server.player.message",
                {
                    "player": self._serialize_player(player),
                    "message": message
                },
                room="chat"
            )

        @self.events.hook("server.player.part")
        def server_player_part(player):
            self.socketio.emit(
                "server.player.part",
                {
                    "player": self._serialize_player(player)
                },
                room="chat"
            )

        super(Methods, self).__init__()

    def _serialize_player(self, player):
        return {
            "username": player.username,
            "uuid": str(player.mcuuid),
        }

    def on_server(self):
        self.verify_token()

        join_room("server")

        server = self.wrapper.server
        players = []

        for player in server.players:
            players.append(
                self._serialize_player(player)
            )

        emit("server", {
            "state": server.state,
            "players": players,
            "world": {
                "name": None,
                "size": None
            },
            "mcversion": None,
            "free_disk_space": None
        })

    def on_chat(self):
        join_room("chat")

        chat_scrollback = []

        for chat in self.wrapper.server.mcserver._chat_scrollback:
            player, message = chat
            chat_scrollback.append({
                "player": self._serialize_player(player),
                "message": message
            })

        emit("chat", chat_scrollback)

    def on_send_chat(self, message):
        self.events.call(
            "server.player.message",
            player=self.wrapper.server.mcserver._console_player,
            message=message
        )


        self.wrapper.server.broadcast("<$Console$> %s" % message)
