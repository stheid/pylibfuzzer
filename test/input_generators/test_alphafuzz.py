from collections import Counter

from pylibfuzzer.input_generators.alphafuzz.alphafuzz import Node


def test_score():
    root = Node(b'')
    child1 = Node(b'', Counter(dict(a=1)))
    root.append_child([child1])

    child2 = Node(b'', Counter(dict(a=1)))
    child1.append_child([child2])

    child3 = Node(b'', Counter(dict(a=1)))
    child2.append_child([child3])

    # print(root)
    assert root.tree_trace['a'] == 3
