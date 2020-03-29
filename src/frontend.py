#!/usr/bin/env python3.8

from argparse import ArgumentParser
from cmd import Cmd
import readline
from pickle import dumps, loads
from pprint import pprint
from requests import get, post


class REPL(Cmd):
    intro = 'Noobcash 1.0\nType "help" for more information.'
    prompt = ">>> "

    def do_load(self, arg):
        
        get(f"http://{address}/from_file")

    def do_transaction(self, arg):
        # TODO remove defaults
        parser = ArgumentParser(prog="transaction", add_help=False)
        parser.add_argument(
            "receiver_address", nargs="?", default="127.0.0.1:5000", type=str
        )
        parser.add_argument("amount", nargs="?", default=1, type=int)
        args = parser.parse_args(args=arg.split())

        data = {"receiver_address": args.receiver_address, "amount": args.amount}
        post(f"http://{address}/create_transaction", data=dumps(data))

    def do_view(self, _):
        transactions = loads(get(f"http://{address}/view").content)
        pprint(transactions)

    def do_balance(self, _):
        balance = loads(get(f"http://{address}/balance").content)
        print(balance)

    def do_help(self, _):
        # TODO add explanations
        print(
            "transaction receiver_address amount", "view", "balance", "help", sep="\n"
        )
    def do_id(self,_):
        id = loads(get(f"http://{address}/id").content)
        print(id)
    def do_exit(self,_):
        exit(0)


parser = ArgumentParser(add_help=False)
parser.add_argument("-h", "--host", default="127.0.0.1", type=str)
parser.add_argument("-p", "--port", default=5000, type=int)
args = parser.parse_args()
address = f"{args.host}:{args.port}"

REPL().cmdloop()
