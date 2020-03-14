from merkle_tree import MerkleTree
import hashlib
import random
import time
import binascii
import copy
import requests
from transaction import Transaction
import pickle


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

class SPVBlock:
    def __init__(self, block):
        # Instantiates object from passed values
        self.header_hash = block.header_hash()
        self.prev_header_hash = block.prev_header_hash
        # TODO add ledger
        self.ledger = None

class BlockChain:
    # chain is a dictionary, key is hash header, value is the header metadata of blocks
    chain = dict()
    TARGET = b"\x00\x00\x0f\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"
    last_hash = None
    # Cleaned keys is an ordered list of all the header hashes, only updated on BlockChain.resolve() call
    cleaned_keys = []
    # Target average time in seconds
    target_average_time = 3.5
    # difficulty_constant not used yet
    difficulty_constant = None
    # difficulty_interval is the difficulty check per X number of blocks
    difficulty_interval = 5
    # difficulty multiplier, ensures difficulty change is linear
    difficulty_multiplier = 1
    # network cached blocks contain blocks that are rejected, key is prev hash header, value is block
    network_cached_blocks = dict()

    def __init__(self, miner_ips):
            self.miner_ips = miner_ips

    def network_add(self, block):
        # check for genesis block
        if block.previous_header_hash is None:
            # check that number of transactions is 1 in genesis block
            if len(block.transactions.leaf_set) != 1:
                print("genesis block should have only one transaction.")
                return False
            coinbase_tx = Transaction.from_json(block.transactions.leaf_set[0])
            if coinbase_tx.amount != 100:
                print("coinbase transaction should have amount == 100")
                return False
            self.chain[binascii.hexlify(block.header_hash()).decode()] = block
            return True

        # check again that incoming block has prev hash and target < nonce (in case malicious miner publishing invalid blocks)
        check1 = self.validate(block)
        # check if transactions are valid (sender has enough money, and TXIDs have not appeared in the previous blocks)
        check2 = self.verify_transactions(block.transactions.leaf_set, block.previous_header_hash)

        if check1 and check2:
            header_hash = binascii.hexlify(block.header_hash()).decode()
            self.chain[header_hash] = block
            # check rejected blocks
            if header_hash in self.network_cached_blocks:
                next_block = self.network_cached_blocks.get(header_hash)
                if self.network_add(next_block):
                    # delete from rejected list if block added to blockchain
                    del self.network_cached_blocks[header_hash]
            return True
        else:
            self.network_cached_blocks[binascii.hexlify(block.header_hash()).decode()] = block
            return False

    def verify_transactions(self, transactions, prev_header_hash):
        self.resolve() # ensure cleaned_keys updated
        # obtain blocks in blockchain uptil block with previous header hash
        chain_uptil_prev = self.cleaned_keys[:self.cleaned_keys.index(prev_header_hash)+1]
        
        # convert transactions to Transaction objects
        for i, transaction in enumerate(transactions):
            transactions[i] = Transaction.from_json(transaction)

        # check coinbase transaction amount
        if transactions[0].amount != 100:
            return False
        
        # loop through all previous blocks
        for hash in reversed(chain_uptil_prev):
            prev_hash = prev_header_hash
            prev_merkle_tree = self.chain[prev_hash].transactions
            # loop through transactions in prev block
            for i, transaction in enumerate(transactions[1:]):
                # check if transaction has appeared in previous blocks
                if prev_merkle_tree.get_proof(transaction) != []:
                    # transaction repeated
                    print(f"this transaction appeared before. Transaction: {transaction}")
                    return False
        
        for transaction in transactions:
            # check if transaction was really sent by the sender
            transaction.validate(transaction.sig)
            # check if sender has enough money
            # if Ledger.get_balance(transaction.sender) - transaction.amount < 0:
                # return False
        return True

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
            check_previous_header = block.previous_header_hash in self.chain or block.previous_header_hash is None
            check_target = block.header_hash() < self.TARGET
            # print(check_previous_header, check_target)
            return check_previous_header and check_target
        else:
            # If Genesis block, there is no need to check for the last hash value
            return block.header_hash() < self.TARGET

    def rebroadcast_transactions(self, block):
        '''rebroadcast transactions from dropped blocks'''
        transactions = block.transactions.leaf_set
        # convert transactions to Transaction objects
        for i, transaction in enumerate(transactions):
            transactions[i] = Transaction.from_json(transaction)

        not_sent = True
        for miner_ip in self.miner_ips:
            for transaction in transactions:
                data = pickle.dumps(transaction, protocol=2)
                while not_sent:
                    try:
                        requests.post("http://"+miner_ip +
                                    "/transaction", data=data)
                        not_sent = False
                    except:
                        time.sleep(0.1)
        return True

    def find_dropped_blocks(self):
        dropped_blocks = dict()
        for hash_value in self.chain:
            if hash_value not in self.cleaned_keys:
                dropped_blocks[hash_value] = self.chain[hash_value]
        return dropped_blocks

    def resolve(self):
        if len(self.chain) > 0:
            longest_chain_length = 0
            for hash_value in self.chain:
                if self.chain[hash_value].previous_header_hash == None:
                    # Find the genesis block's hash value
                    genesis_hash_value = hash_value
                    # Start DP function
                    temp_cleaned_keys = self.resolve_DP(
                        genesis_hash_value, 0, [genesis_hash_value])[1]
                    if len(temp_cleaned_keys) > longest_chain_length:
                        self.cleaned_keys = copy.deepcopy(temp_cleaned_keys)
                        longest_chain_length = len(temp_cleaned_keys)
            try:
                self.last_hash = self.cleaned_keys[-1]
            except IndexError:
                self.last_hash = None

            dropped_blocks = self.find_dropped_blocks()
            for _, block in dropped_blocks.items():
                rebroadcasted = False
                while not rebroadcasted:
                    # retry rebroadcasting until it succeeds
                    rebroadcasted = self.rebroadcast_transactions(block)
                

    def resolve_DP(self, hash_check, score, cleared_hashes):
        # Assuming this is the last block in the chain, it first saves itself to the list
        list_of_linked_hashes = [(score, cleared_hashes)]
        # Scans the chain for a block with previous_header of the header of the previous block that called the DP
        for hash_value in self.chain:
            if self.chain[hash_value].previous_header_hash == hash_check:
                new_cleared_hashes = copy.deepcopy(cleared_hashes)
                new_cleared_hashes.append(hash_value)
                # Increase score and list of cleared_hashes whenever the DP is called
                list_of_linked_hashes.append(self.resolve_DP(
                    hash_value, score + 1, new_cleared_hashes))
        # Scans the list_of_linked_hashes and only return the longest chain
        highest_score = 0
        for i in list_of_linked_hashes:
            if i[0] > highest_score:
                highest_score = i[0]
        for i in list_of_linked_hashes:
            if i[0] == highest_score:
                return i

    # Returns the last block in the chain
    def last_block(self):
        self.resolve()
        if self.last_hash is not None:
            return self.chain[self.last_hash]
        else:
            return None

    def __str__(self):
        reply = "-----------------\nThere are {} blocks in the blockchain\n\n".format(
            len(self.chain))
        for count, i in enumerate(self.chain):
            reply += "Header: {}\tPrev_header: {}\n".format(
                str(i), str(self.chain[i].previous_header_hash))
        reply+="\n~~~\n"
        reply += "The longest chain is {} blocks\n".format(
            len(self.cleaned_keys))
        for count, i in enumerate(self.cleaned_keys):
            reply += i[:10] + " -> "
        reply = reply[:-4]
        return reply


