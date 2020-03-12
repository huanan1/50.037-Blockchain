import ecdsa
from ecdsa import SigningKey
from transaction import Transaction
from blockchain import BlockChain, Block
from merkle_tree import verify_proof

import time

class SPVClient:
    '''
    Each SPVClient acts as a wallet, and should have a private and public key.
    The SPVClient should be able to store all the headers of the blockchain. 
    It can also receive transactions and verify them.
    The SPVClient should also be able to send transactions.
    '''

    def __init__(self, node_id = ''):
        # List to store all the block headers.
        self.block_headers = []

        # To identify each SPVClient and to communicate with the other SPVClients.
        self.node_id = node_id

        # Balance left in the wallet.
        self.balance = 0

        # Public key of the wallet to check privte key for verification.
        self.public_key = None

        # Private key of the wallet to sign outgoing transactions.
        self.private_key = None

    def create_keys(self):
        # Create the private and pulic keys for SPVClient.
        sender = ecdsa.SigningKey.generate()
        sendervk = sender.get_verifying_key()
        return sender, sendervk

    def associate_keys(self):
        # Associate the key pair created for SPVClient.
        private_key, public_key = self.create_keys()
        self.private_key = private_key
        self.public_key = public_key
        return private_key, public_key

    def store_keys(self):
        # Creates a new txt file to save the key pairs into for each SPVClient.
        if self.private_key is not None and self.public_key is not None:
            try:
                with open('wallet-{}.txt'.format(self.node_id), 'w') as f:
                    f.write((self.public_key.to_string().hex()))
                    f.write('\n')
                    f.write((self.private_key.to_string().hex()))
                return True

            # Throws an error when key pairs are not able to be saved.    
            except Exception as E:
                print('Wallet saving failed!')
                print(E)
                return False

    def receive_block_headers(self, BlockChain):
        # Get all the block headers from BlockChain class
        for headers in BlockChain.cleaned_keys:
            self.block_headers.append(headers.to_json()) 
        return self.block_headers

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        trans = Transaction.new(sender=self.pubkey, receiver=receiver,
                                amount=amount, privkey=self.privkey,
                                comment=comment)
        tx_json = trans.to_json()
        msg = "t" + json.dumps({"tx_json": tx_json})
        self.broadcast_message(msg)
        return trans

    def add_transaction(self, tx_json):
        """Add transaction to the pool of transactions"""
        recv_tx = Transaction.from_json(tx_json)
        if not recv_tx.verify():
            raise Exception("New transaction failed signature verification.")
        if self.pubkey not in [recv_tx.sender, recv_tx.receiver]:
            # Transaction does not concern us, discard it
            return
        tx_hash = algo.hash1(tx_json)
        self._trans_lock.acquire()
        try:
            self._hash_transactions_map[tx_hash] = tx_json
        finally:
            self._trans_lock.release()

    def add_block_header(self, header):
        """Add block header to dictionary"""
        header_hash = algo.hash1_dic(header)
        if header_hash >= Block.TARGET:
            raise Exception("Invalid block header hash.")
        self._blkheader_lock.acquire()
        try:
            if header["prev_hash"] not in self._hash_blkheader_map:
                raise Exception("Previous block does not exist.")
            self._hash_blkheader_map[header_hash] = header
        finally:
            self._blkheader_lock.release()

    def request_balance(self):
        """Request balance from network"""
        req = "x" + json.dumps({"identifier": self.pubkey})
        replies = self.broadcast_request(req)
        return int(SPVClient._process_replies(replies))

    def verify_transaction_proof(self, tx_hash):
        """Verify that transaction is in blockchain"""
        req = "r" + json.dumps({"tx_hash": tx_hash})
        replies = self.broadcast_request(req)
        valid_reply = SPVClient._process_replies(replies)
        blk_hash = valid_reply["blk_hash"]
        proof = valid_reply["proof"]
        last_blk_hash = valid_reply["last_blk_hash"]
        # Transaction not in blockchain
        if proof is None:
            return False
        # Assume majority reply is not lying and that two hash checks
        # are sufficient (may not be true IRL)
        self._blkheader_lock.acquire()
        self._trans_lock.acquire()
        try:
            if (blk_hash not in self._hash_blkheader_map
                    or last_blk_hash not in self._hash_blkheader_map):
                return False
            tx_json = self._hash_transactions_map[tx_hash]
            blk_header = self._hash_blkheader_map[blk_hash]
            if not verify_proof(tx_json, proof, blk_header["root"]):
                # Potential eclipse attack
                raise Exception("Transaction proof verification failed.")
        finally:
            self._blkheader_lock.release()
            self._trans_lock.release()
        return True

    def query_transaction(self, block, transaction):
        presence = (transaction.to_json()).encode()
        print(verify_proof(presence, block.get_proof(transaction), block.get_root()))