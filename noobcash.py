#!/usr/bin/env python3

from argparse import ArgumentParser
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from hashlib import sha256
from json import load
from logging import basicConfig, DEBUG, debug
from multiprocessing.connection import Client, Listener
from pickle import loads, dumps
from random import random
from requests import post
from time import sleep, time

basicConfig(format=None, level=DEBUG)


class TransactionOutput:
    counter = 0

    def __init__(
        self, transaction_id, transaction_receiver_public_key, transaction_amount
    ):
        self.id = TransactionOutput.counter
        TransactionOutput.counter += 1
        self.transaction_id = transaction_id
        self.transaction_receiver_public_key = transaction_receiver_public_key
        self.transaction_amount = transaction_amount

    def __repr__(self):
        return f"'TransactionOutput': {self.__dict__}"


class Transaction:
    def __init__(
        self, sender_private_key, sender_public_key, receiver_public_key, amount
    ):
        self.sender_public_key = sender_public_key
        self.receiver_public_key = receiver_public_key
        self.amount = amount

        self.id = SHA512.new(data=dumps(self))
        self.signature = PKCS1_v1_5.new(private_key).sign(self.id)

        uto_amount = 0
        self.transaction_input = []
        if self.amount != 0:
            for uto in utos:
                uto_amount += uto.transaction_amount
                self.transaction_input.append(uto.transaction_amount)
                if uto_amount >= self.amount:
                    break

    def __repr__(self):
        return f"'Transaction': {self.__dict__}"

    def validate(self):
        if not PKCS1_v1_5.new(self.sender_public_key).verify(self.id, self.signature):
            return False

        uto_amount = sum(map(utos, self.transaction_input))
        if uto_amount < self.amount:
            return False

        self.transaction_outputs = [
            TransactionOutput(
                self.id, self.receiver_public_key, uto_amount - self.amount
            ),
            TransactionOutput(self.id, self.receiver_public_key, self.amount),
        ]
        utos.update({to.id: to for to in self.transaction_outputs})
        return True


class Block:
    counter = 0

    def __init__(self):
        self.index = Block.counter
        Block.counter += 1
        self.timestamp = time()
        self.transactions = []
        debug(self)

    def __repr__(self):
        return f"'Block': {self.__dict__}"

    # def __hash__(self): TODO

    def add(self, transaction):
        self.transactions.append(transaction)

    def mine(self):
        h = sha256()
        if self.index == 0:
            self.nonce = 0
            h.update(dumps(self))
            self.current_hash = h.hexdigest()
        else:
            while True:
                self.nonce = random()
                h.update(dumps(self))
                self.current_hash = h.hexdigest()
                if int(self.current_hash[:difficulty], base=16) == 0:
                    break

    def validate(self):
        if self.index == 0:
            return True
        if blockchain.top().current_hash != self.previous_hash:
            return False
        current_hash = self.current_hash
        del self.current_hash
        h = sha256()
        h.update(dumps(self))
        self.current_hash = current_hash
        return current_hash != h.hexdigest()


class Blockchain:
    def __init__(self):
        self.blocks = []

    def __repr__(self):
        return f"'Blockchain': {self.__dict__}"

    def add(self, block):
        self.blocks.append(block)

    def top(self):
        return self.blocks[-1]

    def validate(self):
        return all(block.validate() for block in self.blocks)


"""
Load configuration
"""
with open("config.json") as fp:
    d = load(fp)
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

"""
Initialize nodes
"""
blockchain = Blockchain()

private_key = RSA.generate(2048)
public_key = private_key.publickey()
utos = {}

if address == bootstrap_address:
    index = 0
    nodes = [{"address": bootstrap_address, "public_key": public_key}]

    transaction = Transaction(None, None, public_key, 100 * n_nodes)
    block = Block()
    block.transactions.append(transaction)
    block.mine()

    with Listener(bootstrap_address) as listener:
        for i in range(1, n_nodes):
            with listener.accept() as connection:
                r = connection.recv()
                nodes.append(r)
                connection.send(i)

                transaction = Transaction(private_key, public_key, r["address"], 100)
                if (i - 1) % capacity == 0:
                    blockchain.add(block)
                    block = Block()
                    # block.previous_hash = block.current_hash
                block.add(transaction)

    sleep(1)  # FIXME

    for node in nodes[1:]:
        with Client(node["address"]) as connection:
            connection.send(nodes)
else:
    with Client(bootstrap_address) as connection:
        connection.send({"address": address, "public_key": public_key})
        index = connection.recv()

    with Listener(address) as listener:
        with listener.accept() as connection:
            nodes = connection.recv()
            print(nodes)

