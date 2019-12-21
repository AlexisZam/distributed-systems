from pickle import dumps
from threading import Thread

from requests import post

import node


def broadcast(path, data, threaded=True):
    for address in node.addresses:
        if address != node.address:
            if threaded:
                Thread(
                    target=post,
                    args=[f"http://{address}{path}"],
                    kwargs={"data": dumps(data)},
                ).start()
            else:
                post(f"http://{address}{path}", data=dumps(data))
