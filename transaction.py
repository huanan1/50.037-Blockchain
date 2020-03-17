import json
from ecdsa import SigningKey, VerifyingKey
import hashlib
import binascii
import time
import copy


class Transaction:

    def __init__(self, sender_vk, receiver_vk, amount, comment="", time_=None, txid="", sig=b"", sender_pk=None):
        try:
            # need to do hexlify and decode to change public key to string format during instantiation
            self.sender_vk = binascii.hexlify(sender_vk.to_string()).decode()
        except:
            # already in string format
            self.sender_vk = sender_vk # public key
        # print(type(self.sender_vk))
        try:
            self.receiver_vk = binascii.hexlify(receiver_vk.to_string()).decode()
        except:
            self.receiver_vk = receiver_vk # verifying key
        self.sender_pk = sender_pk  # private key
        assert amount > 0
        self.amount = amount
        self.comment = comment
        if time_ is None:
            time_ = time.time()
        self.time = time_
        self.txid = self.generate_txid()
        if sig == b"":
            self.sig = self.sign()
        else:
            self.sig = sig

    def generate_txid(self):
        m = hashlib.sha256()
        m.update((self.sender_vk + self.receiver_vk + str(self.amount) + str(self.comment) + str(self.time)).encode())
        return m.hexdigest()

    def to_json(self):
        '''
        Serializes object to JSON string
        '''
        json_dict = dict()
        json_dict['sender_vk'] = self.sender_vk
        json_dict['receiver_vk'] = self.receiver_vk
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
        transaction = Transaction(trans['sender_vk'], trans['receiver_vk'], int(trans['amount']), trans['comment'], float(trans['time']), trans['txid'], bytes.fromhex(trans['sig']))
        return transaction

    def transaction_to_string(self):
        '''
        Convert the fields in the current transaction object to string
        '''
        return self.sender_vk + self.receiver_vk + str(self.amount) + self.comment + str(self.txid) + time.asctime(time.localtime(self.time))

    def sign(self):
        '''
        Sign the encoded (byte-form) version of transaction object
        '''
        
        return self.sender_pk.sign(self.transaction_to_string().encode())

    def validate(self, signature):
        '''
        Validate transaction correctness
        Compare signature (signed transaction object in bytes) and transaction object in bytes
        i.e. s(b) and b
        '''
        sender_vk_key = VerifyingKey.from_string(binascii.unhexlify(bytes(self.sender_vk, 'utf-8')))
        assert sender_vk_key.verify(signature, self.transaction_to_string().encode())

    def __str__(self):
        return self.transaction_to_string()

    def __eq__(self, other):
        # Check if all parts of the transaction are equal
        return(self.sender_vk == other.sender_vk and self.receiver_vk == other.receiver_vk and self.amount == other.amount and self.comment == other.comment and 
                self.txid == other.txid and self.time == other.time)

# sender_pk = SigningKey.generate()
# sender_vk = sender_pk.get_verifying_key()

# receiver_vk = SigningKey.generate().get_verifying_key()
# # receiver_vk_vk = receiver_vk.get_verifying_key()
# # print(type(receiver_vk_vk))
# t1 = Transaction(sender_vk, receiver_vk, 100, sender_pk=sender_pk)
# t1_json = copy.deepcopy(t1.to_json())
# t1_back = Transaction.from_json(t1_json)

# # print(t1_json)
# print(t1)
# print(t1_back)
# print(t1==t1_back)
# t1.validate(t1_back.sig)