# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

""" 
Custom Wrapper Exception Classes
"""


class WrapperException(Exception):
    """ Base Wrapper Exception Class """
    pass


class UnsupportedOSException(WrapperException):
    """ Exception raised when a command is not supported by the OS """
    pass


class NonExistentPlugin(WrapperException):
    """ Exception raised when a plugin does not exist """
    pass


class MalformedFileError(WrapperException):
    """ Exception raised on parse error """
    pass


class InvalidServerStartedError(WrapperException):
    """ Exception raised when the MCServer is not in the correct state """
    pass


class UnsupportedMinecraftProtocol(WrapperException):
    """ Exception raised when a non-supported protocol is passed to mcpacket.py """
    pass
