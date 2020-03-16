import random
import time
import copy
import pickle
import requests
import sys
import argparse
import colorama
import binascii
from ecdsa import SigningKey
from flask import Flask, request, jsonify
from multiprocessing import Process, Queue

from blockchain import BlockChain, Block, SPVBlock
from transaction import Transaction
from merkle_tree import MerkleTree
from miner import Miner

'''
Attacker carries out double-spend attack by creating a new fork before the block with a transaction he wants to void
Since attacker has >=51% hashing power, he will eventually have the longer chain which he publishes, causing blocks
on the other fork to be void.

There will be 2 miners in the double-spending demo.
1) Normal miner will mine at half the speed of an attacker (X)
2) When chain reaches 3rd block, attacker publishes transaction from himself to another party
3) Attacker stores that transaction in a list of transactions to ignore so it doesn't get included into his subsequent blocks
4) Attacker starts private fork when transaction is in latest block
5) Attacker publishes private fork when it is longer than current chain

example of run command: python3 double_spend.py --port 25540 --ip_other 127.0.0.1:25541 --color g
'''

app = Flask(__name__)

def color(letter):
    if letter == "g":
        return colorama.Fore.GREEN
    elif letter == "r":
        return colorama.Fore.RED

def create_key():
    private_key = SigningKey.generate()
    return private_key

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run double-spending attack")
    
    parser.add_argument('--port', type=str, help="the port you are listening on. eg. 25540", required=True)
    parser.add_argument('--ip_other', type=str, 
        help="ip address of the other miner eg. 127.0.0.1:25541", required=True)

    parser.add_argument('--attacker', dest='attacker', action="store_true")
    parser.add_argument('--honest', dest='attacker', action="store_false")
    parser.set_defaults(attacker=False)

    parser.add_argument('--color',type=str, default="g")
    parser.add_argument('--private_key',type=str, default=None)

    args = parser.parse_args()
    return args

def broadcast_transaction(transaction):
    not_sent = True
    data = pickle.dumps(transaction, protocol=2)
    while not_sent:
        try:
            request.post("http://" + args.ip_other + 
                        "/transaction", data=data)
            not_sent = False
        except:
            time.sleep(0.1)
    return True

def create_merkle_only_coinbase(sender=SigningKey.generate(), recipient=SigningKey.generate()):
    merkletree = MerkleTree()
    merkletree.add(Transaction(sender, recipient, 100).to_json())
    merkletree.build()
    return merkletree

def start_mining(block_queue, transaction_queue, blockchain_request_queue, blockchain_reply_queue):
    blockchain = BlockChain([args.ip_other])
    miner = Miner(blockchain)
    miner_status = False # whether miner is ready to send
    # variables for double-spending attack
    start_attack = False
    tx_sent = False
    ignore_transactions = []
    private_fork = []
    skip_mine_count = 0
    
    while True:
        merkletree = create_merkle_only_coinbase()
        while True:
            start_attack = len(blockchain.cleaned_keys)>3
            # start_attack = True
            if start_attack and not tx_sent:
                bad_tx = Transaction(private_key,SigningKey.generate(),50,"give me the goods").to_json()
                print("sending transaction...")
                ### broadcast_transaction(bad_tx) # TODO gets stuck here
                print("sent transaction")
                ignore_transactions.append(bad_tx)
                tx_sent = True
            
            if not args.attacker and start_attack:
                if skip_mine_count % 2 == 0:
                    miner_status = miner.mine(merkletree)
                skip_mine_count+=1
            else:
                miner_status = miner.mine(merkletree)

            if miner_status:
                print("at least something mined")

            
        pass


transaction_queue = Queue()

@app.route('/transaction', methods=['POST'])
def new_transaction_network():
    new_transaction = pickle.loads(request.get_data())
    transaction_queue.put(new_transaction)
    return ""


if __name__ == '__main__':
    args = parse_arguments() # access arguments via args.argument
    private_key = create_key() if args.private_key is None else args.private_key
    public_key = private_key.get_verifying_key()

    # Queue objects for passing stuff between processes
    block_queue = Queue()
    transaction_queue = Queue()
    blockchain_request_queue = Queue()
    blockchain_reply_queue = Queue()
    
    p = Process(target=start_mining, args=(block_queue, transaction_queue,blockchain_request_queue, blockchain_reply_queue,))
    p.start()
    app.run(host="0.0.0.0", debug=True, use_reloader=False,port=args.port)