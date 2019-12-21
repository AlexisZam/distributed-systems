#!/usr/bin/env python3.8

from argparse import ArgumentParser
from math import ceil
from time import sleep

from requests import get, post

parser = ArgumentParser(add_help=False)
parser.add_argument("-h", "--host", default="127.0.0.1", type=str)
parser.add_argument("-p", "--port", default=5000, type=int)
parser.add_argument("-n", "--n_nodes", default=1, type=int)
args = parser.parse_args()
address = f"{args.host}:{args.port}"

while True:
    public_keys = get(f"http://{address}/public_keys").json()
    if len(public_keys) == args.n_nodes:
        break

addresses = get(f"http://{address}/addresses").json()
while True:
    if all(
        all(balance == 100 for balance in get(f"http://{address}/balances").json())
        for address in addresses
    ):
        break
    sleep(5)

sleep(30)

public_key = get(f"http://{address}/public_key").json()
index = public_keys.index(public_key)
with open(
    f"/home/user/distributed/transactions/{ceil(args.n_nodes / 5) * 5}nodes/transactions{index}.txt"
) as f:
    for line in f:
        index, amount = map(int, line[2:].split())
        if index < args.n_nodes:
            post(
                f"http://{address}/transaction",
                json={"receiver_public_key": public_keys[index], "amount": amount},
            )

previous_balances = get(f"http://{address}/balances").json()
previous_committed_balances = get(f"http://{address}/committed_balances").json()
n_equals = 0
while True:
    sleep(60)
    current_balances = get(f"http://{address}/balances").json()
    current_committed_balances = get(f"http://{address}/committed_balances").json()
    if (
        current_balances == previous_balances
        and current_committed_balances == previous_committed_balances
    ):
        n_equals += 1
        if n_equals == 5:
            break
    else:
        n_equals = 0
    previous_balances = current_balances
    previous_committed_balances = current_committed_balances

average_block_time = get(f"http://{address}/average_block_time").json()
print("Average block time:", average_block_time)

average_throughput = get(f"http://{address}/average_throughput").json()
print("Average throughput:", average_throughput)

statistics = get(f"http://{address}/statistics").json()
print("Statistics:", statistics)

balances = get(f"http://{address}/balances").json()
print("Balances:", balances)
if sum(balances) != args.n_nodes * 100:
    raise Exception("balances")

committed_balances = get(f"http://{address}/committed_balances").json()
print("Committed balances:", committed_balances)
if sum(committed_balances) != args.n_nodes * 100:
    raise Exception("committed_balances")

post(f"http://{address}/quit")
