# -*- coding: utf-8 -*-

# Copyright (C) 2017 - SurestTexas00.
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.
#
# However, this file is based heavily on this gist:
# http://code.activestate.com/recipes/134892/
# and is therefore also attributed to DannyYoo and company.
#
# Some elements (like the ESCAPE_SEQUENCES construct) are
# attibuted to Miguel Ángel García (@magmax9) and his
# readchar package.


import sys

WINDOWS = True
try:
    import msvcrt
except ImportError:
    WINDOWS = False
    import tty
    import termios

# Linux keyboard constants
ESC = '\x1b'
TAB = '\x09'
LF = '\x0d'
CR = '\x0a'
ENTER = '\x0d'
BACKSPACE = '\x7f'
CTRL_A = '\x01'
CTRL_B = '\x02'
CTRL_C = '\x03'
CTRL_D = '\x04'
CTRL_E = '\x05'
CTRL_F = '\x06'
CTRL_Z = '\x1a'
ALT_TAB = '\x1b\x09'
ALT_A = '\x1b\x61'
CTRL_ALT_A = '\x1b\x01'
UP = '\x1b\x5b\x41'
DOWN = '\x1b\x5b\x42'
LEFT = '\x1b\x5b\x44'
RIGHT = '\x1b\x5b\x43'
CTRL_ALT_DEL = '\x1b\x5b\x33\x5e'
F1 = '\x1b\x4f\x50'
F2 = '\x1b\x4f\x51'
F3 = '\x1b\x4f\x52'
F4 = '\x1b\x4f\x53'
F5 = '\x1b\x5b\x31\x35\x7e'
F1_1 = '\x1b\x5b\x5b\x41'
F2_1 = '\x1b\x5b\x5b\x42'
F3_1 = '\x1b\x5b\x5b\x43'
F4_1 = '\x1b\x5b\x5b\x44'
F5_1 = '\x1b\x5b\x5b\x45'
F6 = '\x1b\x5b\x31\x37\x7e'
F7 = '\x1b\x5b\x31\x38\x7e'
F8 = '\x1b\x5b\x31\x39\x7e'
F9 = '\x1b\x5b\x32\x30\x7e'
F10 = '\x1b\x5b\x32\x31\x7e'
F11_1 = '\x1b\x5b\x32\x33\x7e'
F11 = '\x1b\x5b\x32\x33\x7e\x1b'
F12_1 = '\x1b\x5b\x32\x34\x7e'
F12 = '\x1b\x5b\x32\x34\x7e\x08'
PAGE_UP = '\x1b\x5b\x35\x7e'
PAGE_DOWN = '\x1b\x5b\x36\x7e'
HOME_1 = '\x1b\x5b\x31\x7e'
END_1 = '\x1b\x5b\x34\x7e'
INSERT = '\x1b\x5b\x32\x7e'
DELETE = '\x1b\x5b\x33\x7e'
HOME = '\x1b\x5b\x48'
END = '\x1b\x5b\x46'
# Windows
BACKSPACE_WIN = '\x08'
CTRL_X_WIN = '\x18'
CTRL_ALT_A_WIN = '\x00\x1e'
UP_WIN = '\xe0\x48'
DOWN_WIN = '\xe0\x50'
LEFT_WIN = '\xe0\x4b'
RIGHT_WIN = '\xe0\x4d'
F1_WIN = '\x00\x3b'
F2_WIN = '\x00\x3c'
F3_WIN = '\x00\x3d'
F4_WIN = '\x00\x3e'
F5_WIN = '\x00\x3f'
F6_WIN = '\x00\x40'
F7_WIN = '\x00\x41'
F8_WIN = '\x00\x42'
F9_WIN = '\x00\x43'
F10_WIN = '\x00\x44'
F11_WIN = '\xe0\x85'
F12_WIN = '\xe0\x86'
PAGE_UP_WIN = '\xe0\x49'
PAGE_DOWN_WIN = '\xe0\x51'
INSERT_WIN = '\xe0\x52'
DELETE_WIN = '\xe0\x53'
HOME_WIN = '\xe0\x47'
END_WIN = '\xe0\x4f'
PAGE_UP_WIN_NUMLOCK = '\x00\x49'
PAGE_DOWN_WIN_NUMLOCK = '\x00\x51'
HOME_WIN_NUMLOCK = '\x00\x47'
END_WIN_NUMLOCK = '\x00\x4f'
UP_WIN_NUMLOCK = '\x00\x48'
DOWN_WIN_NUMLOCK = '\x00\x50'
LEFT_WIN_NUMLOCK = '\x00\x4b'
RIGHT_WIN_NUMLOCK = '\x00\x4d'
INSERT_WIN_NUMLOCK = '\x00\x52'
DELETE_WIN_NUMLOCK = '\x00\x53'

