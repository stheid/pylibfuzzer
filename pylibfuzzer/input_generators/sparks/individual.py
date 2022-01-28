import uuid
from collections import defaultdict
from itertools import chain
from random import choice, choices
from typing import List, Dict, Tuple, Optional

import numpy as np
from treelib import Node, Tree

from pylibfuzzer.input_generators.sparks import Grammar, Nonterminal


class Individual:
    def __init__(self, grammar: Grammar, pheno: Optional[bytes] = None, tree=None, nt_refs=None, soft_cutoff=100):
        self.grammar = grammar
        self.soft_cutoff = soft_cutoff
        self.nt_refs = defaultdict(list)  # type: Dict[Nonterminal, List[str]]

        if tree is not None:
            self.tree = tree
            if self.grammar.startword != Nonterminal(tree.get_node(tree.root).tag):
                raise RuntimeError(f'The tree provided is not in alignment with the grammar.'
                                   f' The startword {self.grammar.startword} !='
                                   f' root of parsetree ({Nonterminal(tree.get_node(tree.root).tag)})')
            self.recalc_nt_refs()
        else:
            if pheno is None:
                self.tree, self.nt_refs = self.generate_subtree(self.grammar, self.grammar.startword, self.soft_cutoff)
            else:
                self.tree = self.from_pheno(pheno)
                self.recalc_nt_refs()

    @property
    def startword(self):
        return self.grammar.startword

    @staticmethod
    def generate_subtree(grammar: Grammar, startword: str, soft_cutoff: int) \
            -> Tuple[Tree, Dict[Nonterminal, List[str]]]:
        """
        generates random subtree using the grammar from the startword
        :param grammar: dict containing the rules
        :param startword: the root of new subtree. not necessarily the startsymbol of the grammar
        :param soft_cutoff: position where the alpha is being set to 0.
        :return: Tuple[Tree, Dict[Nonterminal, List[str]]]
        """
        tree = Tree()
        node = Node(startword)
        tree.add_node(node)
        NTs = {node.identifier}
        nt_refs = defaultdict(list)  # type: Dict[Nonterminal, List[str]]
        while NTs:
            nt_node = NTs.pop()
            nt = tree.get_node(nt_node).tag
            nt_refs[nt].append(nt_node)

            # select random rule to expand
            rules, weights = zip(*grammar[nt].items())
            weights = np.array(weights) + 1e-9

            # the soft mask is a weighted mixture between a uniform random distribution
            # and a hard mask that will only allow certain rules (the ones that do not have more than one non-terminal)
            # alpha may be any value between 0 and 1 to mix between the masked and unmasked distribution
            alpha = 1 if len(tree.leaves()) < soft_cutoff else 0
            soft_mask = (alpha, 1 - alpha) @ \
                        np.hstack((np.ones_like(weights[:, 1]) + 1e-9, weights[:, 1])).reshape((-1, 2)).T

            weights = weights[:, 0] * soft_mask
            weights = weights / weights.sum(axis=0)
            sub = choices(rules, weights)[-1]
            # append substitution to the tree
            for elem in sub:
                node = Node(elem)
                if isinstance(elem, Nonterminal):
                    NTs.add(node.identifier)
                tree.add_node(node, nt_node)
        return tree, nt_refs

    def from_pheno(self, phenotype: bytes) -> 'Tree':
        """
        create tree from grammar and then parse given seeds (phenotype) to parse tree

        :param phenotype:
        :return:
        """
        # TODO use lark to parse a bytes object to a tree/individual
        pass

    def to_pheno(self) -> bytes:
        """
        :return: bytes object from tree using transformation
        """
        tree = self.tree
        pheno = b''
        for node in tree.expand_tree(sorting=False):
            node = tree.get_node(node)
            if node.is_leaf():
            # if type(node.tag) != Nonterminal:
                pheno += node.tag.encode()
        return pheno

    def crossover(self, other):
        """
        :param other: individual to crossover with. The given object will not be modified.
        """
        # find all common non-terminals
        common_keys = set(self.nt_refs.keys()).intersection(other.nt_refs.keys()) - {self.startword}
        if not common_keys:
            # if there is no common non-terminal in the trees we skip the crossover and do not throw errors
            return

        # select one non-terminal
        rand_nt = choice(list(common_keys))
        # select one instance of the non-terminal in each individual
        loc = choice(self.nt_refs[rand_nt])
        subtree = other.tree.subtree(choice(other.nt_refs[rand_nt]))

        # do the crossover: take subtree at others non-terminal and place it in the non-terminal in self
        self.tree = Individual.replace_node(self.tree, loc, subtree)
        # return newly generated individual
        self.recalc_nt_refs()
        return self

    def recalc_nt_refs(self):
        """
        traverse tree to find all non-terminals
        :return:
        """
        self.nt_refs = defaultdict(list)
        for nid in self.tree.expand_tree():
            nt = self.tree.get_node(nid).tag
            if isinstance(nt, Nonterminal):
                self.nt_refs[nt].append(nid)

    def __deepcopy__(self, memo) -> 'Individual':
        """

        :return: new individual with all identical fields
        """
        return Individual(grammar=self.grammar, tree=Tree(tree=self.tree, deep=True))

    @staticmethod
    def replace_node(tree: Tree, repl_loc: str, subtree: Tree) -> Tree:
        """
        parameters are modified directly instead of copying,
        :param tree: main tree to be modified
        :param subtree: tree to be replaced in the main tree with
        :param repl_loc: node id in the tree where the subtree should be placed
        :return: modified tree
        """

        # store parent information before removing the subtree
        node = tree.get_node(repl_loc)
        subtree = Tree(subtree, deep=True)

        # replace all ids the subtree to make sure no ids duplicate after we replace the subtree
        for n_ in list(subtree.nodes):
            subtree.update_node(n_, identifier=uuid.uuid1())

        subroot = subtree.get_node(subtree.root).tag
        if node.tag != subroot:
            raise RuntimeError(
                f"root of subtree should be the same non-terminal as replacement location: {node.tag} != {subroot}")

        parent = tree.parent(repl_loc)
        if parent is not None:
            tree.remove_node(repl_loc)
            # replace by pasting at the previously removed node in the tree
            tree.paste(nid=parent.identifier, new_tree=subtree)
        else:
            # if bpointer doesn't exist, then its a root node,
            # in this case, replace entire tree with subtree
            return subtree

        return tree

    def resample(self):
        """
        Directly modifies self without creating a copy.
        Generates a subtree by randomly selecting the startword from nt_refs,
        and then replaces the original node with that of entire subtree
        """
        # todo:
        """
        @stefan:
        Instead of drawing the nonterminals uniformly, we draw them by a weight. 
        the weight is determined by the position of the nonterminal in the tree.
        this weighting function has a "uniformness" hyperparameter that determines 
        how much to overweight NTs closer to the leafs.
        To calculate the weight of a NT, we calculate the longest distance to a leaf, 
        which is the NTs "height".
        Then we calculate the weight by 1/heigh^ɑ
        alpha is a hyperparam. 
        alpha=0: all nodes weighted equal, the larger alpha the more weight on the buttom nodes
        """
        # 1. select one of the values of nt_references with weight information
        randnt = choice(list(chain.from_iterable(self.nt_refs.values())))
        newstartword = self.tree.get_node(randnt).tag
        # 2. generate random tree from randomize
        new_subtree, _ = self.generate_subtree(self.grammar, newstartword, self.soft_cutoff)
        self.tree = Individual.replace_node(tree=self.tree, subtree=new_subtree, repl_loc=randnt)
        self.recalc_nt_refs()
        return self

    def mutate_terminals(self) -> 'Individual':
        """
            - doesn't create copy, modifies self
        """
        # TODO
        # 1. compare "the complement of intersection" with "nt_refs",
        # to select random non-terminal that has only terminal outputs

        # 2. call resample to select a new non-terminal

        pass
