import json
from datetime import datetime
from unittest.mock import patch

from common_test.test_constants import DEFAULT_ADVERSE_ACTION_ID, DEFAULT_DATE_OF_UPDATE_TIMESTAMP
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
MOCK_SSN = '123-12-1234'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestGetProvider(TstFunction):
    def setUp(self):
        super().setUp()

    def _when_testing_provider_user_event_with_custom_claims(self):
        self._load_provider_data()
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_privilege_update_record_in_provider_table(
            value_overrides={
                'updateType': 'encumbrance',
                'encumbranceDetails': {
                    'clinicalPrivilegeActionCategories': ['Non-compliance With Requirements'],
                    'licenseJurisdiction': 'oh',
                    'adverseActionId': DEFAULT_ADVERSE_ACTION_ID,
                },
                'createDate': datetime.fromisoformat('2023-05-05T12:59:59+00:00'),
                'effectiveDate': datetime.fromisoformat('2022-05-05T12:59:59+00:00'),
            }
        )
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'GET'
            event['resource'] = '/v1/provider-users/me/jurisdiction/{jurisdiction}/licenseType/{licenseType}/history'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = test_provider.providerId
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_provider.compact
            event['pathParameters'] = {'jurisdiction': 'ne', 'licenseType': 'slp'}

        return event

    def _when_testing_public_endpoint(self):
        self._load_provider_data()
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_privilege_update_record_in_provider_table(
            value_overrides={
                'updateType': 'encumbrance',
                'encumbranceDetails': {
                    'clinicalPrivilegeActionCategories': ['Non-compliance With Requirements'],
                    'licenseJurisdiction': 'oh',
                    'adverseActionId': DEFAULT_ADVERSE_ACTION_ID,
                },
                'createDate': datetime.fromisoformat('2023-05-05T12:59:59+00:00'),
                'effectiveDate': datetime.fromisoformat('2022-05-05T12:59:59+00:00'),
            }
        )
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'GET'
            event['resource'] = (
                '/v1/public/compacts/{compact}/providers/{providerId}/jurisdiction/{jurisdiction}/licenseType/{licenseType}/history'
            )
            event['pathParameters'] = {
                'jurisdiction': 'ne',
                'licenseType': 'slp',
                'compact': test_provider.compact,
                'providerId': test_provider.providerId,
            }

        return event

    def _when_testing_staff_endpoint(self):
        self._load_provider_data()
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_privilege_update_record_in_provider_table(
            value_overrides={
                'updateType': 'encumbrance',
                'encumbranceDetails': {
                    'clinicalPrivilegeActionCategories': ['Non-compliance With Requirements', 'Misconduct or Abuse'],
                    'licenseJurisdiction': 'oh',
                    'adverseActionId': DEFAULT_ADVERSE_ACTION_ID,
                },
                'createDate': datetime.fromisoformat('2023-05-05T12:59:59+00:00'),
                'effectiveDate': datetime.fromisoformat('2022-05-05T12:59:59+00:00'),
            }
        )
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'GET'
            event['resource'] = (
                '/v1/compacts/{compact}/providers/{providerId}/privileges/jurisdiction/{jurisdiction}/licenseType/{licenseType}/history'
            )
            event['pathParameters'] = {
                'jurisdiction': 'ne',
                'licenseType': 'slp',
                'compact': test_provider.compact,
                'providerId': test_provider.providerId,
            }

        return event

    # Test not found privilege throws exception
    def test_privilege_not_found_returns_404_provider_user_me(self):
        from handlers.privilege_history import privilege_history_handler

        event = self._when_testing_provider_user_event_with_custom_claims()

        event['pathParameters'] = {'jurisdiction': 'ma', 'licenseType': 'slp'}

        resp = privilege_history_handler(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_privilege_not_found_returns_404_public(self):
        from handlers.privilege_history import privilege_history_handler

        event = self._when_testing_public_endpoint()
        event['pathParameters']['jurisdiction'] = 'ma'

        resp = privilege_history_handler(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_privilege_not_found_returns_404_staff(self):
        from handlers.privilege_history import privilege_history_handler

        event = self._when_testing_staff_endpoint()
        event['pathParameters']['jurisdiction'] = 'ma'

        resp = privilege_history_handler(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_get_privilege_history_users_me_returns_expected_history(self):
        from handlers.privilege_history import privilege_history_handler

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = privilege_history_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        history_data = json.loads(resp['body'])

        expected_history = {
            'compact': 'aslp',
            'events': [
                {
                    'createDate': '2016-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2016-05-05T12:59:59+00:00',
                    'effectiveDate': '2016-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'issuance',
                },
                {
                    'createDate': '2020-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2020-05-05T12:59:59+00:00',
                    'effectiveDate': '2020-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'renewal',
                },
                {
                    'createDate': '2023-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'effectiveDate': '2022-05-05T12:59:59+00:00',
                    'npdbCategories': ['Non-compliance With Requirements'],
                    'type': 'privilegeUpdate',
                    'updateType': 'encumbrance',
                },
            ],
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'privilegeId': 'SLP-NE-1',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
        }

        self.assertEqual(expected_history, history_data)

    def test_get_privilege_history_public_returns_expected_history(self):
        from handlers.privilege_history import privilege_history_handler

        event = self._when_testing_public_endpoint()

        resp = privilege_history_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        history_data = json.loads(resp['body'])

        expected_history = {
            'compact': 'aslp',
            'events': [
                {
                    'createDate': '2016-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2016-05-05T12:59:59+00:00',
                    'effectiveDate': '2016-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'issuance',
                },
                {
                    'createDate': '2020-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2020-05-05T12:59:59+00:00',
                    'effectiveDate': '2020-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'renewal',
                },
                {
                    'createDate': '2023-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'effectiveDate': '2022-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'encumbrance',
                },
            ],
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'privilegeId': 'SLP-NE-1',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
        }

        self.assertEqual(expected_history, history_data)

    def test_get_privilege_history_staff_returns_expected_history(self):
        from handlers.privilege_history import privilege_history_handler

        event = self._when_testing_staff_endpoint()

        resp = privilege_history_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        history_data = json.loads(resp['body'])

        expected_history = {
            'compact': 'aslp',
            'events': [
                {
                    'createDate': '2016-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2016-05-05T12:59:59+00:00',
                    'effectiveDate': '2016-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'issuance',
                },
                {
                    'createDate': '2020-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2020-05-05T12:59:59+00:00',
                    'effectiveDate': '2020-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'renewal',
                },
                {
                    'createDate': '2023-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'effectiveDate': '2022-05-05T12:59:59+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'encumbrance',
                    'npdbCategories': ['Non-compliance With Requirements', 'Misconduct or Abuse'],
                },
            ],
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'privilegeId': 'SLP-NE-1',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
        }

        self.assertEqual(expected_history, history_data)
