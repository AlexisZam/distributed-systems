from collections import defaultdict
from copy import deepcopy

import config
import metrics
import state
from block import Block, GenesisBlock


class Blockchain:
    def __init__(self):
        self.blocks = [GenesisBlock()]

        # side effects
        state.blockchain = self

        metrics.statistics["blockchains_created"] += 1

    def add(self, block):
        self.blocks.append(block)

        metrics.average_throughput.time()

    def validate(self):
        previous = self.blocks[0]
        for block in self.blocks[1:]:
            if block.previous_hash != previous.current_hash:
                raise Exception("previous_hash")
            previous = block

        for block in self.blocks[1:]:
            if int(block.hash().hexdigest()[: config.DIFFICULTY], base=16) != 0:
                raise Exception("nonce")

        utxos = defaultdict(dict)
        for block in self.blocks:
            for transaction in block.transactions:
                transaction.validate(utxos, validate_block=True)

        # side effects
        transactions = state.block.transactions + [
            transaction
            for block in state.blockchain.blocks
            for transaction in block.transactions
        ]

        state.blockchain = self
        state.committed_utxos = utxos
        state.utxos = deepcopy(utxos)

        state.block = Block()
        for transaction in transactions:
            if transaction not in [
                transaction
                for block in self.blocks
                for transaction in block.transactions
            ]:
                transaction.validate(state.utxos)

        metrics.statistics["blockchains_validated"] += 1
