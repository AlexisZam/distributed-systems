#!/usr/bin/env python3.8

from os import walk
from re import split

import pandas as pd
import seaborn as sns

sns.set()

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
                if line.startswith("Average"):
                    tokens = line.split(":")
                    d[tokens[0]] = float(tokens[1])
                elif line.startswith("Statistics:"):
                    tokens = [token.strip(" \n{'}") for token in split(":|,", line)[1:]]
                    for i in range(0, len(tokens), 2):
                        key = tokens[i].replace("_", " ").capitalize()
                        if not key.startswith("Blockchain"):
                            d[key] = int(tokens[i + 1])
        data.append(d)

data = pd.DataFrame(data=data)

for y in ["Average block time", "Average throughput"]:
    sns.catplot(
        x="Difficulty",
        y=y,
        hue="Capacity",
        data=data[data["Number of nodes"] == 5],
        kind="bar",
        legend_out=False,
        sharey=False,
    ).savefig(f"../plots/efficiency_{y.lower().replace(' ', '_')}.pdf")

for y in ["Average block time", "Average throughput", "Conflicts resolved"]:
    sns.catplot(
        x="Number of nodes",
        y=y,
        hue="Capacity",
        data=data,
        col="Difficulty",
        kind="bar",
        legend_out=False,
        sharey=False,
    ).savefig(f"../plots/scalability_{y.lower().replace(' ', '_')}.pdf")
