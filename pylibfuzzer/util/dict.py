from functools import reduce, partial
from typing import List

import dpath.util as dutil


def ravel(flat_dict) -> dict:
    # renest kwargs
    d = dict()
    for k, v in flat_dict.items():
        dutil.new(d, k, v)
    return d


def mergeall(dicts: List[dict]) -> dict:
    return reduce(partial(dutil.merge, flags=dutil.MERGE_REPLACE), dicts)
