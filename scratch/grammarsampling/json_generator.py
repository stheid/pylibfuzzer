from itertools import zip_longest
from random import choices, choice
from typing import Union, Dict, Tuple

import click
import numpy as np
import yaml


@click.command()
@click.option('--gram', default='gram.yml', help='file providing the grammar')
@click.option('--node', default='json', help='non-terminal to start with')
def main(gram: str, node: str):
    with open(gram, 'r') as f:
        try:
            grammar = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc)

    grammar = {k: parse_rules(rules) for k, rules in grammar.items()}
    # in dictionary grammar, all strings are rules and terminals are bytes
    # each rule or terminal is key and its value is (count,num)

    symbols = list(parse_symbols(node))[-1]

    # TODO: counting the number of non-terminals and so on is very inefficient.
    # replace by function list_of_non_terminals
    while any([isinstance(symb, str) for symb in symbols]):
        # select first non-terminal
        # TODO: change choice, because it is inefficient
        idx, nt = choice([(i, x) for i, x in enumerate(symbols) if isinstance(x, str)])

        # select random rule to expand
        rules, weights = zip(*grammar[nt].items())
        weights = np.array(weights) + 1e-7

        # the soft mask is a weighted mixture between a uniform random distribution
        # and a hard mask that will only allow certain rules (the ones that do not have more than one non-terminal)
        # alpha may be any value between 0 and 1 to mix between the masked and unmasked distribution
        alpha = 1 if len(symbols) < 1000 else 0
        soft_mask = (
                (alpha, 1 - alpha) @
                np.hstack((np.ones_like(weights[:, 1]) + 1e-7, weights[:, 1])).reshape((-1, 2)).T
        )

        weights = weights[:, 0] * soft_mask
        weights = weights / weights.sum(axis=0)
        sub = choices(rules, weights)[-1]

        # calculate
        symbols = symbols[:idx] + sub + symbols[idx + 1:]

    print(b''.join(symbols).decode())

# function which returns a list of non-terminals of the input-node
# def list_of_non_terminals(node: Dict[Tuple, Tuple[float, float]]) -> List[str]:
# if(has_not_multi_nts ==1) input return of parse_symbols


def parse_rules(rules: Union[dict, list]) -> Dict[Tuple, Tuple[float, float]]:
    if isinstance(rules, dict):
        iter_ = rules.items()
    else:
        iter_ = zip_longest(rules, (1.,), fillvalue=1)

    dictionary = dict()
    for rule, count in iter_:
        for rule_ in parse_symbols(rule):
            has_not_multi_nts = np.clip(2 - len([elem for elem in rule_ if isinstance(elem, str)]), 0, 1)
            dictionary[rule_] = (count, has_not_multi_nts)
    return dictionary # noqa: parse_symbols is a generator and rule_ is indeed a tuple!


def parse_symbols(rule: str) -> Tuple[Union[str, bytes]]:
    elements = rule.split()
    if len(elements) == 3 and '.' == elements[1]:
        # to consider e.g. '"\u0020" . "\u07FF"': 1 in the grammar-file
        try:
            expanded = range(ord(elements[0][1:-1]), ord(elements[2][1:-1]) + 1)
        except TypeError:
            expanded = range(ord(elements[0][1:-1].encode().decode('unicode-escape')),
                             ord(elements[2][1:-1].encode().decode('unicode-escape')) + 1)
        for elem in expanded:
            try:
                yield chr(elem).encode(),  # wegen diesem komma ist es ein tuple
            except UnicodeEncodeError:
                pass
    else:
        new_elems = []
        for elem in elements:
            if isinstance(elem, str) and elem.startswith('"') and elem.endswith('"'):
                try:
                    elem = elem[1:-1].encode().decode('unicode-escape').encode()
                    # without decode('unicode-escape').encode would you get \u0020 in output
                    # removes "" and encode it
                except UnicodeDecodeError:
                    elem = elem.encode()
            new_elems.append(elem)
        yield tuple(new_elems)


if __name__ == '__main__':
    main()
