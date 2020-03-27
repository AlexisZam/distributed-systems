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
        return all(block.validate(utxos, self) for block in self.blocks)

    def update_utxos(self, utxos):
        for block in self.blocks:
            block.update_utxos(utxos)
