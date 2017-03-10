# -*- coding: utf-8 -*-
# Copyright (c) 2014, 2015 Miguel Ángel García (@magmax9).
# Based on previous work on gist getch()-like unbuffered character
# reading from stdin on both Windows and Unix (Python recipe),
# started by Danny Yoo. Licensed under the MIT license.

import sys
import os
import select
import tty
import termios
from . import key


def readchar(wait_for_char=True):
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    charbuffer = ''
    try:
        if wait_for_char or select.select([sys.stdin, ], [], [], 0.0)[0]:
            char = os.read(sys.stdin.fileno(), 1)
            charbuffer = char if type(char) is str else char.decode()
    except Exception:
        charbuffer = ''
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    while True:
        if charbuffer not in key.ESCAPE_SEQUENCES:
            return charbuffer
        c = readchar(False)
        if c is None:
            return charbuffer
        charbuffer += c
