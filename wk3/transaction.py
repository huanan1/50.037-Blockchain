import json
from ecdsa import SigningKey
import binascii


class Transaction:

    def __init__(self, sender, receiver, amount, comment=''):
        # Instantiates object from passed values
        self.sender = sender  # public key
        self.receiver = receiver  # public key
        assert amount > 0
        self.amount = amount
        self.comment = comment
        self.sign()

    def to_json(self):
        # Serializes object to JSON string
        json_dict = self.__dict__
        json_dict['sender'] = json_dict['sender'].to_string().hex()
        json_dict['receiver'] = json_dict['receiver'].to_string().hex()
        return json.dumps(json_dict)

    @classmethod
    def from_json(cls, json_str):
        # Instantiates/Deserializes object from JSON string
        trans = json.loads(json_str)
        transaction = Transaction(SigningKey.from_string(binascii.unhexlify(bytes(trans['sender'], 'utf-8'))), SigningKey.from_string(
            binascii.unhexlify(bytes(trans['receiver'], 'utf-8'))), trans['amount'], trans['comment'])
        return transaction

    def transaction_to_string(self):
        return str(self.sender.to_string()) + str(self.receiver.to_string()) + str(self.amount) + self.comment

    def sign(self):
        # Sign object with private key passed
        # That can be called within new()
        self.sender.sign(self.transaction_to_string().encode())

    def validate(self, trans):
        # Validate transaction correctness.
        # Can be called within from_json()
        sender_vk = self.sender.verifying_key
        assert sender_vk.verify(self.sender.sign(
            trans.encode()), self.transaction_to_string().encode())

    def __str__(self):
        return self.transaction_to_string()

    def __eq__(self, other):
        # Check if all parts of the transaction are equal
        return(self.sender == other.sender and self.receiver == other.receiver and self.amount == other.amount and self.comment == other.comment)


# sender = SigningKey.generate()

# receiver = SigningKey.generate()
# receiver_vk = receiver.verifying_key

# t1 = Transaction(sender, receiver, 100)
# t1_json = t1.to_json()
# t1_back = Transaction.from_json(t1_json)
