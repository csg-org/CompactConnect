# ruff: noqa: T201 we use print statements for smoke testing
#!/usr/bin/env python3
import os
import time
from datetime import UTC, datetime

import requests
from smoke_common import (
    SmokeTestFailureException,
    get_api_base_url,
    get_provider_user_auth_headers_cached,
    load_smoke_test_env,
)

# This script is used to test the military affiliations upload flow against a sandbox environment
# of the Compact Connect API. It requires that you have a provider user set up in the sandbox environment.
# Your sandbox account must also be deployed with the "security_profile": "VULNERABLE" setting in your cdk.context.json

# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def test_military_affiliation_upload():
    # Step 1: Create a military affiliation record in the DB using the POST
    # '/v1/provider-users/me/military-affiliation' endpoint.
    # Step 2: Get the S3 pre-signed URL from the response body and use it to upload a test pdf file to the S3 bucket.
    # Step 3: Verify that the test pdf file was uploaded successfully by checking the response status code.
    # Step 4: Get the provider data from the GET '/v1/provider-users/me' endpoint and verify that the military
    # affiliation record is active.
    headers = get_provider_user_auth_headers_cached()

    post_body = {
        'fileNames': ['military_affiliation.pdf'],
        'affiliationType': 'militaryMember',
    }
    post_api_response = requests.post(
        url=get_api_base_url() + '/v1/provider-users/me/military-affiliation',
        headers=headers,
        json=post_body,
        timeout=10,
    )

    if post_api_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to POST military affiliations record. Response: {post_api_response.json()}'
        )
    print('Successfully called POST military affiliation endpoint.')

    """
    The response body should include S3 pre-sign url form in this format:
    {
    ...
        'documentUploadFields': [
            {
                'fields': {
                    'key': f'compact/{TEST_COMPACT}/provider/{provider_id}/document-type/military-affiliations'
                    f'/{today}/1234#military_affiliation.pdf',
                    'x-amz-algorithm': 'AWS4-HMAC-SHA256',
                },
                'url': 'https://provider-user-bucket.s3.amazonaws.com/',
            }
        ],
        'fileNames': ['military_affiliation.pdf'],
        'status': 'initializing',
    }
    """
    post_api_response_json = post_api_response.json()
    # Use the S3 pre-signed URL to upload a test file to the S3 bucket.
    with open(
        os.path.join(os.path.dirname(__file__), '../resources/test_files/military_affiliation.pdf'), 'rb'
    ) as test_file:
        files = {'file': (test_file.name, test_file)}
        pre_signed_url = post_api_response_json['documentUploadFields'][0]['url']
        pre_signed_fields = post_api_response_json['documentUploadFields'][0]['fields']
        s3_upload_response = requests.post(pre_signed_url, files=files, data=pre_signed_fields, timeout=10)
        if s3_upload_response.status_code != 204:
            raise SmokeTestFailureException(f'Failed to upload test file to S3. Response: {s3_upload_response.text}')
        print('Successfully uploaded test file to S3')

    # Wait for S3 event to trigger the lambda that processes the uploaded file
    # and updates the military affiliation record status to 'active'.
    time.sleep(10)

    # Get the provider data from the GET '/v1/provider-users/me' endpoint.
    get_provider_data_response = requests.get(get_api_base_url() + '/v1/provider-users/me', headers=headers, timeout=10)
    if get_provider_data_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to GET provider data. Response: {get_provider_data_response.json()}')

    provider_data = get_provider_data_response.json()
    military_affiliations = provider_data.get('militaryAffiliations')
    if not military_affiliations:
        raise SmokeTestFailureException('No military affiliations found in provider data')
    today = datetime.now(tz=UTC).date().isoformat()
    matching_military_affiliation = next(
        (ma for ma in military_affiliations if datetime.fromisoformat(ma['dateOfUpload']).date().isoformat() == today),
        None,
    )
    if not matching_military_affiliation:
        raise SmokeTestFailureException(
            f'No military affiliation record found for today. ' f'Military affiliations: ({military_affiliations})'
        )
    if matching_military_affiliation['status'] != 'active':
        raise SmokeTestFailureException(
            f'Military affiliation record is not active. ' f'Status: {matching_military_affiliation["status"]}'
        )

    print(f'Successfully added military affiliation record: {matching_military_affiliation}')


def test_military_affiliation_patch_update():
    # Step 1: Update the military affiliation status in the DB using the PATCH
    # '/v1/provider-users/me/military-affiliation' endpoint.
    # Step 4: Get the provider data from the GET '/v1/provider-users/me' endpoint and verify that all the military
    # affiliation records are inactive.
    headers = get_provider_user_auth_headers_cached()

    patch_body = {
        'status': 'inactive',
    }
    patch_api_response = requests.patch(
        url=get_api_base_url() + '/v1/provider-users/me/military-affiliation',
        headers=headers,
        json=patch_body,
        timeout=10,
    )

    if patch_api_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to PATCH military affiliations record. Response: {patch_api_response.json()}'
        )

    get_provider_data_response = requests.get(get_api_base_url() + '/v1/provider-users/me', headers=headers, timeout=10)
    if get_provider_data_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to GET provider data. Response: {get_provider_data_response.json()}')

    provider_data = get_provider_data_response.json()
    military_affiliations = provider_data.get('militaryAffiliations')
    if not all(ma['status'] == 'inactive' for ma in military_affiliations):
        raise SmokeTestFailureException(f'Not all military affiliation records are inactive: {military_affiliations}')

    print(f'Successfully updated military affiliation records: {military_affiliations}')


if __name__ == '__main__':
    load_smoke_test_env()
    test_military_affiliation_upload()
    test_military_affiliation_patch_update()
