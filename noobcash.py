#!/usr/bin/env python3

from argparse import ArgumentParser
from cmd import Cmd
from collections import defaultdict
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from flask import Flask, request
from json import load
from logging import basicConfig, DEBUG, debug
from multiprocessing import Process
from multiprocessing.connection import Client, Listener
from pickle import loads, dumps
from random import random
from requests import post
from time import sleep, time

basicConfig(format=None, level=DEBUG)


class Address:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __repr__(self):
        return f"{self.host}:{self.port}"


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
        debug(self)

    def __repr__(self):
        return f"'TransactionOutput': {self.__dict__}"


class Transaction:
    def __init__(
        self, sender_private_key, sender_wallet_address, receiver_wallet_address, amount
    ):
        self.sender_wallet_address = sender_wallet_address
        self.receiver_wallet_address = receiver_wallet_address
        self.amount = amount

        h = self.hash()
        self.id = h.hexdigest()
        if self.sender_wallet_address != 0:  # FIXME
            self.signature = PKCS1_v1_5.new(sender_private_key).sign(h)

            uto_amount = 0
            self.transaction_input = []
            if self.amount != 0:
                for uto in utos[self.sender_wallet_address].values():
                    uto_amount += uto.transaction_amount
                    self.transaction_input.append(uto.id)
                    if uto_amount >= self.amount:
                        break
            # TODO: insufficient amount
        debug(self)

        if broadcast:
            for address in nodes:
                post(f"http://{address[0]}:{address[1]}/transaction", data=dumps(self))

    def __repr__(self):
        return f"'Transaction': {self.__dict__}"

    def hash(self):
        data = (self.sender_wallet_address, self.receiver_wallet_address, self.amount)
        return SHA512.new(data=dumps(data))

    def validate(self):
        if self.sender_wallet_address:  # FIXME
            if not PKCS1_v1_5.new(RSA.importKey(self.sender_wallet_address)).verify(
                self.hash(), self.signature
            ):
                return False
            try:
                uto_amount = sum(
                    utos[self.sender_wallet_address].pop(uto_id).transaction_amount
                    for uto_id in self.transaction_input
                )
            except KeyError:
                return False

            if uto_amount < self.amount:
                return False

            sender_to = TransactionOutput(
                self.id, self.receiver_wallet_address, uto_amount - self.amount
            )
            utos[self.sender_wallet_address][sender_to.id] = sender_to
        receiver_to = TransactionOutput(
            self.id, self.receiver_wallet_address, self.amount
        )
        utos[self.receiver_wallet_address][receiver_to.id] = receiver_to
        return True


class Block:
    counter = 0

    def __init__(self):
        self.index = Block.counter
        Block.counter += 1
        self.timestamp = time()
        self.transactions = []
        self.previous_hash = 0 if self.index == 0 else blockchain.top().current_hash
        debug(self)

    def __repr__(self):
        return f"'Block': {self.index}"

    def hash(self):
        data = (
            self.index,
            self.timestamp,
            self.transactions,
            self.previous_hash,
            self.nonce,
        )
        return SHA512.new(data=dumps(data))

    def add(self, transaction):
        if transaction.validate():
            self.transactions.append(transaction)
            debug(self)

    def mine(self):
        if self.index == 0:
            self.nonce = 0
            self.current_hash = self.hash().hexdigest()
        else:
            while True:
                self.nonce = random()
                self.current_hash = self.hash().hexdigest()
                if int(self.current_hash[:difficulty], base=16) == 0:
                    break
        debug(self)

        if broadcast:
            for address in nodes:
                post(f"http://{address}/block", data=self)

    def validate(self):
        return (
            self.index == 0
            or self.previous_hash == blockchain.top().current_hash
            and self.current_hash == self.hash().hexdigest()
        )


class Blockchain:
    def __init__(self):
        self.blocks = []
        debug(self)

    def __repr__(self):
        return f"'Blockchain': {self.__dict__}"

    def add(self, block):
        block.mine()
        if block.validate():
            self.blocks.append(block)
            debug(self)

    def top(self):
        return self.blocks[-1]

    def validate(self):
        return all(block.validate() for block in self.blocks)


"""
Load configuration
"""
with open("config.json") as fp:
    d = load(fp)
    bootstrap_address = Address(d["bootstrap_host"], d["bootstrap_port"])
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
address = Address(args.host, args.port)

broadcast = False

"""
Initialize nodes
"""
private_key = RSA.generate(2048)
public_key = private_key.publickey()
wallet_address = public_key.exportKey()

if address == bootstrap_address:
    blockchain = Blockchain()
    utos = defaultdict(dict)

    index = 0
    nodes = {bootstrap_address: public_key}

    block = Block()
    transaction = Transaction(0, 0, wallet_address, 100 * n_nodes)
    block.add(transaction)
    blockchain.add(block)
    block = Block()

    with Listener(bootstrap_address) as listener:
        for i in range(1, n_nodes):
            with listener.accept() as connection:
                client_address, client_public_key = connection.recv()
                nodes[client_address] = client_public_key
                connection.send(i)

                transaction = Transaction(
                    private_key, wallet_address, client_public_key.exportKey(), 100
                )
                block.add(transaction)
                if (i - 1) % capacity == 0:
                    blockchain.add(block)
                    block = Block()

    sleep(1)  # FIXME

    for client_address in nodes:
        if client_address != address:
            with Client(client_address) as connection:
                connection.send((nodes, blockchain, utos))
else:
    with Client(bootstrap_address) as connection:
        connection.send((address, public_key))
        index = connection.recv()

    with Listener(address) as listener:
        with listener.accept() as connection:
            nodes, blockchain, utos = connection.recv()
            blockchain.validate()  # FIXME

    block = Block()

"""
Flask
"""


def flask():
    app.run(host=address.host, port=address.port)


app = Flask(__name__)


@app.route("/transaction", methods=["POST"])
def post_transaction():
    transaction = loads(request.get_data())
    block.add(transaction)
    # FIXME: capacity check
    print(transaction)
    return "peos"


@app.route("/block", methods=["POST"])
def post_block():
    block = loads(request.get_data())
    blockchain.add(block)
    print(block)
    pass


p = Process(target=flask)
p.start()

broadcast = True


"""
REPL
"""


class REPL(Cmd):
    intro = 'Noobcash 1.0\nType "help" for more information.'
    prompt = ">>> "

    def do_t(self, arg):
        receiver_host, receiver_port, amount = ("127.0.0.1", 5000, 10)
        # FIXME: arg.split()
        # TODO: arg-parse error handling
        receiver_address = (receiver_host, int(receiver_port))
        transaction = Transaction(
            private_key,
            wallet_address,
            nodes[receiver_address].exportKey(),
            int(amount),
        )
        block.add(transaction)

    def do_view(self, _):
        for transaction in blockchain.top().transactions:
            print(transaction)

    def do_balance(self, _):
        print(sum(uto.transaction_amount for uto in utos[wallet_address].values()))

    def do_help(self, _):
        print("t <receiver_address> <amount>\nview\nbalance\nhelp")  # TODO


REPL().cmdloop()

p.join()
