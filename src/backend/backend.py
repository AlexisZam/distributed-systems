#!/usr/bin/env python3.8

from copy import deepcopy
from flask import Flask, jsonify, request
from http import HTTPStatus
from pickle import dumps, loads
from requests import post, put
from threading import Thread

from block import Block, GenesisBlock
from config import bootstrap_address
import node
import state
from transaction import Transaction


def handle_transaction(transaction):
    with state.block_lock:
        state.block.add(transaction)
        if state.block.full():
            if state.block.mine():
                for address in state.nodes:
                    if address != node.address:
                        post(f"http://{address}/block", data=dumps(state.block))
                with state.blockchain_lock:
                    state.blockchain.add(state.block)
                with state.committed_utxos_lock:
                    state.committed_utxos = state.utxos
                with state.utxos_lock:
                    state.utxos = deepcopy(state.committed_utxos)
                with state.block_lock:
                    state.block = Block()


app = Flask(__name__)


@app.route("/view")
def view():
    return dumps(
        [transaction.__dict__ for transaction in state.blockchain.top().transactions]
    )


@app.route("/balance")
def balance():
    return dumps(sum(amount for amount in state.utxos[node.public_key].values()))


@app.route("/create_transaction", methods=["POST"])
def create_transaction():
    data = loads(request.get_data())
    transaction = Transaction(state.nodes[data["receiver_address"]], data["amount"])
    for address in state.nodes:
        if address != node.address:
            post(f"http://{address}/transaction", data=dumps(transaction))
    handle_transaction(transaction)
    return "", HTTPStatus.NO_CONTENT


@app.route("/transaction", methods=["POST"])
def transaction():
    transaction = loads(request.get_data())
    if transaction.validate(state.utxos):
        handle_transaction(transaction)
    return "", HTTPStatus.NO_CONTENT


@app.route("/block", methods=["POST"])
def block():
    block = loads(request.get_data())
    temp_utxos = deepcopy(state.committed_utxos)
    if block.validate(temp_utxos):
        with state.blockchain_lock:
            state.blockchain.add(block)
            with state.committed_utxos_lock:
                committed_utxos = temp_utxos
            with state.utxos_lock:
                state.utxos = deepcopy(committed_utxos)
            with state.block_lock:
                block = Block()
    return "", HTTPStatus.NO_CONTENT


@app.route("/nodes", methods=["POST", "PUT"])
def nodes():
    if request.method == "POST":
        nodes = loads(request.get_data())
        with state.nodes_lock:
            state.nodes = nodes
        return "", HTTPStatus.NO_CONTENT
    else:
        address, public_key = loads(request.get_data())
        with state.nodes_lock:
            state.nodes[address] = public_key

        if node.address == bootstrap_address:
            post(f"http://{address}/nodes", data=dumps(state.nodes))
            for address in state.nodes:
                if address != node.address:
                    put(f"http://{address}/nodes", data=dumps((address, public_key)))
            # FIXME sent twice

            post(f"http://{address}/blockchain", data=dumps(state.blockchain))

            data = {"receiver_address": address, "amount": 100}
            post(f"http://{bootstrap_address}/create_transaction", data=dumps(data))

        return "", HTTPStatus.NO_CONTENT


@app.route("/blockchain", methods=["POST"])
def blockchain():
    blockchain = loads(request.get_data())
    if blockchain.validate(state.utxos):
        state.blockchain = blockchain
        with state.block_lock:
            state.block = Block()
    return "", HTTPStatus.NO_CONTENT


def init():
    if node.address == bootstrap_address:
        state.nodes[bootstrap_address] = node.public_key

        genesis_block = GenesisBlock()
        state.blockchain.add(genesis_block)
        state.block = Block()
    else:
        data = (node.address, node.public_key)
        put(f"http://{bootstrap_address}/nodes", data=dumps(data))


if __name__ == "__main__":
    Thread(target=init).start()
    app.run(host=node.host, port=node.port, debug=True)
