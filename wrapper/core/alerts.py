# -*- coding: utf-8 -*-

# Copyright (C) 2018 - SurestTexas00 and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import json
import smtplib
from email.mime.text import MIMEText
import threading


# noinspection PyBroadException
class Alerts(object):

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        self.log = wrapper.log

    def _err_checks(self, server):
        username = server.get("login-name", None)
        enc_pass = server.get("encrypted-password", None)
        port = server.get("port", None)
        address = server.get("address", None)
        server_type = server.get("type", "invalid")
        if not (username and address and enc_pass and port and server_type != "invalid"):  # noqa
            self.log.warn("incorrectly configured alert!:\n%s",
                          json.dumps(server, sort_keys=True, indent=2))
            return False
        return username, address, enc_pass, port, server_type

    def ui_process_alerts(self, message, group="all", blocking=False):
        """ Process alerts as a daemonized thread to prevent blocking. """
        ui = threading.Thread(target=self.process_alerts, args=(message, group))
        if not blocking:
            ui.daemon = True
        ui.start()

    def ui_send_mail(self, group, recipients, subject, message, blocking=False):
        """ send_mail as a daemonized thread to prevent blocking. """
        ui = threading.Thread(target=self.send_mail,
                              args=(group, recipients, subject, message))
        if not blocking:
            ui.daemon = True
        ui.start()

    def process_alerts(self, message, group="wrapper"):
        """ process all alerts, sending message using the specified group"""
        if not self.config["Alerts"]["enabled"]:
            self.log.debug("Called Alerts, but they are not enabled")
            return False
        serverlist = self.config["Alerts"]["servers"]
        for server in serverlist:
            if group:
                if server["group"] == group or group == "all":
                    self.send_alert(server, message)
            else:
                self.send_alert(server, message)

    def send_alert(self, server, message, alt_recipient=None, alt_subj=None):
        username, address, enc_pass, port, server_type = self._err_checks(server)  # noqa
        mess = message
        subj = alt_subj
        recipients = alt_recipient
        if not subj:
            subj = server.get("subject", "Wrapper")
        if not recipients:
            recipients = server.get("recipients", None)
        else:
            recipients = [username]

        if server_type.lower() == "email":
            self.send_email(
                username, enc_pass, address, port, mess, recipients, subj)
        else:
            self.log.debug("unknown server type listed in Alerts/servers")

    def send_mail(self, group, recipients, subject, message):
        """ use group email server settings to email different recipients
        (independent of alerts settings or enablement)
            :group: "Alerts"["servers"]["group"]
            :recipients: list of email addresses, type=list (even if only one)
            :subject: plain text
            :message: plain text

        """
        serverlist = self.config["Alerts"]["servers"]
        for server in serverlist:
            group_name = server.get("group", "") == group
            is_mail = server.get("type", "").lower() == "email"
            if group_name and is_mail:
                username, address, enc_pass, port, _ = self._err_checks(server)
                self.send_email(username, enc_pass, address, port,
                                message, recipients, subject)

    def send_email(self, user, encrypted_pass, addr, port, mess, recipients, subj):  # noqa
        password = self.wrapper.cipher.decrypt(encrypted_pass)
        if not password:
            self.log.warn("email password for %s did not decrypt!" % addr)
            return False

        mail = smtplib.SMTP(addr, port)

        def login():
            debuglevel = False
            mail.set_debuglevel(debuglevel)
            mail.starttls()
            try:
                mail.login(user, password)
            except smtplib.SMTPAuthenticationError:
                self.log.warn(
                    "Incorrect email account username/password.  This "
                    "can also be because you have not enabled 'less-"
                    "secure' apps on your account.")
            except Exception as exception:
                self.log.warn(exception)
        login()

        for recipient in recipients:
            msg = MIMEText(mess)
            msg['subject'] = subj
            msg['from'] = user
            msg['to'] = recipient
            try:
                mail.sendmail(user, recipient, msg.as_string())
            # sometimes, servers won't send multiple addressees in one login
            except:
                mail.quit()
                mail = smtplib.SMTP(addr, port)
                login()
                mail.sendmail(user, recipient, msg.as_string())
        mail.quit()
