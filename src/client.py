#!/usr/bin/env python3.8

import readline
from argparse import ArgumentParser
from cmd import Cmd
from pprint import pprint

from requests import get, post


class REPL(Cmd):
    intro = 'Noobcash 1.0\nType "help" for more information.'
    prompt = ">>> "

    def do_transaction(self, arg):
        try:
            parser = ArgumentParser(prog="transaction", add_help=False)
            parser.add_argument("index", type=int)
            parser.add_argument("amount", type=int)
            args = parser.parse_args(args=arg.split())
        except:
            return

        post(
            f"http://{address}/transaction",
            json={
                "receiver_public_key": public_keys[args.index],
                "amount": args.amount,
            },
        )

    def do_view(self, _):
        transactions = get(f"http://{address}/blockchain/last_block").json()
        pprint(transactions)

    def do_balance(self, _):
        balance = get(f"http://{address}/balance").json()
        print(balance)

    def do_help(self, _):
        print(
            "transaction receiver_public_key amount",
            "view",
            "balance",
            "help",
            sep="\n",
        )


parser = ArgumentParser(add_help=False)
parser.add_argument("-h", "--host", default="127.0.0.1", type=str)
parser.add_argument("-p", "--port", default=5000, type=int)
args = parser.parse_args()
address = f"{args.host}:{args.port}"

public_keys = get(f"http://{address}/public_keys").json()

REPL().cmdloop()
