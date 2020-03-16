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
from miner_cls import Miner

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

def start_mining(block_queue, transaction_queue):
    blockchain = BlockChain([args.ip_other])
    miner = Miner(blockchain, public_key)
    miner_status = False # whether miner is ready to send
    # variables for double-spending attack
    start_attack = False
    announced_attack = False
    tx_sent = False
    ignore_transactions = []
    private_fork = []
    skip_mine_count = 0
    trigger_block = 3
    trigger_block_hash = ""
    mine_from_trigger_block = False

    while True:
        merkletree, ledger = miner.create_merkle(transaction_queue)
        start_attack = len(blockchain.cleaned_keys)>trigger_block
        if args.attacker and start_attack and not announced_attack:
            print("=============\nStart attack!\n===========")
            announced_attack = True
        while True:
            miner_status = False
            if args.attacker and start_attack and not tx_sent:
                bad_tx = Transaction(public_key,SigningKey.generate().get_verifying_key(),50,"give me the goods", sender_pk=private_key).to_json()
                print("sending transaction...")
                ### broadcast_transaction(bad_tx) # TODO gets stuck here
                print("sent transaction")
                ignore_transactions.append(bad_tx)
                tx_sent = True
                # take the hash of the block before the bad_tx
                trigger_block_hash = blockchain.cleaned_keys[2]
                # set last hash to trigger block hash so it starts mining from there
                blockchain.last_hash = trigger_block_hash
                mine_from_trigger_block = True

            # if attack starts, slow down honest miner
            if not args.attacker and start_attack:
                if skip_mine_count % 500 == 0:
                    miner_status = miner.mine(merkletree, ledger)
                    skip_mine_count = 0 # keep range of skip_mine_count within (0,10]
                skip_mine_count+=1
            elif args.attacker and mine_from_trigger_block:
                miner_status = miner.mine_from_old_block(merkletree, ledger, trigger_block_hash)
                mine_from_trigger_block = miner_status 
            else:
                # mine normally if no attack or if attacker
                miner_status = miner.mine(merkletree, ledger)

            mine_or_recv = ""
            # Check if mine is successful
            if miner_status:
                mine_or_recv = "Block MINED "
                sending_block = blockchain.last_block()
                mine_or_recv += binascii.hexlify(sending_block.header_hash()).decode()
    
                if args.attacker and start_attack:
                   
                    private_fork.append(sending_block)
                    if len(private_fork)==3:
                        mine_or_recv += "launch attack!\n"
                        for block in private_fork:
                            block_data = pickle.dumps(block, protocol=2)
                            send_failed = True
                            while send_failed:
                                try:
                                    requests.post("http://"+args.ip_other+
                                        "/block", data=block_data)
                                    send_failed = False
                                except:
                                    time.sleep(0.1)
                        private_fork = []
                        print("changing attack to False")
                        attack = False

                else: # args.attacker and not start_attack or not args.attacker
                    data = pickle.dumps(sending_block, protocol=2)
                    send_failed = True
                    while send_failed:
                        try:
                            requests.post("http://" + args.ip_other +
                                        "/block", data=data)
                            send_failed = False
                        except:
                            time.sleep(0.2)
                break
            
            if miner.nonce % 1000 == 0:
                # Check if new blocks have been detected
                block_queue_status_initial = block_queue.empty()
                while not block_queue.empty():
                    mine_or_recv += "Block RECEIVED "
                    # If detected, add new block to blockchain
                    new_block = block_queue.get()
                    miner.network_block(new_block)
                    mine_or_recv += binascii.hexlify(new_block.header_hash()).decode() + " "
                if not block_queue_status_initial:
                    mine_or_recv += "\n"
                    break
                block_queue_status_initial= True
        print(color(args.color) +"PORT: {}\n".format(args.port) + mine_or_recv +
              str(miner.blockchain).split("~~~")[1])
        
            

@app.route('/block', methods=['POST'])
def new_block_network():
    new_block = pickle.loads(request.get_data())
    block_queue.put(new_block)
    return ""

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
    
    p = Process(target=start_mining, args=(block_queue, transaction_queue,))
    p.start()
    app.run(host="0.0.0.0", debug=True, use_reloader=False,port=args.port)