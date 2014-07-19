import traceback, ConfigParser, ast, time, os, sys
# configuration
DEFAULT_CONFIG = """[General]
command = java -jar minecraft_server.1.7.9.jar nogui
auto-restart = True
debug = False

[Backups]
enabled = False
backup-folders = ['server.properties', 'world', 'white-list.txt']
backup-interval = 3600
backup-notification = True
backup-location = backup-directory
backups-keep = 10

[IRC]
enabled = False
server = benbaptist.com
port = 6667
nick = MinecraftServ
channels = ['#main']
command-character = !
show-channel-server = True
autorun-irc-commands = ['COMMAND 1', 'COMMAND 2']
control-from-irc = True
obstruct-nicknames = False
control-irc-pass = password
forward-commands-to-irc = False

[Death]
kick-on-death = False
users-to-kick = ['username1', 'username2', 'remove these usernames to kick ALL users upon death']
death-kick-messages = ['You died!']

[Proxy]
enabled = False
server-port = 25564
proxy-port = 25565
bind = 0.0.0.0
motd = Minecraft Server
online-mode = True
"""

"""[Web]
enabled = False
bind = 0.0.0.0
port = 8070
password = blahblah98
public-stats = True"""

class Config:
	version = "0.7"
	debug = False
	def __init__(self, log):
		self.log = log
		self.config = {}
		self.exit = False
	def loadConfig(self):
		if not os.path.exists("wrapper.properties"): # creates new wrapper.properties. The reason I do this is so the ordering isn't random and is a bit prettier
			f = open("wrapper.properties", "w")
			f.write(DEFAULT_CONFIG)
			f.close()
			self.exit = True
		open("wrapper.properties", "a").close()
		self.parser = ConfigParser.ConfigParser()
		self.parser.readfp(open("wrapper.properties"))

		sections = ["General", "Backups", "IRC", "Death", "Proxy", "Web"]
		defaults = {"General":{
			"command": "java -jar minecraft_server.1.7.7.jar",
			"auto-restart": True,
			"debug": False
		},		
		"IRC":{ 
			"enabled": True, 
			"nick": "MinecraftIRC", 
			"server": "benbaptist.com", 
			"port": 6667, 
			"channels": ["#main"], 
			"command-character": "!",
			"obstruct-nicknames": False,
			"autorun-irc-commands": ['COMMAND 1', 'COMMAND 2'],
			"show-channel-server": True,
			"forward-commands-to-irc": False,
			"control-from-irc": False,
			"control-irc-pass": "password"
		},
		"Backups":{ 
			"enabled": True,
			"backups-keep": 10,
			"backup-location": "backup-directory",
			"backup-folders": ['server.properties', 'world'],
			"backup-interval": 3600,
			"backup-notification": True
		},
		"Death":{
			"kick-on-death": False,
			"death-kick-messages": ["You died!"],
			"users-to-kick": ["username1", "username2", "remove these usernames to kick ALL users upon death"]
		},
		"Proxy":{
			"proxy-enabled": False,
			"server-port": 25564,
			"proxy-port": 25565,
			"proxy-bind": "0.0.0.0",
			"motd": "Minecraft Server",
			"online-mode": True
		},
		"Web":{
			"web-enabled": False,
			"web-bind": "0.0.0.0",
			"web-port": 8070,
			"web-password": "usefulpass",
			"public-stats": True
		}}

		
		for section in sections:
			try:
				keys = self.parser.items(section)
				self.config[section] = {}
				for key in keys:
					try:
						self.config[section][key[0]] = ast.literal_eval(key[1])
					except:
						self.config[section][key[0]] = key[1]
			except:
				traceback.print_exc()
				self.parser.add_section(section)
				self.log.debug("Adding section [%s] to configuration" % section)
				self.config[section] = {}
				self.exit = True
		
		for section in defaults:
			for item in defaults[section]:
				if item not in self.config[section]:
					self.config[section][item] = defaults[section][item]
					self.parser.set(section, item, defaults[section][item])
					self.log.debug("Key %s in section %s not in wrapper.properties - adding" % (item, section))
					self.exit = True
				else:
					for key in keys:
						try:
							self.config[section][key[0]] = ast.literal_eval(key[1])
						except:
							self.config[section][key[0]] = key[1]
		self.save()
		Config.debug = self.config["General"]["debug"]
		if self.exit:
			self.log.info("Updated wrapper.properties with new entries - edit configuration if needed and start again")
			sys.exit()
	def save(self):
		self.parser.write(open("wrapper.properties", "wb"))