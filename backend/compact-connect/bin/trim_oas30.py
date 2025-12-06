#!/usr/bin/env python3
"""A quick convenience script for trimming auto-generated schema to supported API paths"""

import argparse
import json
import os
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
    parser = argparse.ArgumentParser(description='Trim OpenAPI specification to supported API paths')
    parser.add_argument(
        '-i', '--internal', action='store_true', help='Use internal API specification files instead of regular ones'
    )
    parser.add_argument('-s', '--search', action='store_true', help='Use search API specification files')

    args = parser.parse_args()

    # Get script directory and workspace directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(script_dir)

    # Determine the base directory based on the flags
    if args.search:
        base_dir = os.path.join('docs', 'search-internal', 'api-specification')
    elif args.internal:
        base_dir = os.path.join('docs', 'internal', 'api-specification')
    else:
        base_dir = os.path.join('docs', 'api-specification')
    file_path = os.path.join(workspace_dir, base_dir, 'latest-oas30.json')

    with open(file_path) as f:
        original_spec = json.load(f)

    new_spec = strip_sort_paths(original_spec)
    new_spec = strip_options_endpoints(new_spec)

    with open(file_path, 'w') as f:
        json.dump(new_spec, f, indent=2)
        f.write('\n')
