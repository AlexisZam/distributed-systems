#!/usr/bin/env python3.8

from copy import deepcopy
from flask import Flask, request
from http import HTTPStatus
from requests import post, put
from pickle import dumps, loads
from threading import Thread

from block import Block, GenesisBlock
from config import bootstrap_address
from repl import REPL
import node
import state
from transaction import Transaction
from utils import broadcast, handle_transaction

# TODO https://stackoverflow.com/questions/48391469/how-to-find-utxo-of-inputs-given-a-bitcoin-transaction/48958148
# TODO add multiple threads in flask

if node.address == bootstrap_address:
    state.nodes[bootstrap_address] = node.public_key

    genesis_block = GenesisBlock()
    state.blockchain.add(genesis_block)
else:
    response = put(
        f"http://{bootstrap_address}/node", data=dumps((node.address, node.public_key))
    )

app = Flask(__name__)


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
        state.nodes = nodes
        return "", HTTPStatus.NO_CONTENT
    else:
        address, public_key = loads(request.get_data())
        state.nodes[address] = public_key

        if node.address == bootstrap_address:
            post(f"http://{address}/nodes", data=dumps(state.nodes))  # FIXME sent twice
            broadcast("nodes", (address, public_key), method=put)

            # post(f"http://{address}/blockchain", data=dumps(state.blockchain))

        #     transaction = Transaction(public_key, 100)
        #     handle_transaction(transaction)

        return "", HTTPStatus.NO_CONTENT


@app.route("/blockchain", methods=["POST"])
def blockchain():
    blockchain = loads(request.get_data())
    if blockchain.validate(state.utxos):
        state.blockchain = blockchain
    return "", HTTPStatus.NO_CONTENT


app.run(host=node.host, port=node.port, debug=True)

# thread = Thread(target=)
# thread.start()

# REPL().cmdloop()

# thread.join()
