import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestLicenses(TstFunction):
    def test_post_licenses_puts_expected_messages_on_the_queue(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # assert that the message was sent to the preprocessing queue
        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(1, len(queue_messages))

        expected_message = json.loads(event['body'])[0]
        # add the compact, jurisdiction, and eventTime to the expected message
        expected_message['compact'] = 'aslp'
        expected_message['jurisdiction'] = 'oh'
        expected_message['eventTime'] = '2024-11-08T23:59:59+00:00'
        self.assertEqual(expected_message, json.loads(queue_messages[0].body))

    def test_post_licenses_invalid_license_type(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data['licenseType'] = 'occupational therapist'
        event['body'] = json.dumps([license_data])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'message': {'0': {'licenseType': ['Must be one of: audiologist, speech-language pathologist.']}}},
            json.loads(resp['body']),
        )

    def test_post_licenses_unknown_field_returns_error(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
            license_data['someOtherField'] = 'foobar'
        event['body'] = json.dumps([license_data])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual({'message': {'0': {'someOtherField': ['Unknown field.']}}}, json.loads(resp['body']))

    def test_post_licenses_null_field_returns_error(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
            license_data['licenseStatusName'] = None
        event['body'] = json.dumps([license_data, license_data])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': {
                    '0': {'licenseStatusName': ['Field may not be null.']},
                    '1': {'licenseStatusName': ['Field may not be null.']},
                }
            },
            json.loads(resp['body']),
        )

    def test_post_licenses_strips_whitespace_from_string_fields(self):
        """Test that whitespace is stripped from all string fields in license data."""
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}

        # Load base license data and add whitespace to string fields
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
            request_body = license_data.copy()

        # Add whitespace around various string fields
        request_body['givenName'] = '  ' + license_data['givenName'] + '  '
        request_body['familyName'] = '  ' + license_data['familyName'] + '  '
        request_body['licenseType'] = '  ' + license_data['licenseType'] + '  '
        request_body['homeAddressStreet1'] = '  ' + license_data['homeAddressStreet1'] + '  '
        request_body['homeAddressCity'] = '  ' + license_data['homeAddressCity'] + '  '
        request_body['homeAddressState'] = '  ' + license_data['homeAddressState'] + '  '
        request_body['homeAddressPostalCode'] = '  ' + license_data['homeAddressPostalCode'] + '  '

        # Add optional fields with whitespace
        request_body['middleName'] = '  ' + license_data['middleName'] + '  '
        request_body['suffix'] = '  ' + license_data.get('suffix', 'Jr.') + '  '
        request_body['licenseNumber'] = '  ' + license_data['licenseNumber'] + '  '
        request_body['emailAddress'] = '  ' + license_data['emailAddress'] + '  '

        event['body'] = json.dumps([request_body])

        resp = post_licenses(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # Verify the message was sent to the preprocessing queue with trimmed data
        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(1, len(queue_messages))

        message_data = json.loads(queue_messages[0].body)

        # Verify that whitespace was stripped from all string fields
        self.assertEqual(license_data['givenName'], message_data['givenName'])  # Should be trimmed
        self.assertEqual(license_data['familyName'], message_data['familyName'])  # Should be trimmed
        self.assertEqual(license_data['licenseType'], message_data['licenseType'])  # Should be trimmed
        self.assertEqual(license_data['homeAddressStreet1'], message_data['homeAddressStreet1'])  # Should be trimmed
        self.assertEqual(license_data['homeAddressCity'], message_data['homeAddressCity'])  # Should be trimmed
        self.assertEqual(license_data['homeAddressState'], message_data['homeAddressState'])  # Should be trimmed
        self.assertEqual(
            license_data['homeAddressPostalCode'], message_data['homeAddressPostalCode']
        )  # Should be trimmed
        self.assertEqual(license_data['middleName'], message_data['middleName'])  # Should be trimmed
        self.assertEqual(license_data.get('suffix', 'Jr.'), message_data['suffix'])  # Should be trimmed
        self.assertEqual(license_data['licenseNumber'], message_data['licenseNumber'])  # Should be trimmed
        self.assertEqual(license_data['emailAddress'], message_data['emailAddress'])  # Should be trimmed
