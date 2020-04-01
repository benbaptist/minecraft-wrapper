import time
import random
import os
import sys
import threading

from uuid import UUID

# Simulate a Minecraft server's console output. Useful for debugging
# wrapper.py's console output without running a bulky Java server.
# Must use Python 3.x.

# Also, 'This Is Us'. You know what I mean. ;)

names = [
    "Kevin", "Kate", "Randall", "Jack", "BabyJack", "Rebecca", "Pearson",
    "benbaptist", "Toby", "DrK", "Sophie", "Nicky", "Beth", "William"
]

messages = [
    "I need a torch",
    "get the wood from the tree",
    "no man, get the wood from the chest",
    "ok fine",
    "I made a torch",
    "Use the force",
    "Eat a potato",
    "Crash at my place?",
    "Need diamonds",
    "dude man",
    "yo do you have any cows",
    "lol that man"
]

class Player:
    def __init__(self):
        self.username = random.choice(names) + str(random.randrange(0, 99))
        self.uuid = UUID(bytes=os.urandom(16))

def fancy_print(msg, thread="Server thread", level="INFO", time="11:12:13"):
    print("[%s] [%s/%s]: %s" % (time, thread, level, msg), file=sys.stdout)

# global ABORT
ABORT = False

def read_console():
    global ABORT
    while not ABORT:
        blob = input("> ")

        if blob == "stop":
            ABORT = True
            fancy_print("Shutting down?")
            time.sleep(1)
            break

t = threading.Thread(target=read_console, args=())
t.daemon = True
t.start()

fancy_print("Starting minecraft server version 1.15.2")
# time.sleep(.5)
fancy_print("Starting Minecraft server on *:25565")
time.sleep(.5)
fancy_print("Preparing level \"flat\"")
time.sleep(.5)
fancy_print("Done (17.526s)! For help, type \"help\"")

players = []

while not ABORT:
    # random events

    # make player join
    if random.randrange(0, 10) == 2:
        player = Player()
        players.append(player)
        fancy_print(
            "UUID of player %s is %s"
            % ( player.username, player.uuid ),
            thread="User Authenticator #1"
        )
        fancy_print("%s[/127.0.0.1:12345] logged in with entity id 123 at (1, 2, 3)" % player.username)

    # make player chat
    if random.randrange(0, 4) == 2:
        if len(players) > 0:
            player = random.choice(players)
            message = random.choice(messages)
            fancy_print("<%s> %s" % (player.username, message))

    # make player leave
    if random.randrange(0, 10) == 2:
        if len(players) > 0:
            player = random.choice(players)
            fancy_print("%s lost connection: Disconnected" % player.username)
            players.remove(player)

    time.sleep(.5)
