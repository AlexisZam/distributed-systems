from base64 import b64decode, b64encode
from pickle import dumps

from Cryptodome.Hash import BLAKE2b
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import PKCS1_v1_5

import config
import metrics
import node
import state
from utils import broadcast


class Transaction:
    def __init__(self, receiver_public_key, amount):
        if receiver_public_key == node.public_key:
            raise ValueError("receiver_public_key")
        if amount <= 0:
            raise ValueError("amount")

        self.sender_public_key = node.public_key
        self.receiver_public_key = receiver_public_key

        utxo_amount = 0
        self.inputs = []
        for tx_id, tx_amount in state.utxos[self.sender_public_key].items():
            if utxo_amount >= amount:
                break
            utxo_amount += tx_amount
            self.inputs.append(tx_id)
        if utxo_amount < amount:
            raise ValueError("amount")

        self.outputs = {"receiver": amount}
        if utxo_amount != amount:
            self.outputs["sender"] = utxo_amount - amount

        h = self.hash()
        self.id = h.hexdigest()
        self.signature = b64encode(PKCS1_v1_5.new(node.private_key).sign(h))

        threaded = (
            node.address != config.BOOTSTRAP_ADDRESS
            or metrics.statistics["transactions_created"] >= config.N_NODES - 1
        )
        broadcast("/transaction/validate", self, threaded=threaded)

        # side effects
        for tx_id in self.inputs:
            del state.utxos[self.sender_public_key][tx_id]
        state.utxos[self.receiver_public_key][self.id] = self.outputs["receiver"]
        if "sender" in self.outputs:
            state.utxos[self.sender_public_key][self.id] = self.outputs["sender"]

        state.block.add(self)

    def __eq__(self, other):
        return self.id == other.id

    def validate(self, utxos, validate_block=False):
        if self.sender_public_key == self.receiver_public_key:
            raise Exception("receiver_public_key")

        if any(tx_id not in utxos[self.sender_public_key] for tx_id in self.inputs):
            raise Exception("inputs")

        if sum(utxos[self.sender_public_key][tx_id] for tx_id in self.inputs) != sum(
            self.outputs.values()
        ):
            raise Exception("outputs")

        h = self.hash()
        if self.id != h.hexdigest():
            raise Exception("id")
        if not PKCS1_v1_5.new(RSA.importKey(self.sender_public_key.encode())).verify(
            h, b64decode(self.signature)
        ):
            raise Exception("signature")

        # side effects
        for tx_id in self.inputs:
            del utxos[self.sender_public_key][tx_id]
        utxos[self.receiver_public_key][self.id] = self.outputs["receiver"]
        if "sender" in self.outputs:
            utxos[self.sender_public_key][self.id] = self.outputs["sender"]

        if not validate_block:
            state.block.add(self)

    def hash(self):
        data = (
            self.sender_public_key,
            self.receiver_public_key,
            self.inputs,
            self.outputs,
        )
        return BLAKE2b.new(data=dumps(data))


class GenesisTransaction(Transaction):
    def __init__(self):
        self.receiver_public_key = node.public_key
        self.id = BLAKE2b.new(data=dumps(self.receiver_public_key)).hexdigest()
        self.outputs = {"receiver": 100 * config.N_NODES}

        # side effects
        state.utxos[self.receiver_public_key][self.id] = self.outputs["receiver"]

    def validate(self, utxos, validate_block=False):
        # side effects
        utxos[self.receiver_public_key][self.id] = self.outputs["receiver"]
