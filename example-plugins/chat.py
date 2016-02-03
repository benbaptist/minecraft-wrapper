NAME = "chat"
AUTHOR = "SurestTexas00"
ID = "com.suresttexas00.plugins.global"
VERSION = (0, 1)
SUMMARY = "Chat handler."
WEBSITE = ""
DISABLED = False
DEPENDENCIES = False
DESCRIPTION = """ simple chat modifier to add rank prefixes and suffixes, and let players create
colored/styled chat.
"""


class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log

	def onEnable(self):
		self.api.registerEvent("player.chatbox", self.playerChatBox)

	def onDisable(self):
		pass

	def playerChatBox(self, payload):
		""" with some wrapper upgrades to this event, we can now modify the chat.
		"""

		player = (payload["player"])
		data = payload["json"]

		if "translate" in data:  # special type of chat
			typechat = str(data["translate"])
		else:
			typechat = "None"  # regular chat or broadcast

		# CHAT MODIFICATIONS SECTION
		if typechat == "chat.type.text":
			esc_code = u'\xa7'
			# we now know the expected format
			chatmessagetext = (data["with"][1]).encode('utf-8')
			modifywith = data["with"][0]

			if player.hasPermission("google.translate"):  # give player a google translate link
				translationtext = chatmessagetext.replace(" ", "%20")
				data["with"][1] = translationtext
				modifywith["hoverEvent"]["action"] = "show_text"
				modifywith["hoverEvent"]["value"] = "Translate this at Google translate..."
				modifywith["clickEvent"]["action"] = "open_url"
				modifywith["clickEvent"]["value"] = "https://translate.google.com/#auto/en/%s" % translationtext

			insertionplayername = modifywith["insertion"]
			chatdisplayname = modifywith["text"]

			# chatdisplayname[0]
			insertionplayer = self.api.minecraft.getPlayer(insertionplayername)
			if insertionplayer.isOp():
				modifywith["text"] = "%s %s7[OP]%sr" % (chatdisplayname, esc_code, esc_code)
				chatdisplayname = modifywith["text"]  # permanently tag OP suffix
			if insertionplayer.hasGroup("member"):
				modifywith["text"] = "%s7[Member]%sr %s" % (esc_code, esc_code, chatdisplayname)
			if insertionplayer.hasGroup("trusted"):
				modifywith["text"] = "%s8[Trusted]%sr %s" % (esc_code, esc_code, chatdisplayname)
			if insertionplayer.hasGroup("helper"):
				modifywith["text"] = "%se[Helper]%sr %s" % (esc_code, esc_code, chatdisplayname)
			if insertionplayer.hasGroup("jrmod"):
				modifywith["text"] = "%se[JrMod]%sr %s" % (esc_code, esc_code, chatdisplayname)
			if insertionplayer.hasGroup("mod"):
				modifywith["text"] = "%sb[Mod]%sr %s" % (esc_code, esc_code, chatdisplayname)
			if insertionplayer.hasGroup("admin"):
				modifywith["text"] = "%s5[Admin]%sr %s" % (esc_code, esc_code, chatdisplayname)
			if insertionplayer.hasGroup("OPS"):
				modifywith["text"] = "%s4[Operator]%sr %s" % (esc_code, esc_code, chatdisplayname)
			if insertionplayer.hasGroup("Owner"):
				modifywith["text"] = "%s4Owner%sr %s" % (esc_code, esc_code, chatdisplayname)

			# player formatting
			playertext = unicode(chatmessagetext, "utf-8")
			newtext = playertext.replace("&", esc_code)

			# return any changes
			data["with"][1] = newtext
			data["with"][0] = modifywith
			return data
		return
