from collections import defaultdict
from pickle import loads
from threading import Event

from requests import get

import config
import node
from block import Block
from blockchain import Blockchain

block = Block()
committed_utxos = defaultdict(dict)
utxos = defaultdict(dict)

validating_block = Event()

if node.address == config.BOOTSTRAP_ADDRESS:
    blockchain = Blockchain()
else:
    blockchain = loads(get(f"http://{config.BOOTSTRAP_ADDRESS}/blockchain").content)
    blockchain.validate()
