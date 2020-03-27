from argparse import ArgumentParser
from Crypto.PublicKey import RSA

_bits = 2048

private_key = RSA.generate(_bits)
public_key = private_key.publickey().exportKey()

_parser = ArgumentParser(add_help=False)
_parser.add_argument("-h", "--host", default="127.0.0.1", type=str)
_parser.add_argument("-p", "--port", default=5000, type=int)
_args = _parser.parse_args()
host = _args.host
port = _args.port
address = f"{host}:{port}"
