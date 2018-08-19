# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

# region Imports
# ------------------------------------------------

# standard
from collections import deque
import io  # PY3
import json
import struct
import zlib
import sys
# import StringIO

# local
from proxy.utils.constants import *

# Py3-2
PY3 = sys.version_info > (3,)

if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range

# endregion

# region Constants
# ------------------------------------------------

PY3 = sys.version_info > (3,)

_CODERS = {
    "string": 0,
    "json": 1,
    "ubyte": 2,
    "byte": 3,
    "int": 4,
    "short": 5,
    "ushort": 6,
    "long": 7,
    "double": 8,
    "float": 9,
    "bool": 10,
    "varint": 11,
    "bytearray": 12,
    "bytearray_short": 13,
    "position": 14,
    "slot": 15,
    # "slot_noNBT": 18,
    "uuid": 16,
    "metadata": 17,
    "metadata1.9": 19,
    "stringarray": 20,
    "rest": 90,
    "raw": 90
}
# endregion


# noinspection PyMethodMayBeStatic,PyBroadException,PyAugmentAssignment
class Packet(object):
    def __init__(self, sock, obj):
        self.socket = sock
        self.obj = obj
        self.log = self.obj.log
        self.recvCipher = None
        self.sendCipher = None
        self.compressThreshold = -1
        self.compression = False
        self.abort = False

        # this is set by the calling class/method.  Not presently used here,
        #  but could be. maybe to decide which metadata parser to use?
        self.version = self.obj.javaserver.protocolVersion
        self.buffer = io.BytesIO()  # Py3
        # self.buffer = StringIO.StringIO()

        self.queue = deque([])

        # encode/decode for NBT operations
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

        # packet send/read operations
        self._PKTSEND = {
            0: self.send_string,
            1: self.send_json,
            2: self.send_ubyte,
            3: self.send_byte,
            4: self.send_int,
            5: self.send_short,
            6: self.send_ushort,
            7: self.send_long,
            8: self.send_double,
            9: self.send_float,
            10: self.send_bool,
            11: self.send_varint,
            12: self.send_bytearray,
            13: self.send_bytearray_short,
            14: self.send_position,
            15: self.send_slot,
            16: self.send_uuid,
            17: self.send_metadata,
            19: self.send_metadata_1_9,
            20: self.send_stringarray,
            90: self.send_pay,
            100: self.send_nothing
        }
        self._PKTREAD = {
            0: self.read_string,
            1: self.read_json,
            2: self.read_ubyte,
            3: self.read_byte,
            4: self.read_int,
            5: self.read_short,
            6: self.read_ushort,
            7: self.read_long,
            8: self.read_double,
            9: self.read_float,
            10: self.read_bool,
            11: self.read_varint,
            12: self.read_bytearray,
            13: self.read_bytearray_short,
            14: self.read_position,
            15: self.read_slot,
            16: self.read_uuid,
            17: self.read_metadata,
            # 18: self.read_slot_nbtless,
            19: self.read_metadata_1_9,
            20: self.read_stringarray,
            90: self.read_rest,
            100: self.read_none
        }

    def close(self):
        self.abort = True

    def hexdigest(self, sh):
        d = int(sh.hexdigest(), 16)
        if d >> 39 * 4 & 0x8:
            return "-%x" % ((-d) & (2 ** (40 * 4) - 1))
        return "%x" % d

    def decompress(self, datalength, payload):
        if datalength > 0:  # it is compressed, unpack it
            return zlib.decompress(payload)
        else:
            return payload

    def pack_varint(self, val):
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

    def unpack_varint(self):
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

    def grab_packet_uncomp(self):
        # unpacking varint recv's the varint byte(s)
        packet_length_rest = self.unpack_varint()
        contents = self.recv(packet_length_rest)
        return contents, False, False

    def grab_packet_comp(self):
        # unpacking varint recv's the varint byte(s)
        packet_length_rest = self.unpack_varint()
        uncomp_data_length = self.unpack_varint()

        if uncomp_data_length == 0:
            # uncompressed data
            uncomp_data = self.recv(packet_length_rest - 1)
            comp_payload = uncomp_data
        else:
            comp_payload = self.recv(
                packet_length_rest -
                len(self.pack_varint(packet_length_rest))
            )
            uncomp_data = zlib.decompress(comp_payload)

        return uncomp_data, comp_payload, uncomp_data_length

    def grabpacket(self):
        """  # noqa

        Visual layout of packets:
        _____________________________________________________________________
        UnCompressed:
            |VarInt                           |VarInt   |ByteArray|
            |len(Packet ID + Data) ==========>|PacketID | Data    |
        _____________________________________________________________________
        Compressed:                                                                        {   <-- Compressed -->   }
            |VarInt                                         |VarInt                        |VarInt    |ByteArray    |
            |Length (DataLength +  PacketID + Data )=======>|DataLength (uncompressed) ===>|PacketID  | Data        |
        _____________________________________________________________________


        """

        # first field - entire raw packet Length
        packet_length = self.unpack_varint()
        length = packet_length
        datalength = 0  # if 0, an uncompressed packet
        if self.compressThreshold != -1:  # if compressed:
            # length of the uncompressed (Packet ID + Data)
            datalength = self.unpack_varint()
            # find the len of the datalength field and subtract it
            # using augmented assignment in the next line seems to BREAK this
            length = packet_length - len(self.pack_varint(datalength))
        orig_payload = self.recv(length)
        payload_read = orig_payload

        if datalength > 0:  # it is compressed, unpack it
            payload_read = zlib.decompress(orig_payload)

        self.buffer = io.BytesIO(payload_read)
        pkid = self.read_varint()
        return pkid, self.pack_varint(datalength) + orig_payload

    def socket_transmit(self, packet):
        if self.sendCipher is None:
            self.socket.send(packet)
        else:
            self.socket.send(self.sendCipher.update(packet))

    def handle_compression(self, compression_threshhold, payload):
        """  # noqa

        Visual layout of packets:
        _____________________________________________________________________
        UnCompressed:
            |VarInt                           |VarInt   |ByteArray|
            |len(Packet ID + Data) ==========>|PacketID | Data    |
        _____________________________________________________________________
        Compressed:                                                                        {   <-- Compressed -->   }
            |VarInt                                         |VarInt                        |VarInt    |ByteArray    |
            |Length (DataLength +  PacketID + Data )=======>|DataLength (uncompressed) ===>|PacketID  | Data        |
        _____________________________________________________________________

        """
        if compression_threshhold > -1:
            # compose compressed packet
            if len(payload) > self.compressThreshold:
                pktcomp = self.pack_varint(len(payload)) + zlib.compress(
                    payload)
                return self.pack_varint(len(pktcomp)) + pktcomp
            else:
                packet = self.pack_varint(0) + payload
                return self.pack_varint(len(packet)) + packet
        else:
            # compose uncompressed packet
            return self.pack_varint(len(payload)) + payload

    def flush(self):
        while len(self.queue) > 0:
            # grab next packet
            packet_tuple = self.queue.popleft()
            # see if it is compressed
            compression = packet_tuple[0]
            packet = packet_tuple[1]  # `payload`
            trans_packet = self.handle_compression(compression, packet)
            self.socket_transmit(trans_packet)

    def send_raw_untouched(self, payload):
        if not self.abort:
            self.queue.append((-1, payload))

    def send_raw(self, payload):
        if not self.abort:
            self.queue.append((self.compressThreshold, payload))

    def readpkt(self, args):
        """
        Usage like:
            # abstracts of integer constants
            `data = packet.readpkt(_DOUBLE, _DOUBLE, _DOUBLE, _BOOL)`
            `x, y, z, on_ground = data`

        Args:
            args: a list of integers representing the type of read operation.
                    Special _NULL (100) type argument allows an extra "padding"
                    argument to be appended.  To see how this is useful, look
                    at serverconnection.py parsing of packet
                    'self.pktCB.SPAWN_OBJECT'

        Returns:  A list of those read results (not a dictionary) in the
                    same order the args were passed.

        """
        result = []
        for arg in args:
            item = self._PKTREAD[arg]()
            result.append(item)
        return result

    def sendpkt(self, pkid, args, payload,):
        """
                Usage like:

                    packet.sendpkt(
                        0xnn,
                        [DOUBLE, DOUBLE, DOUBLE, BOOl], # integer constants
                        (123123, 1233123, 400, True)
                    )

                Args:
                    :args: a list of integers representing the type of send
                     operation.
                    :payload: a tuple of the corresponding values

                Returns:  A list of those read results (not a dictionary) in the
                            same order the args were passed.

                """
        result = b""  # PY 2-3
        # start with packet id
        result += self.send_varint(pkid)
        # append results to the result packet for each type
        argcount = len(args)
        if argcount == 0:
            self.send_raw(result)
            return result
        for x, arg in enumerate(args):
            pay = payload[x]
            result += self._PKTSEND[arg](pay)
        self.send_raw(result)
        return result

    # -- SENDING DATA TYPES -- #
    # ------------------------ #
    def send_string(self, payload):
        try:
            returnitem = payload.encode("utf-8")
        except:
            returnitem = payload
        return self.send_varint(len(returnitem)) + returnitem

    def send_json(self, payload):
        return self.send_string(json.dumps(payload))

    def send_ubyte(self, payload):
        return struct.pack("B", payload)

    def send_byte(self, payload):
        return struct.pack("b", payload)

    def send_int(self, payload):
        return struct.pack(">i", payload)

    def send_short(self, payload):
        return struct.pack(">h", payload)

    def send_ushort(self, payload):
        return struct.pack(">H", payload)

    def send_long(self, payload):
        return struct.pack(">q", payload)

    def send_double(self, payload):
        return struct.pack(">d", payload)

    def send_float(self, payload):
        return struct.pack(">f", payload)

    def send_bool(self, payload):
        if payload:
            return self.send_byte(1)
        else:
            return self.send_byte(0)

    def send_varint(self, payload):
        return self.pack_varint(payload)

    def send_bytearray(self, payload):
        return self.send_varint(len(payload)) + payload

    def send_bytearray_short(self, payload):
        return self.send_short(len(payload)) + payload

    def send_position(self, payload):
        x, y, z = payload
        # position is a Ulong (reason for `Q`)
        return struct.pack(">Q", ((x & 0x3FFFFFF) << 38)
                           | ((y & 0xFFF) << 26)
                           | (z & 0x3FFFFFF))

    def send_slot(self, slot):
        """Sending slots, such as
        {"id":98,"count":64,"damage":0,"nbt":None}"""
        r = self.send_short(slot["id"])
        if slot["id"] == -1:
            return r
        r += self.send_byte(slot["count"])
        if self.version < PROTOCOL_PRE_RELEASE:
            r += self.send_short(slot["damage"])
        if slot["nbt"]:
            r += self.send_tag(slot['nbt'])
        else:
            r += b"\x00"
        return r

    def send_uuid(self, payload):
        return payload.bytes

    def send_metadata_1_9(self, meta_data):
        """ payload is a dictionary of entity metadata items,
        keyed by index number."""
        b = b""
        for index in meta_data:
            # Index
            b += self.send_ubyte(index)
            # Type
            value_type = meta_data[index][0]
            b += self.send_byte(value_type)
            # value
            value = meta_data[index][1]

            if value_type == 0:
                b += self.send_byte(value)
            elif value_type == 1:
                b += self.send_varint(value)
            elif value_type == 2:
                b += self.send_float(value)
            elif value_type == 3:
                b += self.send_string(value)
            elif value_type == 4:
                b += self.send_json(value)
            elif value_type == 5:
                b += self.send_slot(value)
            elif value_type == 6:
                b += self.send_bool(value)
            elif value_type == 7:
                b += self.send_float(value[0])
                b += self.send_float(value[1])
                b += self.send_float(value[2])
            elif value_type == 8:
                b += self.send_position(value)

            elif value_type == 9:  # OPT Position
                bool_option = value[0]
                b += self.send_bool(bool_option)
                if bool_option:
                    b += self.send_position(value[1])

            elif value_type == 10:
                b += self.send_varint(value)

            elif value_type == 11:  # OPT UUID
                bool_option = value[0]
                b += self.send_bool(bool_option)
                if bool_option:
                    b += self.send_uuid(value[1])

            elif value_type == 12:
                b += self.send_varint(value)

            else:
                self.log.error("Unsupported data type '%d' for"
                               " send_metadata() (Class Packet)", value_type)
                raise ValueError
        b += self.send_ubyte(0xff)
        return b

    def send_metadata(self, payload):
        # definitely broken in 1.7.4.  works for 1.8
        b = b""
        for index in payload:
            type_ = payload[index][0]
            value = payload[index][1]
            # "To create the byte, you can use this:
            # (Type << 5 | Index & 0x1F) & 0xFF"
            header = (type_ << 5) | index
            # header = (type_ << 5 | index & 0x1F) & 0xFF
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
                b += self.send_slot(value)
            elif type_ == 6:
                b += self.send_int(value[0])
                b += self.send_int(value[1])
                b += self.send_int(value[2])
            elif type_ == 7:
                b += self.send_float(value[0])
                b += self.send_float(value[1])
                b += self.send_float(value[2])
            else:
                self.log.error("Unsupported data type '%d' for"
                               " send_metadata() (Class Packet)", type_)
                raise ValueError
        b += self.send_ubyte(0x7f)
        return b

    def send_stringarray(self, payload):
        """payload is a list of strings, but first item is a VARINT Count of
        the number of strings in the array.  Hence, this combines the
        Wiki.vg items of `VARINT|STRING(array of STRING)` """
        b = b""
        b += self.pack_varint(len(payload))
        for strings in payload:
            thisone = self.send_string(strings)
            b += thisone
        return b

    def send_pay(self, payload):
        return payload

    # noinspection PyUnusedLocal
    def send_nothing(self, payload):
        """does not really do anything"""
        return b""

    # NBT sending types (self._ENCODERS only)
    # ---------------------------------------
    def send_byte_array(self, payload):
        return self.send_int(len(payload)) + payload

    def send_short_string(self, string_arg):
        return self.send_short(len(string_arg)) + string_arg.encode("utf8")

    def send_list(self, tag):
        # Check that all values are the same type
        r = b""
        typeslist = []
        for i in tag:
            typeslist.append(i['type'])
            if len(set(typeslist)) != 1:
                # raise Exception("Types in list dosn't match!")
                return b''
        # If ok, then continue

        # items type
        r += self.send_byte(typeslist[0])
        # length
        r += self.send_int(len(tag))
        # send every tag
        for e in tag:
            r += self._ENCODERS[typeslist[0]](e["value"])
        return r

    def send_comp(self, tag):
        r = b""

        # Send every tag
        for i in tag:
            r += self.send_tag(i)
        # close compound
        r += b"\x00"
        return r

    def send_int_array(self, values):
        r = self.send_int(len(values))
        return r + struct.pack(">%di" % len(values), *values)

    def send_tag(self, tag):
        """tag is what is found in the item 'nbt':
        This one is empty:
        {'nbt': {'type': 0}, 'count': 28, 'id': 5, 'damage': 1}"""
        # send type indicator
        r = self.send_byte(tag['type'])
        if tag['type'] == 0:
            return r
        # send length prefix
        r += self.send_short(len(tag["name"]))
        # send name
        r += tag["name"].encode("utf8")
        # send tag value
        r += self._ENCODERS[tag["type"]](tag["value"])
        return r

    # -- READING Methods  -- #
    # ---------------------- #
    def recv(self, length):
        if length > 200:
            d = b""  # Py 2-3
            while len(d) < length:
                m = length - len(d)
                if m > 5000:
                    m = 5000
                d += self.socket.recv(m)
        else:
            d = self.socket.recv(length)
            if len(d) == 0:
                raise EOFError("Packet stream ended (Client disconnected")
        if self.recvCipher is None:
            return d
        return self.recvCipher.update(d)

    def read_data(self, length):
        d = self.buffer.read(length)
        if len(d) == 0 and length is not 0:
            # "Received no data or less data than expected - connection closed"
            self.obj.close_server(
                "Received no data or less data than expected - "
                "connection closed"
            )
            return b""
        return d

    # -- READING DATA TYPES -- #
    # ------------------------ #
    def read_string(self):
        return self.read_data(self.read_varint()).decode('utf-8')

    def read_json(self):
        return json.loads(self.read_string())

    def read_ubyte(self):
        return struct.unpack("B", self.read_data(1))[0]

    def read_byte(self):
        return struct.unpack("b", self.read_data(1))[0]

    def read_int(self):
        return struct.unpack(">i", self.read_data(4))[0]

    def read_short(self):
        return struct.unpack(">h", self.read_data(2))[0]

    def read_ushort(self):
        return struct.unpack(">H", self.read_data(2))[0]

    def read_long(self):
        return struct.unpack(">q", self.read_data(8))[0]

    def read_double(self):
        return struct.unpack(">d", self.read_data(8))[0]

    def read_float(self):
        return struct.unpack(">f", self.read_data(4))[0]

    def read_bool(self):
        return struct.unpack("b", self.read_data(1))[0] == 1

    def read_varint(self):
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

    def read_bytearray(self):
        return self.read_data(self.read_varint())

    def read_bytearray_short(self):
        return self.read_data(self.read_short())

    def read_position(self):
        position = struct.unpack(">Q", self.read_data(8))[0]
        if position == 0xFFFFFFFFFFFFFFFF:
            return None
        x = int(position >> 38)
        if x & 0x2000000:
            x = (x & 0x1FFFFFF) - 0x2000000
        y = int((position >> 26) & 0xFFF)
        if y & 0x800:
            y = (y & 0x4FF) - 0x800
        z = int(position & 0x3FFFFFF)
        if z & 0x2000000:
            z = (z & 0x1FFFFFF) - 0x2000000
        return x, y, z

    def read_uuid(self):
        return self.obj.proxy.wrapper.mcuuid(bytes=self.read_data(16))

    def read_metadata_1_9(self):
        meta_data = {}
        while True:
            # index keys the meaning ( base class 0-5, 6 extending, etc)
            index = self.read_ubyte()
            if index == 0xff:
                return meta_data
            data_type = self.read_byte()  # a byte coding the data type
            if data_type == 0:
                meta_data[index] = (data_type, self.read_byte())
            elif data_type == 1:
                meta_data[index] = (data_type, self.read_varint())
            elif data_type == 2:
                meta_data[index] = (data_type, self.read_float())
            elif data_type == 3:
                meta_data[index] = (data_type, self.read_string())

            # old 'thinkofdeath' chat spec:
            # http://wayback.archive.org/web/20160306101755/http://wiki.vg/Chat
            elif data_type == 4:
                meta_data[index] = (data_type, self.read_json())

            elif data_type == 5:
                meta_data[index] = (data_type, self.read_slot())
            elif data_type == 6:
                meta_data[index] = (data_type, self.read_bool())

            # "vector3F" 3 floats: rotation on x, rotation on y, rotation on z
            elif data_type == 7:
                meta_data[index] = (data_type, (
                    self.read_float(), self.read_float(), self.read_float()))

            elif data_type == 8:
                meta_data[index] = (data_type, self.read_position())

            # OptPosition (Bool + Optional Position) Position present if
            #  Boolean is set to true
            elif data_type == 9:
                bool_option = self.read_bool()
                if bool_option:
                    meta_data[index] = (data_type, (
                        bool_option, self.read_position()))
                else:
                    meta_data[index] = (data_type, (bool_option, ))

            # Direction (VarInt) (Down = 0, Up = 1, North = 2, South = 3,
            #   West = 4, East = 5)
            elif data_type == 10:
                meta_data[index] = (data_type, self.read_varint())

            # OptUUID (Boolean + Optional UUID) UUID is present if the
            #  Boolean is set to true
            elif data_type == 11:
                bool_option = self.read_bool()
                if bool_option:
                    meta_data[index] = (data_type, self.read_uuid())
                else:
                    meta_data[index] = (data_type, (bool_option, ))

            # BlockID (VarInt)  notes: id << 4 | data - 0 for absent;
            #  otherwise, id << 4 | data
            elif data_type == 12:
                meta_data[index] = (data_type, self.read_varint())

            elif data_type == 13:
                self.log.error(
                    "1.9 metadata found data type 13 'nbt tag',  "
                    "which wrapper does not parse.. read as 'rest/raw'. "
                    "Added in version 1.12 minecraft??"
                )
                meta_data[index] = (data_type, self.read_rest())
            else:
                self.log.error(
                    "Unsupported data type '%d' for read_metadata_1_9()  "
                    "(Class Packet)", data_type
                )
                raise ValueError

    def read_metadata(self):
        """
        /* Prior to 1.9 only! */
        Sept 3, 2012 in the wayback machine, this was valid for whatever
        the MC version was.  This changed March 6th 2016 with 1.9:
        http://wayback.archive.org/web/20160306082342/http://wiki.vg/Entities
        """
        meta_data = {}
        while True:
            # "To create the byte, you can use this:
            #  (Type << 5 | Index & 0x1F) & 0xFF"
            lead_ubyte = self.read_ubyte()
            if lead_ubyte == 0x7f:
                return meta_data
            index = lead_ubyte & 0x1f  # Lower 5 bits
            data_type = lead_ubyte >> 5
            if data_type == 0:
                meta_data[index] = (data_type, self.read_byte())
            elif data_type == 1:
                meta_data[index] = (data_type, self.read_short())
            elif data_type == 2:
                meta_data[index] = (data_type, self.read_int())
            elif data_type == 3:
                meta_data[index] = (data_type, self.read_float())
            elif data_type == 4:
                meta_data[index] = (data_type, self.read_string())
            elif data_type == 5:
                meta_data[index] = (data_type, self.read_slot())
            elif data_type == 6:
                meta_data[index] = (data_type, (
                    self.read_int(), self.read_int(), self.read_int()))

            # Sept 2014, this was added (MC 1.7.2 protocol 4?)  Oct 22 2015
            elif data_type == 7:
                meta_data[index] = (data_type, (
                    self.read_float(), self.read_float(), self.read_float()))

            else:
                self.log.error(
                    "Unsupported data type '%d' for read_metadata()  "
                    "(Class Packet)", data_type
                )
                raise ValueError

    def read_slot(self):
        sid = self.read_short()
        if sid == -1:
            payload = {"id": -1}
        else:
            count = self.read_ubyte()
            if self.version < PROTOCOL_PRE_RELEASE:
                damage = self.read_short()
            else:
                damage = -1
            nbt = self.read_tag()
            # nbtCount = self.read_ubyte()
            # nbt = self.read_data(nbtCount)
            payload = {"id": sid, "count": count, "damage": damage, "nbt": nbt}
        return payload

    def read_stringarray(self):
        """payload is a list of strings, but first item is a VARINT Count of
        the number of strings in the array.  Hence, this combines the
        Wiki.vg items of `VARINT|STRING(array of STRING)` """

        b = self.read_varint()
        pay = []
        for _ in xrange(b):
            pay.append(self.read_string())
        return pay

    def read_rest(self):
        return self.read_data(1024 * 1024)

    def read_none(self):
        return None

    # NBT reading types (self._DECODERS only)
    # ---------------------------------------
    def read_short_string(self):
        size = self.read_short()
        shortstring = self.read_data(size)
        try:
            return shortstring.decode("utf8")
        except:
            return shortstring.decode("utf-16")

    def read_list(self):
        r = []
        btype = self.read_byte()
        length = self.read_int()
        # _ signifies throwaway variable whose value is not used
        for _ in xrange(length):
            b = {"type": btype,
                 "name": "",
                 "value": self._DECODERS[btype]()}
            r.append(b)
        return r

    def read_comp(self):
        a = []
        while True:
            b = self.read_tag()
            if b['type'] == 0:
                break
            a.append(b)
        return a

    def read_int_array(self):
        size = self.read_int()
        return [self.read_int() for _ in xrange(size)]

    def read_tag(self):
        a = {"type": self.read_byte()}
        if a["type"] != 0:
            a["name"] = self.read_short_string()
            a["value"] = self._DECODERS[a["type"]]()
        return a
