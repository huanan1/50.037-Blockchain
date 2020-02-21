import ecdsa

private = ecdsa.SigningKey.generate()
public = private.get_verifying_key()
sig = private.sign(b"Blockchain Technology")
print(public.verify(sig, b"Blockchain Technology")) # True