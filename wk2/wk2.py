from merkle_tree import MerkleTree
import hashlib
import random
import time
import binascii
import copy

class Block:
    def __init__(self, transactions, previous_header_hash, hash_tree_root, timestamp, nonce):
        # Instantiates object from passed values
        self.transactions = transactions  # MerkleTree object
        self.previous_header_hash = previous_header_hash  # Previous hash in string
        self.hash_tree_root = hash_tree_root  # tree root in bytes
        self.timestamp = timestamp  # unix time in string
        self.nonce = nonce  # nonce in int

    def header_hash(self):
        # Creates header value
        header_joined = binascii.hexlify(
            self.hash_tree_root).decode() + str(self.timestamp) + str(self.nonce)
        if self.previous_header_hash is not None:
            header_joined = self.previous_header_hash + header_joined
        # Double hashes the header value, coz bitcoin does the same
        m = hashlib.sha256()
        m.update(header_joined.encode())
        round1 = m.digest()
        m = hashlib.sha256()
        m.update(round1)
        return m.digest()


class BlockChain:
    chain = dict()
    # Last_hash is the last header hash value in the chain
    TARGET = b"\x00\x00\x0f\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"

    def add(self, block):
        # Checks if block is valid before adding
        if self.validate(block):
            self.chain[binascii.hexlify(block.header_hash()).decode()] = block
            return True
        else:
            return False

    def validate(self, block):
        if len(self.chain) > 0:
            # Checks for previous header and target value
            check_previous_header = block.previous_header_hash in self.chain and block.previous_header_hash is not None
            check_target = block.header_hash() < self.TARGET
            # print(check_previous_header, check_target)
            return check_previous_header and check_target
        else:
            # If Genesis block, there is no need to check for the last hash value
            return block.header_hash() < self.TARGET

    def resolve(self):
        for hash_value in self.chain:
            if self.chain[hash_value].previous_header_hash == None:
                # Find the genesis block's hash value
                genesis_hash_value = hash_value
                break
        # Create a new chain
        cleaned_chain = dict()
        # Start DP function
        cleaned_keys = self.resolve_DP(genesis_hash_value, 0, [genesis_hash_value])[1]
        # Recreates chain based on output of DP function
        for i in self.chain:
            if i in cleaned_keys:
                cleaned_chain[i] = self.chain[i]
        self.chain = copy.deepcopy(cleaned_chain)

    def resolve_DP(self, hash_check, score, cleared_hashes):
        # Assuming this is the last block in the chain, it first saves itself to the list
        list_of_linked_hashes = [(score, cleared_hashes)]
        # Scans the chain for a block with previous_header of the header of the previous block that called the DP
        for hash_value in self.chain:
            if self.chain[hash_value].previous_header_hash == hash_check:
                new_cleared_hashes = copy.deepcopy(cleared_hashes)
                new_cleared_hashes.append(hash_value)
                # Increase score and list of cleared_hashes whenever the DP is called
                list_of_linked_hashes.append(self.resolve_DP(hash_value, score + 1, new_cleared_hashes))
        # Scans the list_of_linked_hashes and only return the longest chain
        highest_score = 0
        for i in list_of_linked_hashes:
            if i[0] > highest_score:
                highest_score = i[0]
        for i in list_of_linked_hashes:
            if i[0] == highest_score:
                return i

    def __str__(self):
        reply = "-----------------\nThere are {} blocks in the blockchain\n\n".format(
            len(self.chain))
        for count, i in enumerate(self.chain):
            if count == 0:
                reply += "Genesis Block \t"
            else:
                reply += "Block {} \t".format(str(count).zfill(5))
            reply += "\tHeader: {}\tPrev_header: {}\n".format(
                str(i), str(self.chain[i].previous_header_hash))
        return reply


# Test

# Chreate blockchain
blockchain = BlockChain()

# Genesis block
merkletree = MerkleTree()
for i in range(100):
    merkletree.add(random.randint(100, 1000))
merkletree.build()
current_time = str(time.time())
for nonce in range(10000000):
    block = Block(merkletree, None, merkletree.get_root(), current_time, nonce)
    # If the add is successful, stop loop
    if blockchain.add(block):
        break
print(blockchain)

# Other blocks (non-linear)
for i in range(6):
    merkletree = MerkleTree()
    for i in range(100):
        merkletree.add(random.randint(100, 1000))
    merkletree.build()
    current_time = str(time.time())
    last_hash = random.choice(
        list(blockchain.chain.keys()))
    for nonce in range(10000000):
        block = Block(merkletree, last_hash,
                      merkletree.get_root(), current_time, nonce)
        if blockchain.add(block):
            # If the add is successful, stop loop
            break
    print(blockchain)

blockchain.resolve()
print("Done resolve")
print(blockchain)
