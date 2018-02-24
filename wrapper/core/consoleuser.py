# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

"""
Collection of Virtual player classes used elsewhere.
"""

import time
from api.helpers import readout


# - due to being refrerenced by the external wrapper API that is camelCase
# noinspection PyUnresolvedReferences,PyPep8Naming,PyBroadException
class ConsolePlayer(object):
    """
    This class minimally represents the console as a player so
    that the console can use wrapper/plugin commands.

    used by core.wrapper.py

    """

    def __init__(self, wrapper, outputstream=None):
        self.username = "*Console*"
        self.loggedIn = time.time()
        self.wrapper = wrapper
        self.log = wrapper.log
        if outputstream is None:
            self.output_stream = self._default_output
        else:
            self.output_stream = outputstream

        # if self.abort is ever used, must follow `self.abort.halt`
        self.abort = wrapper.halt

        # these map minecraft color codes to "approximate" ANSI
        # terminal color used by our color formatter.
        self.message_number_coders = {'0': 'black',
                                      '1': 'blue',
                                      '2': 'green',
                                      '3': 'cyan',
                                      '4': 'red',
                                      '5': 'magenta',
                                      '6': 'yellow',
                                      '7': 'white',
                                      '8': 'black',
                                      '9': 'blue',
                                      'a': 'green',
                                      'b': 'cyan',
                                      'c': 'red',
                                      'd': 'magenta',
                                      'e': 'yellow',
                                      'f': 'white'
                                      }

        # these do the same for color names (things like 'red',
        # 'white', 'yellow, etc, not needing conversion...)
        self.messsage_color_coders = {'dark_blue': 'blue',
                                      'dark_green': 'green',
                                      'dark_aqua': 'cyan',
                                      'dark_red': 'red',
                                      'dark_purple': 'magenta',
                                      'gold': 'yellow',
                                      'gray': 'white',
                                      'dark_gray': 'black',
                                      'aqua': 'cyan',
                                      'light_purple': 'magenta'
                                      }

    @staticmethod
    def isOp():
        return 10

    def __str__(self):
        """
        Permit the console to have a nice display instead of
        returning the object instance notation.
        """
        return self.username

    def _default_output(self, message):
        """This translates chat type messages intended for a minecraft
        client into printed colorized console lines."""
        displaycode, displaycolor = "5", "magenta"
        display = str(message)
        if type(message) is dict:
            jsondisplay = message
        else:
            jsondisplay = False
        # format "&c" type color (roughly) to console formatters color
        if display[0:1] == "&":
            displaycode = display[1:1]
            display = display[2:]
        if displaycode in self.message_number_coders:
            displaycolor = self.message_number_coders[displaycode]
        if jsondisplay:  # or use json formatting, if available
            if "text" in jsondisplay:
                display = jsondisplay["text"]
            if "color" in jsondisplay:
                displaycolor = jsondisplay["color"]
                if displaycolor in self.messsage_color_coders:
                    displaycolor = self.messsage_color_coders[displaycolor]
        readout(display, "", "", pad=15, command_text_fg=displaycolor,
                usereadline=self.wrapper.use_readline)

    def message(self, message, _=0):
        """
        This is a substitute for the player.message() that plugins and
        the command interface expects for player objects.

        :param message : message to user.

        :param _ : unused by Console user interface.  Could be an
         expected argument for player.message(message, position)

        To change the output stream, pass your own function to output_stream:

        `self.output_stream = my_output_function`

        """
        # only option for now is Console output, although the xPlayer/Console
        # interface is used elsewhere in the code (like Web)
        self.output_stream(message)

    def execute(self, string):
        """
        execute as console player directly to server console
        :param string: Command to execute with no leading slash
        :return: returns nothing.. performs action
        """
        self.wrapper.javaserver.console(string)

    @staticmethod
    def hasPermission(*args):
        """return console as always having the requested permission"""
        if args:
            return True
