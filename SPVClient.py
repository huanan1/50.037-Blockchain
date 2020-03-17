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
        print('miner.py -p <port> -i <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('miner.py -p <port> -i <inputfile of list of IPs of other miners> -w <hashed public key of SPVClient>')
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
        self.balance = 0

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
    if request.headers['Content-Type'] == 'application/json':
        # Receive data regarding transaction
        json_received = request.json
        transaction_data = json.loads(json_received)
        print(transaction_data)

        transaction = SPVClient.create_transaction(
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
#TODO: Check for this and createTransaction!!!!!!!!!!!!!!
# @app.route('/send_transaction')
# def request_send_transaction():
#     receiver_public_key = request.args.get('receiver', '')
#     amount = request.args.get('amount', '')
#     new_transaction = Transaction(
#         PUBLIC_KEY, receiver_public_key, int(amount), sender_pk=PRIVATE_KEY)
#     # broadcast to all known miners
#     # print(new_transaction)
#     # data = pickle.dumps(new_transaction, protocol=2)

#     for miner in LIST_OF_MINER_IP:
#         not_sent = True
#         # execute post request to broadcast transaction
#         while not_sent:
#             try:
#                 requests.post(
#                     url="http://" + miner + "/transaction",
#                     data=new_transaction.to_json()
#                 )
#                 not_sent = False
#             except:
#                 time.sleep(0.1)
#     not_sent = True
#     while not_sent:
#         try:
#             requests.post(
#                 url="http://127.0.0.1:" + MY_PORT + "/transaction",
#                 data=new_transaction.to_json()
#             )
#             not_sent = False
#         except:
#             time.sleep(0.1)
#     return jsonify(new_transaction.to_json())


@app.route('/verify_transaction/<txid>', methods=['GET'])
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
    print(entry)
    for i in proof_string:
        if i == "None":
            proof_bytes.append(None)
        else:
            proof_bytes.append([i[0], binascii.unhexlify(bytes(i[1], 'utf-8'))])
    root_bytes = binascii.unhexlify(bytes(response["root"], 'utf-8'))
    print(entry, proof_bytes, root_bytes)
    verify = verify_proof(entry, proof_bytes, root_bytes)
    if verify:
        # # TODO check if full txn in entry has the same TXID
        # if Transaction.txid in entry:
        #     print("Entry has the same TXID.")
        # else:
        #     print("Entry and TXID do not match.")
 
        # # TODO Check if the root is actually in blockchain by comapring if the hashed header is in the cleaned_keys
        # def resolve(self):
        # if len(self.chain) > 0:
        #     longest_chain_length = 0
        #     for hash_value in self.chain:
        #         if self.chain[hash_value].previous_header_hash == None:
        #             # Find the genesis block's hash value
        #             genesis_hash_value = hash_value
        #             # Start DP function
        #             temp_cleaned_keys = self.resolve_DP(
        #                 genesis_hash_value, 0, [genesis_hash_value])[1]
        #             if len(temp_cleaned_keys) > longest_chain_length:
        #                 self.cleaned_keys = copy.deepcopy(temp_cleaned_keys)
        #                 longest_chain_length = len(temp_cleaned_keys)
        #     try:
        #         self.last_hash = self.cleaned_keys[-1]
        #     except IndexError:
        #         self.last_hash = None

        #     dropped_blocks = self.find_dropped_blocks()
        #     for _, block in dropped_blocks.items():
        #         rebroadcasted = False
        #         while not rebroadcasted:
        #             # retry rebroadcasting until it succeeds
        #             rebroadcasted = self.rebroadcast_transactions(block)




        reply = {"Confirmations": 5, "Block_header": "Blah blah"}
        return jsonify(reply)
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
