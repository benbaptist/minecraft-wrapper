# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from __future__ import division

import os
import errno
import sys
import json
import time
import datetime
import socket
import urllib

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

# class Helpers:
"""
This is not actually a class at all, but a module collection of
Wrapper's helpful utilities.

This module is imported with the core API and is accessible
using 'self.api.helpers'

    .. code:: python

        # can be accessed directly:
        self.api.helpers.getargs(args, 2)

        # or a local reference to the module in your plugin:
        <yourobject> = self.api.helpers
        <yourobject>.getargs(args, 2)

    ..

"""


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
    resetcode = '\x1b\x5b\x30\x6d'
    fore = {'blue': '\x33\x34', 'yellow': '\x33\x33', 'green': '\x33\x32',
            'cyan': '\x33\x36', 'black': '\x33\x30',
            'magenta': '\x33\x35', 'white': '\x33\x37', 'red': '\x33\x31'}
    back = {'blue': '\x34\x34', 'yellow': '\x34\x33', 'green': '\x34\x32',
            'cyan': '\x34\x36', 'black': '\x34\x30',
            'magenta': '\x34\x35', 'white': '\x34\x37', 'red': '\x34\x31'}
    optioncodes = {'bold': '\x31', 'italic': '\x33', 'underscore': '\x34',
                   'blink': '\x35', 'reverse': '\x37', 'conceal': '\x38'}

    codes = []
    if text == '' and len(options) == 1 and options[0] == 'reset':
        return resetcode

    if foreground:
        codes.append(fore[foreground])
    if background:
        codes.append(back[background])

    for option in options:
        if option in optioncodes:
            codes.append(optioncodes[option])
    if 'no-reset' not in options:
        text = '%s%s' % (text, resetcode)
    return '%s%s' % (('\x1b\x5b%s\x6d' % '\x3b'.join(codes)), text)


def config_to_dict_read(filename, filepath):
    """
    reads a disk file with '=' lines (like server.properties) and
    returns a keyed dictionary.

    """
    config_dict = {}
    if os.path.exists("%s/%s" % (filepath, filename)):
        config_lines = getfileaslines(filename, filepath)
        if not config_lines:
            return {}
        for line_items in config_lines:
            line_args = line_items.split("=", 1)
            if len(line_args) < 2:
                continue
            item_key = getargs(line_args, 0)
            scrubbed_value = scrub_item_value(getargs(line_args, 1))
            config_dict[item_key] = scrubbed_value
    return config_dict


def scrub_item_value(item):
    """
    Takes a text item value and determines if it should be a boolean,
    integer, or text.. and returns it as the type.

    """
    if not item or len(item) < 1:
        return ""
    if item.lower() == "true":
        return True
    if item.lower() == "false":
        return False
    if str(get_int(item)) == item:  # it is an integer if int(a) = str(a)
        return get_int(item)
    return item


def epoch_to_timestr(epoch_time):
    """
    takes a time represented as integer/string which you supply and
    converts it to a formatted string.

    :arg epoch_time: string or integer (in seconds) of epoch time

    :returns: the string version like "2016-04-14 22:05:13 -0400",
     suitable in ban files.

    """
    # allow argument to be passed as a string or integer
    tm = int(float(epoch_time))
    t = datetime.datetime.fromtimestamp(tm)
    pattern = "%Y-%m-%d %H:%M:%S %z"

    # the %z does not work below py3.2 - we just create a fake offset.
    return "%s-0100" % t.strftime(pattern)


def find_in_json(jsonlist, keyname, searchvalue):
    # internal method used only by proxy base ban code..
    for items in jsonlist:
        if items[keyname] == searchvalue:
            return items
    return None


def format_bytes(number_raw_bytes):
    """
    Internal wrapper function that takes number of bytes
    and converts to Kbtye, MiB, GiB, etc... using 4 most
    significant digits.

    :returns: tuple - (string repr of 4 digits, string units)

    """
    large_bytes = float(number_raw_bytes) / (1024*1024*1024*1024*1024)
    units = "PiB"
    if large_bytes < 1.0:
        large_bytes *= 1024
        units = "TiB"
    if large_bytes < 1.0:
        large_bytes *= 1024
        units = "GiB"
    if large_bytes < 1.0:
        large_bytes *= 1024
        units = "MiB"
    if large_bytes < 1.0:
        large_bytes *= 1024
        units = "KiB"
    # return string tuple (number, units)
    return ("%.4g" % large_bytes), ("%s" % units)


