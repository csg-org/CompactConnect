#!/usr/bin/env python3
"""A quick convenience script for trimming auto-generated schema to supported API paths"""

import json
from collections import OrderedDict


def strip_sort_paths(oas30: dict) -> dict:
    paths = oas30['paths']
    new_paths = OrderedDict()
    trimmed_path_keys = sorted([key for key in paths.keys() if key.startswith('/v1/')])
    for path_key in trimmed_path_keys:
        new_paths[path_key] = paths[path_key]
    oas30['paths'] = new_paths
    return oas30


def strip_options_endpoints(oas30: dict) -> dict:
    """
    The OPTIONS endpoints add a lot of noise to the spec and are not important to developers, so we'll omit them.
    """
    for path_key, path_value in oas30['paths'].items():
        oas30['paths'][path_key] = {
            method_key: method_value for method_key, method_value in path_value.items() if method_key != 'options'
        }
    # Remove now empty paths
    oas30['paths'] = {path_key: path_value for path_key, path_value in oas30['paths'].items() if path_value}
    return oas30


if __name__ == '__main__':
    with open('docs/api-specification/latest-oas30.json') as f:
        original_spec = json.load(f)

    new_spec = strip_sort_paths(original_spec)
    new_spec = strip_options_endpoints(new_spec)

    with open('docs/api-specification/latest-oas30.json', 'w') as f:
        json.dump(new_spec, f, indent=2)
        f.write('\n')
