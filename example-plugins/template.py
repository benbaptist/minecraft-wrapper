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

# The following are optional and affect the plugin import process (for versions after builds circa 107-110).
# Either do not include them or set them to = False if not used:
DISABLED = True  # disables this plugin (for instance, if this *.py file is really only a module for another file/plugin)
DEPENDENCIES = ["example.py", "vault.py", "economy.py", etc]  # even if there is only 1 dependency, it must be a 'list' type (enclosed in '[]').

class Main:
	def __init__(self, api, log):
		self.api = api
		self.log = log
		
	def onEnable(self):  # onEnable and onDisable are required methods
		# sample Storage
		self.data = self.api.getStorage("data", True)
		
		# Sample register command
		self.api.registerCommand("/some_command", self._a_command, "permission.node")
		
		# Sample register help
		self.api.registerHelp("Topic", "description of Topic plugin", [
                        ("/topic1 <argument>", "how to use topic1", "permission.node"),
                        ("/topic2 <arg1> <arg2>", "talk about topic2", "another.permission"),
                        ("/topic3", "...", "another.permission")
                ])
		
		
	def onDisable(self):  # onEnable and onDisable are required methods
		self.data.save()  # save Storage to disk
