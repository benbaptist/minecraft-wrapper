AUTHOR = "PurePi"
VERSION = (0, 1, 0)
SUMMARY = "Minecraft-to-Discord and Discord-to-Minecraft chat relay"
DESCRIPTION = """ This plugin sends all players' messages to a Discord server
and broadcasts messages from the Discord server to the Minecraft server
"""

DISABLED = False

import discord

class Main:
    def __init__(self, api, log):
        self.api = api
        self.log = log

    def onEnable(self):
        self.client = discord.Client()
        self.server = discord.Server(kwargs={"id": "serverID"})

        self.sendChannel = discord.Channel(kwargs={"name": "channelName",
                                                   "server": self.server,
                                                   "id": "channelID"})

        self.api.registerEvent("player.message", self.playerMessage)

        @self.client.event
        async def on_message(self, message):
            self.api.minecraft.broadcast(message)

        self.client.start("token")

    def onDisable(self):
        self.client.logout()
        pass

    def playerMessage(self, payload):
        player = payload["player"]
        playerName = str(player.username)

        @self.client.event
        async def discMessage():
            await self.client.edit_profile(fields = {"username": playerName})
            await self.client.send_message(self.sendChannel, payload["message"])

        discMessage()
