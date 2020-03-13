from blockchain import BlockChain, Block
from transaction import Transaction
from merkle_tree import MerkleTree
import random
import time
import copy
import pickle
import requests
import sys
import getopt
import colorama
from flask import Flask, request
from multiprocessing import Process, Queue

app = Flask(__name__)

# Parsing arguments when entered via CLI
def parse_arguments(argv):
    inputfile = ''
    outputfile = ''
    color = ''
    selfish = False
    list_of_miner_ip = []
    mode = 1
    try:
        opts, args = getopt.getopt(
            argv, "hp:i:c:m:s:", ["port=", "ifile=", "color=", "mode=","selfish="])
    # Only port and input is mandatory
    except getopt.GetoptError:
        print('miner.py -p <port> -i <inputfile of list of IPs of other miners> -c <color w|r|h|y|m|c> -m <mode 1/2> -s <1 if selfish miner>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('miner.py -p <port> -i <inputfile of list of IPs of other miners> -c <color w|r|h|y|m|c> -m <mode 1/2> -s <1 if selfish miner>')
            sys.exit()
        elif opt in ("-p", "--port"):
            my_port = arg
        elif opt in ("-i", "--ifile"):
            inputfile = arg
            f = open(inputfile, "r")
            for line in f:
                list_of_miner_ip.append(line)
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
        elif opt in ("-m", "--mode"):
            mode_arg = arg
            if mode_arg == "2":
                mode = 2
        elif opt in ("-s", "--selfish"):
            if arg=="1":
                selfish = True
    return my_port, list_of_miner_ip, color, mode, selfish

# Get data from arguments
MY_PORT, LIST_OF_MINER_IP, COLOR, MODE, SELFISH = parse_arguments(sys.argv[1:])
# MY_IP will be a single string in the form of "127.0.0.1:5000"
# LIST_OF_MINER_IP will be a list of strings in the form of ["127.0.0.1:5000","127.0.0.1:5001","127.0.0.1:5002"]
# COLOR is color of text using colorama library
# MODE is either 1 or 2, 1 is full details, 2 is shortform
# SELFISH if True, this miner will be a selfish miner


def get_miner_ips():
    return LIST_OF_MINER_IP

class Miner:
    def __init__(self, blockchain):
        self.blockchain = copy.deepcopy(blockchain)
        self.nonce = 0
        self.current_time = str(time.time())

    def mine(self, merkletree):
        block = Block(merkletree, self.blockchain.last_hash,
                      merkletree.get_root(), self.current_time, self.nonce)
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


# Random Merkletree
def create_sample_merkle():
    merkletree = MerkleTree()
    from ecdsa import SigningKey
    sender = SigningKey.generate()
    receiver = SigningKey.generate()
    for i in range(10):
        if i == 0:
            # coinbase
            merkletree.add(Transaction(sender, receiver, 100).to_json())
        merkletree.add(Transaction(sender, receiver, random.randint(100, 1000)).to_json())
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
# 1. The accounts involved have enough money to transact, depending on the ledger (dictionary - key(public address):value(amount left))
# 2. TXID (hash of transaction, not created yet) is not duplicated. I can't think of a way other than looking through EVERY transaction

# Creates a merkle tree by compiling all of the transactions in transaction_queue
# Sends the merkle tree to be made into a Block object
def create_merkle(transaction_queue):
    list_of_raw_transactions = []
    list_of_validated_transactions = []
    while not transaction_queue.empty():
        list_of_raw_transactions.append(
            Transaction.from_json(transaction_queue.get()))
    for transaction in list_of_raw_transactions:
        # TODO: check if transaction makes sense in the ledger
        if True:
            list_of_validated_transactions.append(transaction)

    merkletree = MerkleTree()
    # TODO: Add coinbase TX
    # merkletree.add(COINBASE_TRANSACTION)
    for transaction in list_of_validated_transactions:
        merkletree.add(transaction.to_json())
    merkletree.build()
    return merkletree

blockchain = BlockChain(LIST_OF_MINER_IP)
def start_mining(block_queue, transaction_queue):
    merkletree = create_sample_merkle()
    miner = Miner(blockchain)
    miner_status = False
    list_of_blocks_selfish = []
    # Infinite loop
    while True:
        while True:
            # Mines the nonce every round
            miner_status = miner.mine(merkletree)
            mine_or_recv = ""
            # Check if that mine is successful
            if miner_status:
                mine_or_recv = "Block MINED\n"
                sending_block = blockchain.last_block()
                # Grab the last block and send to network
                # regular miner
                if not SELFISH:
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
                                time.sleep(0.1)
                # If selfish miner
                else:
                    mine_or_recv+="SELFISH MINING\n"
                    list_of_blocks_selfish.append(sending_block)
                    # It will send only every 2 blocks
                    if len(list_of_blocks_selfish) >=2:
                        mine_or_recv+="SENDING SELFISH BLOCKS\n"
                        for block in list_of_blocks_selfish:
                            data = pickle.dumps(block, protocol=2)
                            for miner_ip in LIST_OF_MINER_IP:
                                send_failed = True
                                # Retry until peer receives, idk i think prof say ok right? assume all in stable network lel
                                while send_failed:
                                    try:
                                        requests.post("http://"+miner_ip +
                                                    "/block", data=data)
                                        send_failed = False
                                    except:
                                        time.sleep(0.1)
                        list_of_blocks_selfish=[]
                break
            # Checks value of nonce, as checking queue every cycle makes it very laggy
            if miner.nonce % 10000 == 0:
                # Check if new blocks have been detected
                if not block_queue.empty():
                    mine_or_recv = "Block RECEIVED\n"
                    # If detected, add new block to blockchain
                    # TODO add rebroadcast of signal??
                    new_block = block_queue.get()
                    miner.network_block(new_block)
                    break
        # Section run if the miner found a block or receives a block that has been broadcasted
        print(COLOR + "PORT: {}\n".format(MY_PORT) + mine_or_recv +
              (str(miner.blockchain) if MODE == 1 else str(miner.blockchain).split("~~~\n")[1]))
        # merkletree = create_merkle(transaction_queue)


# Queue objects for passing stuff between processes
block_queue = Queue()
transaction_queue = Queue()
transaction_queue = Queue()

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

@app.route('/request_blockchain')
def request_blockchain():
    # Needs to add a proper transaction object, currently thing will fail
    # TODO add rebroadcast of signal??
    transaction_queue.put("a")

if __name__ == '__main__':
    p = Process(target=start_mining, args=(block_queue, transaction_queue,))
    p.start()
    app.run(debug=True, use_reloader=False, port=MY_PORT)
    p.join()
