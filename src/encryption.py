# -*- coding: utf-8 -*-

# This source file is part of mc4p,
# the Minecraft Portable Protocol-Parsing Proxy.
#
# Copyright (C) 2011 Matthew J. McGill, Simon Marti

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details

from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import AES, DES
from hashlib import md5
from struct import unpack


def decode_public_key(bytes):
    """Decodes a public RSA key in ASN.1 format as defined by x.509"""
    return RSA.importKey(bytes)


def encode_public_key(key):
    """Encodes a public RSA key in ASN.1 format as defined by x.509"""
    return key.publickey().exportKey(format="DER")


def generate_key_pair():
    """Generates a 1024 bit RSA key pair"""
    return RSA.generate(1024)


def generate_random_bytes(length):
    return Random.get_random_bytes(length)


def generate_server_id():
    """Generates 20 random hex characters"""
    return "".join("%02x" % ord(c) for c in generate_random_bytes(10))


def generate_challenge_token():
    """Generates 4 random bytes"""
    return generate_random_bytes(4)


def generate_shared_secret():
    """Generates a 128 bit secret key to be used in symmetric encryption"""
    return generate_random_bytes(16)


def encrypt_shared_secret(shared_secret, public_key):
    """Encrypts the PKCS#1 padded shared secret using the public RSA key"""
    return public_key.encrypt(_pkcs1_pad(shared_secret), 0)[0]


def decrypt_shared_secret(encrypted_key, private_key):
    """Decrypts the PKCS#1 padded shared secret using the private RSA key"""
    return _pkcs1_unpad(private_key.decrypt(encrypted_key))


def encryption_for_version(version):
    if version <= 32:
        return RC4
    else:
        return AES128CFB8


class RC4(object):
    def __init__(self, key):
        self.key = key
        x = 0
        self.box = box = range(256)
        for i in range(256):
            x = (x + box[i] + ord(key[i % len(key)])) % 256
            box[i], box[x] = box[x], box[i]
        self.x = self.y = 0

    def crypt(self, data):
        out = ""
        box = self.box
        for char in data:
            self.x = x = (self.x + 1) % 256
            self.y = y = (self.y + box[self.x]) % 256
            box[x], box[y] = box[y], box[x]
            out += chr(ord(char) ^ box[(box[x] + box[y]) % 256])
        return out

    decrypt = encrypt = crypt


def AES128CFB8(shared_secret):
    """Creates a AES128 stream cipher using cfb8 mode"""
    return AES.new(shared_secret, AES.MODE_CFB, shared_secret)


def _pkcs1_unpad(bytes):
    pos = bytes.find('\x00')
    if pos > 0:
        return bytes[pos+1:]


def _pkcs1_pad(bytes):
    assert len(bytes) < 117
    padding = ""
    while len(padding) < 125-len(bytes):
        byte = Random.get_random_bytes(1)
        if byte != '\x00':
            padding += byte
    return '\x00\x02%s\x00%s' % (padding, bytes)


class PBEWithMD5AndDES(object):
    """PBES1 implementation according to RFC 2898 section 6.1"""
    SALT = '\x0c\x9d\x4a\xe4\x1e\x83\x15\xfc'
    COUNT = 5

    def __init__(self, key):
        key = self._generate_key(key, self.SALT, self.COUNT, 16)
        self.key = key[:8]
        self.iv = key[8:16]

    def encrypt(self, plaintext):
        padding = 8 - len(plaintext) % 8
        plaintext += chr(padding)*padding
        return self._cipher().encrypt(plaintext)

    def decrypt(self, ciphertext):
        plaintext = self._cipher().decrypt(ciphertext)
        return plaintext[:-ord(plaintext[-1])]

    def _cipher(self):
        return DES.new(self.key, DES.MODE_CBC, self.iv)

    def _generate_key(self, key, salt, count, length):
        key = key + salt
        for i in range(count):
            key = md5(key).digest()
        return key[:length]

