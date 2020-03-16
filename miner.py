from blockchain import Block, BlockChain
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
            self.reset_new_mine()
            # print(MY_IP)
            return True
        # Increase nonce everytime the mine fails
        self.nonce += 1
        return False

    def reset_new_mine(self):
        self.nonce = 0
        self.current_time = str(time.time())
        self.blockchain.resolve()
        # resets after every block is added, both network and locally

    # Called when a new block is received by another miner
    def network_block(self, block):
        # Checks if the n
        if self.blockchain.network_add(block):
            self.reset_new_mine()