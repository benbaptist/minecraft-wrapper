# -*- coding: utf-8 -*-

import os
import json
import time
import datetime
from api.base import API

import utils.termcolors as termcolors


def epoch_to_timestr(epoch_time):
    """
    takes a time represented as integer/string which you supply and converts it to a formatted string.
    :param epoch_time: string or integer (in seconds) of epoch time
    :returns: the string version like "2016-04-14 22:05:13 -0400" suitable in ban files
    """
    tm = int(epoch_time)  # allow argument to be passed as a string or integer
    t = datetime.datetime.fromtimestamp(tm)
    pattern = "%Y-%m-%d %H:%M:%S %z"
    return "%s-0100" % t.strftime(pattern)  # the %z does not work below py3.2 - we just create a fake offset.


def find_in_json(jsonlist, keyname, searchvalue):
    for items in jsonlist:
        if items[keyname] == searchvalue:
            return items
    return None


def getargs(arginput, i):
    if not i >= len(arginput):
        return arginput[i]
    else:
        return ""


def getargsafter(arginput, i):
    return " ".join(arginput[i:])


def getjsonfile(filename, directory="./"):
    """
    :param filename: filename without extension
    :param directory: by default, wrapper script directory.
    :returns a dictionary if successful. If unsuccessful; None/no data or False (if file/directory not found)
    """
    if os.path.exists("%s%s.json" % (directory, filename)):
        with open("%s%s.json" % (directory, filename), "r") as f:
            try:
                return json.loads(f.read())
            except ValueError:
                return None
            #  Exit yielding None (no data)
    else:
        return False  # bad directory or filename


def processcolorcodes(message, py3=False):
    """
    Used internally to process old-style color-codes with the & symbol, and returns a JSON chat object.
    message received should be string
    """
    message = message  # .encode('ascii', 'ignore')  # encode to bytes
    extras = []
    bold = False
    italic = False
    underline = False
    obfuscated = False
    strikethrough = False
    url = False
    color = "white"
    current = ""

    it = iter(range(len(message)))

    for i in it:
        char = message[i]

        if char is not "&":
            if char == " ":
                url = False
            current += char
        else:
            if url:
                clickevent = {"action": "open_url", "value": current}
            else:
                clickevent = {}

            extras.append({
                "text": current,
                "color": color,
                "obfuscated": obfuscated,
                "underlined": underline,
                "bold": bold,
                "italic": italic,
                "strikethrough": strikethrough,
                "clickEvent": clickevent
            })

            current = ""

            # noinspection PyBroadException
            try:
                code = message[i + 1]
            except:
                break

            if code in "abcdef0123456789":
                try:
                    color = API.colorcodes[code]
                except KeyError:
                    color = "white"

            obfuscated = (code == "k")
            bold = (code == "l")
            strikethrough = (code == "m")
            underline = (code == "n")
            italic = (code == "o")

            if code == "&":
                current += "&"
            elif code == "@":
                url = not url
            elif code == "r":
                bold = False
                italic = False
                underline = False
                obfuscated = False
                strikethrough = False
                url = False
                color = "white"

            try:  # ugly but probably works  # TODO find a better solution
                it.next()
            except NameError:
                next(it)

    extras.append({
        "text": current,
        "color": color,
        "obfuscated": obfuscated,
        "underlined": underline,
        "bold": bold,
        "italic": italic,
        "strikethrough": strikethrough
    })
    return json.dumps({"text": "", "extra": extras})


def processoldcolorcodes(message):
    """
    Internal private method - Not intended as a part of the public player object API

     message: message text containing '&' to represent the chat formatting codes
    :return: mofified text containing the section sign (§) and the formatting code.
    """
    for i in API.colorcodes:
        message = message.replace("&" + i, "\xc2\xa7" + i)
    return message


def putjsonfile(data, filename, directory="./", indent_spaces=2):
    """
    writes entire data to a json file.
    This is not for appending items to an existing file!

    :param data - json dictionary to write
    :param filename: filename without extension
    :param directory: by default, wrapper script directory.
    :param indent_spaces - indentation level. Pass None for no indents. 2 is the default.
    :returns True if successful. If unsuccessful; None = TypeError, False = file/directory not found/accessible
    """
    if os.path.exists(directory):
        with open("%s%s.json" % (directory, filename), "w") as f:
            try:
                f.write(json.dumps(data, indent=indent_spaces))
            except TypeError:
                return None
            return True
    return False


def read_timestr(mc_time_string):
    """
    Minecraft server (or wrapper, using epoch_to_timestr) creates a string like this: - "2016-04-15 16:52:15 -0400"
    this reads out the date and returns the epoch time (well, really the server local time, I suppose)
    :param mc_time_string: minecraft time string
    :return: regular seconds from epoch (integer).  Invalid data (like "forever") returns 9999999999 (what forever is).
    """
    # create the time for file:
    # time.strftime("%Y-%m-%d %H:%M:%S %z")

    pattern = "%Y-%m-%d %H:%M:%S"  # ' %z' - strptime() function does not the support %z for READING timezones D:
    try:
        epoch = int(time.mktime(time.strptime(mc_time_string[:19], pattern)))
    except ValueError:
        epoch = 9999999999
    return epoch


def readout(commandtext, description, separator=" - ", pad=15):
    """
    display console text only with no logging - useful for displaying pretty console-only messages.
    Args:
        commandtext: The first text field (magenta)
        description: third text field (green)
        separator: second (middle) field (white text)
        pad: minimum number of characters the command text is padded to

    Returns: Just prints to stdout/console
    """
    commstyle = termcolors.make_style(fg="magenta", opts=("bold",))
    descstyle = termcolors.make_style(fg="yellow")
    x = '{0: <%d}' % pad
    commandtextpadded = x.format(commandtext)
    print("%s%s%s" % (commstyle(commandtextpadded), separator, descstyle(description)))