def getargs(arginput, i):
    """
    returns a certain index of argument (without producting an
    error if out of range, etc).

    :Args:
        :arginput: A list of arguments.
        :i:  index of a desired argument.

    :returns:  return the 'i'th argument.  If item does not
     exist, returns ""

    """
    if not i >= len(arginput):
        return arginput[i]
    else:
        return ""


def getargsafter(arginput, i):
    """
    returns all arguments starting at position. (positions start
    at '0', of course.)

    :Args:
        :arginput: A list of arguments.
        :i: Starting index of argument list.

    :returns: sub list of arguments

    """
    return " ".join(arginput[i:])


def getjsonfile(filename, directory=".", encodedas="UTF-8"):
    """
    Read a json file and return its contents as a dictionary.

    :Args:
        :filename: filename without extension.
        :directory: by default, wrapper script directory.
        :encodedas: the encoding

    :returns:
        :if successful: a dictionary
        :if unsuccessful:  None/{}
        :File/directory not found: False

    """
    if not os.path.exists(directory):
        mkdir_p(directory)
    if os.path.exists("%s/%s.json" % (directory, filename)):
        with open("%s/%s.json" % (directory, filename)) as f:
            try:
                return json.loads(f.read(), encoding=encodedas)
            except ValueError:
                return None
            #  Exit yielding None (no data)
    else:
        return False  # bad directory or filename


def getfileaslines(filename, directory="."):
    """
    Reads a file with lines and turns it into a list containing
    those lines.

    :Args:
        :filename: Complete filename
        :directory: by default, wrapper script directory.

    :returns:
        :if successful: a list of lines in the file.
        :if unsuccessful:  None/no data
        :File/directory not found: False

    (Pycharm return definition)
    :rtype: list

    """
    if not os.path.exists(directory):
        mkdir_p(directory)
    if os.path.exists("%s/%s" % (directory, filename)):
        with open("%s/%s" % (directory, filename), "r") as f:
            try:
                return f.read().splitlines()
            except Exception as e:
                print(_addgraphics(
                    "Exception occured while running"
                    " 'getfileaslines': \n", foreground="red"), e)
                return None
    else:
        return False


def mkdir_p(path):
    """
    A simple way to recursively make a directory under any Python.

    :arg path: The desired path to create.

    :returns: Nothing - Raises Exception if it fails

    """
    try:
        # Python > 3.2
        os.makedirs(path, exist_ok=True)
    except TypeError:
        try:
            # Python > 2.5
            os.makedirs(path)
        except OSError as exc:
            # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def get_int(s):
    """
    returns an integer representations of a string, no matter what
    the input value.

    :arg s: Any string value.

    :returns: Applicable value (or 0 for values it can't convert)

    """
    try:
        val = int(s)
    except ValueError:
        val = 0
    return val


def isipv4address(addr):
    """
    Returns a Boolean indicating if the address is a valid IPv4
    address.

    :arg addr: Address to validate.

    :returns: True or False

    """
    try:
        # Attempts to convert to an IPv4 address
        socket.inet_aton(addr)
    except socket.error:
        # If it fails, the ip is not in a valid format
        return False
    return True


