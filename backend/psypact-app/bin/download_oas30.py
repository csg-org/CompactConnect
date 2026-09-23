#!/usr/bin/env python3
"""
Download OpenAPI v3 specifications from AWS API Gateway for both StateApi and LicenseApi.

This script uses boto3 and CLI-configured credentials to find the APIs and download
their OpenAPI specifications to the appropriate local files.
"""

import argparse
import json
import os
import sys

import boto3
from botocore.exceptions import ClientError


def find_api_by_name(apigateway_client, api_name: str) -> str:
    """
    Find an API Gateway API by name and return its ID.

    :param apigateway_client: Boto3 API Gateway client
    :param api_name: Name of the API to find
    :return: API ID if found, None otherwise
    """
    try:
        response = apigateway_client.get_rest_apis()
        for api in response['items']:
            if api['name'] == api_name:
                return api['id']
        raise RuntimeError(f'API {api_name} not found')
    except ClientError as e:
        raise RuntimeError(f'Error finding API {api_name}: {e}') from e


def get_api_stages(apigateway_client, api_id: str) -> list[str]:
    """
    Get all stages for an API.

    :param apigateway_client: Boto3 API Gateway client
    :param api_id: ID of the API
    :return: List of stage names
    """
    try:
        response = apigateway_client.get_stages(restApiId=api_id)
        return [stage['stageName'] for stage in response['item']]
    except ClientError as e:
        raise RuntimeError(f'Error getting stages for API {api_id}: {e}') from e


def download_openapi_spec(apigateway_client, api_id: str, stage_name: str) -> dict:
    """
    Download OpenAPI v3 specification from API Gateway.

    :param apigateway_client: Boto3 API Gateway client
    :param api_id: ID of the API
    :param stage_name: Name of the stage
    :return: OpenAPI specification as dict
    """
    try:
        response = apigateway_client.get_export(
            restApiId=api_id, stageName=stage_name, exportType='oas30', accepts='application/json'
        )

        # Parse the response body
        spec_json = response['body'].read().decode('utf-8')
        return json.loads(spec_json)

    except ClientError as e:
        raise RuntimeError(f'Error downloading OpenAPI spec for API {api_id}, stage {stage_name}: {e}') from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f'Error parsing OpenAPI spec JSON for API {api_id}, stage {stage_name}: {e}') from e


def save_spec_to_file(spec: dict, file_path: str) -> None:
    """
    Save OpenAPI specification to a JSON file.

    :param spec: OpenAPI specification as dict
    :param file_path: Path to save the file
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w') as f:
            json.dump(spec, f, indent=2)
            f.write('\n')

    except Exception as e:
        raise RuntimeError(f'Error saving spec to {file_path}: {e}') from e


def update_server_urls(spec: dict, api_name: str) -> None:
    """
    Update the server URLs to use consistent beta domains.

    :param spec: OpenAPI specification as dict
    :param api_name: Name of the API to determine the correct URL
    """
    if 'servers' not in spec:
        return

    # Determine the correct base URL based on API name
    if api_name == 'StateApi':
        base_url = 'https://state-api.beta.compactconnect.org'
    elif api_name == 'LicenseApi':
        base_url = 'https://api.beta.compactconnect.org'
    elif api_name == 'SearchApi':
        base_url = 'https://search.beta.compactconnect.org'
    else:
        # Keep original URL if API name is not recognized
        return

    # Update all server URLs
    for server in spec['servers']:
        if 'url' in server:
            server['url'] = base_url

    sys.stdout.write(f'Updated server URLs to use: {base_url}\n')


def download_api_spec(api_name: str, output_path: str) -> None:
    """
    Download OpenAPI specification for a specific API.

    :param api_name: Name of the API to download
    :param output_path: Path to save the specification
    """
    apigateway_client = boto3.client('apigateway')

    # Find the API
    api_id = find_api_by_name(apigateway_client, api_name)

    sys.stdout.write(f'Found API "{api_name}" with ID: {api_id}\n')

    # Get stages
    stages = get_api_stages(apigateway_client, api_id)

    # Use the first stage (assuming single stage)
    if len(stages) != 1:
        raise RuntimeError('API has an unexpected number of stages!')
    stage_name = stages[0]
    sys.stdout.write(f'Using stage: {stage_name}\n')

    # Download the specification
    spec = download_openapi_spec(apigateway_client, api_id, stage_name)

    # Update server URLs to use consistent beta domains
    update_server_urls(spec, api_name)

    # Save to file
    save_spec_to_file(spec, output_path)


def main():
    parser = argparse.ArgumentParser(description='Download OpenAPI v3 specifications from AWS API Gateway')
    parser.add_argument('--state-api-only', action='store_true', help='Download only the StateApi specification')
    parser.add_argument('--license-api-only', action='store_true', help='Download only the LicenseApi specification')
    parser.add_argument('--search-api-only', action='store_true', help='Download only the SearchApi specification')

    args = parser.parse_args()

    # Define paths relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(script_dir)

    # Define output paths
    state_api_path = os.path.join(workspace_dir, 'docs', 'api-specification', 'latest-oas30.json')
    license_api_path = os.path.join(workspace_dir, 'docs', 'internal', 'api-specification', 'latest-oas30.json')
    search_api_path = os.path.join(workspace_dir, 'docs', 'search-internal', 'api-specification', 'latest-oas30.json')

    # Download StateApi (external API)
    if not args.license_api_only and not args.search_api_only:
        sys.stdout.write('\n=== Downloading StateApi specification ===\n')
        download_api_spec('StateApi', state_api_path)

    # Download LicenseApi (internal API)
    if not args.state_api_only and not args.search_api_only:
        sys.stdout.write('\n=== Downloading LicenseApi specification ===\n')
        download_api_spec('LicenseApi', license_api_path)

    # Download SearchApi (search internal API)
    if not args.state_api_only and not args.license_api_only:
        sys.stdout.write('\n=== Downloading SearchApi specification ===\n')
        download_api_spec('SearchApi', search_api_path)

    sys.stdout.write('\nAll specifications downloaded successfully!\n')
    sys.exit(0)


if __name__ == '__main__':
    main()
