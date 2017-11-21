# -*- coding: utf-8 -*-

from __future__ import division

import os
import errno
from math import floor

from sys import version_info
PY3 = version_info > (3,)

if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range

AUTHOR = "SurestTexas00"
NAME = "SurestLib"
VERSION = (0, 2)
SUMMARY = "This is not a plugin.  It just contains common methods used in my plugins.  To use it, just" \
          "drop it into the same folder as the other plugins.  Then use 'import SurestLib' in the " \
          "head above the Main() class."
DISABLED = True


def permitted(player, permission, usepermissions, usevanillabehavior):
    """check for player permission to run a command.  This routine returns false
    if the player has no permission and prints a vanilla 'unknown command' message
    versus the wrapper's 'permission denied' type message (unless useVanillaBehavior is False)
    Usage: if self._permitted(player, 'somepermissions.permission') is False: return
    or - if self._permitted(player, 'somepermissions.permission') is True: (Dothis)

    :param player - player object.
    :param permission - permission node (string)
    :param usepermissions - whether or not permissions are being used.
    :param usevanillabehavior - whether to use vanilla or bukkit-like behavior -
        i.e., does it act like the command does not exist? or does it state the user
        has no permission?  Use vanilla bahavior will act like the command is not
        recognized.  Non vanilla will instead tell the user they don't have permission."""
    if (usepermissions is True) and player.hasPermission(permission) is False:
        if usevanillabehavior is True:
            player.message("&cUnknown Command. Try /help for a list of commands")
            return False
        else:
            player.message("&cPermission denied.  Requires permission %s" % permission)
            return False
    return True


def client_show_cube(player, pos1, pos2, block=35, corner=51, sendblock=True, numparticles=1, particle_data=1):
    playerposition = player.getPosition()
    ppos = (playerposition[0], playerposition[1], playerposition[2])
    xlow, ylow, zlow = pos1
    xhi, yhi, zhi = pos2

    # this prevents rendering boundaries that may be out of view.
    if xhi > (ppos[0] + 96):
        xhi = int((ppos[0] + 96))
    if xlow < (ppos[0] - 96):
        xlow = int((ppos[0] - 96))
    if zhi > (ppos[2] + 96):
        zhi = int((ppos[2] + 96))
    if zlow < (ppos[2] - 96):
        zlow = int((ppos[2] - 96))
    if zlow > zhi:
        zlow = zhi
    if xlow > xhi:
        xlow = xhi

    # create our range objects BEFORE we start the loops
    x_coord_range = range(xlow, xhi)
    y_coord_range = range(ylow, yhi)  # this is ok (range) for py2 since we'll re-use the y and z lists
    z_coord_range = range(zlow, zhi)

    # Render our cube
    for x in x_coord_range:
        if xlow == pos1[0]:
            position1 = (x, ylow, zlow)
            position3 = (x, yhi, zlow)
            player.sendBlock(position1, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position3, block, 0, sendblock, numparticles, particle_data)
        if xhi == pos2[0]:
            position2 = (x, ylow, zhi)
            position4 = (x, yhi, zhi)
            player.sendBlock(position2, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position4, block, 0, sendblock, numparticles, particle_data)
        for y in y_coord_range:
            position1 = (xlow, y, zlow)
            position2 = (xlow, y, zhi)
            position3 = (xhi, y, zlow)
            position4 = (xhi, y, zhi)
            player.sendBlock(position1, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position2, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position3, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position4, block, 0, sendblock, numparticles, particle_data)
        for z in z_coord_range:
            position1 = (xlow, ylow, z)
            position2 = (xlow, yhi, z)
            position3 = (xhi, ylow, z)
            position4 = (xhi, yhi, z)
            player.sendBlock(position1, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position2, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position3, block, 0, sendblock, numparticles, particle_data)
            player.sendBlock(position4, block, 0, sendblock, numparticles, particle_data)
        if sendblock:
            player.sendBlock(pos2, corner << 4, sendblock, numparticles, particle_data)
    return


