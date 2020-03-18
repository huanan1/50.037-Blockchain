import ecdsa
from ecdsa import SigningKey
from transaction import Transaction
from blockchain import BlockChain, Block
from merkle_tree import verify_proof
from flask import Flask, request, jsonify
from multiprocessing import Process, Queue
from merkle_tree import verify_proof
from miner import verify_transaction_from_spv

import binascii
import time
import getopt
import sys
import pickle
import json
import requests
import random
import copy

app = Flask(__name__)

# Parsing arguments when entered via CLI
def parse_arguments(argv):
    inputfile = ''
    list_of_miner_ip = []
    private_key=None
    try:
        opts, args = getopt.getopt(
            argv, "hp:m:w:", ["port=", "iminerfile=", "wallet="])
    # Only port and input is mandatory
    except getopt.GetoptError:
        print('SPVClient.py -p <port> -m <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('SPVClient.py -p <port> -m <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
            sys.exit()

        elif opt in ("-p", "--port"):
            my_port = arg

        elif opt in ("-m", "--iminerfile"):
            inputfile = arg
            f = open(inputfile, "r")
            for line in f:
                list_of_miner_ip.append(line)

        elif opt in ("-w", "--wallet"):
            if arg != "NO_WALLET":
                private_key = arg

    return my_port, list_of_miner_ip, private_key

MY_PORT, LIST_OF_MINER_IP, PRIVATE_KEY = parse_arguments(sys.argv[1:])

if PRIVATE_KEY is None:
    PRIVATE_KEY = ecdsa.SigningKey.generate()
PUBLIC_KEY = PRIVATE_KEY.get_verifying_key()
PUBLIC_KEY_STRING = PUBLIC_KEY.to_string().hex()
print(PUBLIC_KEY_STRING)

user = None
block_header_queue = Queue()
transaction_queue = Queue()
blockchain_request_queue = Queue()
blockchain_reply_queue = Queue()

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

    def create_transaction(self, receiver, amount, comment):
        # Create new transaction and sign with private key
        new_txn = Transaction.new(sender=self.PUBLIC_KEY, receiver=receiver, amount=amount, comment=comment)
        new_txn.sign(self.PRIVATE_KEY)
        return new_txn

    # def grab_all_transactions(self, chain):
    #     '''
    #     Keeps a list of all the transactions broadcasted in the network
    #     '''
    #     list_of_all_txns = []
    #     try:
    #         transaction = Transaction.from_json(transaction)
    #         for broadcasted_transaction in list_of_all_txns: 
    #             if broadcasted_transaction not in list_of_all_txns:
    #                 list_of_all_txns.append(transaction)
    #     except:
    #         pass
    #     return list_of_all_txns

@app.route('/block_header', methods=['POST'])
def new_block_header_network():
    new_block_header = pickle.loads(request.get_data())
    block_header_queue.put(new_block_header)
    return ""

# To broadcast to all miners when transaction is created
@app.route('/createTransaction', methods=['POST'])
def createTransaction():
    receiver_public_key = request.args.get('receiver', '')
    amount = request.args.get('amount', '')
    new_transaction = Transaction(
        PUBLIC_KEY, receiver_public_key, int(amount), sender_pk=PRIVATE_KEY)

    # broadcast to all known miners
    for miner in LIST_OF_MINER_IP:
        not_sent = True
        # execute post request to broadcast transaction
        while not_sent:
            try:
                requests.post(
                    url="http://" + miner + "/transaction",
                    data=new_transaction.to_json()
                )
                not_sent = False
            except:
                time.sleep(0.1)
    return jsonify(new_transaction.to_json())


@app.route('/spv_verify_transaction/<txid>', methods=['GET'])
def verify_Transaction(txid):
    # requests.post(url, headers=headers, data=
    miner_ip = random.choice(LIST_OF_MINER_IP)
    # print(miner_ip, txid)
    # try:
    response = json.loads(requests.post("http://"+ miner_ip + "/verify_transaction_from_spv", data=txid).text)
    print(response)
    entry = response["entry"]
    proof_string = response["proof"]
    proof_bytes = []
    for i in proof_string:
        if i == "None":
            proof_bytes.append(None)
        else:
            proof_bytes.append([i[0], binascii.unhexlify(bytes(i[1], 'utf-8'))])
    root_bytes = binascii.unhexlify(bytes(response["root"], 'utf-8'))
    print(entry, proof_bytes, root_bytes)
    verify = verify_proof(entry, proof_bytes, root_bytes)
    if verify:
        # TODO check if response has the same TXID
        if entry["txid"] == txid:
            return ("Received transaction ID same as sent TXID.")
        else:
            return ("Received transaction ID does not match sent TXID.")
 
        #TODO Check if the root is actually in blockchain by comparing if the hashed header is in the cleaned_keys
        #TODO We got the dictonary of block headers. Look through this dictionary for the block header using the specific root returned by miner.
        #TODO After locating the block header, check the cleaned_keys and return the position of the block header in cleaned keys.
        blockchain_request_queue.put(None)
        block_headers = blockchain_reply_queue.get()[0]
        root = root_bytes.decode('utf-8') # Returns the root in string format
        for blk_header in block_headers:
            if blk_header.hash_tree_root == root: # Finds corresponding block header
                blk_header_temp = blk_header
                print("Block header with transaction found.")
                for count, i in enumerate(BlockChain.cleaned_keys):
                    if blk_header_temp in BlockChain.cleaned_keys: # If corresponding block header is in clean_keys list...
                        reply = {"Position in cleaned_keys": (len(BlockChain.cleaned_keys) - count)} # Returns the position of block header in cleaned_keys
                        return jsonify(reply)
            else:
                return jsonify("No block headers found.")
    # finally:
    return jsonify("TXID not found")


@app.route('/account_balance/<public_key>')
def request_account_balance(public_key):
    miner_ip = random.choice(LIST_OF_MINER_IP)
    try:
        response = json.loads(requests.get("http://"+ miner_ip + "/account_balance/" + public_key).text)
        return jsonify(response)
    except:
        return "Cannot find account"

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=MY_PORT)
