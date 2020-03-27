#!/usr/bin/env python3.8

from copy import deepcopy
from flask import Flask, request
from http import HTTPStatus
from pickle import dumps, loads
from requests import get, post
from threading import Thread
from time import sleep

from block import Block, GenesisBlock
from blockchain import Blockchain
from config import bootstrap_address
import node
import state
from transaction import GenesisTransaction, Transaction


# TODO CANNOT VALIDATE BLOCK AND THEN UPDATE UTXOS, UPDATING MUST OCCUR AT TX VALIDATION LEVEL


def generate_transaction(receiver_address, amount):
    sleep(1)  # FIXME
    transaction = Transaction(
        node.public_key,
        node.private_key,
        state.nodes[receiver_address],
        amount,
        state.utxos,
    )

    for address in state.nodes:
        if address != node.address:
            post(f"http://{address}/validate_transaction", data=dumps(transaction))

    handle_transaction(transaction)


def handle_transaction(transaction):
    with state.utxos_lock:
        transaction.update_utxos(state.utxos)
    with state.block_lock:
        state.block.add(transaction)
        if state.block.full():
            mine()


def mine():
    if state.block.mine(state.blockchain):
        for address in state.nodes:
            if address != node.address:
                post(f"http://{address}/validate_block", data=dumps(state.block))
        with state.blockchain_lock:
            state.blockchain.add(state.block)
        with state.committed_utxos_lock:
            state.block.update_utxos(state.committed_utxos)
        with state.utxos_lock:
            state.utxos = deepcopy(state.committed_utxos)
        # TODO with state.block_lock:
        state.block = Block()
        print("mining succeeded")
    else:
        print("mining failed")


app = Flask(__name__)


@app.route("/view")
def view():
    return dumps(
        [transaction.__dict__ for transaction in state.blockchain.top().transactions]
    )


@app.route("/balance")
def balance():
    return dumps(sum(amount for amount in state.utxos[node.public_key].values()))


@app.route("/nodes")
def nodes():
    return dumps(state.nodes)


@app.route("/blockchain")
def blockchain():
    return dumps(state.blockchain)


@app.route("/create_transaction", methods=["POST"])
def create_transaction():
    data = loads(request.get_data())
    generate_transaction(data["receiver_address"], data["amount"])
    return "", HTTPStatus.NO_CONTENT


@app.route("/validate_transaction", methods=["POST"])
def validate_transaction():
    transaction = loads(request.get_data())
    if transaction.validate(state.utxos):
        handle_transaction(transaction)
        print("transaction validating succeeded")
    else:
        print("transaction validating failed")
    return "", HTTPStatus.NO_CONTENT


@app.route("/validate_block", methods=["POST"])
def validate_block():
    block = loads(request.get_data())
    if block.validate(state.committed_utxos, state.blockchain):
        with state.blockchain_lock:
            state.blockchain.add(block)
        with state.committed_utxos_lock:
            state.block.update_utxos(state.committed_utxos)
        with state.utxos_lock:
            state.utxos = deepcopy(state.committed_utxos)
        with state.block_lock:
            block = Block()
        print("block validating succeeded")
    else:
        print("block validating failed")
    return "", HTTPStatus.NO_CONTENT


@app.route("/node", methods=["POST"])
def _():
    address, public_key = loads(request.get_data())
    with state.nodes_lock:
        state.nodes[address] = public_key

    if node.address == bootstrap_address:
        Thread(target=generate_transaction, args=(address, 100)).start()

    return "", HTTPStatus.NO_CONTENT


if node.address == bootstrap_address:
    state.nodes = {bootstrap_address: node.public_key}

    genesis_transaction = GenesisTransaction(node.public_key)
    state.block = GenesisBlock()
    state.block.add(genesis_transaction)
    state.blockchain = Blockchain()

    mine()
else:
    sleep(1)  # FIXME

    state.nodes = loads(get(f"http://{bootstrap_address}/nodes").content)
    with state.nodes_lock:
        state.nodes[node.address] = node.public_key

    blockchain = loads(get(f"http://{bootstrap_address}/blockchain").content)
    for block in blockchain.blocks:
        if block.validate(state.committed_utxos, blockchain):
            with state.committed_utxos_lock:
                block.update_utxos(state.committed_utxos)
        else:
            exit(1)
    with state.blockchain_lock:
        state.blockchain = blockchain
    with state.utxos_lock:
        state.utxos = deepcopy(state.committed_utxos)
    with state.block_lock:
        state.block = Block()
    print(state.utxos)

    for address in state.nodes:
        if address != node.address:
            data = (node.address, node.public_key)
            post(f"http://{address}/node", data=dumps(data))


app.run(host=node.host, port=node.port, debug=True)
