from merkle_tree import MerkleTree
import hashlib
import random
import time
import binascii
import copy
import requests
from transaction import Transaction
import pickle
import copy
import json

class Block:
    def __init__(self, transactions, previous_header_hash, hash_tree_root, timestamp, nonce, ledger):
        # Instantiates object from passed values
        self.transactions = transactions  # MerkleTree object
        self.previous_header_hash = previous_header_hash  # Previous hash in string
        self.hash_tree_root = hash_tree_root  # tree root in bytes
        self.timestamp = timestamp  # unix time in string
        self.nonce = nonce  # nonce in int
        self.ledger = ledger #ledger object

    def header_hash(self):
        # Creates header value
        header_joined = binascii.hexlify(
            self.hash_tree_root).decode() + str(self.timestamp) + str(self.nonce)
        if self.previous_header_hash is not None:
            header_joined = self.previous_header_hash + header_joined
        # Double hashes the header value, coz bitcoin does the same
        m = hashlib.sha256()
        m.update(header_joined.encode())
        round1 = m.digest()
        m = hashlib.sha256()
        m.update(round1)
        return m.digest()

class BlockChain:
    # chain is a dictionary, key is hash header, value is the header metadata of blocks
    chain = dict()
    TARGET = b"\x00\x00\x0a\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"
    last_hash = None
    # Cleaned keys is an ordered list of all the header hashes, only updated on BlockChain.resolve() call
    cleaned_keys = []
    # network cached blocks contain blocks that are rejected, key is prev hash header, value is block
    network_cached_blocks = dict()

    def __init__(self, miner_ips):
            self.miner_ips = miner_ips

    def retrieve_ledger(self):
        block = self.last_block()
        return block.ledger.balance

    def network_block_validate(self, block):
        # check again that incoming block has prev hash and target < nonce (in case malicious miner publishing invalid blocks)
        check1 = self.validate(block)
        # check if transactions are valid (sender has enough money, and TXIDs have not appeared in the previous blocks)
        check2 = self.verify_transactions(copy.deepcopy(block.transactions.leaf_set), block.previous_header_hash,block.ledger)
        return check1 and check2

    def network_add(self, block):
        # check for genesis block
        if block.previous_header_hash is None:
            # check that number of transactions is 1 in genesis block
            if len(block.transactions.leaf_set) != 1:
                print("genesis block should have only one transaction.")
                return False
            coinbase_tx = Transaction.from_json(block.transactions.leaf_set[0])
            if coinbase_tx.amount != 100:
                print("coinbase transaction should have amount == 100")
                return False
            self.chain[binascii.hexlify(block.header_hash()).decode()] = block
            return True

        if self.network_block_validate(block):
            header_hash = binascii.hexlify(block.header_hash()).decode()
            self.chain[header_hash] = block
            # check rejected blocks
            time.sleep(0.05)
            # print("looking through cached blocks...")
            self.network_add_cached_blocks(self.network_cached_blocks)
            # print("finished looking through cached blocks")
            return True
        else:
            # print("\nSaved in cache: ", binascii.hexlify(block.header_hash()).decode(), self.chain)
            self.network_cached_blocks[binascii.hexlify(block.header_hash()).decode()] = copy.deepcopy(block)
            # print(block.previous_header_hash)
            return False
    
    def network_add_cached_blocks(self,cached_blocks):
        '''search through cached blocks to see if any can be added to the blockchain'''
        added = []
        runAgain = True
        while runAgain:
            runAgain = False
            # delete all added blocks and empty list
            for header in added:
                del cached_blocks[header]
                # print(f"here's the cache:{cached_blocks} after deleting header:{header}")
            added = []
            for cached_header in cached_blocks:
                next_block = cached_blocks[cached_header]
                if self.network_block_validate(next_block):
                    print(f"adding block: {binascii.hexlify(next_block.header_hash()).decode()} from cache to chain")
                    self.chain[cached_header] = copy.deepcopy(next_block)
                    added.append(cached_header)
                    runAgain = True
                    break
        
        self.network_cached_blocks = copy.deepcopy(cached_blocks)


        if runAgain == True:
            self.network_add_cached_blocks(self.network_cached_blocks)

    def verify_transactions(self, transactions, prev_header_hash, ledger):
        # obtain blocks in blockchain uptil block with previous header hash
        prev_hash_temp = prev_header_hash
        chain_uptil_prev = [prev_header_hash]
        while True:
            try:
                prev_hash_temp = self.chain[prev_hash_temp].previous_header_hash
                chain_uptil_prev.append(prev_hash_temp)
            except KeyError:
                # print(f"there's no such hash: {prev_hash_temp} in the chain")
                return False
            if prev_hash_temp == None:
                chain_uptil_prev.append(prev_hash_temp)
            break
        # try:
        #     chain_uptil_prev = self.cleaned_keys[:self.cleaned_keys.index(prev_header_hash)+1]
        # except:
        #     return False

        # convert transactions to Transaction objects
        for i, transaction in enumerate(transactions):
            transactions[i] = Transaction.from_json(transaction)

        # check coinbase transaction amount
        if transactions[0].amount != 100:
            print("the amt in the coinbase transaction is not 100")
            return False
        
        # loop through all previous blocks
        for hash in reversed(chain_uptil_prev):
            prev_hash = prev_header_hash
            prev_merkle_tree = self.chain[prev_hash].transactions
            # loop through transactions in prev block
            for i, transaction in enumerate(transactions[1:]):
                # check if transaction has appeared in previous blocks
                if prev_merkle_tree.get_proof(transaction) != []:
                    # transaction repeated
                    print(f"this transaction appeared before. Transaction: {transaction}")
                    return False
        
        for transaction in transactions[1:0]:
            # check if transaction was really sent by the sender
            try:
                transaction.validate(transaction.sig)
            except AssertionError:
                print("sender's signature is not valid")
            # check if sender has enough money

            if ledger.get_balance(transaction.sender_vk) - transaction.amount < 0:
                return False
        return True

    def add(self, block):
        # Checks if block is valid before adding
        if self.validate(block):
            self.chain[binascii.hexlify(block.header_hash()).decode()] = block
            return True
        else:
            return False

    def validate(self, block):
        if len(self.chain) > 0:
            # Checks for previous header and target value
            check_previous_header = block.previous_header_hash in self.chain or block.previous_header_hash is None
            check_target = block.header_hash() < self.TARGET
            # print(check_previous_header, check_target)
            return check_previous_header and check_target
        else:
            # If Genesis block, there is no need to check for the last hash value
            return block.header_hash() < self.TARGET

    def rebroadcast_transactions(self, block, cleared_transactions):
        '''
        rebroadcast transactions from dropped blocks
        Checks cleared_transaction if transaction is already duped in longest chain
        if it is don't send
        '''
        transactions = copy.deepcopy(block.transactions.leaf_set)

        not_sent = True
        for miner_ip in self.miner_ips:
            for transaction in transactions:
                if transaction not in cleared_transactions:
                    while not_sent:
                        try:
                            requests.post("http://"+miner_ip +
                                        "/transaction", data=transaction)
                            not_sent = False
                        except:
                            time.sleep(0.1)
        return True

    def find_dropped_blocks(self):
        dropped_blocks = dict()
        for hash_value in self.chain:
            if hash_value not in self.cleaned_keys:
                dropped_blocks[hash_value] = self.chain[hash_value]
        cleared_transactions = []
        for hash_value in self.cleaned_keys:
            for i in self.chain[hash_value].transactions.leaf_set:
                cleared_transactions.append(i)
        return dropped_blocks, cleared_transactions

    def resolve(self):
        if len(self.chain) > 0:
            longest_chain_length = 0
            for hash_value in self.chain:
                if self.chain[hash_value].previous_header_hash == None:
                    # Find the genesis block's hash value
                    genesis_hash_value = hash_value
                    # Start DP function
                    temp_cleaned_keys = self.resolve_DP(
                        genesis_hash_value, 0, [genesis_hash_value])[1]
                    if len(temp_cleaned_keys) > longest_chain_length:
                        self.cleaned_keys = copy.deepcopy(temp_cleaned_keys)
                        longest_chain_length = len(temp_cleaned_keys)
            try:
                self.last_hash = self.cleaned_keys[-1]
            except IndexError:
                self.last_hash = None

            dropped_blocks, cleared_transactions = self.find_dropped_blocks()
            for _, block in dropped_blocks.items():
                rebroadcasted = False
                while not rebroadcasted:
                    # retry rebroadcasting until it succeeds
                    rebroadcasted = self.rebroadcast_transactions(block, cleared_transactions)
                

    def resolve_DP(self, hash_check, score, cleared_hashes):
        # Assuming this is the last block in the chain, it first saves itself to the list
        list_of_linked_hashes = [(score, cleared_hashes)]
        # Scans the chain for a block with previous_header of the header of the previous block that called the DP
        for hash_value in self.chain:
            if self.chain[hash_value].previous_header_hash == hash_check:
                new_cleared_hashes = copy.deepcopy(cleared_hashes)
                new_cleared_hashes.append(hash_value)
                # Increase score and list of cleared_hashes whenever the DP is called
                list_of_linked_hashes.append(self.resolve_DP(
                    hash_value, score + 1, new_cleared_hashes))
        # Scans the list_of_linked_hashes and only return the longest chain
        highest_score = 0
        for i in list_of_linked_hashes:
            if i[0] > highest_score:
                highest_score = i[0]
        for i in list_of_linked_hashes:
            if i[0] == highest_score:
                return i

    # Returns the last block in the chain
    def last_block(self):
        self.resolve()
        if self.last_hash is not None:
            return self.chain[self.last_hash]
        else:
            return None
            
    def __str__(self):
        reply = "-----------------\nThere are {} blocks in the blockchain\n\n".format(
            len(self.chain))
        for count, i in enumerate(self.chain):
            reply += "Header: {}\tPrev_header: {}\n".format(
                str(i), str(self.chain[i].previous_header_hash))
        reply+="\n~~~\n"
        reply += "The longest chain is {} blocks\n".format(
            len(self.cleaned_keys))
        for count, i in enumerate(self.cleaned_keys):
            reply += i[:10] + " -> "
        reply = reply[:-4]
        return reply

