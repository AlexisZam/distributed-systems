from copy import deepcopy


class Blockchain:
    def __init__(self):
        self.blocks = []

    def add(self, block):
        self.blocks.append(block)

    def top(self):
        return self.blocks[-1]

    def length(self):
        return len(self.blocks)

    def at(self, i):
        return self.blocks[i]

    def validate(self, utxos):
        temp_utxos = deepcopy(utxos)
        for block in self.blocks:
            if block.validate(temp_utxos, self):
                block.update_utxos(temp_utxos)
            else:
                return False

    def update_utxos(self, utxos):
        for block in self.blocks:
            block.update_utxos(utxos)
