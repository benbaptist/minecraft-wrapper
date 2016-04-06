# -*- coding: utf-8 -*-

import uuid

class MCUUID (uuid.UUID):

    def __init__(self, hex=None, bytes=None, bytes_le=None, fields=None, int=None, version=None):
        super(MCUUID, self).__init__(hex, bytes, bytes_le, fields, int, version)

    @property
    def string(self):
        return str(self)

h = MCUUID('12345678123456781234567812345678')

print h.string
print h.hex
print h.int

print uuid.UUID(bytes="12345678123456781234567812345678".decode("hex"))