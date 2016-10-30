# -*- coding: utf-8 -*-

import os
import errno
import sys
import json
import time
import datetime

COLORCODES = {
    "0": "black",
    "1": "dark_blue",
    "2": "dark_green",
    "3": "dark_aqua",
    "4": "dark_red",
    "5": "dark_purple",
    "6": "gold",
    "7": "gray",
    "8": "dark_gray",
    "9": "blue",
    "a": "green",
    "b": "aqua",
    "c": "red",
    "d": "light_purple",
    "e": "yellow",
    "f": "white",
    "r": "\xc2\xa7r",
    "k": "\xc2\xa7k",  # obfuscated
    "l": "\xc2\xa7l",  # bold
    "m": "\xc2\xa7m",  # strikethrough
    "n": "\xc2\xa7n",  # underline
    "o": "\xc2\xa7o",  # italic,
}


def _addgraphics(text='', foreground='white', background='black', options=()):
    """
    encodes text with ANSI graphics codes.
    https://en.wikipedia.org/wiki/ANSI_escape_code#Non-CSI_codes
    options - a tuple of options.
        valid options:
            'bold'
            'italic'
            'underscore'
            'blink'
            'reverse'
            'conceal'
            'reset' - return reset code only
            'no-reset' - don't terminate string with a RESET code

    """
    resetcode = '0'
    fore = {'blue': '34', 'yellow': '33', 'green': '32', 'cyan': '36', 'black': '30',
            'magenta': '35', 'white': '37', 'red': '31'}
    back = {'blue': '44', 'yellow': '43', 'green': '42', 'cyan': '46', 'black': '40',
            'magenta': '45', 'white': '47', 'red': '41'}
    optioncodes = {'bold': '1', 'italic': '3', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}

    codes = []
    if text == '' and len(options) == 1 and options[0] == 'reset':
        return '\x1b[%sm' % resetcode

    if foreground:
        codes.append(fore[foreground])
    if background:
        codes.append(back[background])

    for option in options:
        if option in optioncodes:
            codes.append(optioncodes[option])
    if 'no-reset' not in options:
        text = '%s\x1b[%sm' % (text, resetcode)
    return '%s%s' % (('\x1b[%sm' % ';'.join(codes)), text)


# private static int DataSlotToNetworkSlot(int index)
def dataslottonetworkslot(index):
    """

    Args:
        index: window slot number?

    Returns: "network slot" - not sure what that is.. player.dat file ?

    """

    # // / < summary >
    # https://gist.github.com/SirCmpwn/459a1691c3dd751db160
    # // / Thanks to some idiot at Mojang
    # // / < / summary >

    if index <= 8:
        index += 36
    elif index == 100:
        index = 8
    elif index == 101:
        index = 7
    elif index == 102:
        index = 6
    elif index == 103:
        index = 5
    elif 83 >= index >= 80:
        index -= 79
    return index


def epoch_to_timestr(epoch_time):
    """
    takes a time represented as integer/string which you supply and converts it to a formatted string.
    :param epoch_time: string or integer (in seconds) of epoch time
    :returns: the string version like "2016-04-14 22:05:13 -0400" suitable in ban files
    """
    tm = int(float(epoch_time))  # allow argument to be passed as a string or integer
    t = datetime.datetime.fromtimestamp(tm)
    pattern = "%Y-%m-%d %H:%M:%S %z"
    return "%s-0100" % t.strftime(pattern)  # the %z does not work below py3.2 - we just create a fake offset.


def find_in_json(jsonlist, keyname, searchvalue):
    for items in jsonlist:
        if items[keyname] == searchvalue:
            return items
    return None


def format_bytes(number_raw_bytes):
    large_bytes = float(number_raw_bytes) / 1073741824
    units = "GiB"
    if large_bytes < 1.0:
        large_bytes *= 1024
        units = "MiB"
    if large_bytes < 1.0:
        large_bytes *= 1024
        units = "KiB"
    return "%.4g %s (%d bytes)" % (large_bytes, units, number_raw_bytes)


def getargs(arginput, i):
    if not i >= len(arginput):
        return arginput[i]
    else:
        return ""


def getargsafter(arginput, i):
    return " ".join(arginput[i:])


def getjsonfile(filename, directory=".", encodedas="UTF-8"):
    """
    Args:
        filename: filename without extension
        directory: by default, wrapper script directory.
        encodedas: the encoding

    Returns: a dictionary if successful. If unsuccessful; None/no data or False (if file/directory not found)

    """
    if not os.path.exists(directory):
        mkdir_p(directory)
    if os.path.exists("%s/%s.json" % (directory, filename)):
        with open("%s/%s.json" % (directory, filename), "r") as f:
            try:
                return json.loads(f.read(), encoding=encodedas)
            except ValueError:
                return None
            #  Exit yielding None (no data)
    else:
        return False  # bad directory or filename


