# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# system imports
import uuid
import hashlib
import time
import requests
import os


class MCUUID(uuid.UUID):
    """
    This class is used to conform UUIDs as an object/class instance.
    """

    # noinspection PyShadowingBuiltins
    def __init__(self, hex=None, bytes=None, bytes_le=None, fields=None, int=None, version=None):
        super(MCUUID, self).__init__(hex, bytes, bytes_le, fields, int, version)

    @property
    def string(self):
        return str(self)


class UUIDS(object):
    def __init__(self, loginstance, usercache):
        self.log = loginstance
        self.usercache = usercache

    @staticmethod
    def formatuuid(playeruuid):
        """
        Takes player's hex string uuid with no dashes and returns it as a string with the dashes

        :param playeruuid: string of player uuid with no dashes (such as you might get back from Mojang)
        :return: string hex format "8-4-4-4-12"
        """
        return MCUUID(hex=playeruuid).string

    @staticmethod
    def getuuidfromname(name):
        """
        Get the offline vanilla server UUID

        :param name: The playername  (gets hashed as "OfflinePlayer:<playername>")
        :return: a MCUUID object based on the name
        """
        playername = "OfflinePlayer:%s" % name
        m = hashlib.md5()
        m.update(playername.encode("utf-8"))
        d = bytearray(m.digest())
        d[6] &= 0x0f
        d[6] |= 0x30
        d[8] &= 0x3f
        d[8] |= 0x80
        return MCUUID(bytes=bytes(d))

    def getuuidbyusername(self, username, forcepoll=False):
        """
        Lookup user's UUID using the username. Primarily searches the usercache.  If record is
        older than 30 days (or cannot be found in the cache), it will poll Mojang and also attempt a full
        update of the cache using getusernamebyuuid as well.

        :param username:  username as string
        :param forcepoll:  force polling even if record has been cached in past 30 days
        :returns: returns the online/Mojang MCUUID object from the given name. Updates the wrapper usercache.json
                Yields False if failed.
        """
        user_name = "%s" % username  # create a new name variable that is unrelated the the passed variable.
        frequency = 2592000  # 30 days.
        if forcepoll:
            frequency = 3600  # do not allow more than hourly
        user_uuid_matched = None
        for useruuid in self.usercache:  # try wrapper cache first
            if user_name.lower() == self.usercache[useruuid]["localname"].lower():
                # This search need only be done by 'localname', which is always populated and is always
                # the same as the 'name', unless a localname has been assigned on the server (such as
                # when "falling back' on an old name).'''
                if (time.time() - self.usercache[useruuid]["time"]) < frequency:
                    return MCUUID(useruuid)
                # if over the time frequency, it needs to be updated by using actual last polled name.
                user_name = self.usercache[useruuid]["name"]
                user_uuid_matched = useruuid  # cache for later in case multiple name changes require a uuid lookup.

        # try mojang  (a new player or player changed names.)
        r = requests.get("https://api.mojang.com/users/profiles/minecraft/%s" % user_name)
        if r.status_code == 200:
            useruuid = self.formatuuid(r.json()["id"])  # returns a string uuid with dashes
            correctcapname = r.json()["name"]
            if user_name != correctcapname:  # this code may not be needed if problems with /perms are corrected.
                self.log.warning("%s's name is not correctly capitalized (offline name warning!)", correctcapname)
            # This should only run subject to the above frequency (hence use of forcepoll=True)
            nameisnow = self.getusernamebyuuid(useruuid, forcepoll=True)
            if nameisnow:
                return MCUUID(useruuid)
            self.log.warning("Status code was 200 but still returned False "
                             "(a non-MCUUID object).  This will likely "
                             "create other logical/program flow errors")
            return False
        elif r.status_code == 204:  # try last matching UUID instead.  This will populate current name back in 'name'
            if user_uuid_matched:
                nameisnow = self.getusernamebyuuid(user_uuid_matched, forcepoll=True)
                if nameisnow:
                    return MCUUID(user_uuid_matched)
                self.log.warning("Status code was 204 and returned False "
                                 "(a non-MCUUID object).  This will likely "
                                 "create other logical/program flow errors")
                return False
        else:
            self.log.warning(
                "UUID returned False (a non-MCUUID object).  This "
                "will likely create other logical/program flow errors")
            return False  # No other options but to fail request

    def getusernamebyuuid(self, useruuid: str, forcepoll=False, uselocalname=True):
        """
        Returns the username from the specified UUID.
        If the player has never logged in before and isn't in the user cache, it will poll Mojang's API.
        Polling is restricted to once per day.
        Updates will be made to the wrapper usercache.json when this function is executed.

        :param useruuid:  string UUID
        :param forcepoll:  force polling even if record has been cached in past 30 days.
        :param uselocalname:  Will return the name our server uses for this player.

        :returns: returns the username from the specified uuid, else returns False if failed.
        """
        frequency = 2592000  # if called directly, can update cache daily (refresh names list, etc)
        if forcepoll:
            frequency = 600  # 10 minute limit

        theirname = None
        if useruuid in self.usercache:  # if user is in the cache...
            theirname = self.usercache[useruuid]["localname"]
            if int((time.time() - self.usercache[useruuid]["time"])) < frequency:
                return theirname  # dont re-poll if same time frame (daily = 86400).

        # continue on and poll... because user is not in cache or is old record that needs re-polled
        # else:  # user is not in cache
        names = self._pollmojanguuid(useruuid)
        numbofnames = 0
        if names is not False:  # service returned data
            numbofnames = len(names)

        if numbofnames == 0:
            if theirname is not None:
                self.usercache[useruuid]["time"] = time.time() - frequency + 7200  # may try again in 2 hours
                return theirname
            self.log.warning("Instead of a name, this UUID returned False "
                             "because the name was not found locally and "
                             "the minecraft service poll failed.  This will "
                             "likely create other logical/program flow errors")
            return False  # total FAIL

        pastnames = []
        if useruuid not in self.usercache:
            self.usercache[useruuid] = {
                "time": time.time(),
                "original": None,
                "name": None,
                "online": True,
                "localname": None,
                "IP": None,
                "names": []
            }

        for nameitem in names:
            if "changedToAt" not in nameitem:  # find the original name
                self.usercache[useruuid]["original"] = nameitem["name"]
                self.usercache[useruuid]["online"] = True
                self.usercache[useruuid]["time"] = time.time()
                if numbofnames == 1:  # The user has never changed their name
                    self.usercache[useruuid]["name"] = nameitem["name"]
                    if self.usercache[useruuid]["localname"] is None:
                        self.usercache[useruuid]["localname"] = nameitem["name"]
                    break
            else:
                # Convert java milleseconds to time.time seconds
                changetime = nameitem["changedToAt"] / 1000
                oldname = nameitem["name"]
                if len(pastnames) == 0:
                    pastnames.append({"name": oldname, "date": changetime})
                    continue
                if changetime > pastnames[0]["date"]:
                    pastnames.insert(0, {"name": oldname, "date": changetime})
                else:
                    pastnames.append({"name": oldname, "date": changetime})
        self.usercache[useruuid]["names"] = pastnames
        if numbofnames > 1:
            self.usercache[useruuid]["name"] = pastnames[0]["name"]
            if self.usercache[useruuid]["localname"] is None:
                self.usercache[useruuid]["localname"] = pastnames[0]["name"]
        if uselocalname:
            return self.usercache[useruuid]["localname"]
        else:
            return self.usercache[useruuid]["name"]

    def _pollmojanguuid(self, user_uuid):
        """
        attempts to poll Mojang with the UUID
        :param user_uuid: string uuid with dashes
        :returns:
                False - could not resolve the uuid
                - otherwise, a list of names...
        """

        r = requests.get(
            "https://api.mojang.com/user/profiles/%s/names" %
            str(user_uuid).replace("-", ""))
        if r.status_code == 200:
            return r.json()
        if r.status_code == 204:
            return False
        else:
            rx = requests.get("https://status.mojang.com/check")
            if rx.status_code == 200:
                rx = rx.json()
                for entry in rx:
                    if "account.mojang.com" in entry:
                        if entry["account.mojang.com"] == "green":
                            self.log.warning("Mojang accounts is green, but request failed - have you "
                                             "over-polled (large busy server) or supplied an incorrect UUID??")
                            self.log.warning("uuid: %s", user_uuid)
                            self.log.warning("response: \n%s", str(rx))
                            return False
                        elif entry["account.mojang.com"] in ("yellow", "red"):
                            self.log.warning(
                                "Mojang accounts is experiencing issues (%s).",
                                entry["account.mojang.com"]
                            )
                            return False
                        self.log.warning(
                            "Mojang Status found, but corrupted or in an "
                            "unexpected format (status code %s)",
                            r.status_code
                        )
                        return False
                    else:
                        self.log.warning(
                            "Mojang Status not found - no internet connection, "
                            "perhaps? (status code may not exist)")
                        try:
                            return self.usercache[user_uuid]["name"]
                        except TypeError:
                            return False

    # noinspection PyBroadException
    @staticmethod
    def remove_uuidfiles(olduuid, cwd):
        files = [
            "%s/playerdata/%s.dat" % (cwd, olduuid),
            "%s/stats/%s.json" % (cwd, olduuid),
            "%s/advancements/%s.json" % (cwd, olduuid)
        ]
        for file in files:
            try:
                os.remove(file)
            except Exception:
                continue

    def convert_user(self, serverdirectory=".", worldname="world", uuid_="all", onlinemode=False):  # noqa
        """
        Convert a user's or all users' data files to online or offline mode.

        Converts all files in /playerdata, /stats, /advancements

        :Args:
            :serverdirectory: The server's working directory.  Default is '.'
             This is normally self.wrapper.serverpath.
            :worldname: The server worldname.  Should be obtained by the
             API.minecraft.getWorldName().
            :uuid:
                :if a string: Passing "all" causes every player in the wrapper
                 usercache to be converted.  Otherwise, this is interpreted as
                 the string representation of a UUID
                :if a list: It is presumed to be a list of UUID.strings.
            :onlinemode: set to True to convert files to Online mode, False to
             convert them to Offline mode.

            passed UUIDS are the online versions!

        :returns: Nothing.  Performs action(s), logging successful conversions.

        """
        cwd = "%s/%s" % (serverdirectory, worldname)
        if uuid_ == "all":
            all_uuids = []
            for uuids in self.usercache:
                all_uuids.append(uuids)
        elif type(uuid_) is list:
            all_uuids = uuid_
        else:
            all_uuids = [uuid]

        self._conv_user(all_uuids, cwd, onlinemode)

    def _conv_user(self, alluuids, cwd, online=False):
        for onlineuuid_str in alluuids:
            username_str = self.getusernamebyuuid(onlineuuid_str)
            offlineuuid_str = self.getuuidfromname(username_str).string
            if online:
                self.convert_files(offlineuuid_str, onlineuuid_str, cwd)
            else:
                self.convert_files(onlineuuid_str, offlineuuid_str, cwd)

    def convert_files(self, olduuid, newuuid, cwd):
        """
        Convert a player's old uuid to new uuid.
        Converts all files in /playerdata, /stats, /advancements

        :Args:
            :olduuid: The original UUID (string)
            :nwe UUID: the new UUID (string).
            :cwd: The `./server/world` directory.

        :returns: Nothing.  Performs action, logging successful conversions.

        """

        old_files = [
            "%s/playerdata/%s.dat" % (cwd, olduuid),
            "%s/stats/%s.json" % (cwd, olduuid),
            "%s/advancements/%s.json" % (cwd, olduuid)
        ]
        new_files = [
            "%s/playerdata/%s.dat" % (cwd, newuuid),
            "%s/stats/%s.json" % (cwd, newuuid),
            "%s/advancements/%s.json" % (cwd, newuuid)
        ]
        self._cu_write(old_files, new_files)

    # noinspection PyBroadException
    def _cu_write(self, old, new):
        for x, files in enumerate(old):
            try:
                with open(old[x], 'rb') as f:
                    content = f.read()
            except Exception:
                continue

            try:
                with open(new[x], 'wb') as f:
                    f.write(content)
                self.log.debug("Wrote: %s", new[x])
            except Exception:
                continue
