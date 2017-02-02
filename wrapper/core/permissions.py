# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

"""This module is not used, but may be used in the future as a
 place for pulling out permissions logic."""


class Permissions:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        # self.permissions = storage.Storage("permissions")
        # recall - use self.permissions.Data to access

    def creategroup(self, groupname):
        if groupname in self.wrapper.permissions["groups"]:
            raise Exception("Group '%s' already exists!" % groupname)
        else:
            print('groups:\n%s' % self.wrapper.permissions["groups"])

    def groupexists(self, groupname):
        return groupname in self.wrapper.permissions["groups"]

    # Check for permissions
    def haspermission(self, player, node):
        # uuid = player.uuid  # This would be an MCUUID object
        pass
