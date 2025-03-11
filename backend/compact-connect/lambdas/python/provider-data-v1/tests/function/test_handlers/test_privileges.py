import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction

DEACTIVATION_HISTORY = {
    'type': 'privilegeUpdate',
    'updateType': 'deactivation',
    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
    'compact': 'aslp',
    'jurisdiction': 'ne',
    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
    'previous': {
        'attestations': [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}],
        'dateOfIssuance': '2016-05-05T12:59:59+00:00',
        'dateOfRenewal': '2020-05-05T12:59:59+00:00',
        'dateOfExpiration': '2025-04-04',
        'dateOfUpdate': '2020-05-05T12:59:59+00:00',
        'compactTransactionId': '1234567890',
        'privilegeId': 'SLP-NE-1',
        'persistedStatus': 'active',
        'licenseJurisdiction': 'oh',
        'licenseType': 'speech-language pathologist',
    },
    'updatedValues': {'persistedStatus': 'inactive'},
}


@mock_aws
class TestDeactivatePrivilege(TstFunction):
    def _assert_the_privilege_was_deactivated(self):
        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral ne/aslp.readPrivate'
        event['pathParameters'] = {
            'compact': 'aslp',
            'providerId': expected_provider['providerId'],
            'licenseType': 'aud',
        }

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Update expected provider data to include the deactivation
        expected_provider['privileges'][0]['persistedStatus'] = 'inactive'
        expected_provider['privileges'][0]['status'] = 'inactive'
        # Add the deactivation history
        expected_provider['privileges'][0]['history'].insert(0, DEACTIVATION_HISTORY)
        expected_provider['privileges'][0]['dateOfUpdate'] = '2024-11-08T23:59:59+00:00'

        body = json.loads(resp['body'])

        self.maxDiff = None
        self.assertEqual(expected_provider, body)

    def _request_deactivation_with_scopes(self, scopes: str):
        from handlers.privileges import deactivate_privilege

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = scopes
        event['pathParameters'] = {
            'compact': 'aslp',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            'jurisdiction': 'ne',
            'licenseType': 'slp',
        }
        event['body'] = None

        return deactivate_privilege(event, self.mock_context)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    @patch('handlers.privileges.EventBatchWriter', autospec=True)
    def test_compact_admin_can_deactivate_privilege(self, mock_event_writer):
        """
        If a compact admin has admin permission in the compact, they can deactivate a privilege
        """
        self._load_provider_data()

        # The user has admin permission for aslp
        resp = self._request_deactivation_with_scopes('openid email aslp/admin aslp/admin')
        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'message': 'OK'}, json.loads(resp['body']))

        self._assert_the_privilege_was_deactivated()
        mock_event_writer.return_value.__enter__.return_value.put_event.assert_called_once()
        call_kwargs = mock_event_writer.return_value.__enter__.return_value.put_event.call_args.kwargs
        self.assertEqual(
            call_kwargs,
            {
                'Entry': {
                    'Source': 'org.compactconnect.provider-data',
                    'DetailType': 'privilege.deactivation',
                    'Detail': json.dumps(
                        {
                            'eventTime': '2024-11-08T23:59:59+00:00',
                            'compact': 'aslp',
                            'jurisdiction': 'ne',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                        }
                    ),
                    'EventBusName': 'license-data-events',
                }
            },
        )

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_board_admin_can_deactivate_privilege(self):
        """
        If a board admin has admin permission in the privilege jurisdiction, they can deactivate a privilege
        """
        self._load_provider_data()

        # The user has admin permission for ne
        resp = self._request_deactivation_with_scopes('openid email ne/aslp.admin')
        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'message': 'OK'}, json.loads(resp['body']))

        self._assert_the_privilege_was_deactivated()

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_board_admin_outside_of_jurisdiction_cannot_deactivate_privilege(self):
        """
        If a board admin does not have admin permission in the privilege jurisdiction, they cannot deactivate a
        privilege.
        """
        self._load_provider_data()

        # The user has admin permission for oh
        resp = self._request_deactivation_with_scopes('openid email oh/aslp.admin')
        self.assertEqual(403, resp['statusCode'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_non_admin_cannot_deactivate_privilege(self):
        """
        If a non-admin user attempts to deactivate a privilege, the response should be a 403
        """
        self._load_provider_data()

        # The user has read permission for aslp
        resp = self._request_deactivation_with_scopes('openid email aslp/readGeneral ne/aslp.readPrivate')
        self.assertEqual(403, resp['statusCode'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_deactivate_privilege_not_found(self):
        """
        If a privilege is not found, the response should be a 404
        """
        # Note lack of self._load_provider_data() here - we're _not_ loading the provider in this case
        resp = self._request_deactivation_with_scopes('openid email ne/aslp.admin')
        self.assertEqual(404, resp['statusCode'])
