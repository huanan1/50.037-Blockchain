import ecdsa
import binascii

PRIVATE_KEY = ecdsa.SigningKey.generate()
PRIVATE_KEY.to_string
priv_key = str(binascii.hexlify(PRIVATE_KEY.to_string()).decode())
pub_key = binascii.hexlify(PRIVATE_KEY.get_verifying_key().to_string()).decode()
print("Private key: {}\nPublic key: {}\n".format(priv_key, pub_key))