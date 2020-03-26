from copy import deepcopy
from pickle import dumps
from requests import post

from block import Block
import node
import state


def broadcast(path, data, method=post):  # FIXME
    for address in state.nodes:
        if address != node.address:
            method(f"http://{address}/{path}", data=dumps(data))


def handle_transaction(transaction):
    with state.block_lock:
        state.block.add(transaction)
        if state.block.full():
            if state.block.mine():
                broadcast("block", state.block)
                with state.blockchain_lock:
                    state.blockchain.add(state.block)
                with state.committed_utxos_lock:
                    state.committed_utxos = state.utxos
                with state.utxos_lock:
                    state.utxos = deepcopy(state.committed_utxos)
                with state.block_lock:
                    state.block = Block()
