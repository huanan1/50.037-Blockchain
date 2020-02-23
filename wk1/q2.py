import hashlib
import string
import random

def hash_func(n, msg):
    m = hashlib.sha256()
    m.update(msg)
    return m.digest()[:n]

def randomString(stringLength=100):
    """Generate a random string of fixed length """
    letters = string.printable
    return ''.join(random.choice(letters) for i in range(stringLength))

def collisionLoop(length):
    saved_list = []
    while True:
        hash_val = hash_func(length, randomString().encode())
        if hash_val in saved_list:
            return hash_val
        else:
            saved_list.append(hash_val)

def preimageLoop(length):
    original = b"\x00"*length
    while True:
        hash_val = hash_func(length, randomString().encode())
        if hash_val == original:
            return hash_val

print(collisionLoop(4))
print(preimageLoop(1))