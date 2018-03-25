# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - SurestTexas00 and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Py3-2
import sys
PY3 = sys.version_info > (3,)


def generate_random_bytes(length):
    return os.urandom(length)


def aes128cfb8(shared_secret):
    cipher = Cipher(algorithms.AES(shared_secret), modes.CFB8(shared_secret),
                    backend=default_backend())
    return cipher


def generate_server_id():
    """Generates 20 random hex characters"""
    if PY3:
        return "".join("%02x" % c for c in generate_random_bytes(10))
    else:
        return "".join("%02x" % ord(c) for c in generate_random_bytes(10))


def generate_challenge_token():
    """Generates 4 random bytes"""
    return generate_random_bytes(4)


def generate_private_key_set(bitsize=1024):
    """ def generate_key_pair(): """
    key = rsa.generate_private_key(backend=default_backend(),
                                   public_exponent=65537,
                                   key_size=bitsize)
    return key


def _get_public_key(privatekey):
    public_key = privatekey.public_key()
    return public_key


def get_public_key_bytes(privatekey):
    """ def encode_public_key(key): """
    obj = _get_public_key(privatekey)
    der = obj.public_bytes(encoding=serialization.Encoding.DER,
                           format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return der


def encrypt_PKCS1v15_shared_data(thedata, privatekey):
    y_pubkey = _get_public_key(privatekey)
    ciphertext = y_pubkey.encrypt(thedata, padding.PKCS1v15())
    print(ciphertext)


def decrypt_PKCS1v15_shared_data(thedata, privatekey):
    """def decrypt_shared_secret(encrypted_key, private_key):
    Decrypts the PKCS#1 padded shared secret using the private RSA key

    :param
        :thedata: expects bytes (never a string!)
        :privatekey: private_key object

    :returns bytes

    """
    plaintext = privatekey.decrypt(thedata, padding.PKCS1v15())
    return plaintext
