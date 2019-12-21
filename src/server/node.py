from Cryptodome.PublicKey import RSA
from requests import post

import config

address = f"{config.HOST}:{config.PORT}"

private_key = RSA.generate(2048)
public_key = private_key.publickey().exportKey().decode()

if address == config.BOOTSTRAP_ADDRESS:
    addresses = [address]
    public_keys = [public_key]
else:
    addresses, public_keys = post(
        f"http://{config.BOOTSTRAP_ADDRESS}/login",
        json={"address": address, "public_key": public_key},
    ).json()
