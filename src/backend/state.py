from collections import defaultdict
from threading import Lock

nodes_by_id = None
nodes = None
nodes_lock = Lock()

block = None
block_lock = Lock()

blockchain = None
blockchain_lock = Lock()

committed_utxos = defaultdict(dict)
committed_utxos_lock = Lock()

utxos = None
utxos_lock = Lock()
