# -*- coding: utf-8 -*-

# Copyright (C) 2018 - SurestTexas00
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import sys

PY3 = sys.version_info > (3,)

if PY3:
    def py_str(text, enc):
        # noinspection PyArgumentList
        return str(text, enc)

    def py_bytes(text, enc):
        # noinspection PyArgumentList
        return bytes(text, enc)

else:
    # noinspection PyUnusedLocal
    def py_str(text, enc):
        return str(text)

    # noinspection PyUnusedLocal
    def py_bytes(text, enc):
        return bytes(text)