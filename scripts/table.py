#!/usr/bin/env python3.8

from os import walk
from re import split

import pandas as pd

data = []
for dirpath, _, filenames in walk("../outputs/out_4"):
    for filename in filenames:
        d = {}
        tokens = filename.split(sep="_")
        d["Capacity"], d["Difficulty"], d["Number of nodes"] = map(
            int, [tokens[1], tokens[3], tokens[5]]
        )
        with open(f"{dirpath}/{filename}") as f:
            for line in f:
                if line.startswith("Statistics:"):
                    tokens = [token.strip(" \n{'}") for token in split(":|,", line)[1:]]
                    for i in range(0, len(tokens), 2):
                        key = tokens[i].replace("_", " ").capitalize()
                        if not key.startswith("Blockchain") and not key.startswith(
                            "Conflicts resolved"
                        ):
                            d[key] = int(tokens[i + 1])
        data.append(d)

data = pd.DataFrame(data=data)

data.groupby(
    by=["Capacity", "Difficulty", "Number of nodes"], as_index=False
).mean().to_latex(
    buf="../tables/table.tex", index=False,
)
