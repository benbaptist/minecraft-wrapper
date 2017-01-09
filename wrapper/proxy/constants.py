# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

# Mincraft version constants
# use these constants decide how a packet should be parsed.
PROTOCOL_MAX = 4000

PROTOCOL_1_11 = 314

PROTOCOL_1_10 = 205
#
PROTOCOL_1_9_4 = 110      # post- 1.9.3 "pre" releases (1.9.3 pre-2 -)
# Still in development at versions 201-210(6/14/16)

# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=7817
PROTOCOL_1_9_3PRE3 = 109  # post- 1.9 "pre" releases (1.9.2 - 1.9.3 pre-1)

# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=7617
PROTOCOL_1_9_1PRE = 108   # post- 1.9 "pre" releases (1.9.1 pre-3 through 1.9.1)
PROTOCOL_1_9REL1 = 107    # first stable 1.9 release

# Between 49-106, the protocol is incredibly unstable.  Packet numbers changed almost weekly.
# using a version in this range will raise as UnsupportedMinecraftProtocol Exception
PROTOCOL_1_9START = 48    # start of 1.9 snapshots

# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=7368
PROTOCOL_1_8END = 47      # 1.8.9
PROTOCOL_1_8START = 6     # 1.8 snapshots start- #

# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=6003
PROTOCOL_1_7_9 = 5       # 1.7.6 - 1.7.10

# PAGE: http://wiki.vg/index.php?title=Protocol&oldid=5486
PROTOCOL_1_7 = 4          # 1.7.1-pre to 1.7.5

"""Minecraft version 1.6.4 and older used a protocol versioning scheme separate from the current one.
 Accordingly, an old protocol version number may ambiguously refer to an one of those old versions and
 from the list above.  Do not run a 1.6.4 server with proxy mode."""

# parser constants
PKT = 0
PARSER = 1

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
