from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from pickle import dumps

from config import n_nodes


class Transaction:
    def __init__(
        self, sender_public_key, sender_private_key, receiver_public_key, amount, utxos
    ):
        if sender_public_key == receiver_public_key or amount == 0:
            raise ValueError

        self.sender_public_key = sender_public_key
        self.receiver_public_key = receiver_public_key

        utxo_amount = 0
        self.transaction_input = []
        for tx_id, tx_amount in utxos[self.sender_public_key].items():
            if utxo_amount >= amount:
                break
            utxo_amount += tx_amount
            self.transaction_input.append(tx_id)
        if utxo_amount < amount:
            raise ValueError

        h = self.hash()
        self.id = h.hexdigest()
        self.signature = PKCS1_v1_5.new(sender_private_key).sign(h)

        # TODO disallow zero change
        self.transaction_outputs = {"sender": utxo_amount - amount, "receiver": amount}

    def hash(self):
        data = (
            self.sender_public_key,
            self.receiver_public_key,
            self.transaction_input,
        )
        return SHA512.new(data=dumps(data))

    def validate(self, utxos):
        try:
            return (
                self.sender_public_key != self.receiver_public_key
                and PKCS1_v1_5.new(RSA.importKey(self.sender_public_key)).verify(
                    self.hash(), self.signature
                )
                and sum(
                    utxos[self.sender_public_key][tx_id]
                    for tx_id in self.transaction_input
                )
                == sum(amount for amount in self.transaction_outputs.values())
            )
        except KeyError:
            print('sum')
            return False

    def update_utxos(self, utxos):
        for tx_id in self.transaction_input:
            try:
                del utxos[self.sender_public_key][tx_id]
            except KeyError:
                pass
        utxos[self.sender_public_key][self.id] = self.transaction_outputs["sender"]
        utxos[self.receiver_public_key][self.id] = self.transaction_outputs["receiver"]


class GenesisTransaction(Transaction):
    def __init__(self, receiver_public_key):
        init_amount = 100 * n_nodes  # FIXME

        self.receiver_public_key = receiver_public_key
        h = self.hash()
        self.id = h.hexdigest()
        self.transaction_outputs = {"receiver": init_amount}

    def hash(self):
        data = self.receiver_public_key
        return SHA512.new(data=dumps(data))

    def validate(self, _):
        return True

    def update_utxos(self, utxos):
        utxos[self.receiver_public_key][self.id] = self.transaction_outputs["receiver"]
