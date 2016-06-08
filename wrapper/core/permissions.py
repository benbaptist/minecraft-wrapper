# -*- coding: utf-8 -*-

# This module is not used, but may be used in the future as a place for pulling out permissions logic


class Permissions:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.config = wrapper.config
        # self.permissions = storage.Storage("permissions")

    def creategroup(self, groupname):
        if groupname in self.wrapper.permissions["groups"]:
            raise Exception("Group '%s' already exists!" % groupname)
        else:
            print(self.wrapper.permissions["groups"])

    def groupexists(self, groupname):
        return groupname in self.wrapper.permissions["groups"]

    # Check for permissions
    def haspermission(self, player, node):
        # uuid = player.uuid  # This would be an MCUUID object
        pass