def getfileaslines(filename, directory="."):
    """
    Args:
        filename: Complete filename
        directory: by default, wrapper script directory.

    Returns: a list if successful. If unsuccessful; None/no data or False (if file/directory not found)

    """
    if not os.path.exists(directory):
        mkdir_p(directory)
    if os.path.exists("%s/%s" % (directory, filename)):
        with open("%s/%s" % (directory, filename), "r") as f:
            try:
                return f.read().splitlines()
            except Exception as e:
                print(_addgraphics("Exception occured while running 'getfileaslines': \n", foreground="red"), e)
                return None
    else:
        return False


def mkdir_p(path):
    try:
        os.makedirs(path, exist_ok=True)  # Python > 3.2
    except TypeError:
        try:
            os.makedirs(path)  # Python > 2.5
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def processcolorcodes(messagestring):
    """
    Used internally to process old-style color-codes with the & symbol, and returns a JSON chat object.
    message received should be string
    """
    py3 = sys.version_info > (3,)
    if not py3:
        message = messagestring.encode('ascii', 'ignore')
    else:
        message = messagestring  # .encode('ascii', 'ignore')  # encode to bytes

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

        if char not in ("&", u'&'):
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
                    color = COLORCODES[code]
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

            if sys.version_info > (3,):
                next(it)
            else:
                it.next()

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
    for i in COLORCODES:
        message = message.replace("&" + i, "\xc2\xa7" + i)
    return message


def putjsonfile(data, filename, directory=".", indent_spaces=2, sort=False, encodedas="UTF-8"):
    """
    writes entire data to a json file.
    This is not for appending items to an existing file!

    :param data - json dictionary to write
    :param filename: filename without extension
    :param directory: by default, wrapper script directory.
    :param indent_spaces - indentation level. Pass None for no indents. 2 is the default.
    :param sort - whether or not to sort the records for readability
    :param encodedas - encoding
    :returns True if successful. If unsuccessful; None = TypeError, False = file/directory not found/accessible
    """
    if not os.path.exists(directory):
        mkdir_p(directory)
    if os.path.exists(directory):
        with open("%s/%s.json" % (directory, filename), "w") as f:
            try:
                f.write(json.dumps(data, ensure_ascii=False, indent=indent_spaces, sort_keys=sort, encoding=encodedas))
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
    commstyle = use_style(foreground="magenta", options=("bold",))
    descstyle = use_style(foreground="yellow")
    x = '{0: <%d}' % pad
    commandtextpadded = x.format(commandtext)
    print("%s%s%s" % (commstyle(commandtextpadded), separator, descstyle(description)))


def secondstohuman(seconds):
    results = "None at all!"
    plural = "s"
    if seconds > 0:
        results = "%d seconds" % seconds
    if seconds > 59:
        if (seconds / 60) == 1:
            plural = ""
        results = "%d minute%s" % (seconds / 60, plural)
    if seconds > 3599:
        if (seconds / 3600) == 1:
            plural = ""
        results = "%d hour%s" % (seconds / 3600, plural)
    if seconds > 86400:
        if (seconds / 86400) == 1:
            plural = ""
        results = "%s day%s" % (str(seconds / 86400.0), plural)
    return results


def showpage(player, page, items, command, perpage):
    pagecount = len(items) / perpage
    if (int(len(items) / perpage)) != (float(len(items)) / perpage):
        pagecount += 1
    if page >= pagecount or page < 0:
        player.message("&cNo such page '%s'!" % str(page + 1))
        return
    # Padding, for the sake of making it look a bit nicer
    player.message(" ")
    player.message({
        "text": "--- Showing ",
        "color": "dark_green",
        "extra": [{
            "text": "help",
            "clickEvent": {
                "action": "run_command",
                "value": "/help"
            }
        }, {
            "text": " page %d of %d ---" % (page + 1, pagecount)
        }]
    })
    for i, v in enumerate(items):
        if not i / perpage == page:
            continue
        player.message(v)
    if pagecount > 1:
        if page > 0:
            prevbutton = {
                "text": "Prev", "underlined": True, "clickEvent":
                    {"action": "run_command", "value": "%s %d" % (command, page)}
                }
        else:
            prevbutton = {"text": "Prev", "italic": True, "color": "gray"}
        if page <= pagecount:
            nextbutton = {
                "text": "Next", "underlined": True, "clickEvent":
                    {"action": "run_command", "value": "%s %d" % (command, page + 2)}
                }
        else:
            nextbutton = {"text": "Next", "italic": True, "color": "gray"}
        player.message({
                           "text": "--- ", "color": "dark_green", "extra": [prevbutton, {"text": " | "},
                                                                            nextbutton, {"text": " ---"}]
                           })


def use_style(foreground='white', background='black', options=()):
    """
    Returns a function with default parameters for addgraphics()
    options - a tuple of options.
        valid options:
            'bold'
            'italic'
            'underscore'
            'blink'
            'reverse'
            'conceal'
            'reset' - return reset code only
            'no-reset' - don't terminate string with a RESET code

    """
    return lambda text: _addgraphics(text, foreground, background, options)
