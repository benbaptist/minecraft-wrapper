import logging
import traceback
import os
import time

class LogManager:
	def __init__(self):
		if not os.path.exists("logs"):
			os.mkdir("logs")

		self.start_date = time.strftime("%Y-%m-%d")
		self.formatter = logging.Formatter(fmt="%(asctime)s [Wrapper/%(name)s/%(levelname)s] %(message)s", datefmt='[%Y-%m-%d %H:%M:%S]')

		self.ch = logging.StreamHandler()
		self.ch.setLevel(logging.DEBUG)
		self.ch.setFormatter(self.formatter)

		self.fh = logging.FileHandler("logs/%s.log" % self.start_date, "a")
		self.fh.setLevel(logging.INFO)
		self.fh.setFormatter(self.formatter)

		self.log = self.get_logger(__name__)
	def get_logger(self, name):
		logger = logging.getLogger(name)
		logger.addHandler(self.ch)
		logger.addHandler(self.fh)
		logger.setLevel(logging.DEBUG)

		logger = Logger(logger)

		return logger

class Logger:
	def __init__(self, logger):
		self.logger = logger
		self.debug = logger.debug
		self.info = logger.info
		self.warning  = logger.warning
		self.error = logger.error
	def traceback(self, msg):
		self.error(msg)
		for line in traceback.format_exc().split("\n"):
			self.error(line.replace("\r", ""))
