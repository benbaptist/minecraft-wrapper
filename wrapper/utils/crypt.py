# -*- coding: utf-8 -*-

# Copyright (C) 2017, 2018 - SurestTexas00
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

from base64 import urlsafe_b64encode
from os import urandom
from getpass import getpass

# Py3-2
import sys
PY3 = sys.version_info > (3,)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
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
    # noinspection PyUnusedLocal
    def _str_(text, enc):
        return str(text)

    # noinspection PyUnusedLocal
    def _bytes_(text, enc):
        return bytes(text)


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
        print("Mimimum length is 8 characters; You have %s tries left\n" % (
            attempts - tries))
    return False


# noinspection PyBroadException
class Crypt(object):

    def __init__(self, passphrase, encoding='utf-8'):
        """
        :Args:
            :passphrase: 32 URL-safe Base64 encoded bytes (output of
             phrase_to_url_safebytes)
            :encoding: string encoding

        """
        self.passphrase = passphrase
        self.encoding = encoding

    def check_pw(self, password_string, hashed_pw_str):
        """ cryptography-based Fernet password checker.  Takes a raw string
        password and compares it to the hash of a previously hashed password,
        returning True if the passwords match, or False if not.  If
        cryptography is not installed on the system, the comparison is just
        a comparison of the two supplied strings.
    
            :Args:
                :password_string: password or data string
                :hashed_pw_str: the hashed password to compare with
    
            :returns: True if matching, otherwise False
    
            """
        saved = self.decrypt(hashed_pw_str)
        if password_string == saved:
            return True
        else:
            return False

    def encrypt(self, data):
        """Encrypt password using cryptography Fernet.
    
        :Args:
            :passphrase: 32 URL-safe Base64 encoded bytes
            :data: string data or password to encrypt
    
        :returns: a string repr of the encrypted data
    
        """
        if not Fernet:
            print(
                "\x1b\x5b\x33\x33\x6dWARNING! Package `cryptography` is not "
                "installed. Therefore, `crypt` did not actually encrypt the data: "
                "`%s`.  It was simply returned as plain text"
                "! \x1b\x5b\x30\x6d" % data)
            return data
        cipher = Fernet(self.passphrase)
        byte_data = _bytes_(data, self.encoding)
        encrypted_bytes = cipher.encrypt(byte_data)
    
        return _str_(encrypted_bytes, self.encoding)

    def decrypt(self, encrypted_str_data):
        """ Decrypt password using cryptography Fernet.
    
        :Args:
            :passphrase: 32 URL-safe Base64 encoded bytes
    
        :returns: a string repr of the decrypted data.  Returns False if decrypt fails
    
        """
        if not Fernet:
            print(
                "\x1b\x5b\x33\x33\x6dWARNING! Package `cryptography` is not "
                "installed... `Crypt.decrypt` did not do anything! \x1b\x5b\x30\x6d")
            return encrypted_str_data
        cipher = Fernet(self.passphrase)
        encrypted_byte_data = _bytes_(encrypted_str_data, self.encoding)
        try:
            decrypted_bytes = cipher.decrypt(encrypted_byte_data)
        except:
            # data could not be decryted (probably wrong salt/passphrase)
            return False
    
        return _str_(decrypted_bytes, self.encoding)

    def bcrypt_check_pw(self, password_string, hashed_pw_str):
        """ Bcrypt-based password checker.  Takes a raw string password and
        compares it to the hash of a previously hashed password, returning True
        if the passwords match, or False if not.

        Bcrypt functions are to be used where ever you are storing a user's
        password, but do not ever want to be able to "know" their password
        directly.  We only need to know if the password they supplied is
        correct or not.

        If bcrypt is not installed on
        the system, the comparison is just a comparison of the two supplied
        strings.
            :Args:
                :passphrase: 32 URL-safe Base64 encoded bytes
                :data: string data or password to encrypt
                :encoding: encoding (string).
            :returns: a string repr of the encrypted data
            """
        if not bcrypt:
            print(
                "\x1b\x5b\x33\x33\x6dWARNING! Package `bcrypt` is not installed. "
                "Therefore, `crypt` is only doing a string comparison of the 'hash'"
                " and the 'password'! \x1b\x5b\x30\x6d")
            if password_string == hashed_pw_str:
                return True
            else:
                return False
        password_bytes = _bytes_(password_string, self.encoding)
        hashed_pw = _bytes_(hashed_pw_str, self.encoding)
        return bcrypt.checkpw(password_bytes, hashed_pw)

    def bcrypt_make_hash(self, password_string):
        """ Use bcrypt to hash a password and return a string repr of the hash.

        Bcrypt functions are to be used where ever you are storing a user's
        password, but do not ever want to be able to "know" their password
        directly.  We only need to know if the password they supplied is
        correct or not.
        """
        if not bcrypt:
            print(
                "\x1b\x5b\x33\x33\x6dWARNING! Package `bcrypt` is not installed. "
                "Therefore, `crypt` could not create a hash for this password!"
                " \x1b\x5b\x30\x6d" % password_string)
            return False

        password_bytes = _bytes_(password_string, self.encoding)
        hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return _str_(hashed_bytes, self.encoding)