def coord2chunk(coord):
    if coord >= 0:
        chunk = int((coord // 16))
    else:
        chunk = -int(((abs(coord) + 15) // 16))
    return chunk


def chunk2region(chunk):
    region = (int(floor(chunk // 32.0)))
    return region


def chunk2coord(chunk):
    if chunk >= 0:
        coord = chunk * 16
    else:
        coord = -int((abs(chunk)) * 16)
    return coord


def region2chunk(region):
    chunk = region * 32.0
    return chunk


def getregionnumber(x, z):
    """Get region filename from Coords x,
    :param x coord
    :param z coord
    """
    xregion = chunk2region(coord2chunk(x))
    zregion = chunk2region(coord2chunk(z))
    filename = "r.%d.%d.mca" % (xregion, zregion)
    return filename


def getchunknumber2d(x, z):
    """Get chunk number as x.z from coords x, z
    :param x coord
    :param z coord
    """
    xchunk = coord2chunk(x)
    zchunk = coord2chunk(z)
    chunk = "%d.%d" % (xchunk, zchunk)
    return chunk


def getchunk3d(x, y, z):
    """Get actaul 3D chunk tuple from coords
    :param x coord
    :param y coord
    :param z coord
    """
    xchunk = coord2chunk(x)
    ychunk = coord2chunk(y)
    zchunk = coord2chunk(z)
    chunk = xchunk, ychunk, zchunk
    return chunk


def read_config(self, filepath, configfile, default_item):
    """Reads a config file with line items separated by '=' signs (whitespace around signs is acceptable)
    :param self = (object) wrapper self instance
    :param filepath: At the present time, this is rooted at the server directory path
    :param configfile: Full name (including extension) of file to load
    :param default_item: the item to be returned if an error occurs
    Returns a dictionary of config items if successful.
    """
    if not makenewdir(filepath):
        self.log.error("something when wrong while trying to make path %s" % filepath)
        return default_item
    if not os.path.exists(filepath + "/" + configfile):
        self.log.error("File '%s/%s' does not exist" % (filepath, configfile))
        return default_item
    config = {}
    f = open(filepath + "/" + configfile, 'rb')
    config_data = f.read().decode('utf-8')
    configdata_split = config_data.split("\n")
    for configdata_lines in configdata_split:
        if len(configdata_split) > 1:
            configdata_sep = configdata_lines.split("=")
            if len(configdata_sep) == 2:
                optionname = configdata_sep[0].strip()
                optionvalue = configdata_sep[1].strip()
                config[optionname] = optionvalue
            else:
                self.log.debug("passed up on bad item: %s/n" % str(config_data))  # debug only
    if config == {}:
        return default_item
    return config


def write_config(filepath, configfile, dictionaryofitems):
    """writes a config file with dictionary items separated by ' = '
    :param filepath: At the present time, this is rooted at the minecraft server directory path
    :param configfile: Full name (including extension) of file to write
    :param dictionaryofitems: the items, as a 'dict' to be written.
    returns errortext or 'success'.
    """
    if not os.path.exists(filepath):
        makenewdir(filepath)
    f = open(filepath + "/" + configfile, 'wb')
    for d_item in dictionaryofitems:
        try:
            b_data = (d_item + " = " + dictionaryofitems[d_item] + "\n")
        except Exception as e:
            return "Error with dictionary item: {%s: %s}\n" \
                   "Error: %s" % (d_item, dictionaryofitems[d_item], e)
        try:
            f.write(b_data)
        except Exception as e:
            return "Error writing data: %s\n" \
                   "Error: %s" % (b_data, e)
    return "success"


def printpage(helplines, nameofhelp, playerobj, page):
    """
    :param helplines: text blob of lines to print.
    :param nameofhelp: name of help group/info.
    :param playerobj: player object.
    :param page: Page to display."""
    itemlist = helplines.splitlines()
    x = len(itemlist)
    pages = float(x // 7)  # explicit floor division, converted to float 'x.0'
    if pages != x / 7.0:  # this means a partial page still exists
        pages += 1
    if pages < 2:
        page = 1
    if page > pages:
        page = pages
    playerobj.message({"text": "List of " + nameofhelp + ": ", "color": "yellow",
                       "extra": [{"text": "Page " + str(page) + " of " + str(pages), "color": "green"}]})
    y = (page - 1) * 7
    while y < ((page - 1) * 7) + 7:
        try:
            playerobj.message(itemlist[y])
        except Exception as e:
            print("error with printpage (SurestLib): \n%s" % e)
        y += 1
    return


def printlist(itemlist, itemdesc, x, playerobj, page):
    """I'd like to deprecate this method in favor of printpage, which just takes a blob of
    multiline text and prints that instead.  This printlist method needs the items passed
    separately as a list.
    :param itemlist: list of help items.
    :param itemdesc: name of items.
    :param x: total number of item lines
    :param playerobj: player object
    :param page: page to print (player.message)
    'Takes an itemlist and prints it'
    'usage: SurestLib.printlist(itemlist, nameofItemsinlist, Total#lines, playerobj, whichpagetoprint)'"""
    pages = float(x // 7)  # explicit floor division, converted to float 'x.0'
    if pages != x / 7.0:  # this means a partial page still exists
        pages += 1
    if pages < 2:
        page = 1
    if page > pages:
        page = pages
    playerobj.message({"text": "List of " + itemdesc + ": ", "color": "yellow",
                       "extra": [{"text": "Page " + str(page) + " of " + str(int(pages)), "color": "green"}]})
    y = (page - 1) * 7
    while y < ((page - 1) * 7) + 7:
        try:
            playerobj.message(itemlist[y])
        except Exception as e:
            # list ends when out of range
            break
        y += 1
    return


def makenamevalid(self, namedplayer, online=True, return_uuid=True):
    """ Takes a name and checks it against logged on users and returns their properly capitalized name.
    :param self = (object) wrapper self instance
    :param namedplayer = (string) player's local name.
    :param online = (bool) If True, limit search to currently logged on players.
    :param return_uuid = (bool) If True, return uuid instead of username.
    """
    name = str(namedplayer).lower()
    for x in self.api.minecraft.getPlayers():
        y = str(x).lower()
        if name == y and return_uuid is False:
            return str(x)
        if name == y and return_uuid is True:
            return str(self.api.minecraft.getPlayer(x).mojangUuid)
        # if that did not work, try name validation against previosly logged in accounts
        # if specified, we lookup UUID.
    if online is False:
        uuid = self.api.minecraft.lookupbyName(namedplayer)
        if not uuid:
            return "[]"
        if return_uuid:  # return the UUID or...
            return uuid
        else:
            return self.api.minecraft.lookupbyUUID(uuid)
    return "[]"


def makenewdir(checkforpath):
    try:
        os.makedirs(checkforpath, exist_ok=True)  # Python > 3.2
    except TypeError:
        try:
            os.makedirs(checkforpath)  # Python > 2.5
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                print("encountered File System error")
                return False
    return True
