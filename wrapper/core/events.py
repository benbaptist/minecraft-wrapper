# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import threading
import time

from api.player import Player


class Events(object):

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.listeners = []
        self.events = {}

        self.event_queue = []
        t = threading.Thread(target=self._event_processor,
                             name="event_processor", args=())
        t.daemon = True
        t.start()

    def __getitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        return self.events[index]

    def __setitem__(self, index, value):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        self.events[index] = value
        return self.events[index]

    def __delitem__(self, index):
        if not type(index) == str:
            raise Exception("A string must be passed - got %s" % type(index))
        del self.events[index]

    def __iter__(self):
        for i in self.events:
            yield i

    def callevent(self, event, payload, abortable=True):
        """
        This needs some standardization
        :param event: String name event

        :param payload:  Should have at least these items.
            :playername: Optional string playername
            :player: Player Object - Optional, unless playername is provided

        :param abortable: Callevent must wait for plugins to complete.

        :return:

        """

        if event == "player.runCommand":
            abortable = False

        # Event processor thread

        if abortable:
            return self._callevent(event, payload)
        else:
            self.event_queue.append((event, payload))
            return

    def _event_processor(self):
        while not self.wrapper.halt.halt:
            while len(self.event_queue) > 0:
                _event, _payload = self.event_queue.pop(0)
                self._callevent(_event, _payload)
            time.sleep(0.1)

    def _callevent(self, event, payload):
        if event == "player.runCommand":
            self.wrapper.commands.playercommand(payload)
            return

        # create reference player object for payload, if needed.
        if payload and ("playername" in payload) and ("player" not in payload):

            for client in self.wrapper.servervitals.clients:
                if client.username == payload["playername"]:
                    if client.username not in self.wrapper.servervitals.players:
                        self.wrapper.servervitals.players[
                            client.username] = Player(client.username,
                                                      self.wrapper)
            payload["player"] = self.wrapper.api.minecraft.getPlayer(
                payload["playername"])

        # listeners is normally empty.
        # Supposed to be part of the blockForEvent code.
        for sock in self.listeners:
            sock.append({"event": event, "payload": payload})

        payload_status = None
        # old_payload = payload  # retaining the original payload might be helpful for the future features.  # noqa

        # in all plugins with this event listed..
        for plugin_id in self.events:

            # for each plugin...
            if event in self.events[plugin_id]:

                # run the plugin code and get the plugin's return value
                result = None
                try:
                    # 'self.events[plugin_id][event]' is the
                    # <bound method Main.plugin_event_function>
                    # pass 'payload' as the argument for the plugin-defined
                    # event code function
                    result = self.events[plugin_id][event](payload)
                except Exception as e:
                    self.log.exception(
                        "Plugin '%s' \n"
                        "experienced an exception calling '%s': \n%s",
                        plugin_id, event, e
                    )

                # Evaluate this plugin's result
                # Every plugin will be given equal time to run it's event code.
                # However, if one plugin returns a False, no payload changes
                #  will be possible.
                #
                if result is False or payload_status is False:
                    # mark this event permanently as False
                    payload_status = False

                else:
                    # A payload is being returned
                    # If any plugin rejects the event, no payload changes
                    #  will be authorized.

                    # once the payload is modded, payload status must stay True
                    if result in (None, True) and payload_status is not True:
                        payload_status = None
                    # the next plugin looking at this event sees the
                    #  new payload.
                    else:
                        if type(result) == dict:
                            payload = result
                            payload_status = True
                        else:
                            # non dictionary payloads are deprecated and will
                            # be overridden by dict payloads
                            # Dict payloads are those that return the
                            # payload in the same format as it was passed.
                            self.log.warning("Non-Dict payload %s %s %s",
                                             payload_status,
                                             result,
                                             type(result)
                                             )
                            payload = result
                            payload_status = True

        # payload changed
        if payload_status is True:
            return payload
        # payload did not change
        elif payload_status is None:
            return True
        # payload rejected
        else:
            return False
