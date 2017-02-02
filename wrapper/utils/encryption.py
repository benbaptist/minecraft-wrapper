# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.


from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import AES

# Py3-2
import sys
PY3 = sys.version_info > (3,)


def decode_public_key(thebytes):
    """Decodes a public RSA key in ASN.1 format as defined by x.509"""
    return RSA.importKey(thebytes)


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
    if PY3:
        return "".join("%02x" % c for c in generate_random_bytes(10))
    else:
        return "".join("%02x" % ord(c) for c in generate_random_bytes(10))


def generate_challenge_token():
    """Generates 4 random bytes"""
    return generate_random_bytes(4)


def decrypt_shared_secret(encrypted_key, private_key):
    """Decrypts the PKCS#1 padded shared secret using the private RSA key"""
    return _pkcs1_unpad(private_key.decrypt(encrypted_key))


# noinspection PyPep8Naming
def AES128CFB8(shared_secret):
    """Creates a AES128 stream cipher using cfb8 mode"""
    return AES.new(shared_secret, AES.MODE_CFB, shared_secret)


def _pkcs1_unpad(thebytes):
    null_byte = '\x00'
    if PY3:
        null_byte = 0x00
    pos = thebytes.find(null_byte)
    if pos > 0:
        return thebytes[pos + 1:]
