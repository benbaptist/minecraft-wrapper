import time
import random

from flask import request
from passlib.hash import sha256_crypt

from wrapper.exceptions import *

# Tokens expire in just an hour
TOKEN_EXPIRE_TIME = 60 * 60

class Auth:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.db = wrapper.storify.getDB("dashboard-auth")

        if "sessions" not in self.db:
            self.db["sessions"] = {}
            self.db["users"] = []

        if self.wrapper.config["dashboard"]["root-password"]:
            try:
                sha256_crypt.verify(
                    "",
                    self.wrapper.config["dashboard"]["root-password"]
                )
            except ValueError:
                encrypted = sha256_crypt.encrypt(
                    self.wrapper.config["dashboard"]["root-password"]
                )
                self.wrapper.config["dashboard"]["root-password"] = encrypted

    def _get_pass(self, username):
        if username == "root":
            if not self.wrapper.config["dashboard"]["root-password"]:
                raise AuthError(
                    "Root account is disabled. Set password in configuration "
                    "to continue"
                )
            return self.wrapper.config["dashboard"]["root-password"]

        raise AuthError("'%s' is not a valid username" % username)

    def _gen_token(self):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
        result = ""

        for i in range(64):
            result += random.choice(chars)

        return result

    def authenticate(self, username, password):
        password_encrypted = self._get_pass(username)
        verify = sha256_crypt.verify(password, password_encrypted)

        if not verify:
            raise AuthError("Invalid password for '%s'" % username)

        token = self._gen_token()
        self.db["sessions"][token] = {
            "username": username,
            "time": time.time()
        }

        return token

    def verify_token(self):
        if "_wrapper_token" not in request.cookies:
            raise AuthError("Token invalid")

        token = request.cookies["_wrapper_token"]

        if token in self.db["sessions"]:
            session = self.db["sessions"][token]

            if time.time() - session["time"] > TOKEN_EXPIRE_TIME:
                del self.db["sessions"][token]
                raise AuthError("Token invalid")

            session["time"] = time.time()

            return session["username"]

        raise AuthError("Token invalid")

    def invalidate_token(self, token=None):
        if not token:
            token = request.cookies["_wrapper_token"]

        if token in self.db["sessions"]:
            del self.db["sessions"][token]
