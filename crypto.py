from base64 import b64encode
from hashlib import sha256

import bcrypt


def hash_string(plain_text):
    pw = b64encode(sha256(plain_text.encode('utf-8')).digest())
    return bcrypt.hashpw(pw, bcrypt.gensalt())


def verify_hashed_string(plain_text, hashed):
    pw = b64encode(sha256(plain_text.encode('utf-8')).digest())
    return bcrypt.checkpw(pw, hashed.encode('utf-8'))
