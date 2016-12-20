# -*- coding: utf-8 -*-

from utils.helpers import mkdir_p
from utils.helpers import get_int
from utils.helpers import getargsafter
from utils.helpers import getargs
from utils.helpers import scrub_item_value
from utils.helpers import config_to_dict_read
from utils.helpers import set_item
from utils.helpers import getjsonfile
from utils.helpers import putjsonfile


class Utils:
    """
    These methods are accessed using 'self.api.utils'

    Class that wraps some utils.helpers functions for the plugin API user.
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def getArgs(arginput, i)
    '''
    return the 'i'th argument.  if item does not exist, returns ""

    '0' is 'first' argument, as normal""
    '''

    def getargsafter(arginput, position)
    '''
    returns all arguments starting at position. (positions start at '0', of course.)
    '''

    def get_int(unknown_value)
    '''
    returns an integer no matter what the input value.  returns 0 for values it can't convert.
    '''

    def makeDir(path)
    '''
    Simple way to recursively make a directory under any Python.
    '''

    def readConfigIntoDict(filename, filepath)
    '''
    reads a disk file with '=' lines (like server.properties) and returns a keyed dictionary.
    '''

    def setItem(item, string_val, filename, path='.')
    '''
    reads a file with "item=" lines and looks for 'item'.  If found, replaces the existing value
    with 'item=string_val'.
    '''

    def scrubItemValue(text_value)
    '''
    Takes a text item value and determines if it should be a boolean, integer, or text.. and returns it as that type.
    For instance, takes string 'false' and returns boolean False.  Useful for writing back dictionaries with text
    item values back to json files on disk using the proper types.
    '''

    def getJsonFile(filename, directory=".", encodedas="UTF-8")
    '''
    reads a json file and returns a dictionary if successful. filename is WITHOUT the .json extension!
    If unsuccessful; None/no data or False (if file/directory not found)
    '''

    def putJsonFile(data, filename, directory=".", indent_spaces=2, sort=False, encodedas="UTF-8")
    '''
    writes entire data to a json file. filename is WITHOUT the .json extension!
    '''


    """
    def __init__(self):
        self.getArgs = getargs
        self.getArgsAfter = getargsafter
        self.getInt = get_int
        self.makeDir = mkdir_p
        self.readConfigIntoDict = config_to_dict_read
        self.setItem = set_item
        self.scrubItemValue = scrub_item_value
        self.getJsonFile = getjsonfile
        self.putJsonFile = putjsonfile