class Ledger:

    def __init__(self):
        self.balance = dict()

    def update_ledger(self, transaction):
        try:
            transaction = Transaction.from_json(transaction)
        except:
            pass
        #add recipient to ledger if he doesn't exist
        if transaction.receiver_vk not in self.balance:
            self.balance[transaction.receiver_vk] = transaction.amount
        else:
            self.balance[transaction.receiver_vk] += transaction.amount

        #don't have to check whether sender exists because it is done under verify_transaction
        self.balance[transaction.sender_vk] -= transaction.amount
      

    def coinbase_transaction(self, public_key):
        if public_key not in self.balance:
            self.balance[public_key] = 100
        else:
            self.balance[public_key] += 100

    def get_balance(self, public_key):
        try:
            return self.balance[public_key]
        except:
            return 0
    
    #new_transaction, validated_transaction from create_merkel
    #transactions: validated transactions in existing blocks
    #def verify_transaction(self, new_transaction, validated_transactions, transactions, prev_header_hash, blockchain):
    def verify_transaction(self, new_transaction, validated_transactions, last_header_hash, blockchain):

        # transactions = copy.deepcopy(transactions)
        validated_transactions = copy.deepcopy(validated_transactions)
        for i, transaction in enumerate(validated_transactions):
            try:
                validated_transactions[i] = Transaction.from_json(transaction)
            except:
                validated_transactions[i] = transaction
        
        #check whether sender is in ledger
        if new_transaction.sender_vk not in self.balance:
            return False

        #check whether there is sufficient balance in sender's account
        if new_transaction.amount > self.get_balance(new_transaction.sender_vk):
            print(f"There is insufficient balance for transaction in account {new_transaction.sender_vk}")
            return False
        
        #check signature
        new_transaction.validate(new_transaction.sig)
        
        #check whether txid exists in validated transactions
        for transaction in validated_transactions:
            if new_transaction.txid == transaction.txid:
                print(f"this transaction appeared before. Transaction: {transaction}")
                return False
              
        # obtain blocks in blockchain uptil block with previous header hash
        last_hash_temp = last_header_hash
        chain_uptil_last = [last_header_hash]
        while True:
            try:
                last_hash_temp = blockchain.chain[last_hash_temp].previous_header_hash
                chain_uptil_last.append(last_hash_temp)
            except KeyError:
                print(f"there's no such hash: {last_hash_temp} in the chain")
                return False
            if last_hash_temp == None:
                break
        #for i, transaction in enumerate(transactions):
            #transactions[i] = Transaction.from_json(transaction)

        # check coinbase transaction amount
        # if transactions[0].amount != 100:
        #     print("the amt in the coinbase transaction is not 100")
        #     return False
        
        # loop through all previous blocks
        for hash in reversed(chain_uptil_last):
            prev_hash = last_header_hash
            prev_merkle_tree = blockchain.chain[prev_hash].transactions
            # loop through transactions in prev block
            # for i, transaction in enumerate(transactions[1:]):
                # check if transaction has appeared in previous blocks
            if prev_merkle_tree.get_proof(new_transaction) != []:
                # transaction repeated
                print(f"this transaction appeared before. Transaction: {new_transaction}")
                return False
        
        # print(transactions)
        # for transaction in transactions[1:]:
        #     # check if transaction was really sent by the sender
        #     try:
        #         transaction.validate(transaction.sig)
        #     except AssertionError:
        #         print("sender's signature is not valid")
            # check if sender has enough money
            # if self.balance[transaction.sender_vk] - transaction.amount < 0:
            #     return False
        
        self.update_ledger(new_transaction)
        print("Transaction has been verified: "+json.dumps(self.balance))
        return True
