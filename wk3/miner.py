from blockchain import BlockChain, Block
from transaction import Transaction
from merkle_tree import MerkleTree
import random
import time
import copy


class Miner:

    def __init__(self, blockchain):
        self.blockchain = copy.deepcopy(blockchain)
        self.nonce = 0
        self.current_time = str(time.time())

    def mine(self, merkletree):
        block = Block(merkletree, self.blockchain.last_hash,
                      merkletree.get_root(), self.current_time, self.nonce)
        if self.blockchain.add(block):
            # If the add is successful, reset
            self.new_block(self.blockchain)
            return True
        self.nonce += 1
        # print(block.header_hash())
        return False

    def new_block(self, blockchain):
        self.nonce = 0
        blockchain.resolve()
        self.current_time = str(time.time())
        self.blockchain = copy.deepcopy(blockchain)
        # need to include proper checks


def create_sample_merkle():
    merkletree = MerkleTree()
    for i in range(100):
        merkletree.add(random.randint(100, 1000))
    merkletree.build()
    return merkletree


merkletree = create_sample_merkle()
blockchain = BlockChain()
miner1, miner2, miner3 = Miner(blockchain), Miner(
    blockchain), Miner(blockchain)
while True:
    miner1_status, miner2_status, miner3_status = False, False, False
    while not (miner1_status or miner2_status or miner3_status):
        miner1_status = miner1.mine(merkletree)
        miner2_status = miner2.mine(merkletree)
        miner3_status = miner3.mine(merkletree)
        if miner1_status:
            miner2.new_block(miner1.blockchain)
            miner3.new_block(miner1.blockchain)
        elif miner2_status:
            miner1.new_block(miner2.blockchain)
            miner3.new_block(miner2.blockchain)
        elif miner3_status:
            miner1.new_block(miner3.blockchain)
            miner2.new_block(miner3.blockchain)
    print(miner1.blockchain, miner2.blockchain, miner3.blockchain)
