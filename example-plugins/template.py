NAME = "Template Plugin" # the visible name of the plugin, seen in /plugins and whatnot
AUTHOR = "Ben Baptist" # the creator/developer of the plugin
ID = "com.benbaptist.plugins.template" # the ID of the plugin, used for identifying the plugin for storage objects and more
VERSION = (1, 2) # the version number, with commas in place of periods. add more commas if needed
SUMMARY = "This plugin does nothing at all! :D" # a quick, short summary of the plugin seen in /plugins
WEBSITE = "http://wrapper.benbaptist.com/" # the developer or plugin's website
DESCRIPTION = """This is a longer, more in-depth description about the plugin.
While summaries are for quick descriptions of the plugin, the DESCRIPTION field will be used for a more in-depth explanation.

Descriptions will be used in some parts of Wrapper.py, such as when you 
hover over a plugin name when you run /plugins, or in the web interface. """
class Main:
	def __init__(self, api, log):
		self.api = api
		self.minecraft = api.minecraft
		self.log = log
	def onEnable(self):
		pass
	def onDisable(self):
		pass