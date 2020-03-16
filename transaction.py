import json
from ecdsa import SigningKey
import hashlib
import binascii
import time


class Transaction:

    def __init__(self, sender, receiver, amount, comment="", time=time.time(), txid="", sig=b""):
        self.sender = sender  # public key
        self.receiver = receiver  # public key
        assert amount > 0
        self.amount = amount
        self.comment = comment
        self.time = time
        self.txid = self.generate_txid()
        if sig == b"":
            self.sig = self.sign()
        else:
            self.sig = sig

    def generate_txid(self):
        m = hashlib.sha256()
        m.update((str(self.sender.to_string()) + str(self.receiver.to_string()) + str(self.amount) + self.comment + str(self.time)).encode())
        return m.hexdigest()

    def to_json(self):
        '''
        Serializes object to JSON string
        '''
        json_dict = dict()
        json_dict['sender'] = binascii.hexlify(self.sender.to_string()).decode()
        json_dict['receiver'] = binascii.hexlify(self.receiver.to_string()).decode()
        json_dict['amount'] = str(self.amount)
        json_dict['comment'] = self.comment
        json_dict['time'] = str(self.time)
        json_dict['txid'] = str(self.txid)
        json_dict['sig'] = self.sig.hex()
        return json.dumps(json_dict)

    @classmethod
    def from_json(cls, json_str):
        '''
        Instantiates/Deserializes object from JSON string
        '''
        trans = json.loads(json_str)
        transaction = Transaction(SigningKey.from_string(binascii.unhexlify(bytes(trans['sender'], 'utf-8'))), SigningKey.from_string(
            binascii.unhexlify(bytes(trans['receiver'], 'utf-8'))), int(trans['amount']), trans['comment'], float(trans['time']), trans['txid'], bytes.fromhex(trans['sig']))
        return transaction

    def transaction_to_string(self):
        '''
        Convert the fields in the current transaction object to string
        '''
        return self.sender.to_string().hex() + self.receiver.to_string().hex() + str(self.amount) + self.comment + str(self.txid) + time.asctime(time.localtime(self.time))

    def sign(self):
        '''
        Sign the encoded (byte-form) version of transaction object
        '''
        return self.sender.sign(self.transaction_to_string().encode())

    def validate(self, signature):
        '''
        Validate transaction correctness
        Compare signature (signed transaction object in bytes) and transaction object in bytes
        i.e. s(b) and b
        '''
        sender_vk = self.sender.verifying_key
        assert sender_vk.verify(signature, self.transaction_to_string().encode())

    def __str__(self):
        return self.transaction_to_string()

    def __eq__(self, other):
        # Check if all parts of the transaction are equal
        return(self.sender == other.sender and self.receiver == other.receiver and self.amount == other.amount and self.comment == other.comment and 
                self.txid == other.txid and self.time == other.time)

# sender = SigningKey.generate()

# receiver = SigningKey.generate()
# receiver_vk = receiver.verifying_key

# t1 = Transaction(sender, receiver, 100)
# t1_json = t1.to_json()
# t1_back = Transaction.from_json(t1_json)

# print(t1_json)
# print(t1)
# print(t1_back)
# print(t1==t1_back)
# t1.validate(t1_back.sig)
