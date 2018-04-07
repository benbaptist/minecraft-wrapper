AUTHOR = "PurePi"
VERSION = (0, 1, 0)
NAME = "Discord Relay"
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
        self.server = discord.Server(id = "serverID")
        self.sendChannel = discord.Channel(name = "channelName", server = self.server, id = "channelID")

        self.api.registerEvent("player.message", self.playerMessage)
        self.api.registerEvent("player.login", self.login)
        
        self.discord_storage = self.api.getStorage("discord")
        self.player_data = self.discord_storage.Data

        self.api.registerCommand("discord", self._toggle, None)
        self.api.registerHelp("DiscordRelay","sends and receives messages from Discord",
                              [("/discord toggle",
                                "toggles whether you want to communicate with the Discord server",
                                None)])

        @self.client.event
        async def on_message(message):
            for p in self.api.minecraft.getPlayers():
                if self.player_data[p.uuid] == True:
                    p.message(message)

        self.client.start("token")

    def onDisable(self):
        self.client.logout()
        self.discord_storage.close()
        pass

    def playerMessage(self, payload):
        player = payload["player"]
        playerName = str(player.username)

        @self.client.event
        async def discMessage():
            if self.player_data[player.uuid] == True:
                await self.client.edit_profile(username = playerName)
                self.client.send_message(self.sendChannel, payload["message"])

        discMessage()

    def login(self, payload):
        if payload["player"].uuid not in self.player_data:
            self.player_data[payload["player"].uuid] = True
        pass

    def _toggle(self, player, args):
        if args[0] == "toggle":
            if self.player_data[player.uuid] == True:
                self.player_data[player.uuid] = False
                player.message("Disabled message relay with Discord.")
            else:
                self.player_data[player.uuid] = True
                player.message("Enabled message relay with Discord.")
        else:
            player.message("Wrong argument: type 'toggle'")
        
