import json
from ecdsa import SigningKey
import binascii
import hashlib
import random
import math


class MerkleTree:

    def __init__(self):
        # leaf_unset is the collection of leaves which haven't been built
        self.leaf_unset = []

    def add(self, number):
        # Appended to the leaf_unset list
        self.leaf_unset.append(str(number).encode())

    def build(self):
        # tree is the full collection of all non-leaves, i.e. this not contain any plaintext items
        self.tree = []
        # transfer of leaf_unset to leaf_set, this is to ensure to mixing up just incase more leaves are added after MerkleTree.build()
        self.leaf_set = self.leaf_unset
        number_of_leaf = len(self.leaf_set)
        # rounds is the number of rounds minus the first layer of hashing of plaintext value
        rounds = math.ceil(math.log2(number_of_leaf))
        hash_leaf = []
        # First round of initial hashing of leaves, hash_leaf is the first layer of any hashed value
        for i in self.leaf_set:
            m = hashlib.sha256()
            m.update(i)
            hash_leaf.append(m.digest())
        # Appending said first hashed layer
        self.tree.append(hash_leaf)
        # loop for number of rounds
        for i in range(rounds):
            non_leaf = []
            # Loops through all the nodes in the current lowest layer of tree, jumping every 2 nodes, moving left to right
            for j in range(0, len(self.tree[i]), 2):
                # try and find a 'partner node', ie a 'right' node
                try:
                    new_node = self.tree[i][j] + self.tree[i][j+1]
                except:
                    # If it fails, the node gets promoted to the next layer and re-hashed alone
                    new_node = self.tree[i][j]
                m = hashlib.sha256()
                m.update(new_node)
                non_leaf.append(m.digest())
            # append to tree a full layer
            self.tree.append(non_leaf)

    def get_proof(self, check):
        # check through the leaf_set for the 'check'
        for count, i in enumerate(self.leaf_set):
            # elements is what is returned
            elements = []
            # if it matches
            if i == str(check).encode():
                # make both partner and current equal to the 'starting position'
                partner_node = count
                current_node = partner_node
                # loop through all layers
                for j in range(len(self.tree)):
                    # If the current node is the left of the pair...
                    if current_node % 2 == 0:
                        # Partner node is on the right
                        partner_node += 1
                        # partner_position is 1, if on the right
                        partner_position = 1
                    # If the current node is the right of the pair...
                    else:
                        # Partner node is on the left
                        partner_node -= 1
                        # partner_position is 0, if on the left
                        partner_position = 0
                    try:
                        # appends to elements a tuple e.g., (0, hash_value)
                        elements.append(
                            (partner_position, self.tree[j][partner_node]))
                    except:
                        # append None if there is no partner_node
                        elements.append(None)
                    # Finds the position of the node in the next level before continuing loop
                    current_node = current_node//2
                    partner_node = current_node
            # It loops one too many times, I lazy fix
            elements = elements[:-1]
            # If elements is not empty, it means it found the value, so disrupt loop and return list
            if len(elements) > 0:
                return elements
        # If no values found, return empty list, else if returns None, verify_proof will error
        return []

    def get_root(self):
        return self.tree[-1][0]


def verify_proof(entry, proof, root):
    # hash the entry first
    m = hashlib.sha256()
    m.update(str(entry).encode())
    non_leaf = m.digest()
    # run it through the proof and hash/match each one
    for i in proof:
        # check if i is not None, None means layer promotion without partner
        if i is not None:
            if i[0] == 1:
                # i is on the right
                non_leaf += i[1]
            else:
                # i is on the left
                non_leaf = i[1] + non_leaf
        m = hashlib.sha256()
        m.update(non_leaf)
        non_leaf = m.digest()
    if non_leaf == root:
        return True
    return False


#  TESTS 
merkletree = MerkleTree()

for i in range(8):
    merkletree.add(random.randint(100, 1000))
merkletree.add(453)
for i in range(50):
    merkletree.add(random.randint(100, 1000))

merkletree.build()
# print(merkletree.get_proof(453))
print(verify_proof(453, merkletree.get_proof(453), merkletree.get_root()))
