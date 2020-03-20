from blockchain import BlockChain, Block, Ledger
import copy
import time
from transaction import Transaction
from merkle_tree import MerkleTree
import json
import ecdsa

class Miner:
    def __init__(self, blockchain, public_key=None):
        self.blockchain = copy.deepcopy(blockchain)
        self.nonce = 0
        self.current_time = str(time.time())
        self.public_key = public_key

    def mine(self, merkletree, ledger):
        block = Block(merkletree, self.blockchain.last_hash,
                      merkletree.get_root(), self.current_time, self.nonce, ledger)

        if self.blockchain.add(block):
            # If the add is successful, reset
            self.reset_new_mine()
            # print(MY_IP)
            return True
        # Increase nonce everytime the mine fails
        self.nonce += 1
        return False

    def mine_from_old_block(self, merkletree, ledger, block_hash):
        block = Block(merkletree, block_hash, merkletree.get_root(), 
                self.current_time, self.nonce, ledger)
        
        if self.blockchain.add(block):
            # If the add is successful, reset
            self.reset_new_mine()
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
    
    def create_merkle(self, transaction_queue, tx_to_ignore=None):
    #### not sure how to get the blockchain object here
        block = self.blockchain.last_block()
        if block is None:
            ledger = Ledger()
            # print("ledger for genesis block")
        else:
            ledger = block.ledger
            # print("ledger for non-genesis block: " + json.dumps(block.ledger.balance))
        list_of_raw_transactions = []
        list_of_validated_transactions = []
        while not transaction_queue.empty():
            list_of_raw_transactions.append(
                transaction_queue.get())
            # print("list of raw transactions: " + str(list_of_raw_transactions))
        
        for transaction in list_of_raw_transactions:
            # remove tx_to_ignore from transaction queue
            if tx_to_ignore is not None and transaction in tx_to_ignore:
                print(f"ignoring transaction: {transaction}")
            elif ledger.verify_transaction(transaction, list_of_validated_transactions, block.transactions.leaf_set, block.previous_header_hash):
                list_of_validated_transactions.append(transaction)
                # print("list of validated transactions: " +str(list_of_validated_transactions))
        merkletree = MerkleTree()
        ### CHECK SENDER
        sender = ecdsa.SigningKey.generate()
        sender_vk = sender.get_verifying_key()
        merkletree.add(Transaction(sender_vk,self.public_key,100,sender_pk=sender).to_json())
        ledger.coinbase_transaction(self.public_key)
        # print("merkel tree has been created" + json.dumps(ledger.balance))

        for transaction in list_of_validated_transactions:
            merkletree.add(transaction.to_json())
        merkletree.build()
        return merkletree, ledger
