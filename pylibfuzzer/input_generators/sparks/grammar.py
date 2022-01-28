from itertools import zip_longest
from typing import Tuple, Union, Dict

import numpy as np
import yaml


class Nonterminal(str):
    def __repr__(self):
        return f'NT({super().__repr__()})'


class Terminal(str):
    def __repr__(self):
        return f'T({super().__repr__()})'


class Grammar:
    def __init__(self, grammar_file: str, startword: str):
        with open(grammar_file, 'r') as f:
            try:
                grammar = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                print(exc)
        self.rules = {Nonterminal(k): Grammar.parse_rules(rules) for k, rules in grammar.items()}
        self.startword = Nonterminal(startword)

    def __getitem__(self, item):
        return self.rules.get(item)

    @staticmethod
    def parse_rules(rules: Union[dict, list]) -> Dict[Tuple, Tuple[float, bool]]:
        """

        :param rules:
        :return: mapping of right hand of a rule -> (weight, has_not_multi_nts)
        """
        if isinstance(rules, dict):
            iter_ = rules.items()
        else:
            iter_ = zip_longest(rules, (1.,), fillvalue=1)

        dictionary = dict()
        for rule, weight in iter_:
            for rule_ in Grammar.parse_symbols(rule):
                has_not_multi_nts = bool(np.clip(2 - len([elem for elem in rule_ if isinstance(elem, str)]), 0, 1))
                dictionary[rule_] = (weight, has_not_multi_nts)
        return dictionary  # noqa: parsesymbols is a generator of tuples

    @staticmethod
    def parse_symbols(rule: str) -> Tuple[Union[Nonterminal, Terminal]]:
        elements = rule.split()
        # epsilon rules break things
        if len(elements) == 0:
            elements = ['""']
        if len(elements) == 3 and '.' == elements[1]:
            try:
                expanded = range(ord(elements[0][1:-1]), ord(elements[2][1:-1]) + 1)
            except TypeError:
                expanded = range(ord(elements[0][1:-1].encode().decode('unicode-escape')),
                                 ord(elements[2][1:-1].encode().decode('unicode-escape')) + 1)
            for elem in expanded:
                try:
                    yield Terminal(chr(elem)),
                except UnicodeEncodeError:
                    pass
        else:
            new_elems = []
            for elem in elements:
                if isinstance(elem, str) and elem.startswith('"') and elem.endswith('"'):
                    try:
                        elem = Terminal(elem[1:-1].encode().decode('unicode-escape'))
                    except UnicodeDecodeError:
                        elem = Terminal(elem)
                else:
                    elem = Nonterminal(elem)
                new_elems.append(elem)
            yield tuple(new_elems)
