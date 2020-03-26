from cmd import Cmd
import readline

import node
import state
from transaction import Transaction
from utils import broadcast, handle_transaction


class REPL(Cmd):
    intro = 'Noobcash 1.0\nType "help" for more information.'
    prompt = ">>> "

    def do_transaction(self, arg):
        if not arg:  # FIXME
            receiver_address, amount = "127.0.0.1:5000", 1
        else:
            try:
                receiver_address, amount = arg.split()
                amount = int(amount)
            except ValueError:
                print("usage: transaction receiver_adress amount")
                return

        transaction = Transaction(state.nodes[receiver_address], amount)
        broadcast("transaction", transaction)
        handle_transaction(transaction)
        # TODO act as if sent from another node

    def do_view(self, _):
        for transaction in state.blockchain.top().transactions:
            print(transaction)

    def do_balance(self, _):
        # FIXME commited_utxos
        print(sum(amount for amount in state.utxos[node.public_key].values()))

    def do_nodes(self, _):
        print(state.nodes)

    def do_utxos(self, _):
        print(state.utxos)

    def do_help(self, _):
        # TODO add explanations
        print(
            "transaction receiver_address amount", "view", "balance", "help", sep="\n"
        )
