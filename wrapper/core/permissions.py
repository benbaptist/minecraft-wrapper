# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

"""This module is not used, but may be used in the future as a
 place for pulling out permissions logic."""
import ast
import fnmatch
import copy
import logging
import json


class Permissions:
    """All permissions logic for wrapper. with 1.0.0 release (and
    all earlier dev versions), we will start enforcing the use of
    all lowercase groups and permissions.  The return items on
    these functions are generally intended for use as a printout
    for the calling function; either a console message or
    player.message().

    Pass all UUIDs as string!

    players are only indentified by UUID.

    """

    def __init__(self, wrapper, test_permission_set=None):
        self.wrapper = wrapper

        if not test_permission_set:
            self.log = self.wrapper.log
            # permissions storage Data object
            self.permissions = wrapper.permissions
            self.registered_perms = self.wrapper.registered_permissions
        else:
            # test mode
            self.log = logging.getLogger("wrapper")
            self.permissions = test_permission_set
            self.registered_perms = {}

        # enforcing lowercase perms now, clean data up
        self.empty_user = {"groups": [], "permissions": {}}
        self.clean_perms_data()

        # populate dictionary items to prevent errors due to missing items
        if "groups" not in self.permissions:
            self.permissions["groups"] = {}
        if "default" in self.permissions["groups"]:
            if len(self.permissions["groups"]["default"]["permissions"]) > 0:
                self.log.error(
                    "Your permissions structure contains a 'Default' group"
                    " item with some permissions in it.  This is now"
                    " deprecated by Wrapper's permission logic.  Use the"
                    " 'registerPermission' API item to register default"
                    " permissions.  Manually delete the 'Default' group to"
                    " make this error go away...")
            else:
                self.group_delete("default")

        if "users" not in self.permissions:
            self.permissions["users"] = {}

    def clean_perms_data(self):

        deletes = []
        for user in self.permissions["users"]:
            if self.permissions["users"][user] == self.empty_user:
                deletes.append(user)
        for stale_user in deletes:
            del self.permissions["users"][stale_user]

        if "converted" in self.permissions:
            return
        self.permissions["converted"] = "Yes"
        permstring = json.dumps(self.permissions)
        newstring = permstring.lower()
        self.permissions = json.loads(newstring)

    def group_create(self, groupname):
        """Will create a new (lowercase) groupname."""
        groupname = groupname.lower()
        if groupname in self.permissions["groups"]:
            return "Group '%s' already exists!" % groupname

        self.permissions["groups"][groupname] = {"permissions": {}}
        return "Created a new permissions group '%s'." % groupname

    def group_delete(self, groupname):
        """Will attempt to delete groupname, regardless of case."""
        deletename = groupname.lower()
        if deletename not in self.permissions["groups"]:
            return "Group '%s' does not exist!" % deletename

        del self.permissions["groups"][deletename]
        return "Deleted permissions group '%s'." % deletename

    def group_set_permission(self, groupname, node="", value=True):
        """Sets a permission node for a group."""
        setname = groupname.lower()
        
        # Group not found
        if not self.group_exists(setname):
            return "Group '%s' does not exist!" % groupname

        # ensure valid node
        if not node or node == "":
            return "Invalid permission node name: '%s'" % node

        # allow string true/false or boolean True/False as argument
        try:
            # noinspection PyUnresolvedReferences
            if value.lower() in ("true", "false"):
                value = ast.literal_eval(value)
            # else items default to True below - "value = bool(value) or False"
        except AttributeError:
            pass
        value = bool(value) or False

        # ensure lower case
        setnode = node.lower()

        # set the node
        self.permissions["groups"][setname]["permissions"][setnode] = value
        return "Added node/group '%s' to Group '%s'!" % (setnode, setname)

    def group_delete_permission(self, group, node):

        setgroup = group.lower()
        setnode = node.lower()
        if not self.group_exists(setgroup):
            return "Group '%s' does not exist!" % group

        if setnode in self.permissions["groups"][setgroup]["permissions"]:
            del self.permissions["groups"][setgroup]["permissions"][setnode]
            return "Removed permission node '%s' from group '%s'." % (
                setnode, setgroup)

    def group_exists(self, groupname):
        if groupname.lower() in self.permissions["groups"]:
            return True
        return False

    def _group_match(self, node, group, all_groups):
        """return true if conditions met:
        1) (node in self.permissions["groups"]) -> the group exists
        2) self.permissions["groups"][group]["permissions"][node] ->
                the node is set to True
        3) node not already in all_groups
        """
        if (node in self.permissions["groups"]) and self.permissions[
            "groups"][group]["permissions"][node] and (
                    node not in all_groups):
            return True
        return False

    def has_permission(self, uuid, node=None, groupmatching=True):
        """If the uuid has the specified permission node (either
        directly, or inherited from a group that it is in),
        it will return the value (usually True) of the node.
        Otherwise, it returns False.
        """
        if uuid not in self.permissions["users"]:
            self.permissions["users"][uuid] = copy.copy(self.empty_user)
            return False

        if node is None:
            return True

        # ensure lower case
        node = node.lower()

        # user has permission directly
        for perm in self.permissions["users"][uuid]["permissions"]:
            if node in fnmatch.filter([node], perm):
                return self.permissions[
                    "users"][uuid]["permissions"][perm]

        # return a registered permission;
        for pid in self.registered_perms:
            if node in self.registered_perms[pid]:
                return self.registered_perms[pid][node]

        # an optional way out because group processing can be expensive
        if not groupmatching:
            return False

        # summary of groups, which will include child groups
        allgroups = []

        # get the user's groups
        for group in self.permissions["users"][uuid]["groups"]:
            allgroups.append(group)

        # process and find child groups
            # Start with all groups user is in:
        itemstoprocess = allgroups[:]

        while len(itemstoprocess) > 0:
            # pop out each group to process one-by-one
            groupname = itemstoprocess.pop(0)

            # this must be checked because a race condition can
            # render the groupname non-existent.
            if groupname in self.permissions["groups"]:
                for group_node in self.permissions[
                        "groups"][groupname]["permissions"]:
                    if self._group_match(group_node, groupname, allgroups):
                        allgroups.append(group_node.lower())
                        itemstoprocess.append(group_node)

        # return if group matches
        for group in allgroups:
            # this must be checked because a race condition can
            # render the groupname non-existent.
            if group in self.permissions["groups"]:
                for perm in self.permissions["groups"][group]["permissions"]:
                    if node in fnmatch.filter([node], perm):
                        return self.permissions["groups"][group][
                            "permissions"][perm]

        # no permission;
        return False

    def set_permission(self, uuid, node, value=True):
        """Adds the specified permission node and optionally a
        (boolean) value for that permission.  For instance,
        set to False will cause denial of permission.
        """
        # allow string true/false or boolean True/False as argument
        try:
            # noinspection PyUnresolvedReferences
            if value.lower() in ("true", "false"):
                value = ast.literal_eval(value)
            # else items default to True below - "value = bool(value) or False"
        except AttributeError:
            pass
        value = bool(value) or False

        if uuid not in self.permissions["users"]:
            self.permissions["users"][uuid] = copy.copy(self.empty_user)

        self.permissions["users"][uuid]["permissions"][node.lower()] = value

    def remove_permission(self, uuid, node):
        """Completely removes a permission node from the player. They
        will still inherit this permission from their groups or from
        plugin defaults.  Returns True/False success."""

        if uuid not in self.permissions["users"]:
            self.permissions["users"][uuid] = copy.copy(self.empty_user)
            # Since the user did not even have a permission, return.
            return True
        node = node.lower()

        if node in self.permissions["users"][uuid]["permissions"]:
            del self.permissions["users"][uuid]["permissions"][node]
            return True

        self.log.debug("Uuid:%s does not have permission node '%s'" % (
            uuid, node))
        return False

    def has_group(self, uuid, group):
        """Returns a boolean of whether or not the player is in
        the specified permission group.
        """
        group_lower = group.lower()

        # group does not exist
        if not self.group_exists(group_lower):
            return False

        # user had no permission data
        if uuid not in self.permissions["users"]:
            self.permissions["users"][uuid] = copy.copy(self.empty_user)
            return False

        # user has this group ...
        if group_lower in self.permissions["users"][uuid]["groups"]:
            return True

        # user does not have the group
        return False

    def get_groups(self, uuid):
        """Returns a list of permission groups that the player is in.
        :returns:  a list of groups the user is in.
        """

        if uuid not in self.permissions["users"]:
            self.permissions["users"][uuid] = copy.copy(self.empty_user)
            # Had not permissions set at all..
            return []
        return self.permissions["users"][uuid]["groups"]

    def set_group(self, uuid, group, creategroup=False):
        """
        Adds the player to a specified group.  Returns False if
        group does not exist (set debiug to see error).


        :returns:  Boolean; True if operation succeeds, False
         if it fails (set debug mode to see/log error).

        """
        # (deprecate uppercase checks once wrapper hits 2.x.x)
        group = group.lower()

        if group not in self.permissions["groups"]:
            if creategroup:
                self.group_create(group)
            else:
                self.log.debug("No group with the name '%s' exists", group)
                return False

        if uuid not in self.permissions["users"]:
            self.permissions["users"][uuid] = copy.copy(self.empty_user)
        self.permissions["users"][uuid]["groups"].append(group)

        # return the resulting change (as verification)
        return self.has_group(uuid, group)

    def remove_group(self, uuid, group):
        """Removes the player to a specified group."""

        group = group.lower()
        if uuid not in self.permissions["users"]:
            self.permissions["users"][uuid] = copy.copy(self.empty_user)
            return True

        if group in self.permissions["users"][uuid]["groups"]:
            self.permissions["users"][uuid]["groups"].remove(group)
            return True

        self.log.debug("UUID:%s was not part of the group '%s'" % (
            uuid, group))
        return False


