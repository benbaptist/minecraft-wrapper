class Player:
    def __init__(self, username, mcuuid):
        self.username = username
        self.mcuuid = mcuuid

        self.position = None
        self.ip_address = None
        self.entity_id = None
