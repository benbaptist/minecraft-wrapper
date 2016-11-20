# -*- coding: utf-8 -*-


class Events:

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.log = wrapper.log
        self.listeners = []
        self.events = {}
        self.debugprint = 1

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

    def callevent(self, event, payload):
        self.debugprint += 1
        if 1 < self.debugprint < 4:
            # print("listeners: \n%s\n" % self.listeners)
            print("events: \n%s\n" % self.events)
        if event == "player.runCommand":
            if not self.wrapper.commands.playercommand(payload):
                return False

        # listeners is normally empty.  Supposed to be part of the blockForEvent code.
        for sock in self.listeners:
            sock.append({"event": event, "payload": payload})
        try:
            for pluginID in self.events:
                if event in self.events[pluginID]:
                    try:
                        result = self.events[pluginID][event](payload)
                        if result is None:
                            continue
                        if result is not True:
                            return result
                    except Exception as e:
                        self.log.exception("Plugin '%s' errored out when executing callback event '%s': \n%s",
                                           pluginID, event, e)
        except Exception as ex:
            pass
            self.log.exception("A serious runtime error occurred - if you notice any strange behaviour, please "
                               "restart immediately: \n%s", ex)
        return True
