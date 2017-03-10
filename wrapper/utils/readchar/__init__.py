# -*- coding: utf-8 -*-

# Copyright (c) 2014, 2015 Miguel Ángel García (@magmax9).
# Based on previous work on gist getch()-like unbuffered character
# reading from stdin on both Windows and Unix (Python recipe),
# started by Danny Yoo. Licensed under the MIT license.

from .readchar import readchar, readkey
from . import key

__all__ = [readchar, readkey, key]

__version__ = '1.1.1'
