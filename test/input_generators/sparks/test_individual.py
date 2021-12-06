import random
# from lark import Lark
from copy import deepcopy

import numpy as np
import pytest
from treelib import Tree, Node

from pylibfuzzer.input_generators.sparks import Grammar, Individual, Nonterminal, Terminal


@pytest.fixture
def seeds():
    seedfiles = ["testseed1", "testseed2"]
    return seedfiles


@pytest.fixture
def rand_seed():
    random.seed(42)
    np.random.seed(42)


@pytest.fixture
def grammar():
    return Grammar(grammar_file='input_generators/sparks/gram.yml', startword='S')


@pytest.fixture
def tree1():
    tree = Tree()
    tree.add_node(Node(Nonterminal('S'), 'S'))
    tree.add_node(Node(Nonterminal('A'), 'A'), parent='S')
    tree.add_node(Node(Terminal('a'), 'a'), parent='A')
    return tree


@pytest.fixture
def tree2():
    tree = Tree()
    tree.add_node(Node(Nonterminal('S'), 'S'))
    tree.add_node(Node(Nonterminal('A'), 'A'), parent='S')
    tree.add_node(Node(Terminal('aa'), 'aa'), parent='A')
    return tree


@pytest.fixture
def tree3():
    tree = Tree()
    tree.add_node(Node(Nonterminal('S'), 'S'))
    tree.add_node(Node(Nonterminal('B'), 'B'), parent='S')
    tree.add_node(Node(Terminal('b')), parent='B')
    return tree


@pytest.fixture
def individual_obj(grammar):
    individual_obj = Individual(grammar=grammar)
    return individual_obj


def ident_str(ind: Individual):
    return str(ind.tree.all_nodes())


def test_grammar_assignment(individual_obj):
    # test grammar assignment if a grammar dictionary is provided instead of file name
    new_individual = Individual(grammar=individual_obj.grammar)
    assert new_individual.grammar == individual_obj.grammar


def test_to_pheno(grammar, tree1):
    indiv1 = Individual(grammar=grammar, tree=tree1)
    assert b'a' == indiv1.to_pheno()


def test_deep_copy(grammar, tree1):
    """
    deepcopy should create a copy of each object and not just use references
    """
    indiv1 = Individual(grammar=grammar, tree=tree1)
    copy = deepcopy(indiv1)
    indiv1.tree.remove_node('a')

    old = ident_str(indiv1)
    new = ident_str(copy)
    assert old != new


def test_deep_copy2(grammar, tree1):
    """
    deepcopy should create a copy of each object and not just use references
    """
    indiv1 = Individual(grammar=grammar, tree=tree1)
    copy = deepcopy(indiv1)

    old = ident_str(indiv1)
    new = ident_str(copy)
    assert old == new


def test_nt_refs(individual_obj):
    """
    nt_refs should not change when recalculated for same tree
    """
    nt_refs = individual_obj.nt_refs
    individual_obj.recalc_nt_refs()
    new_nt_refs = individual_obj.nt_refs
    assert sorted([[k] + sorted(v) for k, v in nt_refs.items()]) == \
           sorted([[k] + sorted(v) for k, v in new_nt_refs.items()])


def test_replace_node(individual_obj):
    """check if the replacement node in main tree is same as root node of subtree"""
    tree = individual_obj.tree
    nodetag = "A"
    randnt = ""
    for node in tree.all_nodes():
        if node.tag == nodetag:
            randnt = node.identifier
            break
    subtree, _ = individual_obj.generate_subtree(individual_obj.grammar, startword=individual_obj.startword,
                                                 soft_cutoff=100)
    with pytest.raises(RuntimeError):
        Individual.replace_node(tree=tree, repl_loc=randnt, subtree=subtree)


def test_crossover1(grammar, tree1, tree2):
    indiv1 = Individual(grammar=grammar, tree=tree1)
    indiv2 = Individual(grammar=grammar, tree=tree2)

    # we can only select nonterminal A and this will force to replace the 'a' leaf with 'aa'
    indiv1.crossover(indiv2)
    assert str(indiv1.tree) == str(tree2)


def test_crossover2(grammar, tree1, tree3):
    indiv1 = Individual(grammar=grammar, tree=tree1)
    indiv2 = Individual(grammar=grammar, tree=tree3)

    tree_before = str(indiv1.tree)
    indiv1.crossover(indiv2)
    tree_after = str(indiv1.tree)
    assert tree_before == tree_after
