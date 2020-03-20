from blockchain import Blockchain, Block, Ledger
import time
import copy
from merkle_tree import MerkleTree, verify_proof
from ecdsa import SigningKey
from transaction import Transaction
import binascii

class Miner:
    def __init__(self, blockchain, public_key=None):
        self.blockchain = copy.deepcopy(blockchain)
        self.nonce = 0
        self.current_time = str(time.time())
        self.public_key = public_key
        self.public_key_str = binascii.hexlify(public_key.to_string()).decode()

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

    def create_merkle(self, transaction_queue):
        # print("entered create merkel")
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
        # print("length", len(list_of_raw_transactions))
        for transaction in list_of_raw_transactions:
            # for transaction in TEST_LIST:
            # print("entering verify")
            # TODO: check if transaction makes sense in the ledger
            #if ledger.verify_transaction(transaction, list_of_validated_transactions, block.transactions.leaf_set, block.previous_header_hash, self.blockchain):
            if ledger.verify_transaction(transaction, list_of_validated_transactions, binascii.hexlify(block.header_hash()).decode(), self.blockchain):

                list_of_validated_transactions.append(transaction)
                print("verification complete")
        merkletree = MerkleTree()
        # TODO: Add coinbase TX
        # CHECK SENDER
        coinbase_sender_pk = SigningKey.generate()
        coinbase_sender_vk = coinbase_sender_pk.get_verifying_key()
        merkletree.add(Transaction(coinbase_sender_vk, self.public_key,
                                   100, sender_pk=coinbase_sender_pk).to_json())
        ledger.coinbase_transaction(self.public_key_str)
        # print("merkel tree has been created" + json.dumps(ledger.balance))

        for transaction in list_of_validated_transactions:
            transaction_object = transaction.to_json()
            # print(type(transaction_object))
            merkletree.add(transaction_object)
        merkletree.build()
        # print(merkletree.leaf_set)
        return merkletree, ledger
