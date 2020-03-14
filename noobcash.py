#!/usr/bin/env python3

from argparse import ArgumentParser
from cmd import Cmd
from collections import defaultdict
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from json import load
from logging import basicConfig, DEBUG, debug, error
from multiprocessing.connection import Client, Listener
from pickle import dumps
from pprint import pformat
from random import random
import readline
from threading import Thread
from time import sleep, time

basicConfig(format=None, level=None)


class TransactionOutput:
    def __init__(
        self, transaction_id, transaction_receiver_public_key, transaction_amount
    ):
        self.transaction_id = transaction_id
        self.transaction_receiver_public_key = transaction_receiver_public_key
        # TODO: check if sent to me
        self.transaction_amount = transaction_amount
        self.id = self.hash().hexdigest()
        debug(self)

    def __repr__(self):
        return f"'TransactionOutput'\n{pformat(self.__dict__)}\n"

    def hash(self):
        data = (
            self.transaction_id,
            self.transaction_receiver_public_key,
            self.transaction_amount,
        )
        return SHA512.new(data=dumps(data))


class Transaction:
    def __init__(
        self, sender_private_key, sender_public_key, receiver_public_key, amount
    ):
        self.sender_public_key = sender_public_key
        self.receiver_public_key = receiver_public_key
        self.amount = amount

        h = self.hash()
        self.id = h.hexdigest()
        if self.sender_public_key != 0:  # FIXME
            self.signature = PKCS1_v1_5.new(sender_private_key).sign(h)

            uto_amount = 0
            self.transaction_input = []
            if self.amount != 0:
                for uto in utos[self.sender_public_key].values():
                    uto_amount += uto.transaction_amount
                    self.transaction_input.append(uto.id)
                    if uto_amount >= self.amount:
                        break
            # TODO: insufficient amount
        debug(self)

        if broadcast:
            for server_address in nodes:
                if server_address != address:
                    with Client(server_address) as connection:
                        connection.send(("transaction", self))

    def __repr__(self):
        return f"'Transaction'\n{pformat(self.__dict__)}\n"

    def hash(self):
        data = (self.sender_public_key, self.receiver_public_key, self.amount)
        return SHA512.new(data=dumps(data))

    # NOTE: creator must also validate transaction
    def validate(self):
        if self.sender_public_key:  # FIXME
            if not PKCS1_v1_5.new(RSA.importKey(self.sender_public_key)).verify(
                self.hash(), self.signature
            ):
                return False

            try:
                uto_amount = sum(
                    utos[self.sender_public_key].pop(uto_id).transaction_amount
                    for uto_id in self.transaction_input
                )
            except KeyError:
                return False

            if uto_amount < self.amount:
                return False

            sender_to = TransactionOutput(
                self.id, self.receiver_public_key, uto_amount - self.amount
            )
            utos[self.sender_public_key][sender_to.id] = sender_to
        receiver_to = TransactionOutput(self.id, self.receiver_public_key, self.amount)
        utos[self.receiver_public_key][receiver_to.id] = receiver_to
        return True


mined = validated = False


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
        return f"'Block'\n{pformat((self.__dict__))}\n"

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
                if validated:
                    return False
        debug(self)
        mined = True

        if broadcast:
            for server_address in nodes:
                if server_address != address:
                    with Client(server_address) as connection:
                        connection.send(("block", self))

    def validate(self):
        validated = (
            self.index == 0
            or self.previous_hash == blockchain.top().current_hash
            and self.current_hash == self.hash().hexdigest()
        )
        return validated


class Blockchain:
    def __init__(self):
        self.blocks = []
        debug(self)

    def __repr__(self):
        return f"'Blockchain'\n{pformat(self.__dict__)}\n"

    def add(self, block):
        block.mine()
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
    bootstrap_address = (d["bootstrap_host"], d["bootstrap_port"])
    capacity = d["capacity"]
    difficulty = d["difficulty"]
    n_nodes = d["n_nodes"]

"""
Parse arguments
"""
parser = ArgumentParser(add_help=False)
parser.add_argument("-h", "--host", default="127.0.0.1", type=str)
parser.add_argument("-p", "--port", default=5000, type=int)
args = parser.parse_args()
host = args.host
port = args.port
address = (host, port)

broadcast = False

"""
Initialize nodes
"""
private_key = RSA.generate(2048)
public_key = private_key.publickey().exportKey()

if address == bootstrap_address:
    blockchain = Blockchain()
    utos = defaultdict(dict)

    index = 0
    nodes = {bootstrap_address: public_key}

    block = Block()
    transaction = Transaction(0, 0, public_key, 100 * n_nodes)
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
                    private_key, public_key, client_public_key, 100
                )
                block.add(transaction)
                if (i - 1) % capacity == 0:
                    blockchain.add(block)
                    block = Block()

    sleep(1)  # FIXME

    for server_address in nodes:
        if server_address != address:
            with Client(server_address) as connection:
                connection.send((nodes, blockchain, utos))
else:
    with Client(bootstrap_address) as connection:
        connection.send((address, public_key))
        index = connection.recv()

    with Listener(address) as listener:
        with listener.accept() as connection:
            nodes, blockchain, utos = connection.recv()
            # blockchain.validate()  # FIXME

    Block()  # FIXME
    block = Block()


def server():
    while True:
        with Listener(address) as listener:
            with listener.accept() as connection:
                k, v = connection.recv()
                if k == "transaction":
                    global block, mined, validated  # FIXME
                    block.add(v)
                    if len(block.transactions) == capacity:
                        blockchain.add(block)
                        block = Block()
                        mined = validated = False
                elif k == "block":
                    if v.validate():
                        blockchain.add(v)
                    else:
                        error("block validation failed")


thread = Thread(target=server)
thread.start()

broadcast = True


class REPL(Cmd):
    intro = 'Noobcash 1.0\nType "help" for more information.'
    prompt = ">>> "

    def do_transaction(self, arg):
        try:
            receiver_adress, amount = arg.split()
            receiver_host, receiver_port = receiver_adress.split(":")
            receiver_address = (receiver_host, int(receiver_port))
        except ValueError:
            print("usage: transaction receiver_adress amount")
            return

        transaction = Transaction(
            private_key, public_key, nodes[receiver_address], int(amount),
        )
        global block  # FIXME
        block.add(transaction)
        if len(block.transactions) == capacity:
            blockchain.add(block)
            block = Block()

    def do_view(self, _):
        for transaction in blockchain.top().transactions:
            print(transaction)

    def do_balance(self, _):
        print(sum(uto.transaction_amount for uto in utos[public_key].values()))

    def do_help(self, _):
        print(
            "transaction receiver_address amount", "view", "balance", "help", sep="\n"
        )  # TODO


REPL().cmdloop()

thread.join()
