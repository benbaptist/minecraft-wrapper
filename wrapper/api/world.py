# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import struct
import json


# noinspection PyPep8Naming
class World(object):
    """
    .. code:: python

        def __init__(self, name, mcserver)

    ..

    This class is accessed via getWorld().  Requires a running server.

    .. code:: python

        <object> = self.api.minecraft.getWorld()
        <object>.<World_method>
    ..

    World is established by console when wrapper reads "preparing ...."

    """
    def __init__(self, name, mcserver):
        self.name = name
        self.javaserver = mcserver
        self.log = mcserver.log

        self.chunks = {}  # not implemented

    def __str__(self):
        return self.name

    def setBlock(self, x, y, z, tilename, damage=0, mode="replace", data=None):
        if not data:
            data = {}
        self.javaserver.console("setblock %d %d %d %s %d %s %s" % (
            x, y, z, tilename, damage, mode, json.dumps(data)))

    def fill(self, position1, position2, tilename, damage=0, mode="destroy", data=None):
        """
        Fill a 3D cube with a certain block.

        :Args:
            :position1: tuple x, y, z
            :position2: tuple x, y, z
            :damage: see minecraft Wiki
            :mode: destroy, hollow, keep, outline
            :data: see minecraft Wiki

        """
        if not data:
            data = {}
        if mode not in ("destroy", "hollow", "keep", "outline"):
            raise Exception("Invalid mode: %s" % mode)
        x1, y1, z1 = position1
        x2, y2, z2 = position2
        if self.javaserver.protocolVersion < 6:
            raise Exception("Must be running Minecraft 1.8 or above"
                            " to use the world.fill() method.")
        else:
            self.javaserver.console(
                "fill %d %d %d %d %d %d %s %d %s %s" % (
                 x1, y1, z1, x2, y2, z2,
                 tilename, damage, mode, json.dumps(data)))

    def replace(self, position1, position2, tilename1, damage1, tilename2, damage2=0):
        """
        Replace specified blocks within a 3D cube with another specified block.

        :Args: see minecraft Wiki

        """
        x1, y1, z1 = position1
        x2, y2, z2 = position2
        if self.javaserver.protocolVersion < 6:
            raise Exception(
                "Must be running Minecraft 1.8 or above"
                " to use the world.replace() method.")
        else:
            self.javaserver.console(
                "fill %d %d %d %d %d %d %s %d replace %s %d" % (
                 x1, y1, z1, x2, y2, z2,
                 tilename2, damage2, tilename1, damage1))
        return

    def getBlock(self, pos):
        """
        not implemented

        """
        x, y, z = pos
        chunkx, chunkz = int(x / 16), int(z / 16)
        localx, localz = (x / 16.0 - x / 16) * 16, (z / 16.0 - z / 16) * 16
        # print chunkx, chunkz, localx, y, localz
        return self.chunks[chunkx][chunkz].getBlock(localx, y, localz)

    def setChunk(self, x, z, chunk):
        """ not implemented """
        if x not in self.chunks:
            self.chunks[x] = {}
        self.chunks[x][z] = chunk


# noinspection PyPep8Naming
class Chunk(object):
    """
    not implemented

    """
    def __init__(self, bytesarray, x, z):
        self.ids = struct.unpack("<" + ("H" * (len(bytesarray) / 2)), bytesarray)
        self.x = x
        self.z = z
        # for i,v in enumerate(bytesarray):
        #   y = math.ceil(i/256)
        #   if y not in self.blocks: self.blocks[y] = {}
        #   z = int((i/256.0 - int(i/256.0)) * 16)
        #   if z not in self.blocks[y]: self.blocks[y][z] = {}
        #   x = (((i/256.0 - int(i/256.0)) * 16) - z) * 16
        #   if x not in self.blocks[y][z]: self.blocks[y][z][x] = i

    def getBlock(self, x, y, z):
        # print x, y, z
        i = int((y * 256) + (z * 16) + x)
        bid = self.ids[i]
        return bid
