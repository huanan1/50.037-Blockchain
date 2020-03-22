import hashlib
import random
import time
import binascii
import copy
import requests
import pickle
import copy
import json

from merkle_tree import MerkleTree
from transaction import Transaction


class Block:

    def __init__(self, transactions, previous_header_hash, hash_tree_root, timestamp, nonce, ledger):
        # Instantiates object from passed values
        self.transactions = transactions  # MerkleTree object
        self.previous_header_hash = previous_header_hash  # Previous hash in string
        self.hash_tree_root = hash_tree_root  # Tree root in bytes
        self.timestamp = timestamp  # Unix time in string
        self.nonce = nonce  # Nonce in int
        self.ledger = ledger  # Ledger object

    def header_hash(self):
        # Creates header value
        header_joined = binascii.hexlify(
            self.hash_tree_root).decode() + str(self.timestamp) + str(self.nonce)
        if self.previous_header_hash is not None:
            header_joined = self.previous_header_hash + header_joined
        # Double hashes the header value, as bitcoin does the same
        m = hashlib.sha256()
        m.update(header_joined.encode())
        round1 = m.digest()
        m = hashlib.sha256()
        m.update(round1)
        return m.digest()


class BlockChain:
    # chain is a dictionary -> {hash header (key): header metadata of blocks (value)}
    chain = dict()
    TARGET = b"\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"
    last_hash = None
    # cleaned_keys is an ordered list of all the header hashes, only updated on BlockChain.resolve() call
    cleaned_keys = []
    # network_cached_blocks is a dictionary that contains blocks that are rejected ->  {prev hash header (key): block (value)}
    network_cached_blocks = dict()

    def __init__(self, miner_ips):
        self.miner_ips = miner_ips

    def retrieve_ledger(self):
        # Obtain the most updated ledger from the latest block that was mined
        block = self.last_block()
        try:
            return block.ledger.balance
        except:
            return None

    def network_block_validate(self, block):
        # Check that incoming block has prev hash and target < nonce (in case malicious miner publishing invalid blocks)
        check1 = self.validate(block)
        # Check if transactions are valid (sender has enough money, and TXIDs have not appeared in the previous blocks)
        check2 = self.verify_transactions(copy.deepcopy(
            block.transactions.leaf_set), block.previous_header_hash, block.ledger)
        return check1 and check2

    def network_add(self, block):
        # Check for genesis block
        if block.previous_header_hash is None:
            # Check that number of transactions is 1 in genesis block
            if len(block.transactions.leaf_set) != 1:
                print("Genesis block should have only one transaction.")
                return False
            coinbase_tx = Transaction.from_json(block.transactions.leaf_set[0])
            if coinbase_tx.amount != 100:
                print("Coinbase transaction should have an amount of 100.")
                return False
            self.chain[binascii.hexlify(block.header_hash()).decode()] = block
            return True

        if self.network_block_validate(block):
            header_hash = binascii.hexlify(block.header_hash()).decode()
            self.chain[header_hash] = block
            time.sleep(0.05)
            # Looks through cached blocks
            self.network_add_cached_blocks(self.network_cached_blocks)
            return True
        else:
            self.network_cached_blocks[binascii.hexlify(
                block.header_hash()).decode()] = copy.deepcopy(block)
            return False

    # Search through cached blocks to see if any can be added to the blockchain
    def network_add_cached_blocks(self, cached_blocks):
        added = []
        runAgain = True
        while runAgain:
            runAgain = False
            # Delete all added blocks and empty list
            for header in added:
                del cached_blocks[header]
            added = []
            for cached_header in cached_blocks:
                next_block = cached_blocks[cached_header]
                if self.network_block_validate(next_block):
                    print(
                        f"Adding block: {binascii.hexlify(next_block.header_hash()).decode()} from cache to chain.")
                    self.chain[cached_header] = copy.deepcopy(next_block)
                    added.append(cached_header)
                    runAgain = True
                    break

        self.network_cached_blocks = copy.deepcopy(cached_blocks)

        if runAgain == True:
            self.network_add_cached_blocks(self.network_cached_blocks)

    def verify_transactions(self, transactions, prev_header_hash, ledger):
        # Obtain blocks in blockchain uptil block with previous header hash
        prev_hash_temp = prev_header_hash
        chain_uptil_prev = [prev_header_hash]
        while True:
            try:
                prev_hash_temp = self.chain[prev_hash_temp].previous_header_hash
                chain_uptil_prev.append(prev_hash_temp)
            except KeyError:
                return False
            if prev_hash_temp == None:
                chain_uptil_prev.append(prev_hash_temp)
            break

        # Convert sent transactions to Transaction objects
        for i, transaction in enumerate(transactions):
            transactions[i] = Transaction.from_json(transaction)

        # Checks coinbase transaction amount
        if transactions[0].amount != 100:
            print("The amount in the coinbase transaction is not 100.")
            return False

        # Loop through all previous blocks
        for hash in reversed(chain_uptil_prev):
            prev_hash = prev_header_hash
            prev_merkle_tree = self.chain[prev_hash].transactions
            # Loop through all transactions in previous block except coinbase transaction
            for i, transaction in enumerate(transactions[1:]):
                # Check if transaction has appeared in previous blocks
                if prev_merkle_tree.get_proof(transaction) != []:
                    # If transaction was repeated
                    print(
                        f"This transaction appeared before. Transaction: {transaction}.")
                    return False

        for transaction in transactions[1:0]:
            # Check if transaction was really sent by the sender
            try:
                transaction.validate(transaction.sig)
            except AssertionError:
                print("Sender's signature is not valid!")
            # Check if sender has enough money to carry out transaction
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
            # Check for previous header
            check_previous_header = block.previous_header_hash in self.chain or block.previous_header_hash is None
            # Check to ensure that it is less than target value
            check_target = block.header_hash() < self.TARGET
            return check_previous_header and check_target
        else:
            # If genesis block, there is no need to check for the last hash value
            return block.header_hash() < self.TARGET

    # Rebroadcast transactions from dropped blocks
    def rebroadcast_transactions(self, block, cleared_transactions):
        transactions = copy.deepcopy(block.transactions.leaf_set)[
            1:]  # ignore coinbase transaction

        not_sent = True
        for miner_ip in self.miner_ips:
            for transaction in transactions:
                # Checks cleared_transactions if a transaction is already duplicated in longest chain
                # If it is, don't rebroadcast
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

    # Resolve forks and find the longest blockchain
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
                    # Update the longest length of blockchain
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
                    # Retry rebroadcasting until it succeeds
                    rebroadcasted = self.rebroadcast_transactions(
                        block, cleared_transactions)

    def resolve_DP(self, hash_check, score, cleared_hashes):
        # Assuming this is the last block in the chain, it first saves itself to the list
        list_of_linked_hashes = [(score, cleared_hashes)]
        # Scans the chain for a block with previous_header in the header of the previous block that called the DP
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
        reply += "\n~~~\n"
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
        # Add recipient to ledger if he doesn't exist
        if transaction.receiver_vk not in self.balance:
            self.balance[transaction.receiver_vk] = transaction.amount
        else:
            self.balance[transaction.receiver_vk] += transaction.amount

        # Don't have to check whether sender exists because it is done under verify_transaction()
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

    def verify_transaction(self, new_transaction, validated_transactions, last_header_hash, blockchain):
        validated_transactions = copy.deepcopy(validated_transactions)
        for i, transaction in enumerate(validated_transactions):
            try:
                validated_transactions[i] = Transaction.from_json(transaction)
            except:
                validated_transactions[i] = transaction

        # Check whether sender is in ledger
        if new_transaction.sender_vk not in self.balance:
            return False

        # Check whether there is sufficient balance in sender's account
        if new_transaction.amount > self.get_balance(new_transaction.sender_vk):
            print(
                f"There is insufficient balance for transaction in account {new_transaction.sender_vk}.")
            return False

        # Check signature
        new_transaction.validate(new_transaction.sig)

        # Check whether TXID exists in validated transactions
        for transaction in validated_transactions:
            if new_transaction.txid == transaction.txid:
                print(
                    f"This transaction appeared before. Transaction: {transaction}.")
                return False

        # Obtain blocks in blockchain uptil block with previous header hash
        last_hash_temp = last_header_hash
        chain_uptil_last = [last_header_hash]
        while True:
            try:
                last_hash_temp = blockchain.chain[last_hash_temp].previous_header_hash
                chain_uptil_last.append(last_hash_temp)
            except KeyError:
                print(f"There's no such hash: {last_hash_temp} in the chain.")
                return False
            if last_hash_temp == None:
                break

        # Loop through all previous blocks
        for hash in reversed(chain_uptil_last):
            prev_hash = last_header_hash
            prev_merkle_tree = blockchain.chain[prev_hash].transactions
            # Check if transaction has appeared in previous blocks
            if prev_merkle_tree.get_proof(new_transaction) != []:
                # Transaction repeated
                return False

        self.update_ledger(new_transaction)
        return True
