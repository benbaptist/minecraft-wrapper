import traceback, ConfigParser, ast, time, os, sys
# I'm going to redo the configuration code soon! Don't you worry!
# Default Configuration File
DEFAULT_CONFIG = """[General]
server-name = Minecraft Server
command = java -jar minecraft_server.1.8.jar nogui
auto-restart = True
auto-update-wrapper = False
auto-update-dev-builds = False
pre-1.7-mode = False
timed-reboot = False
timed-reboot-seconds = 86400
timed-reboot-warning-minutes = 5 
debug = False 
shell-scripts = False

[Backups]
;; Automatic backups with automatic backup pruning. Interval is in seconds. ;; 
enabled = False
backup-folders = ['server.properties', 'world']
backup-interval = 3600
backup-notification = True
backup-location = backup-directory
backup-compression = False
backups-keep = 10

[IRC]
;; This allows your users to communicate to and from the server via IRC and vise versa. ;;
enabled = False
server = benbaptist.com
port = 6667
nick = MinecraftWrap
channels = ['#wrapper']
command-character = .
show-channel-server = True
autorun-irc-commands = ['COMMAND 1', 'COMMAND 2']
obstruct-nicknames = False
control-from-irc = False
control-irc-pass = password

[Proxy]
;; This is a man-in-the-middle proxy mode similar to BungeeCord, but allows for extra plugin functionality. ;;
;; The server must be on offline mode. Make sure that the server is inaccessible directly from the outside world. ;;
;; Note: the online-mode option here refers to the proxy only, not to the server's offline mode. ;;
proxy-enabled = False
proxy-port = 25565
proxy-bind = 0.0.0.0
server-port = 25564
online-mode = True
max-players = 1024

[Web]
;; This is a web UI. ;;
web-enabled = False
web-bind = 0.0.0.0
web-port = 8070
web-password = password
web-allow-file-management = True
public-stats = True
"""

class Config:
	version = "0.7.6"
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
#		open("wrapper.properties", "a").close()
		self.parser = ConfigParser.ConfigParser(allow_no_value = True)
		self.parser.readfp(open("wrapper.properties"))

		sections = ["General", "Backups", "IRC", "Proxy", "Web"]
		defaults = {"General":{
			"server-name": "Minecraft Server",
			"command": "java -jar minecraft_server.1.8.jar",
			"auto-restart": True,
			"auto-update-wrapper": False,
			"auto-update-dev-build": False,
			"debug": False,
			"pre-1.7-mode": False,
			"timed-reboot": False,
			"timed-reboot-seconds": 86400,
			"timed-reboot-warning-minutes": 5,
			"shell-scripts": False
		},		
		"IRC":{ 
			"enabled": True, 
			"nick": "MinecraftWrap", 
			"server": "benbaptist.com", 
			"port": 6667, 
			"channels": ["#wrapper"], 
			"command-character": ".",
			"obstruct-nicknames": False,
			"autorun-irc-commands": ['COMMAND 1', 'COMMAND 2'],
			"show-channel-server": True,
			"control-from-irc": False,
			"control-irc-pass": "password"
		},
		"Backups":{ 
			"enabled": True,
			"backups-keep": 10,
			"backup-location": "backup-directory",
			"backup-folders": ['server.properties', 'world'],
			"backup-interval": 3600,
			"backup-notification": True,
			"backup-compression": False
		},
		"Proxy":{
			"proxy-enabled": False,
			"server-port": 25564,
			"proxy-port": 25565,
			"proxy-bind": "0.0.0.0",
			"online-mode": True,
			"max-players": 1024
		},
		"Web":{
			"web-enabled": False,
			"web-bind": "0.0.0.0",
			"web-port": 8070,
			"web-password": "password",
			"web-allow-file-management": False,
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
			self.log.info("Updated wrapper.properties file - check and edit configuration if needed and start again.")
			sys.exit()
	def save(self):
		self.parser.write(open("wrapper.properties", "wb"))
