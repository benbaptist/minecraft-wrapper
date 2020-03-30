from flask import Flask, redirect, url_for, render_template, \
    request, make_response, Response, Markup, g
from flask_socketio import SocketIO, send, emit, join_room, leave_room

import os

from wrapper.dashboard.login import blueprint_login
from wrapper.dashboard.admin import blueprint_admin
from wrapper.dashboard.auth import Auth

class Dashboard:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config["dashboard"]
        self.log = wrapper.log_manager.get_logger("dashboard")

        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.urandom(32)
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True

        self.app.wrapper = self.wrapper

        self.socketio = SocketIO(self.app)

        self.auth = Auth(self.wrapper)

        self.do_decorators()
        self.register_blueprints()

    def do_decorators(self):
        self.app.before_request
        def before_request():
            print("before_request")
            g.wrapper = current_app.wrapper
            print(g.wrapper)

    def register_blueprints(self):
        self.app.register_blueprint(blueprint_login)
        self.app.register_blueprint(blueprint_admin)

    def run(self):
        self.socketio.run(
            self.app,
            host=self.config["bind"]["ip"],
            port=self.config["bind"]["port"],
            debug=self.wrapper.debug,
            use_reloader=False
        )
