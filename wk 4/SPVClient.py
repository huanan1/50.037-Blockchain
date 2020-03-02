import escda
from ecdsa import SigningKey
from wk3.transaction import Transaction
from wk3.blockchain import BlockChain

class SPVClient:
    '''
    Each SPVClient acts as a wallet, and should have a private and public key.
    The SPVClient should be able to store all the headers of the blockchain. 
    It can also receive transactions and verify them.
    The SPVClient should also be able to send transactions.
    '''

    def __init__(self, node_id = ''):
        # List to store all the block headers.
        self.block_headers = []

        # To identify each SPVClient and to communicate with the other SPVClients.
        self.node_id = node_id

        # Balance left in the wallet.
        self.balance = 0

        # Public key of the wallet to check privte key for verification.
        self.public_key = None

        # Private key of the wallet to sign outgoing transactions.
        self.private_key = None

    def create_keys(self):
        # Create the private and pulic keys for SPVClient.
        sender = ecdsa.SigningKey.generate()
        sendervk = sender.get_verifying_key()
        return sender, sendervk

    def associate_keys(self):
        # Associate the key pair created for SPVClient.
        private_key, public_key = self.create_keys()
        self.private_key = private_key
        self.public_key = public_key
        return private_key, public_key

    def store_keys(self):
        # Creates a new txt file to save the key pairs into for each SPVClient.
        if self.private_key is not None and self.public_key is not None:
            try:
                with open('wallet-{}.txt'.format(self.node_id), 'w') as f:
                    f.write((self.public_key.to_string().hex()))
                    f.write('\n')
                    f.write((self.private_key.to_string().hex()))
                return True

            # Throws an error when key pairs are not able to be saved.    
            except Exception as E:
                print('Wallet saving failed!')
                print(E)
                return False

    def receive_block_headers(self, BlockChain):
        # Get all the block headers from BlockChain class
        for headers in BlockChain.cleaned_keys:
            self.block_headers.append(headers.to_json()) 
        return self.block_headers

    def receive_transaction(self, transaction):
        # Information on incoming transaction.
        UTXO = Transaction(transaction.sender, transaction.receiver, transaction.amount, transaction.comment)

        # Add money from transaction to balance.
        self.balance += transaction.amount

    def verify_transaction(self, transaction):
        # Obtain the information of transaction we want to verify.
        UTXO = Transaction(transaction.sender, transaction.receiver, transaction.amount, transaction.comment)
        
        # Make sure that the private key of wallet matches the public key. 
        verification = UTXO.validate(transaction.signature, self.public_key)

    def send_transactions(self, receiver, amount, comment):
        # UTXO means Unspent Transaction Output. 
        UTXO = Transaction(str(self.public_key.to_string().hex()), receiver, amount, comment)
        
        # Sign the transaction with the private key of wallet to show that it is legitimate.
        UTXO.sign(self.private_key)
        
        # Deduct amount sent from wallet balance.
        self.balance -= amount
        return UTXO
    
