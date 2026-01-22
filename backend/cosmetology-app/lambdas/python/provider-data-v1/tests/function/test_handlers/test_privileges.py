import json
from datetime import datetime
from unittest.mock import patch

from aws_lambda_powertools.metrics import MetricUnit
from boto3.dynamodb.types import TypeDeserializer
from cc_common.exceptions import CCInternalException
from moto import mock_aws

from .. import TstFunction

TEST_STAFF_USER_ID = 'a4182428-d061-701c-82e5-a3d1d547d797'
TEST_STAFF_USER_EMAIL = 'test-staff-user@example.com'
TEST_STAFF_USER_FIRST_NAME = 'Joe'
TEST_STAFF_USER_LAST_NAME = 'Dokes'
TEST_NOTE = 'User does not like having this privilege.'

DEACTIVATION_EVENT = {
    'type': 'privilegeUpdate',
    'updateType': 'deactivation',
    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
    'compact': 'cosm',
    'jurisdiction': 'ne',
    'licenseType': 'cosmetologist',
    'createDate': '2024-11-08T23:59:59+00:00',
    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
    'effectiveDate': '2024-11-08T23:59:59+00:00',
    'deactivationDetails': {
        'note': TEST_NOTE,
        'deactivatedByStaffUserId': TEST_STAFF_USER_ID,
        'deactivatedByStaffUserName': f'{TEST_STAFF_USER_FIRST_NAME} {TEST_STAFF_USER_LAST_NAME}',
    },
    'previous': {
        'attestations': [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}],
        'dateOfIssuance': '2016-05-05T12:59:59+00:00',
        'dateOfRenewal': '2020-05-05T12:59:59+00:00',
        'dateOfExpiration': '2025-04-04',
        'dateOfUpdate': '2020-05-05T12:59:59+00:00',
        'privilegeId': 'COS-NE-1',
        'administratorSetStatus': 'active',
        'licenseJurisdiction': 'oh',
    },
    'updatedValues': {'administratorSetStatus': 'inactive'},
}


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestDeactivatePrivilege(TstFunction):
    def setUp(self):
        super().setUp()
        # add test staff user to staff user dynamodb table
        with open('../common/tests/resources/dynamo/user.json') as f:
            staff_user = TypeDeserializer().deserialize({'M': json.load(f)})
            # swap out the default test values with our constants
            staff_user.update(
                {
                    'pk': f'USER#{TEST_STAFF_USER_ID}',
                    'userId': TEST_STAFF_USER_ID,
                    'attributes': {
                        'email': TEST_STAFF_USER_EMAIL,
                        'givenName': TEST_STAFF_USER_FIRST_NAME,
                        'familyName': TEST_STAFF_USER_LAST_NAME,
                    },
                }
            )
            # This item is saved in its serialized form, so we have to deserialize it first
            self.config.users_table.put_item(Item=staff_user)

    def _assert_the_privilege_was_deactivated(self):
        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral ne/cosm.readPrivate'
        event['pathParameters'] = {
            'compact': 'cosm',
            'providerId': expected_provider['providerId'],
            'licenseType': 'cos',
        }

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Update expected provider data to include the deactivation
        expected_provider['privileges'][0]['administratorSetStatus'] = 'inactive'
        expected_provider['privileges'][0]['status'] = 'inactive'
        expected_provider['privileges'][0]['dateOfUpdate'] = '2024-11-08T23:59:59+00:00'
        # remove activeSince Field, since the privilege in this case would not be active
        del expected_provider['privileges'][0]['activeSince']

        body = json.loads(resp['body'])
        self.assertEqual(expected_provider, body)

    def _request_deactivation_with_scopes(self, scopes: str):
        from handlers.privileges import deactivate_privilege

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = scopes
        event['requestContext']['authorizer']['claims']['sub'] = TEST_STAFF_USER_ID
        event['pathParameters'] = {
            'compact': 'cosm',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            'jurisdiction': 'ne',
            'licenseType': 'cos',
        }
        event['body'] = json.dumps({'deactivationNote': TEST_NOTE})

        return deactivate_privilege(event, self.mock_context)

    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.privileges.EventBatchWriter', autospec=True)
    def test_compact_admin_can_deactivate_privilege(self, mock_event_writer, mock_email_service_client):  # noqa: ARG002 unused-argument
        """
        If a compact admin has admin permission in the compact, they can deactivate a privilege
        """
        self._load_provider_data()

        # The user has admin permission for cosm
        resp = self._request_deactivation_with_scopes('openid email cosm/admin cosm/admin')
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
                            'compact': 'cosm',
                            'jurisdiction': 'ne',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                        }
                    ),
                    'EventBusName': 'license-data-events',
                }
            },
        )

    @patch('cc_common.config._Config.email_service_client')
    def test_board_admin_cannot_deactivate_privilege(self, mock_email_service_client):  # noqa: ARG002 unused-argument
        """
        If a board admin has admin permission in the privilege jurisdiction, they can deactivate a privilege
        """
        self._load_provider_data()

        # The user has admin permission for ne
        resp = self._request_deactivation_with_scopes('openid email ne/cosm.admin')
        self.assertEqual(403, resp['statusCode'])
        self.assertEqual({'message': 'Access denied'}, json.loads(resp['body']))

    def test_deactivate_privilege_handler_sends_expected_email_notifications(self):
        """
        If a board admin has admin permission in the privilege jurisdiction, they can deactivate a privilege
        """
        self._load_provider_data()

        # The user has admin permission for ne
        with patch('handlers.privileges.config.email_service_client') as mock_email_service_client:
            resp = self._request_deactivation_with_scopes('openid email cosm/admin')

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'message': 'OK'}, json.loads(resp['body']))

        mock_email_service_client.send_jurisdiction_privilege_deactivation_email.assert_called_once_with(
            compact='cosm',
            jurisdiction='ne',
            privilege_id='COS-NE-1',
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
        )

    def test_invalid_request_exception_raised_if_privilege_already_deactivated(self):
        """
        If a board admin does not have admin permission in the privilege jurisdiction, they cannot deactivate a
        privilege.
        """
        self._load_provider_data()
        with open('../common/tests/resources/dynamo/privilege.json') as f:
            privilege = json.load(f)
            # set persisted status to deactivated
            privilege['administratorSetStatus'] = 'inactive'
            self.config.provider_table.put_item(Item=privilege)
        # calling deactivation on privilege that is already deactivated
        resp = self._request_deactivation_with_scopes('openid email cosm/admin')

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual({'message': 'Privilege already deactivated'}, json.loads(resp['body']))

    @patch('handlers.privileges.metrics')
    def test_deactivate_privilege_handler_pushes_custom_metric_if_state_notification_failed_to_send(self, mock_metrics):
        """
        If the deactivation state notification fails to send, ensure we raise an exception.
        """
        self._load_provider_data()

        with patch('handlers.privileges.config.email_service_client') as mock_email_service_client:
            (
                mock_email_service_client.send_jurisdiction_privilege_deactivation_email
            ).side_effect = CCInternalException('email failed to send')
            # We expect the handler to still return a 200, since the privilege was deactivated
            resp = self._request_deactivation_with_scopes('openid email cosm/admin')

        self.assertEqual(200, resp['statusCode'])

        # assert metric was sent
        mock_metrics.add_metric.assert_called_once_with(
            name='privilege-deactivation-notification-failed', unit=MetricUnit.Count, value=1
        )

    def test_non_admin_cannot_deactivate_privilege(self):
        """
        If a non-admin user attempts to deactivate a privilege, the response should be a 403
        """
        self._load_provider_data()

        # The user has read permission for cosm
        resp = self._request_deactivation_with_scopes('openid email cosm/readGeneral ne/cosm.readPrivate')
        self.assertEqual(403, resp['statusCode'])

    def test_deactivate_privilege_not_found(self):
        """
        If a privilege is not found, the response should be a 404
        """
        # Note lack of self._load_provider_data() here - we're _not_ loading the provider in this case
        resp = self._request_deactivation_with_scopes('openid email cosm/admin')
        self.assertEqual(404, resp['statusCode'])
