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

DEACTIVATION_HISTORY = {
    'type': 'privilegeUpdate',
    'updateType': 'deactivation',
    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
    'compact': 'aslp',
    'jurisdiction': 'ne',
    'licenseType': 'speech-language pathologist',
    'createDate': '2024-11-08T23:59:59+00:00',
    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
    'effectiveDate': '2024-11-08',
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
        'compactTransactionId': '1234567890',
        'privilegeId': 'SLP-NE-1',
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
        expected_provider['privileges'][0]['administratorSetStatus'] = 'inactive'
        expected_provider['privileges'][0]['status'] = 'inactive'
        # Add the deactivation history
        expected_provider['privileges'][0]['history'].insert(0, DEACTIVATION_HISTORY)
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
            'compact': 'aslp',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            'jurisdiction': 'ne',
            'licenseType': 'slp',
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

    @patch('cc_common.config._Config.email_service_client')
    def test_board_admin_cannot_deactivate_privilege(self, mock_email_service_client):  # noqa: ARG002 unused-argument
        """
        If a board admin has admin permission in the privilege jurisdiction, they can deactivate a privilege
        """
        self._load_provider_data()

        # The user has admin permission for ne
        resp = self._request_deactivation_with_scopes('openid email ne/aslp.admin')
        self.assertEqual(403, resp['statusCode'])
        self.assertEqual({'message': 'Access denied'}, json.loads(resp['body']))

    def test_deactivate_privilege_handler_sends_expected_email_notifications(self):
        """
        If a board admin has admin permission in the privilege jurisdiction, they can deactivate a privilege
        """
        self._load_provider_data()

        # The user has admin permission for ne
        with patch('handlers.privileges.config.email_service_client') as mock_email_service_client:
            resp = self._request_deactivation_with_scopes('openid email aslp/admin')

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'message': 'OK'}, json.loads(resp['body']))

        mock_email_service_client.send_provider_privilege_deactivation_email.assert_called_once_with(
            compact='aslp',
            provider_email='björkRegisteredEmail@example.com',
            privilege_id='SLP-NE-1',
        )
        mock_email_service_client.send_jurisdiction_privilege_deactivation_email.assert_called_once_with(
            compact='aslp',
            jurisdiction='ne',
            privilege_id='SLP-NE-1',
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
        resp = self._request_deactivation_with_scopes('openid email aslp/admin')

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual({'message': 'Privilege already deactivated'}, json.loads(resp['body']))

    @patch('handlers.privileges.metrics')
    def test_deactivate_privilege_handler_still_sends_jurisdiction_notification_if_provider_notification_failed_to_send(
        self, mock_metrics
    ):
        """
        If the deactivation notification to the provider fails to send, we want to ensure that the notification to
        the state is still sent.
        """
        self._load_provider_data()

        with patch('handlers.privileges.config.email_service_client') as mock_email_service_client:
            (mock_email_service_client.send_provider_privilege_deactivation_email).side_effect = CCInternalException(
                'email failed to send'
            )
            # We expect the handler to still return a 200, since the privilege was deactivated
            resp = self._request_deactivation_with_scopes('openid email aslp/admin')

        self.assertEqual(200, resp['statusCode'])

        # Even though the first notification failed, the handler should still have attempted to send both
        # notifications
        mock_email_service_client.send_provider_privilege_deactivation_email.assert_called_once_with(
            compact='aslp',
            provider_email='björkRegisteredEmail@example.com',
            privilege_id='SLP-NE-1',
        )
        mock_email_service_client.send_jurisdiction_privilege_deactivation_email.assert_called_once_with(
            compact='aslp',
            jurisdiction='ne',
            privilege_id='SLP-NE-1',
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
        )

        # assert metric was sent so alert will fire
        mock_metrics.add_metric.assert_called_once_with(
            name='privilege-deactivation-notification-failed', unit=MetricUnit.Count, value=1
        )

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
            resp = self._request_deactivation_with_scopes('openid email aslp/admin')

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

        # The user has read permission for aslp
        resp = self._request_deactivation_with_scopes('openid email aslp/readGeneral ne/aslp.readPrivate')
        self.assertEqual(403, resp['statusCode'])

    def test_deactivate_privilege_not_found(self):
        """
        If a privilege is not found, the response should be a 404
        """
        # Note lack of self._load_provider_data() here - we're _not_ loading the provider in this case
        resp = self._request_deactivation_with_scopes('openid email aslp/admin')
        self.assertEqual(404, resp['statusCode'])

    def test_privilege_purchase_message_handler_sends_email(self):
        """
        If a valid event purchase event is passed into the privilege_purchase_message_handler, it should kick off the
        send_privilege_purchase_email lambda
        """
        from handlers.privileges import privilege_purchase_message_handler

        with open('../common/tests/resources/events/purchase_event_body.json') as f:
            purchase_event_body = json.load(f)

        purchase_event = {'Records': [{'messageId': 123, 'body': json.dumps(purchase_event_body)}]}

        with patch('handlers.privileges.config.email_service_client') as mock_email_service_client:
            privilege_purchase_message_handler(purchase_event, self.mock_context)

        mock_email_service_client.send_privilege_purchase_email.assert_called_once()
