# -*- coding: utf-8 -*-
import socket, datetime, time, sys, threading, random, subprocess, os, json, signal, traceback, ConfigParser, ast
from log import Log
from config import Config
from irc import IRC
from server import Server
			
class Wrapper:
	def __init__(self):
		self.log = Log()
		self.halt = False
		self.configManager = Config(self.log)
	def start(self):
		self.configManager.loadConfig()
		self.config = self.configManager.config
		signal.signal(signal.SIGINT, self.SIGINT)
		
		self.server = Server(sys.argv, self.log, self.configManager.config, self)
		
		if self.config["IRC"]["enabled"]:
			self.irc = IRC(self.server, self.config, self.log, self, self.config["IRC"]["server"], self.config["IRC"]["port"], self.config["IRC"]["nick"], self.config["IRC"]["channels"])
			t = threading.Thread(target=self.irc.init, args=())
			t.daemon = True
			t.start()
		
		if len(sys.argv) < 2:
			wrapper.server.serverArgs = wrapper.configManager.config["General"]["command"].split(" ")
		else:
			wrapper.server.serverArgs = sys.argv[1:]
		
		captureThread = threading.Thread(target=self.server.capture, args=())
		captureThread.daemon = True
		captureThread.start()
		consoleDaemon = threading.Thread(target=self.console, args=())
		consoleDaemon.daemon = True
		consoleDaemon.start()
		
		self.server.startServer()
	def SIGINT(self, s, f):
		self.shutdown()
	def shutdown(self):
		self.halt = True
		sys.exit(0)
	def console(self):
		while not self.halt:
			input = raw_input("")
			if len(input) < 1: continue
			if input[0] is not "/": 
				try:
					self.server.run(input)
				except:
					break
				continue
			def args(i): 
				try: return input[1:].split(" ")[i];
				except:pass;
			command = args(0)
			if command == "halt":
				self.server.run("stop")
				self.halt = True
				sys.exit()
			elif command == "stop":
				self.server.run("stop")
				self.server.start = False
			elif command == "start":
				self.server.start = True
			elif command == "restart":
				self.server.run("stop")
			elif command == "help":
				self.log.info("/start & /stop - start and stop the server without auto-restarting respectively without shutting down Wrapper.py")
				self.log.info("/restart - same as just typing 'stop' (without a slash)")				
				self.log.info("/halt - shutdown Wrapper.py completely")
				self.log.info("Wrapper.py version %s" % Config.version)
			else:
				self.log.error("Invalid command %s" % command)
if __name__ == "__main__":
	wrapper = Wrapper()
	log = wrapper.log
	log.info("Wrapper.py started - version %s" % Config.version)
	try:
		t = threading.Thread(target=wrapper.start(), args=())
		t.daemon = True
		t.start()
	except SystemExit:
		#log.error("Wrapper.py received SystemExit")
		wrapper.halt = True
		try:
			for player in wrapper.server.players:
				wrapper.server.run("kick %s Wrapper.py received shutdown signal - bye" % player)
			time.sleep(0.2)
			wrapper.server.run("save-all")
			wrapper.server.run("stop")
		except:
			pass
	except:
		log.error("Wrapper.py crashed - stopping sever to be safe")
		for line in traceback.format_exc().split("\n"):
			log.error(line)
		wrapper.halt = True
		try:
			for player in wrapper.server.players:
				wrapper.server.run("kick %s Wrapper.py crashed - please contact a server admin instantly" % player)
			wrapper.server.run("save-all")
			wrapper.server.run("stop")
		except:
			pass
