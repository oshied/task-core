# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
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
