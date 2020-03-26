from argparse import ArgumentParser
from Crypto.PublicKey import RSA

from config import bootstrap_address

bits = 2048

private_key = RSA.generate(bits)
public_key = private_key.publickey().exportKey()

parser = ArgumentParser(add_help=False)
parser.add_argument("-h", "--host", default="127.0.0.1", type=str)
parser.add_argument("-p", "--port", default=5000, type=int)
args = parser.parse_args()
host = args.host
port = args.port
address = f"{host}:{port}"

address = address
