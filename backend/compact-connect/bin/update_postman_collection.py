#!/usr/bin/env python3
"""
Reads a new `latest-oas30.json` file, uses  the cli tool, `openapi2postmanv2`, to convert it to a Postman collection,
then merges the new collection with the existing Postman collection and fixes the auth data.

Note: This script requires the openapi2postmanv2 CLI tool to be installed.
You can install it with: npm install -g openapi-to-postmanv2
"""

import argparse
import json
import os
import subprocess
import sys
import traceback
from typing import Any


def generate_postman_collection(openapi_path: str, output_path: str):
    """Generate a new Postman collection from OpenAPI spec using openapi2postmanv2."""
    try:
        # Since this is just a CLI tool, run locally on data we trust, we will trust the subprocess call
        subprocess.run(  # noqa: S603
            ['openapi2postmanv2', '-s', openapi_path, '-o', output_path],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f'Failed to generate Postman collection: {e.stderr}\n')
        sys.exit(1)
    except FileNotFoundError:
        sys.stderr.write('openapi2postmanv2 not found. Please install it with: npm install -g openapi-to-postmanv2\n')
        sys.exit(1)


def is_folder(item: dict[str, Any]) -> bool:
    """Check if an item is a folder (has only name and item fields)."""
    return set(item.keys()) == {'name', 'item'}


def is_http_method(item: dict[str, Any]) -> bool:
    """Check if an item represents an HTTP method (has either a request with method or direct method field)."""
    return 'request' in item


def remove_incorrect_auth(collection: dict[str, Any]):
    """Recursively remove incorrect auth fields from HTTP methods."""

    def process_items(items: list[dict[str, Any]]):
        for item in items:
            if is_http_method(item):
                sys.stdout.write(f'HTTP method: {item["name"]}\n')
                # Remove incorrect auth field if it exists and is of type 'apikey'
                request = item['request']
                if request.get('auth') and request['auth'].get('type') == 'apikey':
                    sys.stdout.write('Removing auth field\n')
                    # Removing auth will cause the request to inherit the parent folder's auth
                    del request['auth']
                if 'auth' in request and request['auth'] is None:
                    sys.stdout.write('Setting no auth\n')
                    request['auth'] = {'type': 'noauth'}
            elif 'item' in item:
                # Recursively process nested items
                process_items(item['item'])

    process_items(collection['item'])


