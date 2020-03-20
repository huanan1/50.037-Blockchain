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

from blockchain import BlockChain, Block
from transaction import Transaction
from merkle_tree import MerkleTree
from miner import Miner

'''
Attacker carries out double-spend attack by creating a new fork before the block with a transaction he wants to void
Since attacker has >=51% hashing power, he will eventually have the longer chain which he publishes, causing blocks
on the other fork to be void.

There will be 2 miners in the double-spending demo.
1) Normal miner will mine at half the speed of an attacker
2) When chain reaches 3rd block, attacker publishes transaction from himself to another party
3) Attacker stores that transaction in a list of transactions to ignore so it doesn't get included into his subsequent blocks
4) Attacker starts private fork when transaction is in latest block
5) Attacker publishes private fork when it is longer than current chain

Demo instructions:
1. Open 2 terminals
2. Run this on the 2nd terminal: python3 double_spend.py --port 22541 --ip_other 127.0.0.1:25540 --attacker --color r
3. Run this on the 1st terminal: python3 double_spend.py --port 25540 --ip_other 127.0.0.1:25541 --color g
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

def find_private_block(chain, prev_hash, original_blocks):
    for (header_hash, block) in chain.items():
        if block.previous_header_hash == prev_hash and header_hash not in original_blocks:
            return block

def check_block_in_chain(blockchain, block_header_hash):
    # cleaned_keys doesn't have the most updated chain if resolve not called here
    blockchain.resolve()
    if block_header_hash in blockchain.cleaned_keys:
        return True
    return False


def start_mining(block_queue, transaction_queue, public_key, private_key):
    blockchain = BlockChain([args.ip_other])
    miner = Miner(blockchain, public_key)
    miner_status = False # whether miner is ready to send
    # variables for double-spending attack #
    start_attack = False
    announced_attack = False
    cease_attacks = False
    unsent_bad_tx = False
    sent_tx = False
    ignore_transactions = []
    private_fork = []
    skip_mine_count = 0
    trigger_block = 3
    trigger_block_hash = ""
    mine_private_blocks = False
    private_last_hash = ""
    original_blocks = []

    while True:
        blockchain.resolve()
        if args.attacker and start_attack:
            # make sure new blocks don't include the bad_tx from attacker
            merkletree, ledger = miner.create_merkle(transaction_queue, tx_to_ignore=ignore_transactions)
        else: # not attacker or attacker and not attacking
            merkletree, ledger = miner.create_merkle(transaction_queue)

        if not cease_attacks:
            if args.attacker:
                # 'and sent_tx' ensures attacker only attacks at least one block after bad_tx is sent
                start_attack = len(blockchain.cleaned_keys)>trigger_block and sent_tx
            else:
                start_attack = len(blockchain.cleaned_keys)>trigger_block

            # send a bad transaction after trigger_block number of blocks in chain
            unsent_bad_tx = len(blockchain.cleaned_keys)==trigger_block

            # this if statement should only be True once
            # send transaction with intent to double spend
            if args.attacker and unsent_bad_tx:
                bad_tx = Transaction(public_key,SigningKey.generate().get_verifying_key(),50, 
                                    "give me the goods", sender_pk=private_key).to_json().encode()
                print("sending transaction with intent to double-spend...")
                # broadcast_transaction(bad_tx) # not necessary for demo
                print("sent transaction")
                ignore_transactions.append(bad_tx)
                unsent_bad_tx = False
                sent_tx = True

        while True:
            miner_status = False
            # this if statement should only be True once
            # start of attack
            if not announced_attack and args.attacker and start_attack:
                # take the hash of the block before the bad_tx
                trigger_block_hash = blockchain.cleaned_keys[trigger_block-1]
                private_last_hash = trigger_block_hash

                # used to track which blocks to ignore in trying to build new longest chain
                original_blocks = copy.deepcopy(blockchain.cleaned_keys[trigger_block:])
                print("=============\nSTART ATTACK!\n============")
                announced_attack = True

                # generate new public key and empty out balance from old public key
                new_private_key = create_key()
                new_public_key = new_private_key.get_verifying_key()
                try:
                    print("double-spending: making transaction to empty out old account...")
                    empty_old_account = Transaction(public_key, new_public_key, amount=ledger.get_balance(public_key), comment="transferring all money out", sender_pk=private_key)
                    print("sent transaction")
                except AssertionError:
                    # old account already empty
                    pass
                public_key = new_public_key
                private_key = new_private_key

                # take on a new identity
                miner = Miner(blockchain, new_public_key)
                # need to create merkle again so coinbase goes to new_public_key
                merkletree, ledger = miner.create_merkle(transaction_queue, tx_to_ignore=ignore_transactions)


            # if attack starts, slow down honest miner
            if not args.attacker and start_attack:
                if skip_mine_count % 500 == 0:
                    miner_status = miner.mine(merkletree, ledger)
                    skip_mine_count = 0 # keep range of skip_mine_count within (0,500]
                skip_mine_count+=1
            elif args.attacker and start_attack:
                # start mining from block before bad_tx
                miner_status = miner.mine_from_old_block(merkletree, ledger, private_last_hash)
            else:
                # mine normally if no attack
                miner_status = miner.mine(merkletree, ledger)

            mine_or_recv = ""
            # Check if mine is successful
            if miner_status:
                mine_or_recv = "Block MINED "
    
                if args.attacker and start_attack:
                    # sending_block might not be last block of blockchain
                    sending_block = find_private_block(blockchain.chain, private_last_hash, original_blocks)
                    sending_block_header_hash = binascii.hexlify(sending_block.header_hash()).decode()
                    mine_or_recv += sending_block_header_hash
                    private_fork.append(sending_block)
                    # update private_last_hash
                    private_last_hash = sending_block_header_hash
                    if len(private_fork)==3:
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
                        if not check_block_in_chain(blockchain, original_blocks[0]):
                            print("=============\nATTACK ENDED\n============")
                            # stop attack
                            start_attack = False
                            cease_attacks = True
                        else:
                            print("block to void:", original_blocks[0], "chain:", blockchain.cleaned_keys)
                            print("block we want to void is still in chain! continuing attack...")

                else: # args.attacker and not start_attack or not args.attacker
                    sending_block = blockchain.last_block()
                    mine_or_recv += binascii.hexlify(sending_block.header_hash()).decode()
                    
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
                    break
                block_queue_status_initial= True
        print(color(args.color) +"PORT: {}\n".format(args.port) + mine_or_recv +
              str(miner.blockchain).split("~~~")[1])
        if start_attack and args.attacker:
            print(color(args.color) + "private fork:"+" "*14*(trigger_block-2),trigger_block_hash[:10]+" -> ", 
            [binascii.hexlify(private_block.header_hash()).decode()[:10] for private_block in private_fork])
        
            

@app.route('/block', methods=['POST'])
def new_block_network():
    new_block = pickle.loads(request.get_data())
    block_queue.put(new_block)
    return ""

@app.route('/transaction', methods=['POST'])
def new_transaction_network():
    new_transaction = Transaction.from_json(request.data.decode())
    transaction_queue.put(new_transaction)
    return ""


if __name__ == '__main__':
    args = parse_arguments() # access arguments via args.argument
    private_key = create_key() if args.private_key is None else args.private_key
    public_key = private_key.get_verifying_key()

    # Queue objects for passing stuff between processes
    block_queue = Queue()
    transaction_queue = Queue()
    
    p = Process(target=start_mining, args=(block_queue, transaction_queue,public_key,private_key,))
    p.start()
    app.run(host="0.0.0.0", debug=True, use_reloader=False,port=args.port)