# -*- coding: utf-8 -*-

import socket


# Py2-3
#try:
#    import ConfigParser  # only used to set version
#    PY3 = False
#except ImportError:
#    ConfigParser = False
#    PY3 = True

import io as io

import json
import struct
import zlib

from core.mcuuid import MCUUID

class Packet:
    def __init__(self, sock, obj):
        self.socket = sock
        self.obj = obj
        self.recvCipher = None
        self.sendCipher = None
        self.compressThreshold = -1
        self.version = 5
        self.bonk = False
        self.abort = False
        self.buffer = io.BytesIO()

        self.queue = []

        self._ENCODERS = {
            1: self.send_byte,
            2: self.send_short,
            3: self.send_int,
            4: self.send_long,
            5: self.send_float,
            6: self.send_double,
            7: self.send_byte_array,
            8: self.send_short_string,
            9: self.send_list,
            10: self.send_comp,
            11: self.send_int_array
        }

        self._DECODERS = {
            1: self.read_byte,
            2: self.read_short,
            3: self.read_int,
            4: self.read_long,
            5: self.read_float,
            6: self.read_double,
            7: self.read_bytearray,
            8: self.read_short_string,
            9: self.read_list,
            10: self.read_comp,
            11: self.read_int_array
        }

    def close(self):
        self.abort = True

    def hexdigest(self, sh):
        try:
            d = long(sh.hexdigest(), 16)
        except NameError:  # Py3
            d = int(sh.hexdigest(), 16)
        if d >> 39 * 4 & 0x8:
            return "-%x" % ((-d) & (2 ** (40 * 4) - 1))
        return "%x" % d

    def grabPacket(self):
        length = self.unpack_varInt() # first field - entire raw Packet Length i.e. 55 in test (for annoying disconnect)
        dataLength = 0  # if 0, an uncompressed packet
        if self.compressThreshold != -1:  # if compressed:
            dataLength = self.unpack_varInt()  # length of the uncompressed (Packet ID + Data)
            # using augmented assignment in the next line will BREAK this
            length = length - len(self.pack_varInt(dataLength))  # find the len of the datalength field and subtract it
        payload = self.recv(length)

        if dataLength > 0:  # it is compressed, unpack it
            payload = zlib.decompress(payload)

        self.buffer = io.BytesIO(payload)
        pkid = self.read_varInt()
        return (pkid, payload)

    def pack_varInt(self, val):
        total = b''
        if val < 0:
            val = (1 << 32) + val
        while val >= 0x80:
            bits = val & 0x7F
            val >>= 7
            total += struct.pack('B', (0x80 | bits))
        bits = val & 0x7F
        total += struct.pack('B', bits)
        return total

    def unpack_varInt(self):
        total = 0
        shift = 0
        val = 0x80
        while val & 0x80:
            val = struct.unpack('B', self.recv(1))[0]
            total |= ((val & 0x7F) << shift)
            shift += 7
        if total & (1 << 31):
            total = total - (1 << 32)
        return total

    def setCompression(self, threshold):
        # self.sendRaw("\x03\x80\x02")
        self.send(0x03, "varint", (threshold,))
        self.compressThreshold = threshold
        # time.sleep(1.5)

    def flush(self):
        for p in self.queue:
            packet = p[1]
            pkid = struct.unpack("B", packet[0])[0]
            if p[0] > -1:
                if len(packet) > self.compressThreshold:
                    packetCompressed = self.pack_varInt(len(packet)) + zlib.compress(packet)
                    packet = self.pack_varInt(len(packetCompressed)) + packetCompressed
                else:
                    packet = self.pack_varInt(0) + packet
                    packet = self.pack_varInt(len(packet)) + packet
            else:
                packet = self.pack_varInt(len(packet)) + packet
            if self.sendCipher is None:
                self.socket.send(packet)
            else:
                self.socket.send(self.sendCipher.encrypt(packet))
        self.queue = []

    def sendRaw(self, payload):
        if not self.abort:
            self.queue.append((self.compressThreshold, payload))

    def read(self, expression):
        result = {}
        for exp in expression.split("|"):
            type_ = exp.split(":")[0]
            name = exp.split(":")[1]
            if type_ == "string":
                result[name] = self.read_string()
            elif type_ == "json":
                result[name] = self.read_json()
            elif type_ == "ubyte":
                result[name] = self.read_ubyte()
            elif type_ == "byte":
                result[name] = self.read_byte()
            elif type_ == "int":
                result[name] = self.read_int()
            elif type_ == "short":
                result[name] = self.read_short()
            elif type_ == "ushort":
                result[name] = self.read_ushort()
            elif type_ == "long":
                result[name] = self.read_long()
            elif type_ == "double":
                result[name] = self.read_double()
            elif type_ == "float":
                result[name] = self.read_float()
            elif type_ == "bool":
                result[name] = self.read_bool()
            elif type_ == "varint":
                result[name] = self.read_varInt()
            elif type_ == "bytearray":
                result[name] = self.read_bytearray()
            elif type_ == "bytearray_short":
                result[name] = self.read_bytearray_short()
            elif type_ == "position":
                result[name] = self.read_position()
            elif type_ == "slot":
                result[name] = self.read_slot()
            elif type_ == "uuid":
                result[name] = self.read_uuid()
            elif type_ == "metadata":
                result[name] = self.read_metadata()
            elif type_ == "rest":
                result[name] = self.read_rest()
        return result

    def send(self, pkid, expression, payload):
        result = ""
        result += self.send_varInt(pkid)
        if len(expression) > 0:
            for i, type_ in enumerate(expression.split("|")):
                pay = payload[i]
                if type_ == "string":
                    result += self.send_string(pay)
                elif type_ == "json":
                    result += self.send_json(pay)
                elif type_ == "ubyte":
                    result += self.send_ubyte(pay)
                elif type_ == "byte":
                    result += self.send_byte(pay)
                elif type_ == "int":
                    result += self.send_int(pay)
                elif type_ == "short":
                    result += self.send_short(pay)
                elif type_ == "ushort":
                    result += self.send_ushort(pay)
                elif type_ == "varint":
                    result += self.send_varInt(pay)
                elif type_ == "float":
                    result += self.send_float(pay)
                elif type_ == "double":
                    result += self.send_double(pay)
                elif type_ == "long":
                    result += self.send_long(pay)
                elif type_ == "bytearray":
                    result += self.send_bytearray(pay)
                elif type_ == "bytearray_short":
                    result += self.send_bytearray_short(pay)
                elif type_ == "uuid":
                    result += self.send_uuid(pay)
                elif type_ == "metadata":
                    result += self.send_metadata(pay)
                elif type_ == "bool":
                    result += self.send_bool(pay)
                elif type_ == "position":
                    result += self.send_position(pay)
                elif type_ == "slot":
                    result += self.send_slot(pay)
                elif type_ == "raw":
                    result += pay
        self.sendRaw(result)
        return result

    # -- SENDING DATA TYPES -- #

    def send_byte(self, payload):
        return struct.pack("b", payload)

    def send_ubyte(self, payload):
        return struct.pack("B", payload)

    def send_string(self, payload):
        try:
            returnitem = payload.encode("utf-8", errors="ignore")
        except:
            returnitem = str(payload)
        return self.send_varInt(len(returnitem)) + returnitem

    def send_json(self, payload):
        return self.send_string(json.dumps(payload))

    def send_int(self, payload):
        return struct.pack(">i", payload)

    def send_long(self, payload):
        return struct.pack(">q", payload)

    def send_short(self, payload):
        return struct.pack(">h", payload)

    def send_ushort(self, payload):
        return struct.pack(">H", payload)

    def send_float(self, payload):
        return struct.pack(">f", payload)

    def send_double(self, payload):
        return struct.pack(">d", payload)

    def send_varInt(self, payload):
        return self.pack_varInt(payload)

    def send_bytearray(self, payload):
        return self.send_varInt(len(payload)) + payload

    def send_bytearray_short(self, payload):
        return self.send_short(len(payload)) + payload

    def send_uuid(self, payload):
        return payload.bytes

    def send_position(self, payload):
        x, y, z = payload
        return struct.pack(">Q", ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF))

    def send_metadata(self, payload):
        b = ""
        for index in payload:
            type_ = payload[index][0]
            value = payload[index][1]
            header = (type_ << 5) | index
            b += self.send_ubyte(header)
            if type_ == 0:
                b += self.send_byte(value)
            elif type_ == 1:
                b += self.send_short(value)
            elif type_ == 2:
                b += self.send_int(value)
            elif type_ == 3:
                b += self.send_float(value)
            elif type_ == 4:
                b += self.send_string(value)
            elif type_ == 5:
                print("WIP 5")
            elif type_ == 6:
                print("WIP 6")
            elif type_ == 6:
                print("WIP 7")
        b += self.send_ubyte(0x7f)
        return b

    def send_bool(self, payload):
        if payload:
            return self.send_byte(1)
        else:
            return self.send_byte(0)
        

    # Similar to send_string, but uses a short as length prefix
    def send_short_string(self, string):
        return self.send_short(len(string)) + str.encode("utf8")

    def send_byte_array(self, payload):
        return self.send_int(len(payload)) + payload

    def send_int_array(self, values):
        r = self.send_int(len(values))
        return r + struct.pack(">%di" % len(values), *values)

    def send_list(self, tag):
        # Check that all values are the same type
        r = ""
        typesList = []
        for i in tag:
            typesList.append(i['type'])
            if len(set(typesList)) != 1:
                # raise Exception("Types in list dosn't match!")
                return b''
        # If ok, then continue
        r += self.send_byte(typesList[0])  # items type
        r += self.send_int(len(tag))  # lenght
        for e in tag:  # send every tag
            r += self._ENCODERS[typesList[0]](e["value"])
        return r

    def send_comp(self, tag):
        r = ""
        for i in tag:  # Send every tag
            r += self.send_tag(i)
        r += "\x00"  # close compbound
        return r

    def send_tag(self, tag):
        r = self.send_byte(tag['type'])  # send type indicator
        r += self.send_short(len(tag["name"]))  # send lenght prefix
        r += tag["name"].encode("utf8")  # send name
        r += self._ENCODERS[tag["type"]](tag["value"])  # send tag
        return r

    def send_slot(self, slot):
        """Sending slots, such as {"id":98,"count":64,"damage":0,"nbt":None}"""
        r = self.send_short(slot["id"])
        if slot["id"] == -1:
            return r
        r += self.send_byte(slot["count"])
        r += self.send_short(slot["damage"])
        if slot["nbt"]:
            r += self.send_tag(slot['nbt'])
        else:
            r += "\x00"
        return r

    # -- READING DATA TYPES -- #

    def recv(self, length):
        if length > 200:
            d = ""
            while len(d) < length:
                m = length - len(d)
                if m > 5000:
                    m = 5000
                d += self.socket.recv(m)
        else:  # $ find out why next line sometimes errors out bad file descriptor
            d = self.socket.recv(length)
            if len(d) == 0:
                raise EOFError("Packet stream ended (Client disconnected")
        if self.recvCipher is None:
            return d
        return self.recvCipher.decrypt(d)

    def read_data(self, length):
        d = self.buffer.read(length)
        if len(d) == 0 and length is not 0:
            self.obj.disconnect("Received no data or less data than expected - connection closed")
            return ""
        return d

    def read_byte(self):
        return struct.unpack("b", self.read_data(1))[0]

    def read_ubyte(self):
        return struct.unpack("B", self.read_data(1))[0]

    def read_long(self):
        return struct.unpack(">q", self.read_data(8))[0]

    def read_ulong(self):
        return struct.unpack(">Q", self.read_data(8))[0]

    def read_float(self):
        return struct.unpack(">f", self.read_data(4))[0]

    def read_int(self):
        return struct.unpack(">i", self.read_data(4))[0]

    def read_double(self):
        return struct.unpack(">d", self.read_data(8))[0]

    def read_bool(self):
        return (self.read_data(1) == 0x01)

    def read_short(self):
        return struct.unpack(">h", self.read_data(2))[0]

    def read_ushort(self):
        return struct.unpack(">H", self.read_data(2))[0]

    def read_bytearray(self):
        return self.read_data(self.read_varInt())

    def read_int_array(self):
        size = self.read_int()
        return [self.read_int() for _ in range(size)]

    def read_bytearray_short(self):
        return self.read_data(self.read_short())

    def read_position(self):
        position = struct.unpack(">Q", self.read_data(8))[0]
        if position == 0xFFFFFFFFFFFFFFFF:
            return None
        x = int(position >> 38)
        if (x & 0x2000000):
            x = (x & 0x1FFFFFF) - 0x2000000
        y = int((position >> 26) & 0xFFF)
        if (y & 0x800):
            y = (y & 0x4FF) - 0x800
        z = int(position & 0x3FFFFFF)
        if (z & 0x2000000):
            z = (z & 0x1FFFFFF) - 0x2000000
        return (x, y, z)

    def read_slot(self):
        sid = self.read_short()
        if sid != -1:
            count = self.read_ubyte()
            damage = self.read_short()
            nbt = self.read_tag()
            # nbtCount = self.read_ubyte()
            # nbt = self.read_data(nbtCount)
            return {"id": sid, "count": count, "damage": damage, "nbt": nbt}

    def read_varInt(self):
        total = 0
        shift = 0
        val = 0x80
        while val & 0x80:
            val = struct.unpack('B', self.read_data(1))[0]
            total |= ((val & 0x7F) << shift)
            shift += 7
        if total & (1 << 31):
            total = total - (1 << 32)
        return total

    def read_uuid(self):
        return MCUUID(bytes=self.read_data(16))

    def read_string(self):
        return self.read_data(self.read_varInt())

    def read_json(self):
        return json.loads(self.read_string())

    def read_rest(self):
        return self.read_data(1024 * 1024)

    def read_metadata(self):
        data = {}
        while True:
            a = self.read_ubyte()
            if a == 0x7f:
                return data
            index = a & 0x1f
            type_ = a >> 5
            if type_ == 0:
                data[index] = (type_, self.read_byte())
            elif type_ == 1:
                data[index] = (type_, self.read_short())
            elif type_ == 2:
                data[index] = (type_, self.read_int())
            elif type_ == 3:
                data[index] = (type_, self.read_float())
            elif type_ == 4:
                data[index] = (type_, self.read_string())
            elif type_ == 5:
                data[index] = (type_, self.read_slot())
            elif type_ == 6:
                data[index] = (type_, (self.read_int(), self.read_int(), self.read_int()))
            # elif type_ == 7:
            #   data[index] = ("float", (self.read_int(), self.read_int(), self.read_int()))
        return data

    def read_short_string(self):
        size = self.read_short()
        string = self.read_data(size)
        return string.decode("utf8")

    def read_comp(self):
        a = []
        done = 0
        while done == 0:
            b = self.read_tag()
            if b['type'] == 0:
                done = 1
                break
            a.append(b)
        return a

    def read_tag(self):
        a = {}
        a["type"] = self.read_byte()
        if a["type"] != 0:
            a["name"] = self.read_short_string()
            a["value"] = self._DECODERS[a["type"]]()
        return a

    def read_list(self):
        r = []
        btype = self.read_byte()
        length = self.read_int()
        for l in range(length):  # TODO Py2-3
            b = {}
            b["type"] = btype
            b["name"] = ""
            b["value"] = self._DECODERS[btype]()
            r.append(b)
        return r
