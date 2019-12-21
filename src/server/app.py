#!/usr/bin/env python3.8

from pickle import dumps, loads
from threading import Barrier, Lock, Thread
from time import sleep

from flask import Flask, jsonify, request
from requests import post

import config
import metrics
import node
import state
from transaction import Transaction

app = Flask(__name__)

# Login

if node.address == config.BOOTSTRAP_ADDRESS:

    barrier = Barrier(config.N_NODES - 1)

    @app.route("/login", methods=["POST"])
    def login():
        json = request.get_json()

        node.addresses.append(json["address"])
        node.public_keys.append(json["public_key"])

        barrier.wait()
        return jsonify(node.addresses, node.public_keys)


# Get node


@app.route("/public_key")
def public_key():
    return jsonify(node.public_key)


@app.route("/addresses")
def addresses():
    return jsonify(node.addresses)


@app.route("/public_keys")
def public_keys():
    return jsonify(node.public_keys)


# Get state


@app.route("/balance")
def balance():
    return jsonify(sum(state.utxos[node.public_key].values()))


@app.route("/committed_balances")
def committed_balances():
    return jsonify(
        [
            sum(state.committed_utxos[public_key].values())
            for public_key in node.public_keys
        ]
    )


@app.route("/balances")
def balances():
    return jsonify(
        [sum(state.utxos[public_key].values()) for public_key in node.public_keys]
    )


@app.route("/blockchain")
def blockchain():
    return dumps(state.blockchain)


@app.route("/blockchain/last_block")
def blockchain_last_block():
    transactions = [
        transaction.__dict__ for transaction in state.blockchain.blocks[-1].transactions
    ]
    return jsonify(transactions)


@app.route("/blockchain/length")
def blockchain_length():
    return jsonify(len(state.blockchain.blocks))


# Get metrics


@app.route("/average_throughput")
def average_throughput():
    return jsonify(metrics.average_throughput.get())


@app.route("/average_block_time")
def average_block_time():
    return jsonify(metrics.average_block_time.get())


@app.route("/statistics")
def statistics():
    return jsonify(metrics.statistics)


# Post

lock = Lock()


@app.route("/transaction", methods=["POST"])
def transaction():
    json = request.get_json()

    metrics.average_throughput.increment()

    with lock:
        Transaction(json["receiver_public_key"], json["amount"])

    metrics.statistics["transactions_created"] += 1

    return ""


@app.route("/transaction/validate", methods=["POST"])
def transaction_validate():
    transaction = loads(request.get_data())

    metrics.average_throughput.increment()

    with lock:
        transaction.validate(state.utxos)

    metrics.statistics["transactions_validated"] += 1

    return ""


@app.route("/block/validate", methods=["POST"])
def block_validate():
    block = loads(request.get_data())

    state.validating_block.set()
    with lock:
        try:
            block.validate()
        except:
            state.validating_block.clear()
            state.block.mine()
    state.validating_block.clear()
    return ""


# Quit


@app.route("/quit", methods=["POST"])
def quit():
    request.environ.get("werkzeug.server.shutdown")()
    return ""


Thread(target=app.run, kwargs={"host": config.HOST, "port": config.PORT}).start()

if node.address != config.BOOTSTRAP_ADDRESS:
    sleep(1)

    post(
        f"http://{config.BOOTSTRAP_ADDRESS}/transaction",
        json={"receiver_public_key": node.public_key, "amount": 100},
    )