NAMES = {
    ESC: 'esc',
    TAB: 'tab',
    LF: 'lf',
    CR: 'cr',
    ENTER: 'enter',
    BACKSPACE: 'backspace',
    CTRL_A: 'ctrl-a',
    CTRL_B: 'ctrl-b',
    CTRL_C: 'ctrl-c',
    CTRL_D: 'ctrl-d',
    CTRL_E: 'ctrl-e',
    CTRL_F: 'ctrl-f',
    CTRL_Z: 'ctrl-z',
    ALT_TAB: 'alt-tab',
    ALT_A: 'alt-a',
    CTRL_ALT_A: 'ctrl-alt-a',
    UP: 'up',
    DOWN: 'down',
    LEFT: 'left',
    RIGHT: 'right',
    CTRL_ALT_DEL: 'ctrl-alt-del',
    F1: 'f1',
    F2: 'f2',
    F3: 'f3',
    F4: 'f4',
    F5: 'f5',
    F1_1: 'f1',
    F2_1: 'f2',
    F3_1: 'f3',
    F4_1: 'f4',
    F5_1: 'f5',
    F6: 'f6',
    F7: 'f7',
    F8: 'f8',
    F9: 'f9',
    F10: 'f10',
    F11: 'f11',
    F12: 'f12',
    F11_1: 'f11',
    F12_1: 'f12',
    PAGE_UP: 'page-up',
    PAGE_DOWN: 'page-down',
    HOME_1: 'home',
    END_1: 'end',
    INSERT: 'insert',
    DELETE: 'delete',
    HOME: 'home',
    END: 'end',
    BACKSPACE_WIN: 'backspace',
    CTRL_X_WIN: 'ctrl-x',
    CTRL_ALT_A_WIN: 'ctrl-alt-a',
    UP_WIN: 'up',
    DOWN_WIN: 'down',
    LEFT_WIN: 'left',
    RIGHT_WIN: 'right',
    F1_WIN: 'f1',
    F2_WIN: 'f2',
    F3_WIN: 'f3',
    F4_WIN: 'f4',
    F5_WIN: 'f5',
    F6_WIN: 'f6',
    F7_WIN: 'f7',
    F8_WIN: 'f8',
    F9_WIN: 'f9',
    F10_WIN: 'f10',
    F11_WIN: 'f11',
    F12_WIN: 'f12',
    PAGE_UP_WIN: 'page-up',
    PAGE_DOWN_WIN: 'page-down',
    INSERT_WIN: 'insert',
    DELETE_WIN: 'delete',
    HOME_WIN: 'home',
    END_WIN: 'end',
    PAGE_UP_WIN_NUMLOCK: 'page-up',
    PAGE_DOWN_WIN_NUMLOCK: 'page-down',
    HOME_WIN_NUMLOCK: 'home',
    END_WIN_NUMLOCK: 'end',
    UP_WIN_NUMLOCK: 'up',
    DOWN_WIN_NUMLOCK: 'down',
    LEFT_WIN_NUMLOCK: 'left',
    RIGHT_WIN_NUMLOCK: 'right',
    INSERT_WIN_NUMLOCK: 'insert',
    DELETE_WIN_NUMLOCK: 'delete',
}

ESCAPE_SEQUENCES = (
    ESC,
    ESC + '\x5b',
    ESC + '\x5b' + '\x5b',
    ESC + '\x5b' + '\x31',
    ESC + '\x5b' + '\x32',
    ESC + '\x5b' + '\x33',
    ESC + '\x5b' + '\x34',
    ESC + '\x5b' + '\x35',
    ESC + '\x5b' + '\x36',

    ESC + '\x5b' + '\x31' + '\x33',
    ESC + '\x5b' + '\x31' + '\x34',
    ESC + '\x5b' + '\x31' + '\x35',
    ESC + '\x5b' + '\x31' + '\x36',
    ESC + '\x5b' + '\x31' + '\x37',
    ESC + '\x5b' + '\x31' + '\x38',
    ESC + '\x5b' + '\x31' + '\x39',

    ESC + '\x5b' + '\x32' + '\x30',
    ESC + '\x5b' + '\x32' + '\x31',
    ESC + '\x5b' + '\x32' + '\x32',
    ESC + '\x5b' + '\x32' + '\x33',
    ESC + '\x5b' + '\x32' + '\x34',
    ESC + '\x5b' + '\x32' + '\x33' + '\x7e',
    ESC + '\x5b' + '\x32' + '\x34' + '\x7e',
    ESC + '\x4f',

    ESC + ESC,
    ESC + ESC + '\x5b',
    ESC + ESC + '\x5b' + '\x32',
    ESC + ESC + '\x5b' + '\x33',

    # Windows sequences
    '\x00',
    '\xe0',
)


class _Getch(object):
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.getch = _GetchWindows()
        except ImportError:
            self.getch = _GetchUnix()

    def __call__(self): return self.getch()


class _GetchUnix(object):
    def __init__(self):
        pass

    def __call__(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows(object):
    def __init__(self):
        if not WINDOWS:
            # purposely cause import error for try-except
            # noinspection PyUnresolvedReferences
            import msvcrt

    def __call__(self):
        # noinspection PyUnresolvedReferences
        return msvcrt.getch().decode('latin-1')


def getcharacter():
    g = _Getch()
    charbuffer = ""
    while True:
        # noinspection PyArgumentEqualDefault
        char1 = g.__call__()
        if (charbuffer + char1) not in ESCAPE_SEQUENCES:
            charbuffer += char1
            break

        if (charbuffer + char1) == charbuffer:
            break

        charbuffer += char1
    return charbuffer


def convertchar(charbuffer):
    if charbuffer in NAMES:
        return NAMES[charbuffer]
    return None


def _test():
    running = True
    while running:
        charbuffer = getcharacter()
        name = convertchar(charbuffer)
        if name == "up":
            print("UP key...")
        it = "\\x".join("{:02x}".format(ord(c)) for c in charbuffer)
        if name:
            print(name)
        else:
            print("\\x%s" % it)
        if name == "ctrl-c":
            break


if __name__ == "__main__":
    _test()
