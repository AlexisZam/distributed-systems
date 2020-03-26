class Blockchain:
    def __init__(self):
        self.blocks = []

    def add(self, block):
        self.blocks.append(block)

    def top(self):
        return self.blocks[-1]

    def validate(self, utxos):
        return all(block.validate(utxos) for block in self.blocks)
