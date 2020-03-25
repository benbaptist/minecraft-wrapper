import subprocess
import threading
import time
import os
import reedsolo
import struct

START_FREQ = 60000
SPACE_FREQ = 2000
BAUD = 1200
CARRIERS = 8

# REED = 32
# FRAME_SIZE = 128
#
# FRAME_SIZE_AFTER_REED = FRAME_SIZE - REED

class Carrier:
    def __init__(self, freq, baud):
        print("Carrier %sHz with baud %s" % (freq, baud))
        self.baud = baud
        self.freq = freq

        self.proc = subprocess.Popen(["minimodem", "--tx", str(self.baud), "-R", "192000", "-M", str(self.freq)], stdout=subprocess.PIPE, stdin=subprocess.PIPE)

        self.buffer = ""

        t = threading.Thread(target=self.keepalive, args=())
        t.daemon = True
        t.start()
    def keepalive(self):
        while True:
            # print("keep")
            if len(self.buffer) < 1:
                self.proc.stdin.write("\x00" * (BAUD / 8))
                time.sleep(1)
                print("paddding")
            else:
                print("send")
                self.proc.stdin.write(self.buffer)
                self.buffer = ""
    def write(self, data):
        # print(len(data))
        # if len(data) > FRAME_SIZE_AFTER_REED:
        #     raise Exception("Too long of a packet")
        # elif len(data) < FRAME_SIZE_AFTER_REED:
        #     l = FRAME_SIZE_AFTER_REED - len(data)
        #     padding = "\x00" * l
        #     data = data + padding
        #
        # rs = self.rs.encode(data)
        #
        # print("Packet len: %s" % len(rs))

        print(data)
        self.buffer += data
        # self.proc.stdin.write(data)

    def send_packet(self, packet_id, payload):
        # new packet, two 0xFF bytes
        packet = struct.pack("B", 0xFF)
        packet += struct.pack("B", 0xFF)

        # packet_id, byte
        packet += struct.pack("B", packet_id)

        # reed length, short
        reed_length = int(len(payload) * .25)
        packet += struct.pack("H", reed_length)

        # print("Reed length: %s" % reed_length)

        rs = reedsolo.RSCodec(reed_length)
        payload += rs.encode(payload)

        filtered_payload = bytearray()

        for b in payload:
            # print(b)
            if b != "\xff":
                filtered_payload.append(b)
            else:
                filtered_payload.append("\xff\xfe") # escaped 0xff charac ater

        packet += filtered_payload

        # EOF
        packet += struct.pack("B", 0xFF)
        packet += struct.pack("B", 0x00)

        self.write(packet)

carriers = []

for i in range(CARRIERS):
    carrier = Carrier(START_FREQ + (SPACE_FREQ * i), BAUD)
    carriers.append(carrier)

while True:
    for carrier in carriers:
        carrier.send_packet(0x05, "Hello there!! this is a packet...")
        # carrier.write("Hello there\x00")
    time.sleep(.1)

time.sleep(600000)
