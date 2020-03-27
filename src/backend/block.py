from Crypto.Hash import SHA512
from pickle import dumps
from random import random
from threading import Event

from config import capacity, difficulty

block_validated = Event()


class Block:
    def __init__(self):
        self.transactions = []

    def hash(self):
        data = (self.transactions, self.previous_hash, self.nonce)
        return SHA512.new(data=dumps(data))

    def add(self, transaction):
        self.transactions.append(transaction)

    def full(self):
        return len(self.transactions) == capacity

    def mine(self, blockchain):
        self.previous_hash = blockchain.top().current_hash

        while True:
            if block_validated.is_set():
                block_validated.clear()
                return False
            self.nonce = random()
            self.current_hash = self.hash().hexdigest()
            if int(self.current_hash[:difficulty], base=16) == 0:
                self.index = blockchain.length()  # FIXME
                return True

    def validate(self, utxos, blockchain):
        if not (
            int(self.hash().hexdigest()[:difficulty], base=16) == 0
            and all(transaction.validate(utxos) for transaction in self.transactions)
        ):
            return False

        if not self.previous_hash == blockchain.at(self.index - 1).current_hash:
            # TODO resolve conflict
            return False

        block_validated.set()
        return True

    def update_utxos(self, utxos):
        for transaction in self.transactions:
            transaction.update_utxos(utxos)


class GenesisBlock(Block):
    def __init__(self):
        self.transactions = []

    def add(self, transaction):
        self.transactions.append(transaction)

    def mine(self, _):
        self.current_hash = 0
        self.index = 0
        return True

    def validate(self, utxos, _):
        return all(transaction.validate(utxos) for transaction in self.transactions)
