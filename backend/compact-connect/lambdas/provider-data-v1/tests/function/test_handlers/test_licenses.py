import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestLicenses(TstFunction):
    def test_post_licenses(self):
        from handlers.licenses import post_licenses

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read aslp/write aslp/oh.write'
        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'oh'
        }
        with open('tests/resources/api/license-post.json', 'r') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

    def test_post_licenses_invalid_license_type(self):
        from handlers.licenses import post_licenses

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read aslp/write aslp/oh.write'
        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'oh'
        }
        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = json.load(f)
        license_data['licenseType'] = 'occupational therapist'
        event['body'] = json.dumps([license_data])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