def find_folder_by_name(items: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Find a folder by name in the items list."""
    for item in items:
        if item.get('name') == name:
            return item
        if 'item' in item:
            result = find_folder_by_name(item['item'], name)
            if result:
                return result
    return None


def find_request_by_path(items: list[dict[str, Any]], path_fragment: str) -> dict[str, Any]:
    """Find a request by a fragment of its path."""
    for item in items:
        if 'request' in item and 'name' in item and path_fragment in item['name']:
            return item
        if 'item' in item:
            result = find_request_by_path(item['item'], path_fragment)
            if result:
                return result
    return None


def preserve_bulk_upload_script(new_collection: dict[str, Any], existing_collection: dict[str, Any]):
    """Preserve the script content in the GET bulk-upload request."""
    # Find the bulk-upload request in both collections
    existing_bulk_upload = find_request_by_path(existing_collection['item'], '/licenses/bulk-upload')
    new_bulk_upload = find_request_by_path(new_collection['item'], '/licenses/bulk-upload')

    if existing_bulk_upload and new_bulk_upload:
        # Check if the existing request has a test script
        if 'event' in existing_bulk_upload:
            for event in existing_bulk_upload['event']:
                if event.get('listen') == 'test' and 'script' in event:
                    # Copy the script to the new request
                    sys.stdout.write('Preserving bulk-upload test script\n')

                    # Ensure the new request has an event array
                    if 'event' not in new_bulk_upload:
                        new_bulk_upload['event'] = []

                    # Check if the new request already has a test event
                    test_event_exists = False
                    for i, event in enumerate(new_bulk_upload['event']):
                        if event.get('listen') == 'test':
                            # Replace the existing test script
                            test_event_exists = True
                            new_bulk_upload['event'][i] = next(
                                (e for e in existing_bulk_upload['event'] if e.get('listen') == 'test'), event
                            )
                            break

                    # If no test event exists, add it
                    if not test_event_exists:
                        new_bulk_upload['event'].append(
                            next(e for e in existing_bulk_upload['event'] if e.get('listen') == 'test')
                        )
                    break


def copy_upload_document_request(new_collection: dict[str, Any], existing_collection: dict[str, Any]):
    """Copy the Upload Document request from the existing collection to the new one."""
    # Find the Upload Document request in the existing collection
    upload_document = next(
        (item for item in existing_collection['item'] if item.get('name') == 'Upload Document'), None
    )

    if upload_document:
        sys.stdout.write('Copying Upload Document request\n')

        # Check if the request already exists in the new collection
        existing_upload_document = next(
            (item for item in new_collection['item'] if item.get('name') == 'Upload Document'), None
        )

        if existing_upload_document:
            # Replace the existing request
            for i, item in enumerate(new_collection['item']):
                if item.get('name') == 'Upload Document':
                    new_collection['item'][i] = upload_document
                    break
        else:
            # Add the request to the new collection
            new_collection['item'].append(upload_document)


def merge_collections(new_collection: dict[str, Any], existing_collection: dict[str, Any]):
    """Merge the existing collection's auth data into the new collection."""
    # Copy top-level auth
    new_collection['auth'] = existing_collection['auth']

    # Copy Staff-Auth folder
    staff_auth = next((item for item in existing_collection['item'] if item['name'] == 'Staff-Auth'), None)
    if staff_auth:
        new_collection['item'].insert(0, staff_auth)

    # Copy provider-users folder auth
    v1_folder = find_folder_by_name(new_collection['item'], 'v1')
    if v1_folder:
        new_provider_users = find_folder_by_name(v1_folder['item'], 'provider-users')
        existing_provider_users = find_folder_by_name(existing_collection['item'], 'provider-users')
        if new_provider_users and existing_provider_users and 'auth' in existing_provider_users:
            new_provider_users['auth'] = existing_provider_users['auth']

    # Preserve the bulk-upload script
    preserve_bulk_upload_script(new_collection, existing_collection)

    # Copy the Upload Document request
    copy_upload_document_request(new_collection, existing_collection)


def set_standard_fields(collection: dict[str, Any]):
    """Set the standard fields for the collection."""
    collection['info']['name'] = 'CompactConnect API'


def cleanup_collection(collection: dict[str, Any]):
    """Remove unnecessary top-level fields from the collection."""
    for field in ['event', 'variable']:
        if field in collection:
            del collection[field]


def main():
    parser = argparse.ArgumentParser(description='Update Postman collection from OpenAPI specification')
    parser.add_argument(
        '-i', '--internal', action='store_true', help='Use internal API specification files instead of regular ones'
    )

    args = parser.parse_args()

    # Define paths relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(script_dir)

    # Determine the base directory based on the internal flag
    base_dir = os.path.join('internal', 'api-specification') if args.internal else os.path.join('api-specification')
    postman_dir = os.path.join('internal', 'postman') if args.internal else os.path.join('postman')

    openapi_path = os.path.join(workspace_dir, 'docs', base_dir, 'latest-oas30.json')
    tmp_path = os.path.join(workspace_dir, 'tmp.json')
    postman_path = os.path.join(workspace_dir, 'docs', postman_dir, 'postman-collection.json')

    # Generate new collection from OpenAPI spec
    generate_postman_collection(openapi_path, tmp_path)

    try:
        # Load the generated and existing collections
        with open(tmp_path) as f:
            new_collection = json.load(f)
        with open(postman_path) as f:
            existing_collection = json.load(f)

        # Process the new collection
        remove_incorrect_auth(new_collection)
        merge_collections(new_collection, existing_collection)
        set_standard_fields(new_collection)
        cleanup_collection(new_collection)

        # Write the updated collection
        with open(postman_path, 'w') as f:
            json.dump(new_collection, f, sort_keys=True, indent=4)
            f.write('\n')

        # Clean up temporary file
        os.remove(tmp_path)

    except FileNotFoundError as e:
        sys.stderr.write(f'Failed to find required file: {e.filename}\n')
        sys.exit(1)
    except json.JSONDecodeError as e:
        sys.stderr.write(f'Failed to parse JSON: {str(e)}\n')
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f'Unexpected error: {str(e)}\n')
        sys.stderr.write(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
