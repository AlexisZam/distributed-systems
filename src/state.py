from collections import defaultdict
from threading import Lock

from blockchain import Blockchain
from config import bootstrap_address
import node

nodes = {}

block = None
block_lock = Lock()

blockchain = Blockchain()
blockchain_lock = Lock()

committed_utxos = defaultdict(dict)
committed_utxos_lock = Lock()

utxos = defaultdict(dict)
utxos_lock = Lock()
