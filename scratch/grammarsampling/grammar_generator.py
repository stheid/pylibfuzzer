import os.path
from itertools import zip_longest
from random import choices, choice
from typing import Union, Dict, Tuple

import click
import numpy as np
import yaml
from tqdm import tqdm


@click.command()
@click.option('--gram', default='gram.yml', help='file providing the grammar.')
@click.option('--start', default='element', help='non-terminal to start with.')
@click.option('--steps', default=1, help='number of texts to be generated.')
@click.option('--num_output_files', default=1, help='number of output files to be generated.')
@click.option('--out_dir', default='generated_inputs/', help='creates the directory to store output files in.')
def main(gram: str, start: str, steps: int, num_output_files: int = 1, out_dir: str = 'generated_inputs/'):
    num_files_to_generate = num_output_files
    export_dir = out_dir
    if not os.path.exists(export_dir):
        os.mkdir(export_dir)
    with open(gram, 'r') as f:
        try:
            grammar = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc)

    grammar = {k: parse_rules(rules) for k, rules in grammar.items()}

    # todo: debug yaml dump -> creates error for non-printable characters.
    # export(grammar, start)
    for ix in tqdm(range(num_files_to_generate)):
        for _ in range(steps):
            symbols = list(parse_symbols(start))[-1]
            # TODO: counting the number of non-terminals and so on is very inefficient.
            while any([isinstance(symb, str) for symb in symbols]):
                # select first non-terminal
                idx, nt = choice([(i, x) for i, x in enumerate(symbols) if isinstance(x, str)])

                # select random rule to expand
                try:
                    rules, weights = zip(*grammar[nt].items())
                    weights = np.array(weights) + 1e-7

                    # the soft mask is a weighted mixture between a uniform random distribution and a hard mask that will
                    # only allow certain rules (the ones that do not have more than one non-terminal) alpha may be any
                    # value between 0 and 1 to mix between the masked and unmasked distribution
                    alpha = 1 if len(symbols) < 1000 else 0
                    soft_mask = (alpha, 1 - alpha) @ \
                                np.hstack((np.ones_like(weights[:, 1]), weights[:, 1] + 1e-7)).reshape((-1, 2)).T

                    weights = weights[:, 0] * soft_mask
                    weights = weights / weights.sum(axis=0)
                    sub = choices(rules, weights)[-1]
                    # print(f"nt:{nt} choice: {sub}")

                    # calculate
                    symbols = symbols[:idx] + sub + symbols[idx + 1:]
                except Exception as e:
                    print("Exception occurred : ", e)
                    print(nt)
                    quit()

            out = b''.join(symbols)
            with open(f'{export_dir}sample_grammar_{ix}.txt', 'wb') as f:
                f.write(out)


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
    return dictionary  # noqa: parse_symbols is an generator generating tuples


def parse_symbols(rule: str) -> Tuple[Union[str, bytes]]:
    elements = rule.split()
    if len(elements) == 3 and '.' == elements[1]:
        # processing range type rules
        try:
            expanded = range(ord(elements[0][1:-1]), ord(elements[2][1:-1]) + 1)
        except TypeError:
            expanded = range(ord(elements[0][1:-1].encode().decode('unicode-escape')),
                             ord(elements[2][1:-1].encode().decode('unicode-escape')) + 1)
        for elem in expanded:
            try:
                elem_bytes = chr(elem).encode()
                if len(elem_bytes) > 1:
                    # print(f"Warning: failed to encode char:{elem}, trying with raw_unicode_escape")
                    elem_bytes = chr(elem).encode('raw_unicode_escape')
                yield elem_bytes,
            except UnicodeEncodeError:
                pass
    else:
        new_elems = []
        for elem in elements:
            if isinstance(elem, str) and elem.startswith('"') and elem.endswith('"'):
                try:
                    elem = elem[1:-1].encode().decode('unicode-escape').encode('raw_unicode_escape')
                except UnicodeDecodeError:
                    # elem = elem[1:-1].encode()
                    elem = bytes([ord(x) for x in elem[1:-1]])
            new_elems.append(elem)
        yield tuple(new_elems)


def export(grammar, start):
    with open('out.yml', 'wb') as f:
        yaml.dump(dict(startSymbol=dict(value=start),
                       prodRules={k: [
                           dict(substitution=[
                               dict(
                                   type=("terminal" if isinstance(elem, bytes) else 'nonterminal'),
                                   value=(elem if isinstance(elem, str) else str(elem, "utf-8"))) for elem in sub],
                               # the weight
                               weight=weights[0])
                           for sub, weights in rule.items()
                       ] for k, rule in grammar.items()}), f)


if __name__ == '__main__':
    main()
