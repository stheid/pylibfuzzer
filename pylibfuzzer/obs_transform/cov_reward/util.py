import json
from os.path import isfile
from time import sleep

import networkx as nx

from pylibfuzzer.util.timer import timer


def digraph_from_jgrapht(path, onbusy_callback=lambda: None, wait_for_file=True):
    with timer() as elapsed:
        while wait_for_file and not isfile(path):
            print(f'Waiting for {path} to appear ({elapsed():.1f}s)', end='\r')
            sleep(.1)
            onbusy_callback()

    with open(path) as f:
        d = json.load(f)
    G = nx.DiGraph()
    # by adding only the edges, the graph only contains only edge-induced nodes. Singleton nodes are pruned
    G.add_edges_from([(int(e['source']), int(e['target'])) for e in d['edges']])
    return G
