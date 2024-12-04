# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing
import os
import time
from datetime import UTC, datetime

import requests

# This script is used to test the military affiliations upload flow of the Compact Connect API.
# It is currently configured to run locally against a sandbox environment. To run this script, you must
# set the following constant values to match your environment
# This should include the https:// prefix  (ex. https://sandbox.compactconnect.org)
API_URL = os.environ['API_URL']
# The cognito ID token issued when the user is authenticated. This can be fetched by logging
# into the Compact Connect UI of your test environment and copying the value of 'id_token_licensee' from the
# browser's local storage.
TEST_USER_COGNITO_ID_TOKEN = os.environ['TEST_PROVIDER_USER_ID_TOKEN']

def test_military_affiliation_upload():
    # Step 1: Create a military affiliation record in the DB using the POST
    # '/v1/provider-users/me/military-affiliation' endpoint.
    # Step 2: Get the S3 pre-signed URL from the response body and use it to upload a test pdf file to the S3 bucket.
    # Step 3: Verify that the test pdf file was uploaded successfully by checking the response status code.
    # Step 4: Get the provider data from the GET '/v1/provider-users/me' endpoint and verify that the military
    # affiliation record is active.
    headers = {
        'Authorization': 'Bearer ' + TEST_USER_COGNITO_ID_TOKEN,
    }

    post_body = {
        'fileNames': ['military_affiliation.pdf'],
        'affiliationType': 'militaryMember',
    }
    post_api_response = requests.post(
        url=API_URL + '/v1/provider-users/me/military-affiliation', headers=headers, json=post_body, timeout=10
    )

    assert (
        post_api_response.status_code == 200
    ), f'Failed to POST military affiliations record. Response: {post_api_response.json()}'

    '''
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
    '''
    post_api_response_json = post_api_response.json()
    # Use the S3 pre-signed URL to upload a test file to the S3 bucket.
    with open('../resources/test_files/military_affiliation.pdf', 'rb') as test_file:
        files = {'file': (test_file.name, test_file)}
        pre_signed_url = post_api_response_json['documentUploadFields'][0]['url']
        pre_signed_fields = post_api_response_json['documentUploadFields'][0]['fields']
        s3_upload_response = requests.post(pre_signed_url, files=files, data=pre_signed_fields, timeout=10)
        assert (
            s3_upload_response.status_code == 204
        ), f'Failed to upload test file to S3. Response: {s3_upload_response.text}'

    # Wait a couple of seconds for S3 event to trigger the lambda that processes the uploaded file
    # and updates the military affiliation record status to 'active'.
    time.sleep(2)

    # Get the provider data from the GET '/v1/provider-users/me' endpoint.
    get_provider_data_response = requests.get(API_URL + '/v1/provider-users/me', headers=headers, timeout=10)
    assert (
        get_provider_data_response.status_code == 200
    ), f'Failed to GET provider data. Response: {get_provider_data_response.json()}'
    # check the response for a top level 'militaryAffiliations' field and verify it has a record with an upload date of
    # today and a status of 'active'
    provider_data = get_provider_data_response.json()
    military_affiliations = provider_data.get('militaryAffiliations')
    assert military_affiliations, 'No military affiliations found in provider data'
    today = datetime.now(tz=UTC).date().isoformat()
    matching_military_affiliation = next(
        (ma for ma in military_affiliations if datetime.fromisoformat(ma['dateOfUpload']).date().isoformat() == today),
        None,
    )
    assert matching_military_affiliation, f'No military affiliation record found for today ({today})'
    assert matching_military_affiliation['status'] == 'active', 'Military affiliation record is not active'

    print(f'Successfully added military affiliation record: {matching_military_affiliation}')


def test_military_affiliation_patch_update():
    # Step 1: Update the military affiliation status in the DB using the PATCH
    # '/v1/provider-users/me/military-affiliation' endpoint.
    # Step 4: Get the provider data from the GET '/v1/provider-users/me' endpoint and verify that all the military
    # affiliation records are inactive.
    headers = {
        'Authorization': 'Bearer ' + TEST_USER_COGNITO_ID_TOKEN,
    }

    patch_body = {
        'status': 'inactive',
    }
    patch_api_response = requests.patch(
        url=API_URL + '/v1/provider-users/me/military-affiliation', headers=headers, json=patch_body, timeout=10
    )

    assert (
        patch_api_response.status_code == 200
    ), f'Failed to PATCH military affiliations record. Response: {patch_api_response.json()}'

    get_provider_data_response = requests.get(API_URL + '/v1/provider-users/me', headers=headers, timeout=10)
    assert (
        get_provider_data_response.status_code == 200
    ), f'Failed to GET provider data. Response: {get_provider_data_response.json()}'

    provider_data = get_provider_data_response.json()
    military_affiliations = provider_data.get('militaryAffiliations')
    assert all(
        ma['status'] == 'inactive' for ma in military_affiliations
    ), f'Not all military affiliation records are inactive: {military_affiliations}'

    print(f'Successfully updated military affiliation records: {military_affiliations}')


if __name__ == '__main__':
    test_military_affiliation_upload()
    test_military_affiliation_patch_update()
