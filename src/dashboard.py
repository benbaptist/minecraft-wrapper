try:
	from flask import Flask, g, redirect, url_for, render_template, request, make_response, Response, Markup
	from flask_socketio import SocketIO, send, emit, join_room, leave_room

	IMPORT_SUCCESS = True
except ImportError:
	IMPORT_SUCCESS = False

import os
import time
import threading
import random
import traceback
import datetime
import storage
import log

class Web:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		self.log = log.PluginLog(self.wrapper.log, "Web")

		self.app = Flask(__name__)
		self.app.config['SECRET_KEY'] = "".join([chr(random.randrange(48, 90)) for i in range(32)]) # LOL
		self.socketio = SocketIO(self.app)

		# Flask filters
		def strftime(f):
			return datetime.datetime.fromtimestamp(int(f)).strftime('%Y-%m-%d @ %I:%M%p')
		self.app.jinja_env.filters["strftime"] = strftime

		# Register handlers
		self.add_decorators()

		# Storage
		self.data = storage.Storage("web", self.log)
		if "keys" not in self.data: self.data["keys"] = []

		self.loginAttempts = 0
		self.lastAttempt = 0
		self.disableLogins = 0

		# Start thread for running server
		t = threading.Thread(target=self.run, args=())
		t.daemon = True
		t.start()

	# Authorization methods
	def checkLogin(self, password):
		if time.time() - self.disableLogins < 60: return False # Threshold for logins
		if password == self.wrapper.config["Web"]["web-password"]: return True
		self.loginAttempts += 1
		if self.loginAttempts > 10 and time.time() - self.lastAttempt < 60:
			self.disableLogins = time.time()
			self.log.warn("Disabled login attempts for one minute")
		self.lastAttempt = time.time()
	def makeKey(self, rememberMe):
		chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@-_"
		a = "".join([random.choice(chars) for i in range(64)])

		self.data["keys"].append([a, time.time(), rememberMe])
		return a
	def validateKey(self):
		if "__wrapper_cookie" not in request.cookie:
			return False
			

		key = request.cookie["__wrapper_cookie"]
		for i in self.data["keys"]:
			expireTime = 7884000 # Three weeks old
			if len(i) > 2:
				if not i[2]: expireTime = 21600
			if i[0] == key and time.time() - i[1] < expireTime: # Validate key and ensure it's under the expireTime
				self.loginAttempts = 0
				return True
		return False
	def removeKey(self, key):
		for i,v in enumerate(self.data["keys"]):
			if v[0] == key:
				del self.data["keys"][i]

	# Dectorators and misc.
	def add_decorators(self):
		@self.app.before_request
		def handle():
			print("I'm a freakin' sandwich dude!")

		@self.app.route("/")
		def index():
			return render_template("dashboard.html")

		@self.app.route("/login", methods=["GET", "POST"])
		def login():
			badPass = False
			if request.method == "POST":
				password = request.form["password"]
				rememberMe = "remember" in request.form

				if self.checkLogin(password):
					key = self.makeKey(rememberMe)
					return redirect("/")
					# self.log.warn("%s logged in to web mode (remember me: %s)" % (request.addr, rememberMe))
				else:
					badPass = True

			return render_template("login.html", badPass=badPass)

		@self.socketio.on('connect')
		def handle_connect():
			pass
		@self.socketio.on('disconnect')
		def handle_disconnect():
			pass
	def run(self):
		self.socketio.run(self.app, host=self.wrapper.config["Web"]["web-bind"], port=self.wrapper.config["Web"]["web-port"])
