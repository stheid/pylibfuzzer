import json

import networkx as nx


def digraph_from_jgrapht(path):
    with open(path) as f:
        d = json.load(f)
    G = nx.DiGraph()
    # by adding only the edges, the graph only contains only edge-induced nodes. Singleton nodes are pruned
    G.add_edges_from([(int(e['source']), int(e['target'])) for e in d['edges']])
    return G
