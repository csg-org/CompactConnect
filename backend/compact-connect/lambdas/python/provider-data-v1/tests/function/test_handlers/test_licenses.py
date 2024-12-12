import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestLicenses(TstFunction):
    def test_post_licenses(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/write aslp/oh.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

    def test_post_licenses_invalid_license_type(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/write aslp/oh.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data['licenseType'] = 'occupational therapist'
        event['body'] = json.dumps([license_data])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
