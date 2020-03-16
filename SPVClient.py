import ecdsa
from ecdsa import SigningKey
from transaction import Transaction
from blockchain import BlockChain, Block
from merkle_tree import verify_proof
from flask import Flask, request
from multiprocessing import Process, Queue

import time
import getopt
import sys
import pickle
import json
import requests
import random

app = Flask(__name__)
user = None
block_header_queue = Queue()

# Parsing arguments when entered via CLI
def parse_arguments(argv):
    inputfile = ''
    list_of_miner_ip = []
    wallet_arg=None
    try:
        opts, args = getopt.getopt(
            argv, "hp:i:w:", ["port=", "iminerfile=", "wallet="])
    # Only port and input is mandatory
    except getopt.GetoptError:
        print('miner.py -p <port> -i <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('miner.py -p <port> -i <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
            sys.exit()

        elif opt in ("-p", "--port"):
            my_port = arg

        elif opt in ("-i", "--iminerfile"):
            inputfile = arg
            f = open(inputfile, "r")
            for line in f:
                list_of_miner_ip.append(line)

        elif opt in ("-w", "--wallet"):
            wallet_arg = arg

    return my_port, list_of_miner_ip, wallet_arg

MY_PORT, LIST_OF_MINER_IP, WALLET = parse_arguments(sys.argv[1:])

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
        self.PRIVATE_KEY = None

    def create_keys(self):
        # Create the private and pulic keys for SPVClient.
        sender = ecdsa.SigningKey.generate()
        sendervk = sender.get_verifying_key()
        return sender, sendervk

    def associate_keys(self):
        # Associate the key pair created for SPVClient.
        private_key, public_key = self.create_keys()
        self.PRIVATE_KEY = private_key
        self.PUBLIC_KEY = public_key
        return private_key, public_key

    def receive_block_headers(self, BlockChain):
        # Get all the block headers from BlockChain class
        for headers in BlockChain.cleaned_keys:
            self.block_headers.append(headers.to_json()) 
        return self.block_headers

    def create_transaction(self, receiver, amount, comment):
        # Create new transaction and sign with private key
        new_txn = Transaction.new(sender=self.PUBLIC_KEY, receiver=receiver,
                                amount=amount, comment=comment)
        new_txn.sign(self.PRIVATE_KEY)
        return new_txn

    #TODO: Is it this part need to accept prev header and current header?
    def check_balance(self, ledger):
        balance = getBalance(self.PUBLIC_KEY)
        return balance


@app.route('/')
def homepage():
    return ""


# For a single SPVClient
@app.route('/login/<pub>/<priv>')
def login(pub, priv):
    # temporary
    global user
    user = SPVClient(privatekey=priv, publickey=pub)
    return homepage()


@app.route('/block_header', methods=['POST'])
def new_block_header_network():
    new_block_header = pickle.loads(request.get_data())
    block_header_queue.put(new_block_header)
    return ""


# To broadcast to all miners when transaction is created
@app.route('/createTransaction', methods=['POST'])
def createTransaction():
    if user is None:
        return "Please login"

    if request.headers['Content-Type'] == 'application/json':
        # Receive data regarding transaction
        json_received = request.json
        transaction_data = json.loads(json_received)
        print(transaction_data)

        transaction = user.createTransaction(
                        receivervk=transaction_data["recv"],
                        amount=transaction_data["Amount"],
                        comment=transaction_data["Comment"]
                        )

        # broadcast to all known miners
        for miner in LIST_OF_MINER_IP:
            # execute post request to broadcast transaction
            broadcast_endpoint = miner + "/newTransaction"
            requests.post(
                url=broadcast_endpoint,
                json=transaction.to_json()
            )

    else:
        return 'wrong format of transaction sent'


# To check the latest ledger frmo latest block.
#TODO: Update this part when ledger component is done!!
@app.route('/clientCheckBalance', methods=['GET'])
def clientCheckBalance():
    return user.check_balance(Ledger)

@app.route('/verify_transaction', methods=['POST'])
def verify_Transaction():
    data = request.data.decode()
    # requests.post(url, headers=headers, data=
    miner_ip = random.choice(LIST_OF_MINER_IP)
    requests.post("http://"+ miner_ip + "/verify_transaction_from_spv", data=data)
    return None
    

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=MY_PORT)
