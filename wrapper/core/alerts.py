# -*- coding: utf-8 -*-

# Copyright (C) 2018 - SurestTexas00 and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import json
import smtplib
from email.mime.text import MIMEText


class Alerts(object):

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        self.log = wrapper.log
        self.encoding = self.config["General"]["encoding"]
        self.active = self.config["Alerts"]["enabled"]

    def process_alerts(self, message, group="wrapper"):
        if not self.config["Alerts"]["enabled"]:
            self.log.debug("Called Alerts, but they are not enabled")
            return False
        serverlist = self.config["Alerts"]["servers"]
        for server in serverlist:
            if group:
                if server["group"] == group:
                    self.send_alert(server, message)
            else:
                self.send_alert(server, message)

    def send_alert(self, server, message):
        username = server.get("login-name", None)
        enc_pass = server.get("encrypted-password", None)
        port = server.get("port", None)
        address = server.get("address", None)
        server_type = server.get("type", None)
        subj = server.get("subject", "Wrapper")
        mess = message
        emails = server.get("recipients", None)
        if not (username and address and enc_pass and port and server_type):
            self.log.warn("incorrectly configured alert!:\n%s",
                          json.dumps(server, sort_keys=True, indent=2))
            return False
        if server_type.lower() == "email":
            for email in emails:
                self.send_email(
                    username, enc_pass, address, port, mess, email, subj)
        else:
            self.log.debug("unknown server type listed in Alerts/servers")

    def send_email(self, user, encrypted_pass, addr, port, mess, email, subj):
        password = self.wrapper.cipher.decrypt(encrypted_pass)
        if not password:
            self.log.warn("email password for %s did not decrypt!" % addr)
            return False
        debuglevel = False

        if not email:
            email = user

        msg = MIMEText(mess)
        msg['subject'] = "%s: %s" % (subj, mess[0:20])
        msg['from'] = user
        msg['to'] = email

        mail = smtplib.SMTP(addr, port)
        mail.set_debuglevel(debuglevel)
        mail.starttls()
        try:
            mail.login(user, password)
        except smtplib.SMTPAuthenticationError:
            self.log.warn("Incorrect email account username/password.  This "
                          "can also be because you have not enabled 'less-"
                          "secure' apps on you account.")
        except Exception as exception:
            self.log.warn(exception)
        mail.sendmail(user, email, msg.as_string())
        mail.quit()
