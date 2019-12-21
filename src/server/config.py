from argparse import ArgumentParser

parser = ArgumentParser(add_help=False)
parser.add_argument("-h", "--host", default="127.0.0.1", type=str)
parser.add_argument("-p", "--port", default=5000, type=int)
parser.add_argument("-b", "--bootstrap_address", default="127.0.0.1:5000", type=str)
parser.add_argument("-c", "--capacity", default=1, type=int)
parser.add_argument("-d", "--difficulty", default=1, type=int)
parser.add_argument("-n", "--n_nodes", default=1, type=int)
args = parser.parse_args()

HOST = args.host
PORT = args.port
BOOTSTRAP_ADDRESS = args.bootstrap_address
CAPACITY = args.capacity
DIFFICULTY = args.difficulty
N_NODES = args.n_nodes
