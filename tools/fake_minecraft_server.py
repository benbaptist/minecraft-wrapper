import time
import random
import os

from uuid import UUID

names = [
    "Kevin", "Kate", "Randall", "Jack", "BabyJack", "Rebecca", "Pearson",
    "benbaptist", "Toby", "DrK", "Sophie", "Nicky", "Beth", "William"
]

class Player:
    def __init__(self):
        self.username = random.choice(names) + str(random.randrange(0, 99))
        self.uuid = UUID(bytes=os.urandom(16))

print("[11:11:11] [Server thread/INFO]: Starting minecraft server version 1.15.2\n\r")
time.sleep(.5)
print("[11:11:11] [Server thread/INFO]: Starting Minecraft server on *:25565\n\r")
time.sleep(.5)
print("[11:11:11] [Server thread/INFO]: Preparing level \"flat\"\n\r")
time.sleep(.5)
print("[11:11:11] [Server thread/INFO]: Done (17.526s)! For help, type \"help\"\n\r")

players = []

while True:
    # random events

    # make player join
    if random.randrange(0, 10) == 2:
        player = Player()
        players.append(player)
        print("[11:11:11] [User Authenticator #1/INFO]: UUID of player %s is %s" % ( player.username, player.uuid ))
        print("[11:11:11] [Server thread/INFO]: %s[127.0.0.1:12345] logged in with entity id 123 at (1, 2, 3)" % player.username)

    # make player chat
    if random.randrange(0, 10) == 2:
        pass

    # make player leave
    if random.randrange(0, 10) == 2:
        if len(players) > 0:
            player = random.choice(players)
            print("[11:11:11] [Server thread/INFO]: %s lost connection: Disconnected" % player.username)
            players.remove(player)

    time.sleep(.5)
