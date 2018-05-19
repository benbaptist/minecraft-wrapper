# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from __future__ import division
from __future__ import print_function

import os
import errno
import sys
import json
import time
import datetime
import socket

version = sys.version_info
PY3 = version[0] > 2

if PY3:
    # noinspection PyPep8Naming
    import pickle as Pickle
else:
    # noinspection PyUnresolvedReferences
    import cPickle as Pickle

VALID_CODES = list("0123456789abcdefrklmno")
VALID_COLORS = list("0123456789abcdef")

CODENAMES = {
    "black": "0",
    "dark_blue": "1",
    "dark_green": "2",
    "dark_aqua": "3",
    "dark_red": "4",
    "dark_purple": "5",
    "gold": "6",
    "gray": "7",
    "dark_gray": "8",
    "blue": "9",
    "green": "a",
    "aqua": "b",
    "red": "c",
    "light_purple": "d",
    "yellow": "e",
    "white": "f",
    "reset": "r",
    "obfuscated": "k",
    "bold": "l",
    "strikethrough": "m",
    "underline": "n",
    "italic": "o"
}

COLORS = {
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
    "f": "white"
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


def config_write_from_dict(filename, filepath, dictionary):
    """
    Use a keyed dictionary and write a disk file with '='
    lines (like server.properties).
    """
    config_dict = dictionary
    newfile = ""
    for items in config_dict:
        newfile += "%s=%s\n" % (items, config_dict[items])

    with open("%s/%s" % (filepath, filename), "w") as f:
        f.write(newfile)


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
    and converts to KiB, MiB, GiB, etc... using 4 most
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
    returns a certain index of argument (without producing an
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
        :File not found: False (any requested directory would be created)

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

    :returns: Applicable value (or 0 for values it can't convert). Booleans or
     other types return their truth value as 1 (true) or 0 (false)

    """
    try:
        val = int(s)
    except ValueError:
        val = 0
    except TypeError:
        if s:
            val = 1
        else:
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


def pickle_load(path, filename):
    """
    Load data from a Pickle file (*.pkl).  Normally the returned data would
     be a dictionary or other python object.  Used to retrieve data that was
     previously `pickle_save`d.

    :Args:
        :path: path to file (no trailing slash)
        :filename: filename including extension

    :returns: saved data.  Failure will yield empty dictionary

    """
    with open("%s/%s" % (path, filename), "rb") as f:
        try:
            return Pickle.load(f)
        except EOFError:
            return {}


def pickle_save(path, filename, data, encoding="machine"):
    """
    Save data to Pickle file (*.pkl).  Allows saving dictionary or other
    data in a way that json cannot always be saved due to json formatting
    rules.

    :Args:
        :path: path to file (no trailing slash)
        :filename: filename including *.pkl extension
        :data: Data to be pickled.
        :encoding: 'Machine' or 'Human' - determines whether file contents
         can be viewed in a text editor.

    :returns: Nothing.  Assumes success; errors will raise exception.

    """
    if "human" in encoding.lower():
        _protocol = 0
    else:
        # using something less than HIGHEST allows both Pythons 2/3
        # to use the files interchangeably.  It should also allow
        # moving files between machines with different configurations
        # with fewer issues.
        #
        # Python 2 cPickle does not have a DEFAULT_PROTOCOL
        # constant like Python 3 pickle (else I would just
        # use the Default (currently 3, I believe).
        #
        # This will probably use either 1 or 2 depending on
        # which python you use.
        #
        # We imported either pickle (Py3) or cPickle (Py2) depending
        # on what wrapper detected.  Both are implemented in C for
        # speed.
        #
        # The MAIN POINT:
        # I wanted the code to use something better/faster than
        # Human-readable (unless that is what you specify), while
        # still permitting some portability of the final files
        _protocol = Pickle.HIGHEST_PROTOCOL // 2

    with open("%s/%s" % (path, filename), "wb") as f:
        Pickle.dump(data, f, protocol=_protocol)


def processcolorcodes(messagestring):
    """
    Mostly used internally to process old-style color-codes with
    the & symbol, and returns a JSON chat object. message received
    should be string.

    upgraded to allow inserting URLS by 

    :arg messagestring: String argument with "&" codings.

    :returns: Dictionary chat

    """
    if not PY3:
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

        # probably needed because some Py2 code may try to pass a byte string
        if char not in ("&", u'&'):

            # Space is used to end any URL designation
            if char == " ":
                url = False

            # add normal characters to text buffer
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

            if code in VALID_COLORS:
                color = COLORS[code]

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

            # Py2-3
            try:
                # noinspection PyUnresolvedReferences
                it.next()
            except AttributeError:
                # noinspection PyUnresolvedReferences
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
    return {"text": "", "extra": extras}


def processoldcolorcodes(message):
    """
    Just replaces text containing the (&) ampersand with section
    signs instead (§).

    """
    for i in VALID_CODES:
        message = message.replace("&" + i, "§" + i)
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
def _readout(commandtext, description, separator, pad,
             command_text_fg, command_text_opts, description_text_fg,
             usereadline):
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


# Single line required by documentation creator (at this time)
def readout(commandtext, description, separator=" - ", pad=15, command_text_fg="magenta", command_text_opts=("bold",), description_text_fg="yellow", usereadline=True, player=None):  # noqa
    """
    (wraps _readout)
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
        :player: if the console, it goes via standard readout. otherwise,
         for other players, it passes to a player.message().

    :returns: Nothing. Just prints to stdout/console for console
     operator readout:

    :DISPLAYS:
        .. code:: python

            '[commandtext](padding->)[separator][description]'
        ..

    """

    if player is None or player.username == "*Console*":
        _readout(commandtext, description, separator, pad,
                 command_text_fg, command_text_opts,
                 description_text_fg, usereadline)
    else:
        x = '{0: <%d}' % pad
        commandtextpadded = x.format(commandtext)
        message = "%s%s%s" % (commandtextpadded, separator, description)
        player.message({"text": message, "color": "dark_purple"})


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
    """ Convert a chat dictionary to a string with '§_' codes
    
    :jsondata: Dictionary of minecraft chat 
    :returns: a string formatted with '§_' codes
    
    """
    total = _handle_chat_items(jsondata)
    if "extra" in jsondata:
        for extra in jsondata["extra"]:
            total += _handle_chat_items(extra)
    return total


def _handle_chat_items(items):
    """ take dictionary of items and handle top-level items
    :items: The chat dictionary or one of its extra items
    """
    extras = ""

    # if "text" in items and len(items["text"]) > 0:
    #  only process codes it there is associated text
    if "color" in items:
        extras += _getformatcode(items["color"])

    formats = (
        "italic", "bold", "obfuscated", "strikethrough", "underline")
    for codes in formats:
        if codes in items and items[codes] is True:
            extras += _getformatcode(codes)

    if "text" in items:
        extras += items["text"]
    if "string" in items:
        extras += items["string"]
    return extras


def _getformatcode(name):
    """
    return the named code as a '§_' color/formatting code. If name
    is not a valid code, returns the reset code '§r'.
    :param name: a name of a color ('blue', 'green', etc)
    """
    if name in CODENAMES:
        return "§" + CODENAMES[name]
    return "§r"


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


def _test():
    # from pprint import pprint
    timecurr = time.time()
    print("Current system time:", timecurr)
    x = epoch_to_timestr(timecurr)
    print("Today's date in minecraft format:", x)
    print("coverted back to epoch format:", read_timestr(x))
    print("")

    testpath = "/home/surest/Desktop/testservers/server"
    testuuid = "d2a44ac6-6427-4f3a-98b8-33441c263cd4"
    print("test server path is:", testpath)
    print("test UUID (str):", testuuid)

    banlist = getjsonfile("banned-players", testpath)
    x = find_in_json(banlist, "uuid", testuuid)
    print("ban record (as a dictionary) for uuid", testuuid)
    print("    :", x)
    print("")

    print("making assertion tests...")
    time.sleep(.1)
    banlist = getjsonfile("banned-ips", testpath)
    x = find_in_json(banlist, "ip", "127.0.0.8")
    assert type(x) is dict

    x = config_to_dict_read("server.properties", testpath)
    assert type(x) is dict
    assert 'pvp' in x
    new_pvp = not(x['pvp'])

    set_item('pvp', new_pvp, "server.properties", testpath)
    x = config_to_dict_read("server.properties", testpath)
    assert 'pvp' in x
    assert x['pvp'] == new_pvp

    config_write_from_dict("server.properties", testpath, x)
    y = config_to_dict_read("server.properties", testpath)
    print("Asserting config write works")
    assert(x == y)

    assert (format_bytes(1024)) == ('1', 'KiB')
    assert (format_bytes(1048576 * 2)) == ('2', 'MiB')
    assert (format_bytes(1073741824.0)) == ('1', 'GiB')
    assert (format_bytes(1234234230000)) == ('1.123', 'TiB')
    assert (format_bytes(1234234230000000)) == ('1.096', 'PiB')
    assert (format_bytes(123423423000000000)) == ('109.6', 'PiB')

    assert (isipv4address("123.123.123.123")) is True
    assert (isipv4address("honkin")) is False
    assert (isipv4address("www.surestcraft.com")) is False

    assert (_secondstohuman(36986) == '10.27 hours')
    assert (3698 // 3600) == 1

    mydict = {"obfuscated": True, "underlined": True, "bold": True,
              "italic": True, "color": "white", "text": "hello",
              "clickEvent": {}, "strikethrough": False}

    # test chat items
    print("testing _handle_chat_items")
    assert _handle_chat_items(mydict) == "§f§o§l§khello"
    print("_handle_chat_items passsed")

    print("testing processcolorcodes")
    newdict = {
        "text": "", "extra": [
            {"obfuscated": False, "underlined": False, "bold": False,
             "italic": False, "color": "white", "text": "", "clickEvent": {},
             "strikethrough": False},
            {"obfuscated": False, "underlined": False, "bold": False,
             "italic": True, "color": "white", "text": "", "clickEvent": {},
             "strikethrough": False},
            {"obfuscated": False, "underlined": False, "bold": False,
             "italic": False, "color": "dark_aqua", "text": "harro ",
             "clickEvent": {}, "strikethrough": False},
            {"obfuscated": False, "underlined": False, "bold": True,
             "italic": False, "color": "dark_aqua", "text": "",
             "clickEvent": {}, "strikethrough": False},
            {"obfuscated": False, "bold": False, "color": "gold",
             "text": "there", "strikethrough": False,
             "underlined": False, "italic": False}]}

    print("-------------------------")
    print(newdict)

    print("-------------------------")

    print(processcolorcodes('&o&3harro &l&6there'))
    assert processcolorcodes(
        '&o&3harro &l&6there') == newdict

    print("testing processcolorcodes passed")
    assert chattocolorcodes(newdict) == "§f§f§o§3harro §3§l§6there"

    print("assertion tests succeeded.")
    print(epoch_to_timestr(1501437714))


if __name__ == "__main__":
    _test()
