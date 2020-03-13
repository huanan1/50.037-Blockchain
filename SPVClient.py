import ecdsa
from ecdsa import SigningKey
from transaction import Transaction
from blockchain import BlockChain, Block
from merkle_tree import verify_proof

import time
import getopt
import sys

class SPVClient:
    '''
    Each SPVClient acts as a wallet, and should have a private and public key.
    The SPVClient should be able to store all the headers of the blockchain. 
    It can also receive transactions and verify them.
    The SPVClient should also be able to send transactions.
    '''

    def __init__(self):
        # List to store all the block headers.
        self.block_headers = []

        # Public key of the wallet to check privte key for verification.
        self.PUBLIC_KEY = None

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
        self.PUBLIC_KEY = public_key
        return private_key, public_key

    def receive_block_headers(self, BlockChain):
        # Get all the block headers from BlockChain class
        for headers in BlockChain.cleaned_keys:
            self.block_headers.append(headers.to_json()) 
        return self.block_headers

    def create_transaction(self, receiver, amount, comment):
        new_txn = Transaction.new(sender=self.pubkey, receiver=receiver,
                                amount=amount, privkey=self.privkey,
                                comment=comment)
        new_txn.sign(self.private_key)
        return new_txn

    #TODO: Get balance from ledger in latest block
    def request_balance(self):
        pass

# Parsing arguments when entered via CLI
def parse_arguments(argv):
    inputfile = ''
    list_of_miner_ip = []
    try:
        opts, args = getopt.getopt(
            argv, "hp:im:w:", ["port=", "iminerfile=", "wallet="])
    # Only port and input is mandatory
    except getopt.GetoptError:
        print('miner.py -p <port> -im <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('miner.py -p <port> -im <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
            sys.exit()

        elif opt in ("-p", "--port"):
            my_port = arg

        elif opt in ("-im", "--iminerfile"):
            inputfile = arg
            f = open(inputfile, "r")
            for line in f:
                list_of_miner_ip.append(line)

        elif opt in ("-w", "--wallet"):
            wallet_arg = arg

    return my_port, list_of_miner_ip, wallet_arg