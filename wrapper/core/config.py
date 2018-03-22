# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import os
import sys
import logging
from api.helpers import getjsonfile, putjsonfile
from api.wrapperconfig import *


class Config(object):
    def __init__(self):
        self.log = logging.getLogger('Config')
        self.config = {}
        self.exit = False

    def loadconfig(self):
        # load older versions of wrapper.properties to preserve prior settings.
        if os.path.exists("wrapper.properties"):
            with open("wrapper.properties", "r") as f:
                oldconfig = f.read()
            oldconfig = "Deprecated File!  Use the 'wrapper.properties.json' instead!\n\n%s" % oldconfig
            with open("_wrapper.properties", "w") as f:
                f.write(oldconfig)
            os.remove("wrapper.properties")

        # Create new config if none exists
        if not os.path.exists("wrapper.properties.json"):
            putjsonfile(CONFIG, "wrapper.properties", sort=True)
            self.exit = True

        # Read existing configuration
        self.config = getjsonfile("wrapper.properties")  # the only data file that must be UTF-8
        if self.config is None:
            self.log.error("I think you messed up the Json formatting of your "
                           "wrapper.properties.json file. "
                           "Take your file and have it checked at: \n"
                           "http://jsonlint.com/")
            self.exit = True

        # detection and addition must be separated to prevent changing dictionary while iterating over it.
        # detect changes
        changesmade = False
        deprecated_entries = []
        new_sections = []
        new_entries = []
        for section in CONFIG:
            if section not in self.config:
                self.log.debug("Adding section [%s] to configuration", section)
                new_sections.append(section)
                changesmade = True

            for configitem in CONFIG[section]:
                if section in self.config:
                    # mark deprecated items for deletion
                    if configitem in self.config[section]:
                        if CONFIG[section][configitem] == "deprecated":
                            self.log.debug("Deprecated item '%s' in section '%s'. - removing it from"
                                           " wrapper properties", configitem, section)
                            deprecated_entries.append([section, configitem])
                            changesmade = True
                    # mark new items for addition
                    else:
                        # handle new items in an existing section
                        if CONFIG[section][configitem] != "deprecated":  # avoid re-adding deprecated items
                            self.log.debug("Item '%s' in section '%s' not in wrapper properties - adding it!",
                                           configitem, section)
                            new_entries.append([section, configitem])
                            changesmade = True
                else:
                    # handle new items in a (new) section
                    self.log.debug("Item '%s' in new section '%s' not in wrapper properties - adding it!",
                                   configitem, section)
                    new_entries.append([section, configitem])
                    changesmade = True

        # Apply changes and save.
        if changesmade:
            # add new section
            if len(new_sections) > 0:
                for added_section in new_sections:
                    self.config[added_section] = {}

            # Removed deprecated entries
            if len(deprecated_entries) > 0:
                for removed in deprecated_entries:
                    del self.config[removed[0]][removed[1]]

            # Add new entries
            if len(new_entries) > 0:
                for added in new_entries:
                    self.config[added[0]][added[1]] = CONFIG[added[0]][added[1]]

            self.save()
            self.exit = True

        if self.exit:
            self.log.warning(
                "Updated wrapper.properties.json file - check and edit configuration if needed and start again.")
            sys.exit()

    def change_item(self, section, item, desired_value):
        if section in self.config:
            if item in self.config[section]:
                self.config[section][item] = desired_value
                return True
            else:
                self.log.error("Item '%s' not found in section '%s' of the wrapper.properties.json" % (item, section))
                return False
        else:
            self.log.error("Section '%s' does not exist in the wrapper.properties.json" % section)
            return False

    def save(self):
        putjsonfile(self.config, "wrapper.properties", sort=True)