def processcolorcodes(messagestring):
    """
    Mostly used internally to process old-style color-codes with
    the & symbol, and returns a JSON chat object. message received
    should be string.

    :arg messagestring: String argument with "&" codings.

    :returns: Json dumps() string.

    """
    py3 = sys.version_info > (3,)
    if not py3:
        message = messagestring.encode('ascii', 'ignore')
    else:
        # .encode('ascii', 'ignore')  # encode to bytes
        message = messagestring

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
                try:
                    # Py2-3
                    # noinspection PyUnresolvedReferences
                    it.next()
                except AttributeError:
                    it.__next__()

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
    Just replaces text containing the (&) ampersand with section
    signs instead (§).

    """
    for i in COLORCODES:
        message = message.replace("&" + i, "\xc2\xa7" + i)
    return message


def putjsonfile(data, filename, directory=".", indent_spaces=2, sort=True):
    """
    Writes entire data dictionary to a json file.

    :Args:
        :data: Dictionary to write as Json file.
        :filename: filename without extension.
        :directory: by default, current directory.
        :indent_spaces: indentation level. Pass None for no
         indents. 2 is the default.
        :sort: whether or not to sort the records for readability.

    *There is no encodedas argument: This was removed for Python3*
    *compatibility.  Python 3 has no encoding argument for json.dumps.*

    :returns:
            :True: Successful write
            :None: TypeError
            :False: File/directory not found / not accessible:

    """
    if not os.path.exists(directory):
        mkdir_p(directory)
    if os.path.exists(directory):
        with open("%s/%s.json" % (directory, filename), "w") as f:
            try:
                f.write(json.dumps(data, ensure_ascii=False,
                                   indent=indent_spaces, sort_keys=sort))
            except TypeError:
                return None
            return True
    return False


def read_timestr(mc_time_string):
    """
    The Minecraft server (or wrapper, using epoch_to_timestr) creates
    a string like this:

         "2016-04-15 16:52:15 -0400"

    This method reads out the date and returns the epoch time (well,
    really the server local time, I suppose)

    :arg mc_time_string: minecraft time string.

    :returns:
        :regular seconds from epoch: Integer
        :9999999999 symbolizing forever: For invalid data
         (like "forever").

    """

    # create the time for file:
    # time.strftime("%Y-%m-%d %H:%M:%S %z")

    # ' %z' - strptime() function does not the support %z for
    # READING timezones D:
    pattern = "%Y-%m-%d %H:%M:%S"

    try:
        epoch = int(time.mktime(time.strptime(mc_time_string[:19], pattern)))
    except ValueError:
        epoch = 9999999999
    return epoch


# Single line required by documentation creator (at this time)
def readout(commandtext, description, separator=" - ", pad=15,
            command_text_fg="magenta", command_text_opts=("bold",),
            description_text_fg="yellow", usereadline=True):
    """
    display console text only with no logging - useful for displaying
    pretty console-only messages.

    Args:
        :commandtext: The first text field (magenta)
        :description: third text field (green)
        :separator: second (middle) field (white text)
        :pad: minimum number of characters the command text is padded to
        :command_text_fg: Foreground color, magenta by default
        :command_text_opts: Tuple of ptions, '(bold,)' by default)
        :description_text_fg: description area foreground color
        :usereadline: Use default readline  (or 'False', use
         readchar/readkey (with anti- scroll off capabilities))

    :returns: Nothing. Just prints to stdout/console for console
     operator readout:

    :DISPLAYS:
        .. code:: python

            '[commandtext](padding->)[separator][description]'
        ..

    """
    commstyle = _use_style(foreground=command_text_fg,
                           options=command_text_opts)
    descstyle = _use_style(foreground=description_text_fg)
    x = '{0: <%d}' % pad
    commandtextpadded = x.format(commandtext)
    if usereadline:
        print("%s%s%s" % (commstyle(commandtextpadded),
                          separator, descstyle(description)))
    else:
        print("\033[1A%s%s%s\n" % (commstyle(commandtextpadded),
                                   separator, descstyle(description)))


def _secondstohuman(seconds):

    divisor = seconds
    if seconds < 1:
        divisor = 1
    unit = "seconds"
    if seconds > 59:
        unit = "minutes"
        divisor = 60
    if seconds > 3599:
        unit = "hours"
        divisor = 3600
    if seconds > 86399:
        unit = "days"
        divisor = 86400
    value = float(seconds) / divisor
    return "{0:.2f} {1}".format(value, unit)


def set_item(item, string_val, filename, path='.'):
    """
    Reads a file with "item=" lines and looks for 'item'. If
    found, it replaces the existing value with 'item=string_val'.
    Otherwise, it adds the entry, creating the file if need be.

    :Args:
        :item: the config item in the file.  Will search the file
         for occurences of 'item='.
        :string_val: must have a valid __str__ representation (if
         not an actual string).
        :filename: full filename, including extension.
        :path: defaults to wrappers path.

    :returns:  Nothing.  Writes the file with single entry if
     the file is not found.  Adds the entry to end of file if
     it is missing.

    """
    new_file = ""
    searchitem = "%s=" % item
    if os.path.isfile("%s/%s" % (path, filename)):
        with open("%s/%s" % (path, filename)) as f:
            file_contents = f.read()

        if searchitem in file_contents:
            current_value = str(
                file_contents.split(searchitem)[1].splitlines()[0])
            replace_item = "%s%s" % (searchitem, current_value)
            new_item = '%s%s' % (searchitem, string_val)
            new_file = file_contents.replace(replace_item, new_item)
            with open("%s/%s" % (path, filename), "w") as f:
                f.write(new_file)
            return True
        else:
            new_file = file_contents

    with open("%s/%s" % (path, filename), "w") as f:
        f.write("%s\n%s=%s" % (new_file.rstrip(), item, string_val))


def _showpage(player, page, items, command, perpage, command_prefix='/'):
    fullcommand = "%s%s" % (command_prefix, command)
    pagecount = len(items) // perpage
    if (int(len(items) // perpage)) != (float(len(items)) / perpage):
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
                "value": "%shelp" % command_prefix
            }
        }, {
            "text": " page %d of %d ---" % (page + 1, pagecount)
        }]
    })
    for i, v in enumerate(items):
        if not i // perpage == page:
            continue
        player.message(v)
    if pagecount > 1:
        if page > 0:
            prevbutton = {
                "text": "Prev", "underlined": True, "clickEvent":
                    {"action": "run_command", "value": "%s %d" % (
                        fullcommand, page)}
                }
        else:
            prevbutton = {"text": "Prev", "italic": True, "color": "gray"}
        if page <= pagecount:
            nextbutton = {
                "text": "Next", "underlined": True, "clickEvent":
                    {"action": "run_command", "value": "%s %d" % (
                        fullcommand, page + 2)}
                }
        else:
            nextbutton = {"text": "Next", "italic": True, "color": "gray"}
        player.message(
            {"text": "--- ", "color": "dark_green",
             "extra": [prevbutton, {"text": " | "},
                       nextbutton, {"text": " ---"}
                       ]})


def _use_style(foreground='white', background='black', options=()):
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


def chattocolorcodes(jsondata):

    total = _handle_extras(jsondata)
    if "extra" in jsondata:
        for extra in jsondata["extra"]:
            total += _handle_extras(extra)
    return total


def _handle_extras(extra):
    extras = ""
    if "color" in extra:
        extras += _getcolorcode(extra["color"])
    if "text" in extra:
        extras += extra["text"]
    if "string" in extra:
        extras += extra["string"]
    return extras


def _getcolorcode(color):
    for code in COLORCODES:
        if COLORCODES[code] == color:
            return u"\xa7" + code
    return ""


def _create_chat(
        translateable="death.attack.outOfWorld", insertion="<playername>",
        click_event_action="suggest_command",
        click_event_value="/msg <playername> ",
        hov_event_action="show_entity",
        hov_event_text_value="{name:\"<playername>\","
                             "id:\"3269fd15-5be9-3c2a-af6c-0000000000000\"}",
        with_text="<playername>", plain_dict_chat=""):

    """
    Internal for now.
    Creates a json minecraft chat object string (for sending over Protocol).

    :param translateable:
    :param insertion:
    :param click_event_action:
    :param click_event_value:
    :param hov_event_action:
    :param hov_event_text_value:
    :param with_text:
    :param plain_dict_chat:
    :return:

    """
    if not translateable:
        return [json.dumps(plain_dict_chat)]

    chat = {"translate": translateable,
            "with": [
                 {"insertion": insertion,
                  "clickEvent":
                      {"action": click_event_action,
                       "value": click_event_value
                       },
                  "hoverEvent":
                      {
                          "action": hov_event_action,
                          "value":
                              {
                                  "text": hov_event_text_value
                              }
                      },
                  "text": with_text
                  }
             ]
            }
    return [json.dumps(chat)]


def get_req(something, request):
    # This is a private function used by management.web
    for a in request.split("/")[1:][1].split("?")[1].split("&"):
        if a[0:a.find("=")] == something:
            # TODO PY3 unquote not a urllib (py3) method - impacts: Web mode
            # noinspection PyUnresolvedReferences
            return urllib.unquote(a[a.find("=") + 1:])
    return ""


def _test():
    testpath = "/home/surest/Desktop/testservers/server"
    banlist = getjsonfile("banned-players", testpath)
    x = find_in_json(banlist, "uuid", "d2a44ac6-6427-4f3a-98b8-33441c263cd4")
    print(x)

    banlist = getjsonfile("banned-ips", testpath)
    x = find_in_json(banlist, "ip", "127.0.0.8")
    print(x)

    x = config_to_dict_read("server.properties", testpath)
    print(x)
    print(x['pvp'])
    new_pvp = not(x['pvp'])
    set_item('pvp', new_pvp, "server.properties", testpath)
    x = config_to_dict_read("server.properties", testpath)
    print(x['pvp'])

    print(format_bytes(1024))
    print(format_bytes(1048576 * 2))
    print(format_bytes(1073741824.0))
    print(format_bytes(1234234230000))
    print(format_bytes(1234234230000000))
    print(format_bytes(123423423000000000))

    print(isipv4address("123.123.123.123"))
    print(isipv4address("honkin"))
    print(isipv4address("www.surestcraft.com"))

    timecurr = time.time()
    x = epoch_to_timestr(timecurr)
    print(str(x))
    print(read_timestr(str(x)))
    print(time.time())
    print(_secondstohuman(36986))
    print(3698 // 3600)


if __name__ == "__main__":
    _test()