def _test():
    from helpers import getjsonfile, putjsonfile
    permsdata = getjsonfile("permsdata", "/home/surest/Desktop")
    perms = Permissions("wrapper", permsdata)

    x = perms.group_create("nubs")
    print("created nubs: %s" % x)

    x = perms.group_exists("nubs")
    print("do nubs exist? %s" % x)

    perms.group_set_permission("nubs", "GooFYGOOBer", True)

    perms.set_group("83799ba6-bbac-4d8e-9930-af051cc193a5", "NUBS", True)
    x = perms.has_permission("83799ba6-bbac-4d8e-9930-af051cc193a5",
                             "goofygOOber")
    print("Is that nub a goofygoober?: %s" % x)

    ifhehas = perms.has_group("83799ba6-bbac-4d8e-9930-af051cc193a5", "OWNeR")
    print(ifhehas)

    ifhehas = perms.has_permission("83799ba6-bbac-4d8e-9930-af051cc193a5",
                                   "vclaims.use")
    print(ifhehas)

    x = perms.has_group("4f953255-6775-4dc6-a612-fb4230588eff", "owNer")
    print(x)

    x = perms.has_permission("4f953255-6775-4dc6-a612-fb4230588eff",
                             "vclaims.admin")
    print(x)

    x = perms.group_delete("nubs")
    print("deleted nubs: %s" % x)

    x = perms.group_exists("nubs")
    print("do they exist? %s" % x)

    x = perms.has_permission("83799ba6-bbac-4d8e-9930-af051cc193a5",
                             "goofygOOber")
    print("Is that nub a goofygoober?: %s" % x)

    putjsonfile(perms.permissions, "permsdata_", "/home/surest/Desktop")

if __name__ == "__main__":
    _test()
