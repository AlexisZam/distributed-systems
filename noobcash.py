#!/usr/bin/env python3.8

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

basicConfig(format=None, level=DEBUG)


class TransactionOutput:
    def __init__(
        self, transaction_id, transaction_receiver_public_key, transaction_amount
    ):
        self.transaction_id = transaction_id
        self.transaction_receiver_public_key = transaction_receiver_public_key
        # TODO check if sent to me
        self.transaction_amount = transaction_amount
        self.id = self.hash().hexdigest()

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
            # TODO insufficient amount

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
                return False  # FIXME

            if uto_amount < self.amount:
                return False

            sender_to = TransactionOutput(
                self.id, self.receiver_public_key, uto_amount - self.amount
            )
            utos[self.sender_public_key][sender_to.id] = sender_to
        else:
            debug("genesis block")
        receiver_to = TransactionOutput(self.id, self.receiver_public_key, self.amount)
        utos[self.receiver_public_key][receiver_to.id] = receiver_to
        print(
            [sum(uto.transaction_amount for uto in v.values()) for v in utos.values()]
        )
        return True


validated = False


class Block:
    counter = 0

    def __init__(self):
        self.index = Block.counter
        Block.counter += 1
        self.timestamp = time()
        self.transactions = []
        self.previous_hash = 0 if self.index == 0 else blockchain.top().current_hash

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
        debug("transaction validation started")
        if transaction.validate():
            debug("transaction validation successfull")
            self.transactions.append(transaction)
        else:
            debug("transaction validation failed")

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

        sleep(random())  # FIXME

        if broadcast:
            for server_address in nodes:
                if server_address != address:
                    with Client(server_address) as connection:
                        connection.send(("block", self))
        return True

    def validate(self):
        global validated
        validated = False
        validated = (
            self.index == 0
            or self.previous_hash == blockchain.top().current_hash
            and self.current_hash == self.hash().hexdigest()
        )
        return validated


class Blockchain:
    def __init__(self):
        self.blocks = []

    def __repr__(self):
        return f"'Blockchain'\n{pformat(self.__dict__)}\n"

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
    block.mine()
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
                    block.mine()
                    blockchain.add(block)
                    block = Block()

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
                Thread(target=target, args=[k, v]).start()


def target(k, v):
    if k == "transaction":
        global block, validated  # FIXME
        block.add(v)
        if len(block.transactions) == capacity:
            debug("block mining started (received)")
            if block.mine():
                debug("block mining successfull (received)")
                blockchain.add(block)
                block = Block()
                validated = False
            else:
                debug("block mining failed (received)")
    elif k == "block":
        debug("block validation started (received)")
        if v.validate():
            debug("block validation successfull (received)")
            blockchain.add(v)
        else:
            debug("block validation failed (received)")


thread = Thread(target=server)
thread.start()

broadcast = True


class REPL(Cmd):
    intro = 'Noobcash 1.0\nType "help" for more information.'
    prompt = ">>> "

    def do_transaction(self, arg):
        if not arg:
            receiver_address, amount = ("127.0.0.1", 5000), 1
        else:
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
        global block, validated  # FIXME
        block.add(transaction)
        if len(block.transactions) == capacity:
            debug("block mining started (sent)")
            if block.mine():
                debug("block mining successfull (sent)")
                blockchain.add(block)
                block = Block()
                validated = False
            else:
                debug("block mining failed (sent)")

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
