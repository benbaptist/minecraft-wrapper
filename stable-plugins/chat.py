# coding=utf-8

import copy
import sys

PY3 = sys.version_info[0] > 2

NAME = "chat"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.chat"
VERSION = (1, 0)
SUMMARY = "A chat handler that adds ranks."
WEBSITE = ""
DISABLED = False
if not PY3:
    DISABLED = True
DEPENDENCIES = False
DESCRIPTION = """ A simple chat modifier to add rank prefixes and suffixes, 
and let players create colored/styled chat.
"""

SECT = u'\xa7'


# noinspection PyPep8Naming,PyMethodMayBeStatic,PyUnusedLocal
# noinspection PyClassicStyleClass,PyAttributeOutsideInit
class Main:
    def __init__(self, api, log):

        self.api = api
        self.log = log

    def onEnable(self):
        self.api.registerEvent("player.chatbox", self.playerChatBox)
        self.api.registerEvent("player.logout", self.logout)

        self.player_ranks = {}
        self.default = {
            "trans": False,
            "isOp": False,
            "rank": None,
            "color": "f"  # white
        }
        self.ranks = [  # from highest to lowest
            # perm               display rank       display color
            {"perm": "owner", "rank": "Owner", "color": "4"},
            {"perm": "operator", "rank": "Operator", "color": "4"},
            {"perm": "admin", "rank": "Admin", "color": "5"},
            {"perm": "mod", "rank": "Mod", "color": "b"},
            {"perm": "jrmod", "rank": "JrMod", "color": "e"},
            {"perm": "helper", "rank": "Helper", "color": "e"},
            {"perm": "trusted", "rank": "Trusted", "color": "8"},
            {"perm": "member", "rank": "Member", "color": "7"},
        ]

    def onDisable(self):
        pass

    def verify(self, player):
        """ Obtain the player's rank """
        if player.uuid not in self.player_ranks:
            uuid = player.uuid
            self.player_ranks[uuid] = copy.copy(self.default)
            if player.isOp():
                self.player_ranks[uuid]["isOp"] = True

            if player.hasPermission("google.translate"):
                self.player_ranks[uuid]["trans"] = True
            for ranks in self.ranks:
                if player.hasGroup(ranks["perm"]):
                    self.player_ranks[uuid]["rank"] = ranks["rank"]
                    self.player_ranks[uuid]["color"] = ranks["color"]
                    return

    def logout(self, payload):
        """ Clear player rank so when he logs in, it gets refreshed. """
        player = payload["player"]
        uuid = player.uuid
        if uuid in self.player_ranks:
            del self.player_ranks[uuid]

    # noinspection PyCompatibility

    def playerChatBox(self, payload):
        """ We can modify the chat.

        All the permissions legwork that could slow up the code
        is done just once when player chat is first used..
        we have to keep this packet moving to prevent lag!

        {'translate': 'chat.type.text',
         'with': [__[0]__{'clickEvent': {'action': 'suggest_command',
                                  'value': '/msg SurestTexas00 '},
                          'hoverEvent': {'action': 'show_entity',
                                  'value': {'text': '{name:"SurestTexas00",id:"3269fd15-5be9-3c2a-af6c-12147a760f78"}'}},  # noqa
                          'insertion': 'SurestTexas00',
                          'text': 'SurestTexas00'},

                  __[1]__'hello']}


        """

        player = payload["player"]
        data = payload["json"]
        self.verify(player)

        if "translate" in data:  # special type of chat

            # CHAT MODIFICATIONS SECTION
            if data["translate"] == "chat.type.text":
                # we now know the expected format
                chatmessagetext = data["with"][1]
                if self.player_ranks[player.uuid]["trans"]:
                    # give player a google translate link
                    translationtext = chatmessagetext.replace(" ", "%20")
                    data["with"][1] = translationtext
                    data["with"][0]["hoverEvent"]["action"] = "show_text"
                    data["with"][0]["hoverEvent"]["value"] = "Translate this at Google translate..."  # noqa
                    data["with"][0]["clickEvent"]["action"] = "open_url"
                    data["with"][0]["clickEvent"]["value"] = "https://translate.google.com/#auto/en/%s" % translationtext  # noqa

                insertionplayername = data["with"][0]["insertion"]
                chatdisplayname = data["with"][0]["text"]

                # chatdisplayname[0]
                insertionplayer = self.api.minecraft.getPlayer(insertionplayername)  # noqa
                self.verify(insertionplayer)
                # permanently tag OP suffix
                if self.player_ranks[insertionplayer.uuid]["isOp"]:
                    data["with"][0]["text"] = "%s §8[OP]§r" % chatdisplayname
                    chatdisplayname = data["with"][0]["text"]

                if self.player_ranks[insertionplayer.uuid]["rank"]:
                    data["with"][0]["text"] = "§%s[%s]§r %s" % (
                        self.player_ranks[insertionplayer.uuid]["color"],
                        self.player_ranks[insertionplayer.uuid]["rank"],
                        chatdisplayname
                    )

                # allow color codes in chat
                if "&" in list(chatmessagetext):
                    newtext = self.api.helpers.processcolorcodes(
                        chatmessagetext
                    )
                    data["with"][1] = newtext

                # return any changes
                return data
        return
