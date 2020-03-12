#!/usr/bin/env python3

from argparse import ArgumentParser
from Crypto.Hash import SHA384  # FIXME
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from hashlib import sha256
from json import load
from multiprocessing.connection import Client, Listener
from os import urandom
from pickle import loads, dumps
from random import random
from requests import post
from time import sleep, time

"""
Wallet
"""


class Wallet:
    def __init__(self):
        self.private_key = RSA.generate(2048)
        self.public_key = self.private_key.publickey()
        self.unspent_transaction_outputs = []

    def wallet_balance(self):
        return sum(self.unspent_transaction_outputs)


"""
Transaction
"""


class Transaction:
    def __init__(self, sender_public_key, receiver_public_key, amount):
        self.sender_public_key = sender_public_key
        self.receiver_public_key = receiver_public_key
        self.amount = amount

    def sign_transaction(self, private_key):
        self.index = SHA384.new(data=dumps(self))
        self.signature = PKCS1_v1_5.new(private_key).sign(self.index)

    def verify_signature(self):
        return PKCS1_v1_5.new(self.sender_public_key).verify(self.index, self.signature)

    # def validate_transaction(self, public_key):
    #     if not self.verify_signature(public_key):
    #         return False


"""
Block
"""


class Block:
    def __init__(self, index):
        self.index = index
        self.timestamp = time()
        self.transactions = []

    def mine_block(self):
        h = sha256()
        if self.index == 0:
            self.nonce = 0
            h.update(dumps(block))
            self.current_hash = h.hexdigest()
        else:
            while True:
                self.nonce = random()
                h.update(dumps(block))
                self.current_hash = h.hexdigest()
                if int(self.current_hash[:difficulty], base=16) == 0:
                    return block

    def validate_block(self):
        if self.index == 0:
            return True
        if blockchain[block.index - 1].current_hash != self.previous_hash:
            return False
        current_hash = self.current_hash
        del self.current_hash
        h = sha256()
        h.update(dumps(self))
        self.current_hash = current_hash
        return current_hash != h.hexdigest()


def validate_chain():
    return all(block.validate_block() for block in blockchain)


"""
Load configuration
"""

with open("config.json") as fp:
    d = load(fp)
    print(d)
    bootstrap_address = (d["bootstrap_host"], d["bootstrap_port"])
    capacity = d["capacity"]
    difficulty = d["difficulty"]
    n_nodes = d["n_nodes"]

"""
Parse arguments
"""

parser = ArgumentParser()
parser.add_argument("--host", default="127.0.0.1", type=str)  # TODO: -h
parser.add_argument("-p", "--port", default=5000, type=int)
args = parser.parse_args()
address = (args.host, args.port)

blockchain = []

wallet = Wallet()

if address == bootstrap_address:
    index = 0
    ring = [{"address": bootstrap_address, "public_key": wallet.public_key}]

    transaction = Transaction(0, wallet.public_key, 100 * n_nodes)
    block = Block(0)
    block.transactions.append(transaction)
    block.mine_block()

    with Listener(bootstrap_address) as listener:
        for i in range(1, n_nodes):
            with listener.accept() as connection:
                r = connection.recv()
                ring.append(r)
                connection.send(i)

                transaction = Transaction(wallet.public_key, r["address"], 100)
                if (i - 1) % capacity == 0:
                    blockchain.append(block)
                    block = Block(blockchain[-1].index + 1)
                    block.previous_hash = block.current_hash
                block.transactions.append(transaction)

    sleep(1)  # FIXME

    for node in ring[1:]:
        with Client(node["address"]) as connection:
            connection.send(ring)
else:
    with Client(bootstrap_address) as connection:
        connection.send({"address": address, "public_key": wallet.public_key})
        index = connection.recv()

    with Listener(address) as listener:
        with listener.accept() as connection:
            ring = connection.recv()
            print(ring)
