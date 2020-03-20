import msgpack
import os
import threading
import time
import copy
import traceback
import shutil

# This version of Storify has been updated to
# remove JSON completely and add Python 3.x support.

class DummyLogger:
	def info(self): pass
	def debug(self): pass
	def error(self): pass
	def warning(self): pass
	def traceback(self): pass

class Storify:
	def __init__(self, root="data", log=DummyLogger()):
		self.root = root
		self.databases = []

		self.log = log

		if not os.path.exists(self.root):
			os.mkdir(self.root)

		if not os.path.exists(os.path.join(self.root, ".backups")):
			os.mkdir(os.path.join(self.root, ".backups"))
	def getDB(self, name):
		db = Database(name, self.root, self.log)
		self.databases.append(db)
		return db
	def tick(self, force=False):
		a = len(self.databases)
		i = 0
		while i < a:
			# Safely iterate through databases without any RuntimeErrors
			db = self.databases[i]

			if force:
				db.flush()
			else:
				if time.time() - db.lastFlush > 60 * 2: # Saves every two minutes
					db.flush()

			i += 1
	def flush(self):
		self.tick(force=True)

class Database:
	def __init__(self, name, root, log):
		self.name = name
		self.root = root
		self.lastFlush = time.time()
		self.data = {}
		self.backupsAttentedTo = None # Unused
		self.backups = None
		self.log = log

		path = os.path.join(self.root, "%s.mpack" % self.name)
		if os.path.exists(path):
			try:
				self.data = self.unpack(path)
			except:
				self.log.traceback("Database '%s' corrupted, reading from backup..." % self.name)

				# Read from backups
				while True:
					backup = self.grabLastBackup()
					if backup == None:
						self.log.error("Unfortunately, no backup was found. Fresh start!")
						return

					try:
						self.log.warning("Reading from backup `%s`..." % backup)
						self.data = self.unpack(backup)
						break
					except:
						continue

			return
	def unpack(self, path):
		with open(path, "rb") as f:
			blob = f.read()
			return msgpack.unpackb(blob, encoding="utf-8")
	def grabLatestBackup(self):
		backupPath = os.path.join(self.root, ".backups", self.name)

		if not os.path.exists(backupPath):
			os.mkdir(backupPath)
			return 0

		self.backups = os.listdir(backupPath)
		self.backups = [int(i) for i in self.backups]
		self.backups.sort()
		self.backups.reverse()

		if len(self.backups) > 0:
			return int(self.backups[0])
		else:
			return 0
	def grabLastBackup(self):
		backupPath = os.path.join(self.root, ".backups", self.name)

		if self.backups == None:
			if not os.path.exists(backupPath):
				return

			self.backups = os.listdir(backupPath)
			self.backups = [int(i) for i in self.backups]
			self.backups.sort()
			self.backups.reverse()

		if len(self.backups) < 1:
			return

		backup = str(self.backups[0])
		del self.backups[0]
		return os.path.join(backupPath, backup)
	# def asdfghjklqwertyuiopzxcvbnm
	def flush(self):
		# Save code here
		path = os.path.join(self.root, "%s.mpack" % self.name)

		# Backup before flushing
		if os.path.exists(path):
			self.log.debug("Backing up data")
			backupID = str(self.grabLatestBackup() + 1)

			try:
				shutil.copy(path, os.path.join(self.root, ".backups", self.name, backupID))
			except IOError:
				self.log.traceback("Possibly out of space, aggressively deleting overly-redundant backups...")
				while len(self.backups) > 7:
					self.log.debug("Deleting backup %s/%s..." % (self.name, self.backups[0]))
					os.remove(os.path.join(self.root, ".backups", self.name, str(self.backups[0])))
					del self.backups[0]
				return

			self.backups = os.listdir(os.path.join(self.root, ".backups", self.name))
			self.backups = [int(i) for i in self.backups]
			self.backups.sort()

			while len(self.backups) > 15:
				self.log.debug("Deleting backup %s/%s..." % (self.name, self.backups[0]))
				os.remove(os.path.join(self.root, ".backups", self.name, str(self.backups[0])))
				del self.backups[0]


		try:
			with open(path, "wb") as f:
				self.log.warning("Syncing data to disk")
				f.write(msgpack.packb(self.data))
			self.lastFlush = time.time()
		except IOError:
			self.log.error("Possibly out of space... not sure how to handle this one. Just hopefully some space is made before the script goes down to ensure this gets written.")

	def __getitem__(self, index):
		if not (type(index) in (str, bytes)):
			raise Exception("A string must be passed to the stuff")
		return self.data[index]
	def __setitem__(self, index, value):
		if not (type(index) in (str, bytes)):
			raise Exception("A string must be passed to the stuff")
		self.data[index] = value
		return self.data[index]
	def __delattr__(self, index):
		if not (type(index) in (str, bytes)):
			raise Exception("A string must be passed to the stuff")
		del self.data[index]
	def __delitem__(self, index):
		if not (type(index) in (str, bytes)):
			raise Exception("A string must be passed to the stuff")
		del self.data[index]
	def __iter__(self):
		for i in self.data:
			# if type(i) == str:
			# 	i = i.encode("utf8")
			yield i
