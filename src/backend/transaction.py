from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from pickle import dumps
from pprint import pformat

from config import n_nodes
import node
import state


class Transaction:
    def __init__(self, receiver_public_key, amount):
        if node.public_key == receiver_public_key:
            raise ValueError

        self.sender_public_key = node.public_key
        self.receiver_public_key = receiver_public_key

        utxo_amount = 0
        self.transaction_input = []
        with state.utxos_lock:
            while utxo_amount < amount:
                tx_id, amount = state.utxos[
                    self.sender_public_key
                ].popitem()  # TODO KeyError
                utxo_amount += amount
                self.transaction_input.append(tx_id)

        h = self.hash()
        self.id = h.hexdigest()
        self.signature = PKCS1_v1_5.new(node.private_key).sign(h)

        self.transaction_outputs = {"sender": utxo_amount - amount, "receiver": amount}

        with state.utxos_lock:
            state.utxos[self.sender_public_key][self.id] = utxo_amount - amount
            state.utxos[self.receiver_public_key][self.id] = amount

    def hash(self):
        data = (
            self.sender_public_key,
            self.receiver_public_key,
            self.transaction_input,
        )
        return SHA512.new(data=dumps(data))

    def validate(self, utxos):
        if self.sender_public_key == self.receiver_public_key:
            raise ValueError

        if not PKCS1_v1_5.new(RSA.importKey(self.sender_public_key)).verify(
            self.hash(), self.signature
        ):
            return False

        try:
            with state.utxos_lock:
                utxo_amount = sum(
                    utxos[self.sender_public_key].pop(tx_id)
                    for tx_id in self.transaction_input
                )
        except KeyError:
            return False

        if utxo_amount != sum(amount for amount in self.transaction_outputs.values()):
            return False

        with state.utxos_lock:
            utxos[self.sender_public_key][self.id] = self.transaction_outputs["sender"]
            utxos[self.receiver_public_key][self.id] = self.transaction_outputs[
                "receiver"
            ]

        return True


class GenesisTransaction(Transaction):
    def __init__(self, receiver_public_key):
        amount = 100 * n_nodes  # FIXME

        self.receiver_public_key = receiver_public_key
        h = self.hash()
        self.id = h.hexdigest()
        self.transaction_outputs = {"receiver": amount}
        with state.utxos_lock:
            state.utxos[self.receiver_public_key][self.id] = amount

    def hash(self):
        data = self.receiver_public_key
        return SHA512.new(data=dumps(data))

    def validate(self, utxos):
        with state.utxos_lock:
            utxos[self.receiver_public_key][self.id] = self.transaction_outputs[
                "receiver"
            ]

        return True
