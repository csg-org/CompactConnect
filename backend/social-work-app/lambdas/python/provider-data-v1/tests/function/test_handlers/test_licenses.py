import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from cc_common.exceptions import CCAmbiguousLicenseNumberException, CCInternalException
from common_test.sign_request import sign_request
from moto import mock_aws

from .. import TstFunction

mock_flag_client = MagicMock()
mock_flag_client.return_value = True


@mock_aws
@patch('cc_common.feature_flag_client.is_feature_enabled', mock_flag_client)
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestLicenses(TstFunction):
    def setUp(self):
        super().setUp()
        # Load test keys for signature authentication
        with open('../common/tests/resources/client_private_key.pem') as f:
            self.private_key_pem = f.read()
        with open('../common/tests/resources/client_public_key.pem') as f:
            self.public_key_pem = f.read()

        # Load signature public key into the compact configuration table for functional testing
        self._load_signature_public_key('socw', 'oh', 'test-key-001', self.public_key_pem)

    def _load_signature_public_key(self, compact: str, jurisdiction: str, key_id: str, public_key_pem: str):
        """Load a signature public key into the compact configuration table."""
        item = {
            'pk': f'{compact}#SIGNATURE_KEYS#{jurisdiction}',
            'sk': f'{compact}#JURISDICTION#{jurisdiction}#{key_id}',
            'publicKey': public_key_pem,
            'compact': compact,
            'jurisdiction': jurisdiction,
            'keyId': key_id,
            'createdAt': '2024-01-01T00:00:00Z',
        }
        self._compact_configuration_table.put_item(Item=item)

    def _create_signed_event(self, event: dict) -> dict:
        """Add signature headers to an event for optional signature authentication."""
        from cc_common.config import config

        # Generate current timestamp and nonce
        timestamp = config.current_standard_datetime.isoformat()
        nonce = str(uuid4())
        key_id = 'test-key-001'

        # Sign the request
        headers = sign_request(
            method=event['httpMethod'],
            path=event['path'],
            query_params=event.get('queryStringParameters') or {},
            timestamp=timestamp,
            nonce=nonce,
            key_id=key_id,
            private_key_pem=self.private_key_pem,
        )

        # Add signature headers to event
        event['headers'].update(headers)
        return event

    def test_post_licenses_puts_expected_messages_on_the_queue(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # assert that the message was sent to the preprocessing queue
        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(1, len(queue_messages))

        expected_message = json.loads(event['body'])[0]
        # add the compact, jurisdiction, and eventTime to the expected message
        expected_message['compact'] = 'socw'
        expected_message['jurisdiction'] = 'oh'
        expected_message['eventTime'] = '2024-11-08T23:59:59+00:00'
        self.assertEqual(expected_message, json.loads(queue_messages[0].body))

    def test_post_licenses_does_not_let_request_body_override_path_parameters(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        # Test case where request body attempts to specify a different compact and jurisdiction
        license_data.update({'compact': 'coun', 'jurisdiction': 'ne'})
        event['body'] = json.dumps(
            [
                license_data,
            ]
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # assert that the message was sent to the preprocessing queue
        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(1, len(queue_messages))

        expected_message = json.loads(event['body'])[0]
        # the expected compact and jurisdiction from the path parameters should not be modified
        expected_message['compact'] = 'socw'
        expected_message['jurisdiction'] = 'oh'
        expected_message['eventTime'] = '2024-11-08T23:59:59+00:00'
        self.assertEqual(expected_message, json.loads(queue_messages[0].body))

    def test_post_licenses_invalid_license_type(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data['licenseType'] = 'occupational therapist'
        event['body'] = json.dumps([license_data])

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {
                    '0': {
                        'licenseType': [
                            'Must be one of: licensed clinical social worker, licensed master social worker, '
                            'licensed bachelors social worker.'
                        ]
                    }
                },
            },
            json.loads(resp['body']),
        )

    def test_post_licenses_license_type_not_recognized_in_jurisdiction_returns_400(self):
        from handlers.licenses import post_licenses

        self._load_signature_public_key('socw', 'co', 'test-key-001', self.public_key_pem)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral co/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'co'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data['licenseType'] = 'licensed bachelors social worker'
        event['body'] = json.dumps([license_data])

        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {
                    '0': {
                        'licenseType': [
                            'License type licensed bachelors social worker is not recognized in jurisdiction co.'
                        ]
                    }
                },
            },
            json.loads(resp['body']),
        )

        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(0, len(queue_messages))

    def test_post_licenses_handles_invalid_json_request_body(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        # Test case where list contains strings instead of dictionaries
        event['body'] = json.dumps(
            [
                license_data,
                ['this is totally a license'],
                'and another license',
            ]
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {
                    '1': {'INVALID_JSON_OBJECT': ['Must be a JSON object.']},
                    '2': {'INVALID_JSON_OBJECT': ['Must be a JSON object.']},
                },
            },
            json.loads(resp['body']),
        )

    def test_post_licenses_handles_empty_license_object(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        # Test case where list contains strings instead of dictionaries
        event['body'] = json.dumps([license_data, {}])

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {
                    '1': {
                        'compactEligibility': ['Missing data for required field.'],
                        'dateOfBirth': ['Missing data for required field.'],
                        'dateOfExpiration': ['Missing data for required field.'],
                        'dateOfIssuance': ['Missing data for required field.'],
                        'familyName': ['Missing data for required field.'],
                        'givenName': ['Missing data for required field.'],
                        'homeAddressCity': ['Missing data for required field.'],
                        'homeAddressPostalCode': ['Missing data for required field.'],
                        'homeAddressState': ['Missing data for required field.'],
                        'homeAddressStreet1': ['Missing data for required field.'],
                        'licenseNumber': ['Missing data for required field.'],
                        'licenseScope': ['Missing data for required field.'],
                        'licenseStatus': ['Missing data for required field.'],
                        'licenseType': ['Missing data for required field.'],
                        # ssn is no longer a required field, so its absence is not reported here.
                    }
                },
            },
            json.loads(resp['body']),
        )

    def test_post_licenses_handles_invalid_request_body_not_list(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

        # Test case where request body is not a list
        event['body'] = json.dumps({'message': 'hi'})

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual({'message': 'Request body must be an array of license objects'}, json.loads(resp['body']))

    def test_post_licenses_handles_invalid_request_body_not_json(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

        # Test case where request body is not deserializable
        event['body'] = 'hello'

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'message': 'Invalid JSON: Expecting value: line 1 column 1 (char 0)'}, json.loads(resp['body'])
        )

    def test_post_licenses_handles_empty_request_body(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

        # Test case where request body is not deserializable
        event['body'] = None

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'message': 'Invalid request body'},
            json.loads(resp['body']),
        )

    def test_post_licenses_unknown_field_returns_error(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
            license_data['someOtherField'] = 'foobar'
        event['body'] = json.dumps([license_data])

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {'0': {'someOtherField': ['Unknown field.']}},
            },
            json.loads(resp['body']),
        )

    def test_post_licenses_null_field_returns_error(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
            license_data['licenseStatusName'] = None
        event['body'] = json.dumps([license_data, license_data])

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {
                    '0': {'licenseStatusName': ['Field may not be null.']},
                    '1': {'licenseStatusName': ['Field may not be null.']},
                },
            },
            json.loads(resp['body']),
        )

    def test_post_licenses_returns_400_if_repeated_ssns_detected(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        event['body'] = json.dumps([license_data, license_data])

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {
                    'SSN': 'Same SSN, license type, and license scope detected on multiple rows. '
                    'Every record must have a unique SSN per license type and scope within the same request.',
                },
            },
            json.loads(resp['body']),
        )

    def test_post_licenses_succeeds_with_same_ssn_different_license_types(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

        with open('../common/tests/resources/api/license-post.json') as f:
            license_data_1 = json.load(f)

        # Create second license with same SSN but different license type
        license_data_2 = license_data_1.copy()
        license_data_1['licenseType'] = 'licensed master social worker'
        license_data_2['licenseType'] = 'licensed clinical social worker'

        event['body'] = json.dumps([license_data_1, license_data_2])

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # assert that the messages were sent to the preprocessing queue
        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(2, len(queue_messages))

    def test_post_licenses_strips_whitespace_from_string_fields(self):
        """Test that whitespace is stripped from all string fields in license data."""
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

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

        # Add signature authentication headers
        event = self._create_signed_event(event)

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

    def test_post_licenses_succeeds_without_signature_when_no_keys_configured(self):
        """
        Test that posting licenses succeeds without signature when no signature keys are configured for the
        jurisdiction.
        """
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for socw/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        # Do NOT add signature authentication headers - this should succeed when no keys are configured
        # First, remove any existing signature keys for this jurisdiction
        self._compact_configuration_table.delete_item(
            Key={'pk': 'socw#SIGNATURE_KEYS#oh', 'sk': 'socw#JURISDICTION#oh#test-key-001'}
        )

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # assert that the message was sent to the preprocessing queue
        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(1, len(queue_messages))

        expected_message = json.loads(event['body'])[0]
        # add the compact, jurisdiction, and eventTime to the expected message
        expected_message['compact'] = 'socw'
        expected_message['jurisdiction'] = 'oh'
        expected_message['eventTime'] = '2024-11-08T23:59:59+00:00'
        self.assertEqual(expected_message, json.loads(queue_messages[0].body))


# TODO - once LICENSE_UPLOAD_WITHOUT_SSN_FLAG is removed, drop the flag patches in this class  # noqa: FIX002
#  and keep the tests themselves
@mock_aws
@patch('cc_common.feature_flag_client.is_feature_enabled', mock_flag_client)
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPostLicensesWithoutSsn(TstFunction):
    """
    Tests for uploading a license record without an SSN, identifying the practitioner by the license
    number a previous SSN-bearing upload stored for them.
    """

    def setUp(self):
        super().setUp()
        with open('../common/tests/resources/client_public_key.pem') as f:
            public_key_pem = f.read()
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'socw#SIGNATURE_KEYS#oh',
                'sk': 'socw#JURISDICTION#oh#test-key-001',
                'publicKey': public_key_pem,
                'compact': 'socw',
                'jurisdiction': 'oh',
                'keyId': 'test-key-001',
                'createdAt': '2024-01-01T00:00:00Z',
            }
        )

    def _seed_existing_license(self, **overrides):
        """Store the license record a previous SSN-bearing upload would have created."""
        return self.test_data_generator.put_default_license_record_in_provider_table(value_overrides=overrides)

    def _build_event(self, license_records: list[dict]) -> dict:
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        event['body'] = json.dumps(license_records)
        # this endpoint's signature auth is optional and only enforced when keys are configured
        self._compact_configuration_table.delete_item(
            Key={'pk': 'socw#SIGNATURE_KEYS#oh', 'sk': 'socw#JURISDICTION#oh#test-key-001'}
        )
        return event

    @staticmethod
    def _license_without_ssn(**overrides) -> dict:
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        del license_data['ssn']
        license_data.update(overrides)
        return license_data

    def _published_ingest_events(self) -> list[dict]:
        return [
            json.loads(entry['Detail']) for entry in self._published_entries if entry['DetailType'] == 'license.ingest'
        ]

    def _post(self, license_records: list[dict], failed_entry_count: int = 0):
        """POST the records with the event writer patched, so published entries can be inspected.

        The writer is patched rather than the events client because config.events_client is a
        cached_property: once any test in the session has touched it, patching the class attribute no
        longer affects the instance the feature module holds.
        """
        from handlers.licenses import post_licenses

        event = self._build_event(license_records)
        with patch('license_upload_without_ssn.EventBatchWriter') as mock_event_writer_class:
            mock_event_writer = mock_event_writer_class.return_value.__enter__.return_value
            mock_event_writer.failed_entry_count = failed_entry_count
            try:
                return post_licenses(event, self.mock_context)
            finally:
                self._published_entries = [call.kwargs['Entry'] for call in mock_event_writer.put_event.call_args_list]

    def test_publishes_ingest_event_for_a_known_license_number(self):
        existing_license = self._seed_existing_license()

        resp = self._post([self._license_without_ssn(licenseNumber=existing_license.licenseNumber)])

        self.assertEqual(200, resp['statusCode'])

        # nothing goes to the SSN preprocessing queue, because there is no SSN to strip
        self.assertEqual(0, len(self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)))

        published = self._published_ingest_events()
        self.assertEqual(1, len(published))
        self.assertEqual(str(existing_license.providerId), published[0]['providerId'])
        self.assertEqual(existing_license.ssnLastFour, published[0]['ssnLastFour'])
        self.assertNotIn('ssn', published[0])
        self.assertEqual('2024-11-08T23:59:59+00:00', published[0]['eventTime'])

    def test_returns_400_when_the_license_number_is_unknown(self):
        from license_upload_without_ssn import LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE

        resp = self._post([self._license_without_ssn(licenseNumber='NOT-A-REAL-NUMBER')])

        self.assertEqual(400, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertEqual('Invalid license records in request. See errors for more detail.', body['message'])
        self.assertEqual({'0': {'licenseNumber': [LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE]}}, body['errors'])
        self.assertEqual([], self._published_ingest_events())

    def test_raises_when_the_license_number_maps_to_multiple_providers(self):
        """
        A license number that identifies more than one practitioner is unexpected data, so it surfaces as
        a server error rather than something the state is asked to correct. Like the other internal
        failures on this endpoint, it propagates out of the handler for API Gateway to turn into a 5xx.
        """
        existing_license = self._seed_existing_license()
        self._seed_existing_license(
            providerId='2d3f1b0e-4c5a-4d6b-8e7f-9a0b1c2d3e4f',
            licenseType='licensed master social worker',
        )

        with self.assertRaises(CCAmbiguousLicenseNumberException):
            self._post([self._license_without_ssn(licenseNumber=existing_license.licenseNumber)])

        self.assertEqual([], self._published_ingest_events())

    def test_returns_400_for_duplicate_license_number_and_license_type_in_one_request(self):
        existing_license = self._seed_existing_license()
        license_record = self._license_without_ssn(licenseNumber=existing_license.licenseNumber)

        resp = self._post([license_record, dict(license_record)])

        self.assertEqual(400, resp['statusCode'])
        body = json.loads(resp['body'])
        # the error is reported against the duplicate row, not the first occurrence
        self.assertEqual(
            [
                'Same license number, license type, and license scope detected on multiple rows. Every '
                'record must have a unique license number per license type and scope within the same request.'
            ],
            body['errors']['1']['licenseNumber'],
        )
        self.assertEqual([], self._published_ingest_events())

    def test_accepts_the_same_license_number_for_two_license_types(self):
        """
        A jurisdiction may hold one license number across license types for the same practitioner, so
        those rows are not duplicates of each other.
        """
        existing_license = self._seed_existing_license()
        self._seed_existing_license(licenseType='licensed master social worker')

        resp = self._post(
            [
                self._license_without_ssn(licenseNumber=existing_license.licenseNumber),
                self._license_without_ssn(
                    licenseNumber=existing_license.licenseNumber, licenseType='licensed master social worker'
                ),
            ]
        )

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual(2, len(self._published_ingest_events()))

    def test_processes_a_mixed_batch_down_both_paths(self):
        existing_license = self._seed_existing_license()

        with open('../common/tests/resources/api/license-post.json') as f:
            license_with_ssn = json.load(f)
        license_with_ssn['licenseType'] = 'licensed master social worker'

        resp = self._post([license_with_ssn, self._license_without_ssn(licenseNumber=existing_license.licenseNumber)])

        self.assertEqual(200, resp['statusCode'])
        # the SSN-bearing record still goes through the preprocessor
        self.assertEqual(1, len(self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)))
        self.assertEqual(1, len(self._published_ingest_events()))

    def test_raises_when_the_event_bus_rejects_entries(self):
        """Matches the existing behavior for a failed preprocessing-queue send: raise, so the caller sees
        a server error and the failure is alarmed on rather than silently reported as success."""
        existing_license = self._seed_existing_license()

        with self.assertRaises(CCInternalException):
            self._post(
                [self._license_without_ssn(licenseNumber=existing_license.licenseNumber)],
                failed_entry_count=1,
            )

    def test_returns_400_when_the_license_number_is_missing(self):
        """licenseNumber is required on this endpoint, so an upload without it cannot identify anyone."""
        license_record = self._license_without_ssn()
        del license_record['licenseNumber']

        resp = self._post([license_record])

        self.assertEqual(400, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertEqual({'0': {'licenseNumber': ['Missing data for required field.']}}, body['errors'])

    def test_returns_400_when_the_matched_provider_has_no_indexed_license_number(self):
        """
        licenseNumber is optional on license records, so a practitioner whose record predates license
        number collection cannot be resolved and must still be uploaded with their SSN.
        """
        from license_upload_without_ssn import LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE

        license_data = self.test_data_generator.generate_default_license()
        license_record = license_data.serialize_to_database_record()
        del license_record['licenseNumber']
        self.test_data_generator.store_record_in_provider_table(license_record)

        resp = self._post([self._license_without_ssn(licenseNumber='A0608337260')])

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'0': {'licenseNumber': [LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE]}},
            json.loads(resp['body'])['errors'],
        )

    # TODO - remove this test once the LICENSE_UPLOAD_WITHOUT_SSN_FLAG scaffolding is removed  # noqa: FIX002
    def test_returns_400_when_the_feature_flag_is_disabled(self):
        from handlers.licenses import post_licenses
        from license_upload_without_ssn import FLAG_DISABLED_ERROR_MESSAGE

        existing_license = self._seed_existing_license()
        event = self._build_event([self._license_without_ssn(licenseNumber=existing_license.licenseNumber)])

        with patch('handlers.licenses.license_upload_without_ssn_flag_enabled', False):
            resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(FLAG_DISABLED_ERROR_MESSAGE, json.loads(resp['body'])['message'])
        self.assertEqual(0, len(self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)))
