from blockchain import BlockChain, Block
from transaction import Transaction
from merkle_tree import MerkleTree
import random
import time
import copy
from flask import Flask
from multiprocessing import Process, Queue

app = Flask(__name__)

MY_IP = "$MY_IP_HERE"
MY_PORT = MY_IP.split(":")[1]
LIST_OF_MINER_IP = "$LIST_OF_MINER_IP_HERE"
# MY_IP will be a single string in the form of "127.0.0.1:5000"
# LIST_OF_MINER_IP will be a list of strings in the form of ["127.0.0.1:5000","127.0.0.1:5001","127.0.0.1:5002"]

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
            self.reset_new_mine()
            print(MY_IP)
            return True
        self.nonce += 1
        # print(block.header_hash())
        return False

    def reset_new_mine(self):
        self.nonce = 0
        self.current_time = str(time.time())
        self.blockchain.resolve()
        # need to include proper checks when new block is added
        # check should be in here or resolve?
        self.blockchain.difficulty_adjust()

    def new_block(self, block):
        self.blockchain.chain.add(block)
        self.reset_new_mine()
        

# Random Merkletree
def create_sample_merkle():
    merkletree = MerkleTree()
    for i in range(100):
        merkletree.add(random.randint(100, 1000))
    merkletree.build()
    return merkletree

def start_mining(block_queue):
    merkletree = create_sample_merkle()
    blockchain = BlockChain()
    miner = Miner(blockchain)
    miner_status = False
    while True:
        miner_status = miner.mine(merkletree)
        # Right now, each miner copies the entire chain from another miner... maybe do block?
        if miner_status:
            # todo Broadcast to network
            print(miner.blockchain)
            pass
        if not block_queue.empty():
            new_block = block_queue.get()
            miner.new_block(new_block)
            print(miner.blockchain)

block_queue = Queue()

@app.route('/block')
def new_block_network():
    block_queue.put("a")

if __name__ == '__main__':
    p = Process(target=start_mining, args=(block_queue,))
    p.start()
    app.run(debug=True, use_reloader=False, port=MY_PORT)
    p.join()