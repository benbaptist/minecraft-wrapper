# -*- coding: utf-8 -*-

# This module is not used, but may be useful for pulling out permissions logic

class Permissions:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        #self.permissions = storage.Storage("permissions")

    def createGroup(self, groupName):
        if groupName in self.permissions["groups"]:
            raise Exception("Group '%s' already exists!" % groupName)
        else:
            self.permissions["groups"]

    def doesGroupExist(self, groupName):
        return groupName in self.permissions["groups"]

    # Check for permissions
    def doesPlayerHavePermission(self, player, node):
        uuid = player.uuid # This would be an MCUUID object
