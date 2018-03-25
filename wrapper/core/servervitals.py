# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.


class ServerVitals(object):
    """ Centralized location for server information.  This class also
    permits sharing of server information between the caller (such as
    a Wrapper instance) and proxy."""
    def __init__(self, playerobjects):

        # operational info
        self.serverpath = ""
        self.state = 0
        self.server_port = "25564"
        self.command_prefix = "/"

        # Shared data structures and run-time
        self.players = playerobjects

        # TODO - I don't think this is used or needed (same name as proxy.entity_control!)
        self.entity_control = None
        # -1 until a player logs on and server sends a time update
        self.timeofday = -1
        self.spammy_stuff = ["found nothing", "vehicle of", "Wrong location!",
                             "Tried to add entity", ]

        # PROPOSE
        self.clients = []

        # owner/op info
        self.ownernames = {}
        self.operator_list = []

        # server properties and folder infos
        self.properties = {}
        self.worldname = None
        self.worldsize = 0
        self.maxplayers = 20
        self.motd = None
        self.serverIcon = None

        # # Version information
        # -1 until proxy mode checks the server's MOTD on boot
        self.protocolVersion = -1
        # this is string name of the version, collected by console output
        self.version = ""
        # a comparable number = x0y0z, where x, y, z = release,
        #  major, minor, of version.
        self.version_compute = 0
