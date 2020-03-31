from flask import g
from flask_socketio import Namespace, send, emit, join_room, leave_room

class Methods(Namespace):
    def __init__(self, wrapper, auth):
        self.wrapper = wrapper
        self.verify_token = auth.verify_token

        super(Methods, self).__init__()

    def on_server_status(self):
        self.verify_token()

        server = self.wrapper.server

        emit("server_status", {
            "state": server.state,
            "players": server.players
        })

class IOMethods:
    def __init__(self, wrapper, socketio):
        self.wrapper = wrapper
        self.socketio = socketio

        @self.socketio.on("server_status")
        def server_status():
            g.verify_token()
            server = self.wrapper.server

            emit("server_status", {
                "state": server.state
            })

        @self.socketio.on("test")
        def test(msg):
            print("Test received")
            return
