# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

# Data constants
# ------------------------------------------------

STRING = 0
JSON = 1
UBYTE = 2
BYTE = 3
INT = 4
SHORT = 5
USHORT = 6
LONG = 7
DOUBLE = 8
FLOAT = 9
BOOL = 10
VARINT = 11
BYTEARRAY = 12
BYTEARRAY_SHORT = 13
POSITION = 14

# gets full slot info, including NBT data.
SLOT = 15

# This fellow is a bit of a hack that allows getting the basic slot data where the NBT part may be buggy or
#  you are not sure you are correctly parsing the NBT data (like in older pre-1.8 minecrafts).
SLOT_NO_NBT = 18

UUID = 16

METADATA = 17  # this is the old pre-1.9 metadata parsing.  It is radically different in 1.9+ now (through 11.2 atm)
METADATA_1_9 = 19


# Both of these just read or send the rest of the packet in its raw bytes form.
REST = 90
RAW = 90

# allows the insertion of padding into argument lists.  Any field with this designation is just
#  silently skipped.
NULL = 100
