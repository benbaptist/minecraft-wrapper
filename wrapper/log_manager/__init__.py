import logging
import traceback
import os
import time
import gzip

LOG_PATH = "logs/wrapper"

class LogManager:
	def __init__(self):
		# Make sure the log directory exists
		if not os.path.exists(LOG_PATH):
			os.makedirs(LOG_PATH)

		# Default to logging level INFO
		self.level = logging.INFO

		self.formatter = logging.Formatter(fmt="%(asctime)s [Wrapper/%(name)s/%(levelname)s] %(message)s", datefmt='[%Y-%m-%d %H:%M:%S]')

		self.ch = logging.StreamHandler()
		self.ch.setLevel(logging.DEBUG)
		self.ch.setFormatter(self.formatter)

		self.fh = None
		self.grab_log_file()
		self.log = self.get_logger(__name__)

		# GZIP Compress old logs
		for log in os.listdir(LOG_PATH):
			try:
				name, ext = log.rsplit(".", 1)
			except:
				continue

			if name == time.strftime("%Y-%m-%d"):
				continue

			log_path = os.path.join(LOG_PATH, log)
			log_compressed_path = os.path.join(LOG_PATH, log + ".gz")

			if ext == "log":
				# File was already compressed before, ignore
				if os.path.exists(log_compressed_path):
					continue

				# Compress log file
				self.log.info("Compressing %s" % log)
				with gzip.open(log_compressed_path, "wb") as cf, \
					open(log_path, "r") as uf:
					cf.write(uf.read())

	def grab_log_file(self):
		if self.fh:
			self.fh.close()

		self.start_date = time.strftime("%Y-%m-%d")

		self.fh = logging.FileHandler("logs/wrapper/%s.log" % self.start_date, "a")
		self.fh.setLevel(logging.DEBUG)
		self.fh.setFormatter(self.formatter)

	def get_logger(self, name):
		logger = logging.getLogger(name)
		logger.addHandler(self.ch)
		logger.addHandler(self.fh)
		logger.setLevel(logging.DEBUG)

		logger = Logger(self, logger)

		return logger

class Logger:
	def __init__(self, main, logger):
		self.main = main
		self.logger = logger

	def _check_rotate(self):
		if time.strftime("%Y-%m-%d") != self.main.start_date:
			self.main.grab_log_file()

	def debug(self, msg):
		self._check_rotate()
		if self.main.level <= logging.DEBUG:
			self.logger.debug(msg)

	def info(self, msg):
		self._check_rotate()
		if self.main.level <= logging.INFO:
			self.logger.info(msg)

	def warning(self, msg):
		self._check_rotate()
		if self.main.level <= logging.WARNING:
			self.logger.warning(msg)

	def error(self, msg):
		self._check_rotate()
		if self.main.level <= logging.ERROR:
			self.logger.error(msg)

	def traceback(self, msg):
		self._check_rotate()
		self.error(msg)
		for line in traceback.format_exc().split("\n"):
			self.error(line.replace("\r", ""))
