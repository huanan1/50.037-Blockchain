from blockchain import Block, BlockChain
import time
import copy
import pickle
import requests
import sys
import getopt
import colorama
import binascii
import ecdsa
import json
from ecdsa import SigningKey
from flask import Flask, request, jsonify
from multiprocessing import Process, Queue
import json

from blockchain import BlockChain, Block, SPVBlock, Ledger
from transaction import Transaction
from merkle_tree import MerkleTree, verify_proof



app = Flask(__name__)

# Parsing arguments when entered via CLI
def parse_arguments(argv):
    inputfile = ''
    outputfile = ''
    color = ''
    selfish = False
    double_spending_attack = False
    list_of_miner_ip = []
    list_of_spv_ip = []
    mode = 1
    private_key = None
    try:
        opts, args = getopt.getopt(
            argv, "hp:m:s:c:d:f:w:a:", ["port=", "iminerfile=", "ispvfile=","color=", "description=","selfish=", "wallet=","double_spending_attack="])
    # Only port and input is mandatory
    except getopt.GetoptError:
        print('miner.py -p <port> -m <inputfile of list of IPs of other miners> -s <inputfile of list of IPs of SPV clients> -c <color w|r|h|y|m|c> -d <description 1/2> -s <1 if selfish miner> -a <1 if demo double-spending attack>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('miner.py -p <port> -m <inputfile of list of IPs of other miners> -s <inputfile of list of IPs of SPV clients> -c <color w|r|h|y|m|c> -d <description 1/2> -s <1 if selfish miner> -a <1 if demo double-spending attack>')
            sys.exit()
        elif opt in ("-p", "--port"):
            my_port = arg
        elif opt in ("-m", "--iminerfile"):
            inputfile = arg
            f = open(inputfile, "r")
            for line in f:
                list_of_miner_ip.append(line.strip())
        elif opt in ("-s", "--ispvfile"):
            print("NO")
            inputfile = arg
            f = open(inputfile, "r")
            for line in f:
                list_of_spv_ip.append(line.strip())
        elif opt in ("-c", "--color"):
            color_arg = arg
            if color_arg == "w":
                color = colorama.Fore.WHITE
            elif color_arg == "r":
                color = colorama.Fore.RED
            elif color_arg == "g":
                color = colorama.Fore.GREEN
            elif color_arg == "y":
                color = colorama.Fore.YELLOW
            elif color_arg == "b":
                color = colorama.Fore.BLUE
            elif color_arg == "m":
                color = colorama.Fore.MAGENTA
            elif color_arg == "c":
                color = colorama.Fore.CYAN
        elif opt in ("-d", "--description"):
            mode_arg = arg
            if mode_arg == "2":
                mode = 2
        elif opt in ("-f", "--selfish"):
            if arg=="1":
                selfish = True
        elif opt in ("-w", "--wallet"):
            if arg != "NO_WALLET":
                private_key = arg
        elif opt in ("-a", "--attack"):
            if arg=="1":
                double_spending_attack = True
    return my_port, list_of_miner_ip, list_of_spv_ip, color, mode, selfish, private_key, double_spending_attack


# Get data from arguments
MY_PORT, LIST_OF_MINER_IP, LIST_OF_SPV_IP, COLOR, MODE, SELFISH, PRIVATE_KEY, DOUBLE_SPENDING_ATTACK = parse_arguments(sys.argv[1:])
# MY_IP will be a single string in the form of "127.0.0.1:5000"
# LIST_OF_MINER_IP will be a list of strings in the form of ["127.0.0.1:5000","127.0.0.1:5001","127.0.0.1:5002"]
# COLOR is color of text using colorama library
# MODE is either 1 or 2, 1 is full details, 2 is shortform
# SELFISH if True, this miner will be a selfish miner

if PRIVATE_KEY is None:
    PRIVATE_KEY = ecdsa.SigningKey.generate()
PUBLIC_KEY = PRIVATE_KEY.get_verifying_key()
PUBLIC_KEY_STRING = PUBLIC_KEY.to_string().hex()
print(PUBLIC_KEY_STRING)

class Miner:
    def __init__(self, blockchain):
        self.blockchain = copy.deepcopy(blockchain)
        self.nonce = 0
        self.current_time = str(time.time())

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
    #### not sure how to get the blockchain object here
        block = self.blockchain.last_block()
        if block is None:
            ledger = Ledger()
            print("ledger for genesis block")
        else:
            ledger = block.ledger
            print("ledger for non-genesis block: " + json.dumps(block.ledger.balance))
        list_of_raw_transactions = []
        list_of_validated_transactions = []
        while not transaction_queue.empty():
            list_of_raw_transactions.append(
                transaction_queue.get())
            print("list of raw transactions: " + str(list_of_raw_transactions))
        for transaction in list_of_raw_transactions:
            # TODO: check if transaction makes sense in the ledger
            if ledger.verify_transaction(transaction, list_of_validated_transactions, block.transactions.leaf_set, block.previous_header_hash):
                list_of_validated_transactions.append(transaction)
                print("list of validated transactions: " +str(list_of_validated_transactions))
        merkletree = MerkleTree()
        # TODO: Add coinbase TX
        ### CHECK SENDER
        merkletree.add(Transaction(ecdsa.SigningKey.generate().get_verifying_key(),PUBLIC_KEY,100).to_json())
        ledger.coinbase_transaction(PUBLIC_KEY)
        print("merkel tree has been created" + json.dumps(ledger.balance))

        for transaction in list_of_validated_transactions:
            merkletree.add(transaction.to_json())
        merkletree.build()
        return merkletree, ledger


# Random Merkletree
def create_sample_merkle():
    merkletree = MerkleTree()
    from ecdsa import SigningKey
    sender = SigningKey.generate()
    sender_vk = sender.get_verifying_key()
    receiver = SigningKey.generate()
    receiver_vk = receiver.get_verifying_key()
    for i in range(10):
        if i == 0:
            # coinbase
            merkletree.add(Transaction(sender_vk, receiver_vk, 100).to_json())
        # merkletree.add(Transaction(sender_vk, receiver_vk, random.randint(100, 1000)).to_json())
    merkletree.build()
    return merkletree

# TODO Youngmin, so erm, it's a bit complex regarding the ledger
# There has to be a copy of the ledger at every single block
# This is to ensure that Huan An's validation code can work
# I am not sure if you want to do a class, or a text file or something
# I suggest putting the ledger in the Block object, so every Block has a copy
# of the ledger, then when the new transactions come, you can pull out the latest
# block, using Blockchain.last_block() will return you the latest block, so you will
# have the latest ledger to be used here in the merkle_tree

# There are 2 main checks to be done here
# 1. The accounts involved have enough money to transact, depending on the ledger
# 2. TXID (hash of transaction, not created yet) is not duplicated. I can't think of a way other than looking through EVERY transaction

# Creates a merkle tree by compiling all of the transactions in transaction_queue
# Sends the merkle tree to be made into a Block object



def start_mining(block_queue, transaction_queue, blockchain_request_queue, blockchain_reply_queue):
    blockchain = BlockChain(LIST_OF_MINER_IP)
    miner = Miner(blockchain)
    merkletree = create_sample_merkle()
    miner_status = False
    list_of_blocks_selfish = []
    # Infinite loop
    while True:
        #merkletree, ledger = create_sample_merkle()
        #create a merkel tree from transaction queue
        merkletree, ledger = miner.create_merkle(transaction_queue)

        while True:
            # print(LIST_OF_MINER_IP)
            # Mines the nonce every round
            miner_status = miner.mine(merkletree, ledger)
            mine_or_recv = ""
            # Check if that mine is successful
            if miner_status:
                mine_or_recv = "Block MINED "
                sending_block = blockchain.last_block()
                mine_or_recv += binascii.hexlify(sending_block.header_hash()).decode()
                
                if DOUBLE_SPENDING_ATTACK:
                    data = pickle.dumps(sending_block, protocol=2)
                    for miner_ip in LIST_OF_MINER_IP:
                        send_failed = True
                        while send_failed:
                            try:
                                requests.post("http://"+miner_ip +
                                            "/block", data=data)
                                send_failed = False
                            except:
                                time.sleep(0.2)                    

                # Grab the last block and send to network
                # regular miner
                elif not SELFISH:
                    data = pickle.dumps(sending_block, protocol=2)
                    for miner_ip in LIST_OF_MINER_IP:
                        send_failed = True
                        # Retry until peer receives, idk i think prof say ok right? assume all in stable network lel
                        while send_failed:
                            try:
                                requests.post("http://"+miner_ip +
                                            "/block", data=data)
                                send_failed = False
                            except:
                                # print("Send failed", miner_ip)
                                time.sleep(0.2)
                # If selfish miner
                else:
                    mine_or_recv+="SELFISH MINING\n"
                    list_of_blocks_selfish.append(sending_block)
                    # It will send only every 2 blocks
                    if len(list_of_blocks_selfish) >=2:
                        mine_or_recv+="SENDING SELFISH BLOCKS\n"
                        for block in list_of_blocks_selfish:
                            block_data = pickle.dumps(block, protocol=2)
                            spv_block_data = pickle.dumps(SPVBlock(block), protocol=2)
                            for miner_ip in LIST_OF_MINER_IP:
                                send_failed = True
                                # Retry until peer receives, idk i think prof say ok right? assume all in stable network lel
                                while send_failed:
                                    try:
                                        requests.post("http://"+miner_ip +
                                                    "/block", data=block_data)
                                        send_failed = False
                                    except:
                                        time.sleep(0.1)
                            for spv_ip in LIST_OF_SPV_IP:
                                send_failed = True
                                # Retry until peer receives, idk i think prof say ok right? assume all in stable network lel
                                while send_failed:
                                    try:
                                        requests.post("http://"+spv_ip +
                                                    "/block_header", data=spv_block_data)
                                        send_failed = False
                                    except:
                                        time.sleep(0.1)
                        list_of_blocks_selfish=[]
                break
            # Checks value of nonce, as checking queue every cycle makes it very laggy
            if miner.nonce % 100 == 0:
                # Check if new blocks have been detected
                block_queue_status_initial = block_queue.empty()
                while not block_queue.empty():
                    mine_or_recv += "Block RECEIVED "
                    # If detected, add new block to blockchain
                    # TODO add rebroadcast of signal??
                    new_block = block_queue.get()
                    miner.network_block(new_block)
                    mine_or_recv += binascii.hexlify(new_block.header_hash()).decode() + " "
                if not block_queue_status_initial:
                    mine_or_recv += "\n"
                    break
                if not blockchain_request_queue.empty():
                    print("Received request of blockchain")
                    blockchain_request_queue.get()
                    print(blockchain.last_block())
                    #ERROR block object is empty.
                    print(blockchain.retrieve_ledger())
                    blockchain_reply_queue.put((copy.deepcopy(blockchain.cleaned_keys), copy.deepcopy(blockchain.chain),
                        copy.deepcopy(blockchain.retrieve_ledger())))
        # Section run if the miner found a block or receives a block that has been broadcasted
        print(COLOR +"PORT: {}\n".format(MY_PORT) + mine_or_recv +
              (str(miner.blockchain) if MODE == 1 else str(miner.blockchain).split("~~~\n")[1]))
        # merkletree = create_merkle(transaction_queue)

# Queue objects for passing stuff between processes
block_queue = Queue()
transaction_queue = Queue()
blockchain_request_queue = Queue()
blockchain_reply_queue = Queue()

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

@app.route('/verify_transaction_from_spv', methods=['POST'])
def verify_transaction_from_spv():
    data = request.data.decode()
    print(data)
    blockchain_request_queue.put(None)
    blockchain_tuple = blockchain_reply_queue.get()
    cleaned_keys, chain = blockchain_tuple[0], blockchain_tuple[1]
    for count, i in enumerate(cleaned_keys):
        merkle_tree = chain[i].transactions
        # print(i, merkle_tree.leaf_set)
        for j in merkle_tree.leaf_set:
            print(json.loads(j.decode())["txid"])
            if json.loads(j.decode())["txid"] == data:
                # reply = json.loads(j.decode())
                proof_bytes = merkle_tree.get_proof(j.decode())
                proof_string = []
                print(proof_bytes)
                for k in proof_bytes:
                    proof_string.append(binascii.hexlify(k).decode())
                root_bytes = merkle_tree.get_root()
                root_string = binascii.hexlify(root_bytes).decode()
                print("YEAH")
                print(j.decode(), proof_bytes, root_bytes)
                # print ("verify", verify_proof(j.decode(), proof_bytes, root_bytes))
                reply = {"entry": j.decode(), "proof": proof_string, "root": root_string}
                return jsonify(reply)
                # reply["confirmations"] = len(len(cleaned_keys)- count)
        # print(merkle_tree.leaf_set)
    return ""

@app.route('/request_blockchain_headers')
def request_blockchain_headers():
    blockchain_request_queue.put(None)
    return jsonify({"blockchain_headers":blockchain_reply_queue.get()[0]})

@app.route('/request_full_blockchain')
def request_full_blockchain():
    blockchain_request_queue.put(None)
    chain = blockchain_reply_queue.get()[1]
    dic_chain = dict()
    for i in chain:
        block_dictionary = dict()
        block = chain[i]
        block_dictionary["header_hash"] =  binascii.hexlify(block.header_hash()).decode()
        block_dictionary["previous_header_hash"] = block.previous_header_hash
        block_dictionary["hash_tree_root"] = binascii.hexlify(block.hash_tree_root).decode()
        block_dictionary["timestamp"] = block.timestamp
        block_dictionary["nonce"] = block.nonce
        # TODO Modify transactions when the real transactions come
        transaction_list = []
        for i in block.transactions.leaf_unset:
            transaction_list.append(i.decode())
        block_dictionary["transactions"] = transaction_list
        dic_chain[block_dictionary["header_hash"]] = block_dictionary
    return jsonify(dic_chain)

@app.route('/request_block/<header_hash>')
def request_block(header_hash):
    blockchain_request_queue.put(None)
    chain = blockchain_reply_queue.get()[1]
    try:
        block = chain[header_hash]
    except:
        return jsonify("Unable to find block")
    block_dictionary = dict()
    block_dictionary["header_hash"] = header_hash
    block_dictionary["previous_header_hash"] = block.previous_header_hash
    block_dictionary["hash_tree_root"] = binascii.hexlify(block.hash_tree_root).decode()
    block_dictionary["timestamp"] = block.timestamp
    block_dictionary["nonce"] = block.nonce
    # TODO Modify transactions when the real transactions come
    transaction_list = []
    for i in block.transactions.leaf_unset:
        transaction_list.append(i.decode())
    block_dictionary["transactions"] = transaction_list
    return jsonify(block_dictionary)
    
@app.route('/account_balance/<public_key>')
def request_account_balance(public_key):
    blockchain_request_queue.put(None)
    ledger = blockchain_reply_queue.get()[2]
    return jsonify(ledger[public_key])

@app.route('/send_transaction?receiver=<receiver_public_key>&amount=<amount>')
def request_send_transaction(receiver_public_key, amount):
    # TODO Send to all miners
    # TODO Add to own transaction queue
    return None

if __name__ == '__main__':
    p = Process(target=start_mining, args=(block_queue, transaction_queue,blockchain_request_queue, blockchain_reply_queue,))
    p.start()
    app.run(host='0.0.0.0', debug=True, use_reloader=False, port=MY_PORT)
    p.join()
