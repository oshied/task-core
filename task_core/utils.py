#!/usr/bin/env python3
"""util classess"""
import logging

LOG = logging.getLogger(__name__)


def merge_dict(base, to_merge, merge_extend=False) -> dict:
    """Deep merge two dictionaries"""
    if not isinstance(to_merge, dict):
        raise Exception(f"Cannot merge {type(to_merge)} into {type(base)}")
    for key, value in to_merge.items():
        if key not in base:
            base[key] = value
        elif isinstance(value, dict):
            base[key] = merge_dict(base.get(key, {}), value, merge_extend)
        elif merge_extend and isinstance(value, (list, tuple, set)):
            if isinstance(base.get(key), tuple):
                base[key] += tuple(value)
            elif isinstance(base.get(key), list):
                base[key].extend(list(value))
            elif isinstance(base.get(key), set):
                base[key].update(set(value))
        else:
            base[key] = to_merge[key]
    return base
