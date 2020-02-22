from merkle_tree import MerkleTree
import hashlib
import random
import time
import binascii


class Block:
    def __init__(self, transactions, previous_header_hash, hash_tree_root, timestamp, nonce):
        # Instantiates object from passed values
        self.transactions = transactions  # MerkleTree object
        self.previous_header_hash = previous_header_hash
        self.hash_tree_root = hash_tree_root
        self.timestamp = timestamp
        self.nonce = nonce

    def header_hash(self):
        header_joined = binascii.hexlify(
            self.hash_tree_root).decode() + str(self.timestamp) + str(self.nonce)
        if self.previous_header_hash is not None:
            header_joined = binascii.hexlify(self.previous_header_hash).decode() + header_joined
        m = hashlib.sha256()
        m.update(header_joined.encode())
        round1 = m.digest()
        m = hashlib.sha256()
        m.update(round1)
        return m.digest()


# hashlib.md5(b'hello world').hexdigest().decode('hex') == hashlib.md5(b'hello world').digest()
class BlockChain:
    chain = []
    last_hash = None
    TARGET = b"\x00\x00\x0f\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"

    def add(self, block):
        if self.validate(block):
            self.chain.append(block)
            self.last_hash = self.chain[-1].header_hash()
            return True
        else:
            return False

    def validate(self, block):
        if len(self.chain) > 0:
            check_previous_header = block.previous_header_hash == self.last_hash
            check_target = block.header_hash() < self.TARGET
            # is the timestamp check required?
            check_timestamp = block.timestamp > self.chain[-1].timestamp
            return check_previous_header and check_target and check_timestamp
        else:
            return block.header_hash() < self.TARGET

    def __str__(self):
        reply="There are {} blocks in the blockchain\n\n".format(len(self.chain))
        for count, i in enumerate(self.chain):
            if count == 0:
                reply += "Genesis Block \t"
            else:
                reply+="Block {} \t".format(str(count).zfill(5))
            reply+="\tHeader: {}\tPrev_header: {}\n".format(str(i.header_hash()),str(i.previous_header_hash))
        return reply

    # def to_json(self):
    #     # Serializes object to JSON string
    #     json_dict = self.__dict__
    #     json_dict['sender'] = json_dict['sender'].to_string().hex()
    #     json_dict['receiver'] = json_dict['receiver'].to_string().hex()
    #     return json.dumps(json_dict)

    # @classmethod
    # def from_json(cls, json_str):
    #     # Instantiates/Deserializes object from JSON string
    #     trans = json.loads(json_str)
    #     transaction = Transaction(SigningKey.from_string(binascii.unhexlify(bytes(trans['sender'],'utf-8'))),SigningKey.from_string(binascii.unhexlify(bytes(trans['receiver'],'utf-8'))), trans['amount'], trans['comment'])
    #     return transaction

    # def transaction_to_string(self):
    #   return str(self.sender.to_string()) + str(self.receiver.to_string()) + str(self.amount) + self.comment

    # def sign(self):
    #     # Sign object with private key passed
    #     # That can be called within new()
    #     self.sender.sign(self.transaction_to_string().encode())

    # def __eq__(self, other):
    #     # Check if all parts of the transaction are equal
    #     return(self.sender == other.sender and self.receiver == other.receiver and self.amount == other.amount and self.comment == other.comment)


blockchain = BlockChain()

merkletree = MerkleTree()
for i in range(100):
    merkletree.add(random.randint(100, 1000))
merkletree.build()
current_time = str(time.time())
for nonce in range(10000000):
    block = Block(merkletree, None, merkletree.get_root(), current_time, nonce)
    if blockchain.validate(block):
        blockchain.add(block)
        break

while True:
    merkletree = MerkleTree()
    for i in range(100):
        merkletree.add(random.randint(100, 1000))
    merkletree.build()
    current_time = str(time.time())
    for nonce in range(10000000):
        block = Block(merkletree, blockchain.last_hash, merkletree.get_root(), current_time, nonce)
        if blockchain.validate(block):
            blockchain.add(block)
            break
    print(blockchain)