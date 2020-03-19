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

class SPVBlock:
    def __init__(self, block):
        # Instantiates object from passed values
        self.previous_header_hash = block.previous_header_hash  # Previous hash in string
        self.hash_tree_root = block.hash_tree_root  # tree root in bytes
        self.timestamp = block.timestamp  # unix time in string
        self.nonce = block.nonce  # nonce in int
        self.header_hash = binascii.hexlify(block.header_hash()).decode()

class SPVBlockChain:
    # chain is a dictionary, key is hash header, value is the header metadata of blocks
    chain = dict()
    last_hash = None
    # Cleaned keys is an ordered list of all the header hashes, only updated on SPVBlockChain.resolve() call
    cleaned_keys = []
    # network cached blocks contain blocks that are rejected, key is prev hash header, value is block
    network_cached_blocks = dict()

    def network_add(self, spv_block):
        # check for genesis block
        self.chain[spv_block.header_hash] = spv_block


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