# -*- coding: utf-8 -*-

# Copyright (C) 2017, 2018 - SurestTexas00
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from base64 import urlsafe_b64encode
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from os import urandom
from getpass import getpass

# Py3-2
import sys
PY3 = sys.version_info > (3,)

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = False

try:
    import bcrypt
except ImportError:
    bcrypt = False

if PY3:
    def _str_(text, enc):
        return str(text, enc)

    def _bytes_(text, enc):
        return bytes(text, enc)
else:
    def _str_(text, enc):
        return str(text)

    def _bytes_(text, enc):
        return bytes(text)

"""
Sample code usages:

        ## generating self.passphrase, plus salting, is done by wrapper already...
        # passphrase must not be stored anywhere on disk
        # pass phrase must be 32 URL-safe Base64 encoded bytes for the Fernet cipher
        self.passphrase = phrase_to_url_safebytes(secret_passphrase, self.encoding, self.salt)


        # # saving and decrypting data: 
        self.configManager.config["Web"]["web-password"] = encrypt(self.passphrase, "super secret password")
        self.configManager.save()
        
        decrypted_text = decrypt(self.passphrase, self.configManager.config["Web"]["web-password"], self.encoding)
        print(decrypted_text)  # ==> super secret password


        #  ## saving a hashed password and checking it later against user input:
        # hash a password and save to disk
        self.configManager.config["Web"]["web-password"] = make_hash("this secret password")
        self.configManager.save()

        # check the password against the hash
        storedpw = self.configManager.config["Web"]["web-password"]
        x = check_pw("this secret password", storedpw, self.encoding)
        if x:
            print("password matches!")
        
"""


def check_pw(password_string, hashed_pw_str, encoding='utf-8'):
    """ Bcrypt-based password checker.  Takes a raw string password and
    compares it to the hash of a previously hashed password, returning True
    if the passwords match, or False if not.  If bcrypt is not installed on
    the system, the comparison is just a comparison of the two supplied
    strings.  Basically, these functions use bcrypt if it is installed
    and do nothing if it is not.

        :Args:
            :passphrase: 32 URL-safe Base64 encoded bytes
            :data: string data or password to encrypt
            :encoding: encoding (string).

        :returns: a string repr of the encrypted data

        """
    if not bcrypt:
        print(
            "\x1b\x5b\x33\x33\x6dWARNING! Package `bcrypt` is not installed. "
            "Therefore, Wrapper is only doing a string comparison of the 'hash'"
            " and the 'password'! \x1b\x5b\x30\x6d")
        if password_string == hashed_pw_str:
            return True
        else:
            return False
    password_bytes = _bytes_(password_string, encoding)
    hashed_pw = _bytes_(hashed_pw_str, encoding)
    return bcrypt.checkpw(password_bytes, hashed_pw)


def make_hash(password_string, encoding='utf-8'):
    """ Hash a password and return a string repr of the hash. """
    if not bcrypt:
        print("\x1b\x5b\x33\x33\x6dWARNING! Package `bcrypt` is not installed. "
              "Therefore, Wrapper did not create a hash for this password! (%s)"
              "  The password was returned (and probably saved!) in plain text!"
              " \x1b\x5b\x30\x6d" % password_string)
        return password_string

    password_bytes = _bytes_(password_string, encoding)
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return _str_(hashed_bytes, encoding)


def encrypt(passphrase, data, encoding='utf-8'):
    """Encrypt password using cryptography Fernet.

    :Args:
        :passphrase: 32 URL-safe Base64 encoded bytes
        :data: string data or password to encrypt
        :encoding: encoding (string).

    :returns: a string repr of the encrypted data

    """
    if not Fernet:
        print(
            "\x1b\x5b\x33\x33\x6dWARNING! Package `cryptography` is not "
            "installed. Therefore, Wrapper did not actually encrypt the data: "
            "`%s`.  It was simply returned back to the caller in plain text"
            "! \x1b\x5b\x30\x6d" % data)
        return data
    cipher = Fernet(passphrase)
    byte_data = _bytes_(data, encoding)
    encrypted_bytes = cipher.encrypt(byte_data)

    return _str_(encrypted_bytes, encoding)


def decrypt(passphrase, encrypted_str_data, encoding='utf-8'):
    """ Decrypt password using cryptography Fernet.

    :Args:
        :passphrase: 32 URL-safe Base64 encoded bytes
        :encoding: encoding (string).

    :returns: a string repr of the decrypted data.  Returns False if decrypt fails

    """
    if not Fernet:
        print(
            "\x1b\x5b\x33\x33\x6dWARNING! Package `cryptography` is not "
            "installed... decrypt did not do anything! \x1b\x5b\x30\x6d")
        return encrypted_str_data
    cipher = Fernet(passphrase)
    encrypted_byte_data = _bytes_(encrypted_str_data, encoding)
    try:
        decrypted_bytes = cipher.decrypt(encrypted_byte_data)
    except:
        # data could not be decryted (probably wrong salt/passphrase)
        return False

    return _str_(decrypted_bytes, encoding)


def gensalt(encoding='utf-8'):
    rand = urandom(16)
    enc = urlsafe_b64encode(rand)
    return _str_(enc, encoding)


def get_passphrase(text_prompt, attempts=3):
    if not Fernet:
        return "nopassword"

    tries = 0
    while tries < attempts:
        _secret_key = getpass(text_prompt)
        if len(_secret_key) > 7:
            return _secret_key
        tries += 1
        print("Mimimum length is 8 characters; You have %s tries left\n" % (attempts - tries))
    return False


def phrase_to_url_safebytes(pass_phrase, encoding='utf-8', salt=b'AAAAA'):
    """return 32, url-safe, base64 encoded bytes from a string"""

    passphrase = _bytes_(pass_phrase, encoding)
    if not Fernet:
        return passphrase

    backend = default_backend()
    salt_b = _bytes_(salt, encoding)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_b,
        iterations=100000,
        backend=backend
    )
    return urlsafe_b64encode(kdf.derive(passphrase))
