#!/usr/bin/env python3.6

from copy import deepcopy
from flask import Flask, request
from http import HTTPStatus
from pickle import dumps, loads
from requests import get, post
from threading import Thread
from time import sleep
from multiprocessing import Value
from collections import defaultdict


from block import Block, GenesisBlock
from blockchain import Blockchain
from config import bootstrap_address
import node
import state
from transaction import GenesisTransaction, Transaction


# TODO CANNOT VALIDATE BLOCK AND THEN UPDATE UTXOS, UPDATING MUST OCCUR AT TX VALIDATION LEVEL

def resolve_conflicts():
    blockchain = deepcopy(state.blockchain)
    max_length = blockchain.length()
    for address in state.nodes:
        if address != node.address:
            tmp = loads(get(f"http://{address}/blockchain").content)
            if tmp.length() > max_length:
                max_length = tmp.length()
                blockchain = tmp
    
    if blockchain.validate(defaultdict(dict)):
        with state.committed_utxos_lock:
            state.committed_utxos = defaultdict(dict)
            blockchain.update_utxos(state.committed_utxos)
        with state.blockchain_lock:
            state.blockchain = blockchain
        with state.utxos_lock:
            state.utxos = deepcopy(state.committed_utxos)
        with state.block_lock:
            state.block = Block()
        sum(amount for amount in state.utxos[node.public_key].values())
        print('Blockchain validation succeeded')

        
    else:
        print('Blockchain validation failed')

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

@app.route("/nodes_by_id")
def nodes_by_id():
    return dumps(state.nodes_by_id)

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
    try: 
        if block.validate(state.committed_utxos, state.blockchain):
            with state.blockchain_lock:
                state.blockchain.add(block)
            with state.committed_utxos_lock:
                block.update_utxos(state.committed_utxos)
                
            with state.utxos_lock:
                state.utxos = deepcopy(state.committed_utxos)
            with state.block_lock:
                state.block = Block()
            print("block validating succeeded")
            
        else:
            print("block validating failed")
    except ValueError:
        print('YOu HOo')
        resolve_conflicts()
    return "", HTTPStatus.NO_CONTENT


@app.route("/node", methods=["POST"])
def _():
    id,address, public_key = loads(request.get_data())
    with state.nodes_lock:
        state.nodes[address] = public_key
        state.nodes_by_id[id] = address

    if node.address == bootstrap_address:
        Thread(target=generate_transaction, args=(address, 100)).start()

    return "", HTTPStatus.NO_CONTENT

@app.route("/node_id", methods=["GET"])
def node_id():

    with counter.get_lock():
        
        counter.value += 1
        ret = counter.value 

    return dumps(ret)

@app.route("/id")
def id():
    return dumps(node.id)

@app.route("/from_file")
def from_file():
    # FIXME add to config
    path = "/home/osboxes/distributed/transactions/5nodes/"
    input_file = path+'transactions'+str(node.id)+'.txt'
    print(state.nodes_by_id)
    with open(input_file, 'r') as f:
        for line in f:
            id = int(line.split()[0].split('d')[1])
            amount = int(line.split()[1])
            generate_transaction(state.nodes_by_id[id], amount)
    return ""

if node.address == bootstrap_address:
    counter = Value('i', 0)
    state.nodes_by_id = {0: bootstrap_address}
    state.nodes = {bootstrap_address: node.public_key}
    node.id = 0

    genesis_transaction = GenesisTransaction(node.public_key)
    state.block = GenesisBlock()
    state.block.add(genesis_transaction)
    state.blockchain = Blockchain()

    mine()
else:
    sleep(1)  # FIXME

    state.nodes = loads(get(f"http://{bootstrap_address}/nodes").content)
    state.nodes_by_id = loads(get(f"http://{bootstrap_address}/nodes_by_id").content)

    node.id = loads(get(f"http://{bootstrap_address}/node_id").content)
    with state.nodes_lock:
        state.nodes[node.address] = node.public_key

    blockchain = loads(get(f"http://{bootstrap_address}/blockchain").content)
    for block in blockchain.blocks:
        if block.validate(state.committed_utxos, blockchain):
            with state.committed_utxos_lock:
                block.update_utxos(state.committed_utxos)
    with state.blockchain_lock:
        state.blockchain = blockchain
    with state.utxos_lock:
        state.utxos = deepcopy(state.committed_utxos)
    with state.block_lock:
        state.block = Block()

    for address in state.nodes:
        if address != node.address:
            data = (node.id, node.address, node.public_key)
            post(f"http://{address}/node", data=dumps(data))


app.run(host=node.host, port=node.port, debug=True, use_reloader = False)