# Test
def main():
    # Create blockchain
    blockchain = BlockChain([])

    # Genesis block
    merkletree = MerkleTree()
    for i in range(100):
        merkletree.add(random.randint(100, 1000))
    merkletree.build()
    current_time = str(time.time())
    for nonce in range(10000000):
        block = Block(merkletree, None, merkletree.get_root(),
                      current_time, nonce)
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

def test_network_add():
    # Create blockchain
    blockchain = BlockChain([])

    from ecdsa import SigningKey
    sender = SigningKey.generate()
    receiver = SigningKey.generate()

    # Genesis block
    merkletree = MerkleTree()
    for i in range(1):
        merkletree.add(Transaction(sender, sender, 100).to_json())
    merkletree.build()
    current_time = str(time.time())
    for nonce in range(10000000):
        block = Block(merkletree, None, merkletree.get_root(),
                      current_time, nonce)
        # If the add is successful, stop loop
        if blockchain.validate(block):
            blockchain.network_add(block)
            break
    print(blockchain)

    # Other blocks (non-linear)
    for i in range(2):
        merkletree = MerkleTree()
        for i in range(5):
            if i == 0: merkletree.add(Transaction(sender, sender, 100).to_json())
            else:
                merkletree.add(Transaction(sender, receiver, random.randint(100,1000)).to_json())
        merkletree.build()
        current_time = str(time.time())
        last_hash = random.choice(
            list(blockchain.chain.keys()))
        for nonce in range(10000000):
            block = Block(merkletree, last_hash,
                          merkletree.get_root(), current_time, nonce)
            if blockchain.validate(block):
                blockchain.network_add(block)
                # If the add is successful, stop loop
                break
        print(blockchain)

    blockchain.resolve()
    print("Done resolve")
    print(blockchain)


if __name__ == '__main__':
    test_network_add()