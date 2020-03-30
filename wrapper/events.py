class Events:

    def __init__(self):
        self.listeners = []

    def call(self, event, *args, **kwargs):
        for listener in self.listeners:
            if listener.event == event:
                listener.callback(*args, **kwargs)

    def _hook(self, event, callback):
        listener = Listener(event, callback)
        self.listeners.append(listener)

    def hook(self, event):
        def wrap(func):
            self._hook(event, func)

        return wrap

class Listener:
    def __init__(self, event, callback):
        self.event = event
        self.callback = callback
