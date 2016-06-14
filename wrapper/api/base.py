# -*- coding: utf-8 -*-

# p2 and py3 compliant (no PyCharm IDE-flagged errors)
#  (still has weak warnings in both versions)

import time

import core.exceptions as exceptions

from api.minecraft import Minecraft
from core.storage import Storage

""" api.py contains the majority of code for the plugin API. """


# noinspection PyPep8Naming
class API:
    """ 
    The API class contains methods for basic plugin functionality, such as handling events,
    registering commands, and more. Most methods aren't related to gameplay, aside from commands
    and events, but for core stuff. See the Minecraft class (accessible at self.api.minecraft)
    for more gameplay-related methods.
    """
    statuseffects = {
        "speed": 1,
        "slowness": 2,
        "haste": 3,
        "mining_fatigue": 4,
        "strength": 5,
        "instant_health": 6,
        "instant_damage": 7,
        "jump_boost": 8,
        "nausea": 9,
        "regeneration": 10,
        "resistance": 11,
        "fire_resistance": 12,
        "water_breathing": 13,
        "invisibility": 14,
        "blindness": 15,
        "night_vision": 16,
        "hunger": 17,
        "weakness": 18,
        "poison": 19,
        "wither": 20,
        "health_boost": 21,
        "absorption": 22,
        "saturation": 23
    }
    colorcodes = {
        "0": "black",
        "1": "dark_blue",
        "2": "dark_green",
        "3": "dark_aqua",
        "4": "dark_red",
        "5": "dark_purple",
        "6": "gold",
        "7": "gray",
        "8": "dark_gray",
        "9": "blue",
        "a": "green",
        "b": "aqua",
        "c": "red",
        "d": "light_purple",
        "e": "yellow",
        "f": "white",
        "r": "\xc2\xa7r",
        "k": "\xc2\xa7k",  # obfuscated
        "l": "\xc2\xa7l",  # bold
        "m": "\xc2\xa7m",  # strikethrough
        "n": "\xc2\xa7n",  # underline
        "o": "\xc2\xa7o",  # italic,
    }

    def __init__(self, wrapper, name="", someid=None, internal=False):
        self.wrapper = wrapper
        self.name = name
        self.minecraft = Minecraft(wrapper)
        self.javaserver = wrapper.javaserver
        self.config = wrapper.config
        self.serverpath = self.config["General"]["server-directory"]
        self.internal = internal
        if someid is None:
            self.id = name
        else:
            self.id = someid

    def registerCommand(self, command, callback, permission=None):
        """
        This registers a command that, when executed in Minecraft, will execute callback(player, args).
        permission is an optional attribute if you want your command to only be executable if the player
        has a specified permission node.
        """
        commands = []
        if type(command) in (tuple, list):
            for i in command:
                commands.append(i)
        else:
            commands = [command]
        for name in commands:
            if not self.internal:
                self.wrapper.log.debug("[%s] Registered command '%s'", self.name, name)
            if self.id not in self.wrapper.commands:
                self.wrapper.commands[self.id] = {}
            self.wrapper.commands[self.id][name] = {"callback": callback, "permission": permission}

    def registerEvent(self, eventtype, callback):
        """
        Register an event and a callback. See [doc link needed here] for a list of events.
        callback(payload) when an event occurs, and the contents of payload varies between events.
        """
        if not self.internal:
            self.wrapper.log.debug("[%s] Registered event '%s'", self.name, eventtype)
        if self.id not in self.wrapper.events:
            self.wrapper.events[self.id] = {}
        self.wrapper.events[self.id][eventtype] = callback

    def registerPermission(self, permission=None, value=False):
        """
        Used to set a default for a specific permission node.
        Note: You do not need to run this function unless you want certain permission nodes
        to be granted by default.  i.e. `essentials.list` should be on by default, so players
        can run /list without having any permissions.
        """
        if not self.internal:
            self.wrapper.log.debug("[%s] Registered permission '%s' with default value: %s",
                                   self.name, permission, value)
        if self.id not in self.wrapper.registered_permissions:
            self.wrapper.registered_permissions[self.id] = {}
        self.wrapper.registered_permissions[self.id][permission] = value

    def registerHelp(self, groupname, summary, commands):
        """
        Used to create a help group for the /help command. groupname is the name you'll see in
        the list when you run /help, and summary is the text that you'll see next to it.
        The 'commands' argument is passed in the following format: 
        [("/i <TileName>[:Data] [Count]", "Gives the player the requested item and puts it directly
        in their inventory.", "essentials.give"), ("/")]
        """
        if not self.internal:
            self.wrapper.log.debug("[%s] Registered help group '%s' with %d commands",
                                   self.name, groupname, len(commands))
        if self.id not in self.wrapper.help:
            self.wrapper.help[self.id] = {}
        self.wrapper.help[self.id][groupname] = (summary, commands)

    def blockForEvent(self, eventtype):
        """ Blocks until the specified event is called. """
        sock = []
        self.wrapper.listeners.append(sock)
        while True:
            for event in sock:
                if event["event"] == eventtype:
                    payload = event["payload"][:]
                    self.wrapper.listeners.remove(sock)
                    return payload
                else:
                    sock.remove(event)
            time.sleep(0.05)

    def callEvent(self, event, payload):
        """
        Invokes the specific event. Payload is extra information relating to the event. Errors
        may occur if you don't specify the right payload information.
        """
        return self.wrapper.callevent(event, payload)

    def getPluginContext(self, pid):
        """
        Returns the content of another plugin with the specified ID.
        i.e. api.getPluginContext("com.benbaptist.plugins.essentials")
        """
        if pid in self.wrapper.plugins:
            return self.wrapper.plugins[pid]["main"]
        else:
            raise exceptions.NonExistentPlugin("Plugin %s does not exist!" % pid)

    def getStorage(self, name, world=False):
        """
        Return a storage object for storing configurations, player data, and any other data your
        plugin will need to remember across reboots.
        Setting world=True will store the data inside the current world folder, for world-specific data.  
        """
        if world:
            return Storage(name, root="%s/%s/plugins/%s" %
                                      (self.serverpath, self.minecraft.getWorldName(), self.id))
        else:
            return Storage(name, root="wrapper-data/plugins/%s" % self.id)
