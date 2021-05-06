from itertools import zip_longest
from random import choice, choices
from typing import List, Tuple, Union, Dict

import numpy as np
import yaml

from pylibfuzzer.algos.base import BaseFuzzer
from pylibfuzzer.obs_extraction import PcVectorExtractor


class PrototypePCFGGenFuzzer(BaseFuzzer):
    supported_extractors = [PcVectorExtractor]

    def __init__(self, pcfg_file):
        super().__init__()
        self.model = PCFG(pcfg_file)
        self.batch = None

    def load_seed(self, path):
        self._initialized = True

    def create_inputs(self) -> List[bytes]:
        self.batch = [self.model.gen('json')]
        return self.batch

    def observe(self, fuzzing_result: List[np.ndarray]):
        for i, res in enumerate(fuzzing_result):
            cov = sum(res)
            if cov > 2000:
                print(self.batch[i].decode())


class PCFG:
    def __init__(self, file):
        with open(file, 'r') as f:
            try:
                grammar = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                print(exc)
        self.grammar = {k: self._parse_rules(rules) for k, rules in grammar.items()}

    def gen(self, startword) -> bytes:

        symbols = list(self._parse_symbols(startword))[-1]
        # TODO: counting the number of non-terminals and so on is very inefficient.
        while any([isinstance(symb, str) for symb in symbols]):
            # select first non-terminal
            idx, nt = choice([(i, x) for i, x in enumerate(symbols) if isinstance(x, str)])

            # select random rule to expand
            rules, weights = zip(*self.grammar[nt].items())
            weights = np.array(weights) + 1e-9

            # the soft mask is a weighted mixture between a uniform random distribution
            # and a hard mask that will only allow certain rules (the ones that do not have more than one non-terminal)
            # alpha may be any value between 0 and 1 to mix between the masked and unmasked distribution
            alpha = 1 if len(symbols) < 1000 else 0
            soft_mask = (alpha, 1 - alpha) @ \
                        np.hstack((np.ones_like(weights[:, 1]) + 1e-9, weights[:, 1])).reshape((-1, 2)).T

            weights = weights[:, 0] * soft_mask
            weights = weights / weights.sum(axis=0)
            sub = choices(rules, weights)[-1]

            # calculate
            symbols = symbols[:idx] + sub + symbols[idx + 1:]

        return b''.join(symbols)

    @classmethod
    def _parse_rules(cls, rules: Union[dict, list]) -> Dict[Tuple, Tuple[float, float]]:
        if isinstance(rules, dict):
            iter_ = rules.items()
        else:
            iter_ = zip_longest(rules, (1.,), fillvalue=1)

        dictionary = dict()
        for rule, count in iter_:
            for rule_ in cls._parse_symbols(rule):
                has_not_multi_nts = np.clip(2 - len([elem for elem in rule_ if isinstance(elem, str)]), 0, 1)
                dictionary[rule_] = (count, has_not_multi_nts)
        return dictionary  # noqa: parsesymbols is a generator of tuples

    @staticmethod
    def _parse_symbols(rule: str) -> Tuple[Union[str, bytes]]:
        elements = rule.split()
        if len(elements) == 3 and '.' == elements[1]:
            try:
                expanded = range(ord(elements[0][1:-1]), ord(elements[2][1:-1]) + 1)
            except TypeError:
                expanded = range(ord(elements[0][1:-1].encode().decode('unicode-escape')),
                                 ord(elements[2][1:-1].encode().decode('unicode-escape')) + 1)
            for elem in expanded:
                try:
                    yield chr(elem).encode(),
                except UnicodeEncodeError:
                    pass
        else:
            new_elems = []
            for elem in elements:
                if isinstance(elem, str) and elem.startswith('"') and elem.endswith('"'):
                    try:
                        elem = elem[1:-1].encode().decode('unicode-escape').encode()
                    except UnicodeDecodeError:
                        elem = elem.encode()
                new_elems.append(elem)
            yield tuple(new_elems)
