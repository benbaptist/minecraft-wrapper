from uuid import UUID
import hashlib
import json

class UUID_Cache:
    def __init__(self, online_mode=True):
        self.online_mode = online_mode

        self.uuid_cache = {}

    def add_uuid(self, username, uuid_obj):
        self.uuid_cache[username] = uuid_obj

    def get_offline_uuid(self, username):
        playername = "OfflinePlayer:%s" % username
        m = hashlib.md5()
        m.update(playername.encode("utf-8"))
        d = bytearray(m.digest())
        d[6] &= 0x0f
        d[6] |= 0x30
        d[8] &= 0x3f
        d[8] |= 0x80
        return UUID(bytes=bytes(d))

    def get_uuid(self, username):
        if not online_mode:
            return self.get_offline_uuid(username)

        if username in self.uuid_cache:
            return self.uuid_cache[username]

        with open("usercache.json", "r") as f:
            data = json.loads(f.read())
            for player in data:
                if player["name"] == username:
                    return player["uuid"]

        raise EOFError("No UUID could be found for the username %s" % username)
