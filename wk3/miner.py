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
            self.new_block(self.blockchain.chain)
            print(MY_IP)
            return True
        self.nonce += 1
        # print(block.header_hash())
        return False

    def new_block(self, chain):
        self.nonce = 0
        self.current_time = str(time.time())
        self.blockchain.chain = copy.deepcopy(chain)
        self.blockchain.resolve()
        # need to include proper checks when new block is added
        # check should be in here or resolve?
        self.blockchain.difficulty_adjust()

# Random Merkletree
def create_sample_merkle():
    merkletree = MerkleTree()
    for i in range(100):
        merkletree.add(random.randint(100, 1000))
    merkletree.build()
    return merkletree

def start_mining(queue):
    merkletree = create_sample_merkle()
    blockchain = BlockChain()
    miner = Miner(blockchain)

    while queue.empty():
        miner_status = False
        while not miner_status:
            miner_status = miner.mine(merkletree)
            # Right now, each miner copies the entire chain from another miner... maybe do block?
            if miner_status:
                pass
                # todo Broadcast to network
        print(miner.blockchain)

    print("DONE")

queue = Queue()

@app.route('/')
def hello_world():
    queue.put("a")
    return 'Hello, World!'

if __name__ == '__main__':
    p = Process(target=start_mining, args=(queue,))
    p.start()
    app.run(debug=True, use_reloader=False, port=MY_PORT)
    p.join()

# merkletree = create_sample_merkle()
# blockchain = BlockChain()
# miner1, miner2, miner3 = Miner(blockchain), Miner(
#     blockchain), Miner(blockchain)
# while True:
#     miner1_status, miner2_status, miner3_status = False, False, False
#     while not (miner1_status or miner2_status or miner3_status):
#         miner1_status = miner1.mine(merkletree)
#         miner2_status = miner2.mine(merkletree)
#         miner3_status = miner3.mine(merkletree)
#         # Right now, each miner copies the entire chain from another miner... maybe do block?
#         if miner1_status:
#             miner2.new_block(miner1.blockchain.chain)
#             miner3.new_block(miner1.blockchain.chain)
#         elif miner2_status:
#             miner1.new_block(miner2.blockchain.chain)
#             miner3.new_block(miner2.blockchain.chain)
#         elif miner3_status:
#             miner1.new_block(miner3.blockchain.chain)
#             miner2.new_block(miner3.blockchain.chain)
#     print(miner1.blockchain)
