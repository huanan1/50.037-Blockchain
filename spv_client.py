import ecdsa
from ecdsa import SigningKey
from transaction import Transaction
from merkle_tree import verify_proof
from flask import Flask, request, jsonify
from merkle_tree import verify_proof
from miner import verify_transaction_from_spv
from spv_block import SPVBlock, SPVBlockChain

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

spv_blockchain = SPVBlockChain()

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
    # print("received block")
    new_block_header = pickle.loads(request.get_data())
    spv_blockchain.network_add(new_block_header)
    return ""

# To broadcast to all miners when transaction is created
@app.route('/send_transaction', methods=['POST'])
def createTransaction():
    receiver_public_key = request.args.get('receiver', '')
    amount = request.args.get('amount', '')
    miner_ip = random.choice(LIST_OF_MINER_IP)
    response = json.loads(requests.get("http://"+ miner_ip + "/account_balance/" + PUBLIC_KEY_STRING).text)
    balance = response["amount"]
    if balance >= int(amount):
        new_transaction = Transaction(
            PUBLIC_KEY, receiver_public_key, int(amount), sender_pk=PRIVATE_KEY)
    else:
        return ("Insufficient balance in account to proceed.")

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
    not_sent = True
    while not_sent:
        try:
            requests.post(
                url="http://127.0.0.1:" + MY_PORT + "/transaction",
                data=new_transaction.to_json()
            )
            not_sent = False
        except:
            time.sleep(0.1)
    return jsonify(new_transaction.to_json())


@app.route('/verify_transaction/<txid>', methods=['GET'])
def verify_Transaction(txid):
    # requests.post(url, headers=headers, data=
    miner_ip = random.choice(LIST_OF_MINER_IP)
    # print(miner_ip, txid)
    try:
        response = json.loads(requests.post("http://"+ miner_ip + "/verify_transaction_from_spv", data=txid).text)
    except:
        return jsonify("TXID not found")
    entry = response["entry"]
    proof_string = response["proof"]
    proof_bytes = []
    for i in proof_string:
        if i == "None":
            proof_bytes.append(None)
        else:
            proof_bytes.append([i[0], binascii.unhexlify(bytes(i[1], 'utf-8'))])
    root_bytes = binascii.unhexlify(bytes(response["root"], 'utf-8'))
    # print(entry, proof_bytes, root_bytes)
    verify = verify_proof(entry, proof_bytes, root_bytes)
    entry_dictionary = json.loads(entry)
    if verify:
        # TODO check if response has the same TXID
        if entry_dictionary["txid"] != txid:
            return ("Received transaction ID does not match sent TXID.")
            
 
        #TODO Check if the root is actually in blockchain by comparing if the hashed header is in the cleaned_keys
        #TODO We got the dictonary of block headers. Look through this dictionary for the block header using the specific root returned by miner.
        #TODO After locating the block header, check the cleaned_keys and return the position of the block header in cleaned keys.
        spv_blockchain.resolve()
        for count, i in enumerate(spv_blockchain.cleaned_keys):
            if spv_blockchain.chain[i].hash_tree_root == root_bytes: # Finds corresponding block header
                # reply = {"Position in cleaned_keys": (len(spv_blockchain.cleaned_keys) - count)} # Returns the position of block header in cleaned_keys
                reply = {"entry": entry, "proof": proof_string, "root": binascii.hexlify(root_bytes).decode(), "verify": True, "confirmations": (len(spv_blockchain.cleaned_keys) - count), "block_header": i}
                return jsonify(reply)
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
