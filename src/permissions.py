# this was a stupid idea, i shold probably remove this file ioksaodksaisaoijd LOLOLOLOLOOL
# because it goes unused
# LOLLOOLOLOL
class Permissions:
	def __init__(self, wrapper):
		self.wrapper = wrapper
		#self.permissions = storage.Storage("permissions", self.log)
	def createGroup(self, groupName):
		if groupName in self.permissions["groups"]:
			raise Exception("Group '%s' already exists!" % groupName)
		else:
			self.permissions["groups"]
	def doesGroupExist(self, groupName):
		return groupName in self.permissions["groups"]
	
	# Check for permissions
	def doesPlayerHavePermission(self, player, node):
		uuid = player.uuid