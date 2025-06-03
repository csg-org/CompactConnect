import json
from datetime import date, datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from cc_common.exceptions import CCInternalException
from common_test.test_constants import DEFAULT_DATE_OF_UPDATE_TIMESTAMP
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
MOCK_SSN = '123-12-1234'
MOCK_MILITARY_AFFILIATION_FILE_NAME = 'military_affiliation.pdf'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestGetProvider(TstFunction):
    def _when_testing_provider_user_event_with_custom_claims(self):
        self._load_provider_data()
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'GET'
            event['resource'] = '/v1/provider-users/me'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = test_provider.providerId
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_provider.compact

        return event

    def test_get_provider_returns_provider_information(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        expected_provider = self.test_data_generator.generate_default_provider_detail_response()

        self.assertEqual(expected_provider, provider_data)

    #  TODO: temp test to ensure backwards compatibility # noqa: FIX002
    #   it should be removed as part of https://github.com/csg-org/CompactConnect/issues/763
    def test_get_provider_maps_current_home_jurisdiction_to_deprecated_home_jurisdiction_selection(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()
        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        self.assertEqual(
            {
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                'type': 'homeJurisdictionSelection',
            },
            provider_data['homeJurisdictionSelection'],
        )

    def test_get_provider_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_get_provider_raises_exception_if_user_claims_do_not_match_any_provider_in_database(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['requestContext']['authorizer']['claims']['custom:providerId'] = 'some-provider-id'

        # calling get_provider without creating a provider first
        with self.assertRaises(CCInternalException):
            provider_users_api_handler(event, self.mock_context)

    def test_get_provider_returns_license_adverse_actions_if_present(self):
        from cc_common.data_model.schema.common import AdverseActionAgainstEnum
        from handlers.provider_users import provider_users_api_handler

        test_provider_record = self.test_data_generator.put_default_provider_record_in_provider_table()
        test_license_record = self.test_data_generator.put_default_license_record_in_provider_table()
        test_adverse_action = self.test_data_generator.generate_default_adverse_action()
        test_adverse_action.actionAgainst = AdverseActionAgainstEnum.LICENSE
        test_adverse_action.jurisdiction = test_license_record.jurisdiction
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides=test_adverse_action.to_dict()
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'GET'
            event['resource'] = '/v1/provider-users/me'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = test_provider_record.providerId
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_provider_record.compact

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        license_adverse_actions = provider_data['licenses'][0]['adverseActions']
        self.assertEqual(1, len(license_adverse_actions))

        self.assertEqual(
            [self.test_data_generator.convert_data_to_api_response_formatted_dict(test_adverse_action)],
            license_adverse_actions,
        )

    def test_get_provider_returns_privilege_adverse_actions_if_present(self):
        from cc_common.data_model.schema.common import AdverseActionAgainstEnum
        from handlers.provider_users import provider_users_api_handler

        test_provider_record = self.test_data_generator.put_default_provider_record_in_provider_table()
        test_privilege_record = self.test_data_generator.put_default_privilege_record_in_provider_table()
        test_adverse_action = self.test_data_generator.generate_default_adverse_action()
        test_adverse_action.actionAgainst = AdverseActionAgainstEnum.PRIVILEGE
        test_adverse_action.jurisdiction = test_privilege_record.jurisdiction
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides=test_adverse_action.to_dict()
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'GET'
            event['resource'] = '/v1/provider-users/me'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = test_provider_record.providerId
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_provider_record.compact

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        privileges_adverse_actions = provider_data['privileges'][0]['adverseActions']
        self.assertEqual(1, len(privileges_adverse_actions))

        self.assertEqual(
            [self.test_data_generator.convert_data_to_api_response_formatted_dict(test_adverse_action)],
            privileges_adverse_actions,
        )


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPostProviderMilitaryAffiliation(TstFunction):
    def _get_military_affiliation_records(self, event):
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']
        return self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{TEST_COMPACT}#PROVIDER#{provider_id}')
            & Key('sk').begins_with(
                f'{TEST_COMPACT}#PROVIDER#military-affiliation#',
            )
        )['Items']

    def _when_testing_post_provider_user_military_affiliation_event_with_custom_claims(self):
        self._load_provider_data()
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'POST'
            event['resource'] = '/v1/provider-users/me/military-affiliation'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = test_provider.providerId
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_provider.compact
            event['body'] = json.dumps(
                {
                    'fileNames': [MOCK_MILITARY_AFFILIATION_FILE_NAME],
                    'affiliationType': 'militaryMember',
                }
            )

        return event

    @patch('handlers.provider_users.uuid')
    def test_post_provider_military_affiliation_returns_affiliation_information(self, mock_uuid):
        from handlers.provider_users import provider_users_api_handler

        mock_uuid.uuid4.return_value = '1234'

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        military_affiliation_data = json.loads(resp['body'])

        # remove dynamic fields from s3 response
        del military_affiliation_data['documentUploadFields'][0]['fields']['policy']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-signature']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-date']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-credential']

        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']

        # remove the dynamic dateOfUpload field
        military_affiliation_data.pop('dateOfUpload')

        self.assertEqual(
            {
                'affiliationType': 'militaryMember',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'documentUploadFields': [
                    {
                        'fields': {
                            'key': f'compact/{TEST_COMPACT}/provider/{provider_id}/document-type/military-affiliations'
                            f'/2024-11-08/1234#military_affiliation.pdf',
                            'x-amz-algorithm': 'AWS4-HMAC-SHA256',
                        },
                        'url': 'https://provider-user-bucket.s3.amazonaws.com/',
                    }
                ],
                'fileNames': ['military_affiliation.pdf'],
                'status': 'initializing',
            },
            military_affiliation_data,
        )

    @patch('handlers.provider_users.uuid')
    def test_post_provider_military_affiliation_handles_file_with_uppercase_extension(self, mock_uuid):
        from handlers.provider_users import provider_users_api_handler

        mock_uuid.uuid4.return_value = '1234'

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()
        event['body'] = json.dumps(
            {
                'fileNames': [MOCK_MILITARY_AFFILIATION_FILE_NAME.upper()],
                'affiliationType': 'militaryMember',
            }
        )

        resp = provider_users_api_handler(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

    def test_post_provider_military_affiliation_sets_previous_record_status_to_inactive(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        # We'll set the 'current datetime' to a date after the initial military affiliation record was uploaded
        # so we can create a second record with an 'inactive' status
        with patch(
            'cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-09T23:59:59+00:00')
        ):
            resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # get the military affiliation record
        military_affiliation_records = self._get_military_affiliation_records(event)
        # There should have been another record loaded previously with an 'active' status by the
        # test setup, so now we check to see if it has been set to 'inactive'
        self.assertEqual(2, len(military_affiliation_records))
        # record with the oldest upload date should be inactive, the other should be initializing
        affiliations_sorted_by_date = sorted(military_affiliation_records, key=lambda x: x['dateOfUpload'])
        self.assertEqual('inactive', affiliations_sorted_by_date[0]['status'])
        self.assertEqual('initializing', affiliations_sorted_by_date[1]['status'])

    def test_post_provider_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def _when_testing_file_names(self, file_names: list[str]):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()
        event['body'] = json.dumps(
            {
                'fileNames': file_names,
                'affiliationType': 'militaryMember',
            }
        )

        return provider_users_api_handler(event, self.mock_context)

    def test_post_provider_returns_400_if_file_name_using_unsupported_file_extension(self):
        resp = self._when_testing_file_names(['military_affiliation.guff'])

        self.assertEqual(400, resp['statusCode'])
        message = json.loads(resp['body'])['message']

        self.assertEqual(
            'Invalid file type "guff" The following file types are supported: '
            + "('pdf', 'jpg', 'jpeg', 'png', 'docx')",
            message,
        )

    def test_post_provider_returns_200_if_file_extensions_valid(self):
        resp = self._when_testing_file_names(['file.pdf', 'file.jpg', 'file.jpeg', 'file.png', 'file.docx'])

        self.assertEqual(200, resp['statusCode'])


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPatchProviderMilitaryAffiliation(TstFunction):
    def _when_testing_patch_provider_user_military_affiliation_event_with_custom_claims(self):
        self._load_provider_data()
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'PATCH'
            event['resource'] = '/v1/provider-users/me/military-affiliation'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = test_provider.providerId
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_provider.compact
            event['body'] = json.dumps({'status': 'inactive'})

        return event

    def _get_military_affiliation_records(self, event):
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']
        return self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{TEST_COMPACT}#PROVIDER#{provider_id}')
            & Key('sk').begins_with(
                f'{TEST_COMPACT}#PROVIDER#military-affiliation#',
            )
        )['Items']

    def test_patch_provider_military_affiliation_returns_message(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_patch_provider_user_military_affiliation_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        resp_body = json.loads(resp['body'])

        self.assertEqual({'message': 'Military affiliation updated successfully'}, resp_body)

    def test_patch_provider_military_affiliation_returs_400_if_invalid_body(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_patch_provider_user_military_affiliation_event_with_custom_claims()

        event['body'] = json.dumps({'status': 'active'})

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        message = json.loads(resp['body'])['message']

        self.assertEqual('Invalid status value. Only "inactive" is allowed.', message)

    def test_patch_provider_military_affiliation_updates_status(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_patch_provider_user_military_affiliation_event_with_custom_claims()

        # get the military affiliation record loaded in the test setup and confirm it is active
        affiliation_record = self._get_military_affiliation_records(event)
        self.assertEqual(1, len(affiliation_record))
        self.assertEqual('active', affiliation_record[0]['status'])

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now confirm the status has been updated to inactive
        affiliation_record = self._get_military_affiliation_records(event)

        self.assertEqual(1, len(affiliation_record))
        self.assertEqual('inactive', affiliation_record[0]['status'])


# constants for home jurisdiction update tests
STARTING_JURISDICTION = 'oh'
PRIVILEGE_JURISDICTION = 'ky'
TEST_LICENSE_TYPE = 'audiologist'
SECOND_LICENSE_TYPE = 'speech-language pathologist'
NEW_JURISDICTION = 'ne'
NEW_LICENSE_VALID_EXPIRATION_DATE = '2026-12-12'
NEW_LICENSE_EXPIRED_EXPIRATION_DATE = '2023-12-12'
# this other keyword is used for jurisdictions not listed in the system.
OTHER_NON_MEMBER_JURISDICTION = 'other'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPutProviderHomeJurisdiction(TstFunction):
    def _when_provider_has_one_license_and_privilege(
        self,
        license_encumbered: bool = False,
        license_type: str = TEST_LICENSE_TYPE,
        privilege_jurisdiction: str = PRIVILEGE_JURISDICTION,
    ):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum, PrivilegeEncumberedStatusEnum

        test_current_license_record = self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': STARTING_JURISDICTION,
                'compact': TEST_COMPACT,
                'licenseType': license_type,
                'encumberedStatus': LicenseEncumberedStatusEnum.ENCUMBERED
                if license_encumbered
                else LicenseEncumberedStatusEnum.UNENCUMBERED,
            }
        )

        test_provider_record = self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': STARTING_JURISDICTION,
                'compact': TEST_COMPACT,
                'currentHomeJurisdiction': test_current_license_record.jurisdiction,
            }
        )

        # add privilege in Kentucky for the current license
        test_privilege_record = self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'compact': TEST_COMPACT,
                'jurisdiction': privilege_jurisdiction,
                'licenseJurisdiction': test_current_license_record.jurisdiction,
                'licenseType': license_type,
                'encumberedStatus': PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED
                if license_encumbered
                else PrivilegeEncumberedStatusEnum.UNENCUMBERED,
            }
        )

        return test_provider_record, test_current_license_record, test_privilege_record

    def _when_provider_has_license_in_new_home_state(
        self,
        license_encumbered: bool = False,
        license_expired: bool = False,
        license_compact_eligible: bool = True,
        license_type: str = TEST_LICENSE_TYPE,
    ):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum

        return self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': NEW_JURISDICTION,
                'compact': TEST_COMPACT,
                'licenseType': license_type,
                'dateOfExpiration': date.fromisoformat(NEW_LICENSE_EXPIRED_EXPIRATION_DATE)
                if license_expired
                else date.fromisoformat(NEW_LICENSE_VALID_EXPIRATION_DATE),
                'encumberedStatus': LicenseEncumberedStatusEnum.ENCUMBERED
                if license_encumbered
                else LicenseEncumberedStatusEnum.UNENCUMBERED,
                'jurisdictionUploadedCompactEligibility': 'eligible' if license_compact_eligible else 'ineligible',
                # setting these new fields on the license relevant to the provider record so we can verify it is copied
                # over
                'givenName': 'John',
                'familyName': 'Doe',
                'suffix': 'Jr.',
                'licenseNumber': '1234567890',
                'dateOfIssuance': date.fromisoformat('2020-01-01'),
                'dateOfRenewal': date.fromisoformat('2024-01-01'),
            }
        )

    def _when_provider_has_no_license_in_new_selected_jurisdiction(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have a license, and they move to Nebraska,
        where they don't have a license. They also have one privilege for this license
        """
        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record

    def _when_provider_moves_to_non_member_jurisdiction(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have a license and a privilege in KY.
        They move to an international location, which is not a member of the compact.
        """
        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )

        event = self._when_testing_put_provider_home_jurisdiction(OTHER_NON_MEMBER_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record

    def _when_original_home_state_license_is_encumbered(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an encumbered license
        and a privilege in KY.

        They move to a new state with an unencumbered license with a new expiration date.
        """
        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege(license_encumbered=True)
        )

        # add unencumbered license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(license_encumbered=False)

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return (
            event,
            test_provider_record,
            test_current_license_record,
            test_privilege_record,
            new_jurisdiction_license_record,
        )

    def _when_new_home_state_license_is_encumbered(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an active license and a privilege in KY.
        They move to a new state with an encumbered license.
        """
        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege(license_encumbered=False)
        )

        # add encumbered license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(license_encumbered=True)

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return (
            event,
            test_provider_record,
            test_current_license_record,
            test_privilege_record,
            new_jurisdiction_license_record,
        )

    def _when_new_home_state_license_is_expired(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an active license and a privilege in KY.
        They move to a new state with an expired license.
        """
        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege(license_encumbered=False)
        )

        # add expired license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(license_expired=True)

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return (
            event,
            test_provider_record,
            test_current_license_record,
            test_privilege_record,
            new_jurisdiction_license_record,
        )

    def _when_new_home_state_license_is_not_compact_eligible(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an active license and a privilege in KY.
        They move to a new state with a license that is not compact eligible.
        """
        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege(license_encumbered=False)
        )

        # add compact ineligible license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(
            license_compact_eligible=False
        )

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return (
            event,
            test_provider_record,
            test_current_license_record,
            test_privilege_record,
            new_jurisdiction_license_record,
        )

    def _when_testing_put_provider_home_jurisdiction(self, new_jurisdiction: str, provider_data):
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'PUT'
            event['resource'] = '/v1/provider-users/me/home-jurisdiction'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = provider_data.providerId
            event['requestContext']['authorizer']['claims']['custom:compact'] = provider_data.compact
            event['body'] = json.dumps({'jurisdiction': new_jurisdiction})

        return event

    def test_put_provider_home_jurisdiction_returns_message(self):
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )

        event = self._when_testing_put_provider_home_jurisdiction(OTHER_NON_MEMBER_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        resp_body = json.loads(resp['body'])

        self.assertEqual({'message': 'ok'}, resp_body)

    def test_put_provider_home_jurisdiction_returns_400_with_invalid_jurisdiction(self):
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )

        event = self._when_testing_put_provider_home_jurisdiction('foo', test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        resp_body = json.loads(resp['body'])

        self.assertEqual({'message': 'Invalid jurisdiction selected.'}, resp_body)

    def test_put_provider_home_jurisdiction_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )

        event = self._when_testing_put_provider_home_jurisdiction(OTHER_NON_MEMBER_JURISDICTION, test_provider_record)

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_put_provider_home_jurisdiction_deactivates_privileges_if_no_license_in_new_jurisdiction(self):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        (event, test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_no_license_in_new_selected_jurisdiction()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('inactive', stored_privilege_data.homeJurisdictionChangeStatus)

    def test_put_provider_home_jurisdiction_only_deactivates_privileges_for_non_existent_license_in_new_jurisdiction(
        self,
    ):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        """
        In this test case, the user has two licenses in the current jurisdiction, but only one license in the new
        jurisdiction when the user updates the home jurisdiction selection. The privilege for the matching license type
        should be moved over, the other should be deactivated.
        """

        (
            test_provider_record,
            test_current_license_record_with_matching_license_in_new_jurisdiction,
            test_privilege_record_with_matching_license_in_new_jurisdiction,
        ) = self._when_provider_has_one_license_and_privilege(license_type=TEST_LICENSE_TYPE)
        # another license is uploaded for this provider, and they have purchased a privilege for it
        (
            test_provider_record,
            test_current_license_record_without_matching_license_in_new_jurisdiction,
            test_privilege_record_without_matching_license_in_new_jurisdiction,
        ) = self._when_provider_has_one_license_and_privilege(license_type=SECOND_LICENSE_TYPE)

        # license is uploaded for new jurisdiction for the first license type
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(
            license_type=TEST_LICENSE_TYPE
        )
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data_for_privilege_without_matching_license = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(
                test_privilege_record_without_matching_license_in_new_jurisdiction
            )
        )
        self.assertEqual('inactive', stored_privilege_data_for_privilege_without_matching_license.status)
        self.assertEqual(
            'inactive',
            stored_privilege_data_for_privilege_without_matching_license.homeJurisdictionChangeStatus,
        )
        self.assertEqual(
            test_current_license_record_without_matching_license_in_new_jurisdiction.dateOfExpiration,
            stored_privilege_data_for_privilege_without_matching_license.dateOfExpiration,
        )
        self.assertEqual(
            test_current_license_record_without_matching_license_in_new_jurisdiction.jurisdiction,
            stored_privilege_data_for_privilege_without_matching_license.licenseJurisdiction,
        )

        # now verify the privilege with the matching license in the new jurisdiction is moved over
        stored_privilege_data_for_privilege_with_matching_license = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(
                test_privilege_record_with_matching_license_in_new_jurisdiction
            )
        )
        self.assertEqual('active', stored_privilege_data_for_privilege_with_matching_license.status)
        # this should not be set, since there was a valid license to move the privilege over to
        self.assertNotIn(
            'homeJurisdictionChangeStatus',
            stored_privilege_data_for_privilege_with_matching_license.to_dict(),
        )
        # verify the new license field values were set on the privilege record
        self.assertEqual(
            new_jurisdiction_license_record.dateOfExpiration,
            stored_privilege_data_for_privilege_with_matching_license.dateOfExpiration,
        )
        self.assertEqual(
            new_jurisdiction_license_record.jurisdiction,
            stored_privilege_data_for_privilege_with_matching_license.licenseJurisdiction,
        )

    def test_put_provider_home_jurisdiction_updates_privileges_for_multiple_license_types_in_new_jurisdiction(self):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        """
        In this test case, the user has two licenses in the current jurisdiction, and two matching licenses in the new
        jurisdiction when the user updates the home jurisdiction selection. The privileges should be moved over to their
        respective license types.
        """

        (test_provider_record, test_current_license_record_type_one, test_privilege_record_license_type_one) = (
            self._when_provider_has_one_license_and_privilege(license_type=TEST_LICENSE_TYPE)
        )
        # another license is uploaded for this provider, and they have purchased a privilege for it
        (test_provider_record, test_current_license_record_type_two, test_privilege_record_license_type_two) = (
            self._when_provider_has_one_license_and_privilege(license_type=SECOND_LICENSE_TYPE)
        )

        # license is uploaded for new jurisdiction for the first license type
        new_jurisdiction_license_record_type_one = self._when_provider_has_license_in_new_home_state(
            license_type=TEST_LICENSE_TYPE
        )
        # second license type in new jurisdiction is expired
        new_jurisdiction_license_record_type_two = self._when_provider_has_license_in_new_home_state(
            license_type=SECOND_LICENSE_TYPE, license_expired=True
        )
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # verify the privilege is associated with the expected license data
        stored_privilege_data_for_license_type_one = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record_license_type_one)
        )
        self.assertEqual('active', stored_privilege_data_for_license_type_one.status)
        # this should not be set, since there was a valid license to move the privilege over to
        self.assertNotIn('homeJurisdictionChangeStatus', stored_privilege_data_for_license_type_one.to_dict())
        # verify the new license field values were set on the privilege record
        self.assertEqual(
            new_jurisdiction_license_record_type_one.dateOfExpiration,
            stored_privilege_data_for_license_type_one.dateOfExpiration,
        )
        self.assertEqual(
            new_jurisdiction_license_record_type_one.jurisdiction,
            stored_privilege_data_for_license_type_one.licenseJurisdiction,
        )
        self.assertEqual(
            new_jurisdiction_license_record_type_one.licenseType, stored_privilege_data_for_license_type_one.licenseType
        )

        # verify the privilege for the second license type was moved over to the expired license
        stored_privilege_data_for_license_type_two = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record_license_type_two)
        )

        self.assertEqual('inactive', stored_privilege_data_for_license_type_two.status)
        # this should not be set, since there was a valid license to move the privilege over to
        self.assertNotIn('homeJurisdictionChangeStatus', stored_privilege_data_for_license_type_two.to_dict())
        self.assertEqual(
            new_jurisdiction_license_record_type_two.dateOfExpiration,
            stored_privilege_data_for_license_type_two.dateOfExpiration,
        )
        self.assertEqual(
            new_jurisdiction_license_record_type_two.jurisdiction,
            stored_privilege_data_for_license_type_two.licenseJurisdiction,
        )
        self.assertEqual(
            new_jurisdiction_license_record_type_two.licenseType, stored_privilege_data_for_license_type_two.licenseType
        )

    def test_put_provider_home_jurisdiction_sets_status_on_provider_record_if_no_license_in_new_jurisdiction(
        self,
    ):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        (event, test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_no_license_in_new_selected_jurisdiction()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the provider record should show provider is ineligible since they do not have a license in their home state.
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )
        self.assertEqual('ineligible', stored_provider_data.compactEligibility)
        self.assertEqual(NEW_JURISDICTION, stored_provider_data.currentHomeJurisdiction)

    def test_put_provider_home_jurisdiction_deactivates_privileges_if_new_jurisdiction_non_member(self):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        (event, test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_moves_to_non_member_jurisdiction()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there new jurisdiction is not a member of the compact
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('inactive', stored_privilege_data.homeJurisdictionChangeStatus)

    def test_put_provider_home_jurisdiction_sets_deactivation_status_on_provider_record_if_new_jurisdiction_non_member(
        self,
    ):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        (event, test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_moves_to_non_member_jurisdiction()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the provider record should show provider is in a jurisdiction that is not a member of the compact
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )
        self.assertEqual('ineligible', stored_provider_data.compactEligibility)
        # this value must be set to show the provider is in a non-member jurisdiction
        self.assertEqual('other', stored_provider_data.currentHomeJurisdiction)
        # assert the provider's license jurisdiction and expiration has not changed
        self.assertEqual(test_current_license_record.jurisdiction, stored_provider_data.licenseJurisdiction)
        self.assertEqual(test_current_license_record.dateOfExpiration, stored_provider_data.dateOfExpiration)

    def test_put_provider_home_jurisdiction_does_not_update_privileges_if_starting_home_state_license_is_encumbered(
        self,
    ):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        (event, test_provider_record, test_current_license_record, test_privilege_record, test_new_license_record) = (
            self._when_original_home_state_license_is_encumbered()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should remain encumbered and not be updated because the original license was encumbered
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        # this field should not be added, since the privilege is already encumbered, it should not be deactivated
        # by this operation
        self.assertNotIn('homeJurisdictionChangeStatus', stored_privilege_data.to_dict())
        # these values should remain the same since it was previously encumbered, and we do not update privileges to
        # new license information if they are encumbered
        self.assertEqual('licenseEncumbered', stored_privilege_data.encumberedStatus)
        self.assertEqual(test_current_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)
        self.assertEqual(test_current_license_record.jurisdiction, stored_privilege_data.licenseJurisdiction)

    def test_put_provider_home_jurisdiction_encumbers_privileges_if_new_home_state_license_is_encumbered(self):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        # In this scenario, the new license is encumbered, and the privileges should be moved over to the new license
        # and become encumbered.

        (event, test_provider_record, test_current_license_record, test_privilege_record, test_new_license_record) = (
            self._when_new_home_state_license_is_encumbered()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        # this field should not be added, since the privilege is going to be encumbered, not deactivated
        self.assertNotIn('homeJurisdictionChangeStatus', stored_privilege_data.to_dict())
        # these values should be set since the new license is encumbered
        self.assertEqual('licenseEncumbered', stored_privilege_data.encumberedStatus)
        # we move the privilege over to the new license, so the expiration date should match
        self.assertEqual(test_new_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)
        # new jurisdiction should be put on record as well.
        self.assertEqual(test_new_license_record.jurisdiction, stored_privilege_data.licenseJurisdiction)

    def test_put_provider_home_jurisdiction_expires_privileges_if_new_home_state_license_is_expired(self):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        (event, test_provider_record, test_current_license_record, test_privilege_record, test_new_license_record) = (
            self._when_new_home_state_license_is_expired()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        # the privilege should be inactive because the new license is expired
        self.assertEqual('inactive', stored_privilege_data.status)
        # this field should not be added, since the privilege is going to be expired, not deactivated
        self.assertNotIn('homeJurisdictionChangeStatus', stored_privilege_data.to_dict())
        # verify the expiration dates match on the new license and privilege record
        self.assertEqual(test_new_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)

    def test_put_provider_home_jurisdiction_deactivates_privileges_if_new_home_state_license_is_not_compact_eligible(
        self,
    ):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        (event, test_provider_record, test_current_license_record, test_privilege_record, test_new_license_record) = (
            self._when_new_home_state_license_is_not_compact_eligible()
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        # the privilege should be deactivated because the new license is compact ineligible
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('inactive', stored_privilege_data.homeJurisdictionChangeStatus)

        # verify the expiration dates match on the current license and privilege record
        # since in this case they should not be moved over
        self.assertEqual(test_current_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)
        self.assertEqual(test_current_license_record.jurisdiction, stored_privilege_data.licenseJurisdiction)

    def test_put_provider_home_jurisdiction_updates_expiration_on_privileges_even_if_they_are_encumbered(self):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )

        new_license_record = self._when_provider_has_license_in_new_home_state()
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        # add one more privilege record in az that is encumbered
        encumbered_privilege = self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'compact': TEST_COMPACT,
                'jurisdiction': 'az',
                'licenseJurisdiction': test_current_license_record.jurisdiction,
                'licenseType': TEST_LICENSE_TYPE,
                'encumberedStatus': 'encumbered',
            }
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be successfully moved over since it is not encumbered
        stored_unencumbered_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('active', stored_unencumbered_privilege_data.status)
        # this field should not be added, since the privilege is going to be moved over to a valid license
        self.assertNotIn('homeJurisdictionChangeStatus', stored_unencumbered_privilege_data.to_dict())

        # verify these match on the new license and privilege record
        self.assertEqual(new_license_record.dateOfExpiration, stored_unencumbered_privilege_data.dateOfExpiration)
        self.assertEqual(new_license_record.jurisdiction, stored_unencumbered_privilege_data.licenseJurisdiction)

        # now check the values on the encumbered privilege to ensure they were still updated to the new license
        stored_encumbered_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(encumbered_privilege)
        )
        self.assertEqual('inactive', stored_encumbered_privilege_data.status)
        self.assertEqual('encumbered', stored_encumbered_privilege_data.encumberedStatus)
        # this field should not be added here either, since the privilege is encumbered,
        # not deactivated by this operation
        self.assertNotIn('homeJurisdictionChangeStatus', stored_encumbered_privilege_data.to_dict())

        # verify the encumbered privilege was updated to the new license as well
        self.assertEqual(new_license_record.dateOfExpiration, stored_encumbered_privilege_data.dateOfExpiration)
        self.assertEqual(new_license_record.jurisdiction, stored_encumbered_privilege_data.licenseJurisdiction)

    def test_put_provider_home_jurisdiction_updates_provider_record_with_new_license_information(self):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )
        new_license_record = self._when_provider_has_license_in_new_home_state()
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )
        self.assertEqual('active', stored_provider_data.licenseStatus)
        self.assertEqual('eligible', stored_provider_data.compactEligibility)

        # verify these match on the new license and privilege record
        self.assertEqual(new_license_record.dateOfExpiration, stored_provider_data.dateOfExpiration)
        self.assertEqual(new_license_record.jurisdiction, stored_provider_data.licenseJurisdiction)
        # verify the new home jurisdiction selection is set on the provider record
        self.assertEqual(NEW_JURISDICTION, stored_provider_data.currentHomeJurisdiction)
        # ensure the name is updated based on the new license
        self.assertEqual(new_license_record.familyName, stored_provider_data.familyName)
        self.assertEqual(new_license_record.givenName, stored_provider_data.givenName)
        self.assertEqual(new_license_record.suffix, stored_provider_data.suffix)

    def test_put_provider_home_jurisdiction_adds_privilege_update_record_when_privilege_moved_over_to_license(self):
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )
        new_license_record = self._when_provider_has_license_in_new_home_state()
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now get all the update records for the privilege record
        stored_privilege_update_records = (
            self.test_data_generator.query_privilege_update_records_for_given_record_from_database(
                test_privilege_record
            )
        )
        self.assertEqual(1, len(stored_privilege_update_records))

        update_data = stored_privilege_update_records[0]
        # the updateType should be homeJurisdictionChange
        self.assertEqual('homeJurisdictionChange', update_data.updateType)
        # this should not be present since the record was moved over
        self.assertNotIn('homeJurisdictionChangeStatus', update_data.updatedValues)
        # the updateData should be the new home jurisdiction
        self.assertEqual(new_license_record.jurisdiction, update_data.updatedValues['licenseJurisdiction'])
        self.assertEqual(new_license_record.dateOfExpiration, update_data.updatedValues['dateOfExpiration'])

    def test_put_provider_home_jurisdiction_adds_provider_update_record_when_valid_member_jurisdiction(self):
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )
        new_license_record = self._when_provider_has_license_in_new_home_state()
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now get all the update records for the provider
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(test_provider_record)
        )
        self.assertEqual(1, len(stored_provider_update_records))

        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])
        # the updateType should be homeJurisdictionChange
        self.assertEqual('homeJurisdictionChange', update_data.updateType)
        self.assertNotIn('homeJurisdictionChangeStatus', update_data.updatedValues)
        # the updateData should include the new home jurisdiction and the license jurisdiction fields
        self.assertEqual(new_license_record.jurisdiction, update_data.updatedValues['licenseJurisdiction'])
        self.assertEqual(NEW_JURISDICTION, update_data.updatedValues['currentHomeJurisdiction'])

    def test_put_provider_home_jurisdiction_adds_provider_update_record_when_non_member_jurisdiction(self):
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )
        event = self._when_testing_put_provider_home_jurisdiction(OTHER_NON_MEMBER_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now get all the update records for the provider
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(test_provider_record)
        )
        self.assertEqual(1, len(stored_provider_update_records))

        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])

        # the updateType should be homeJurisdictionChange
        self.assertEqual('homeJurisdictionChange', update_data.updateType)
        # In this case, the license information should stay the same as before, and the currentHomeJurisdiction
        # should be set to 'other'
        self.assertEqual('other', update_data.updatedValues['currentHomeJurisdiction'])

    def test_put_provider_home_jurisdiction_adds_provider_update_record_when_member_jurisdiction(self):
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now get all the update records for the provider
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(test_provider_record)
        )
        self.assertEqual(1, len(stored_provider_update_records))

        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])

        # the updateType should be homeJurisdictionChange
        self.assertEqual('homeJurisdictionChange', update_data.updateType)
        # In this case, the currentHomeJurisdiction should be set to the new jurisdiction
        self.assertEqual(NEW_JURISDICTION, update_data.updatedValues['currentHomeJurisdiction'])

    def test_put_provider_home_jurisdiction_adds_provider_update_record_when_license_compact_ineligible_in_jurisdiction(
        self,
    ):
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege()
        )

        # add compact ineligible license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(
            license_compact_eligible=False
        )

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now get all the update records for the provider
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(test_provider_record)
        )
        self.assertEqual(1, len(stored_provider_update_records))

        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])

        # the updateType should be homeJurisdictionChange
        self.assertEqual('homeJurisdictionChange', update_data.updateType)
        # In this case, the currentHomeJurisdiction should be set to the new jurisdiction
        self.assertEqual(
            new_jurisdiction_license_record.jurisdiction, update_data.updatedValues['currentHomeJurisdiction']
        )

    def test_put_provider_home_jurisdiction_deactivates_privilege_if_jurisdiction_is_same_as_new_home_state_license(
        self,
    ):
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        self._when_provider_has_license_in_new_home_state()

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege(privilege_jurisdiction=NEW_JURISDICTION)
        )

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('inactive', stored_privilege_data.homeJurisdictionChangeStatus)

        # verify the expiration dates match on the current license and privilege record
        # since in this case they should not be moved over
        self.assertEqual(test_current_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)
        self.assertEqual(test_current_license_record.jurisdiction, stored_privilege_data.licenseJurisdiction)

    def test_put_provider_home_jurisdiction_adds_update_record_when_privilege_same_jurisdiction_as_new_home_state(
        self,
    ):
        from handlers.provider_users import provider_users_api_handler

        self._when_provider_has_license_in_new_home_state()

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege(privilege_jurisdiction=NEW_JURISDICTION)
        )
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now get all the update records for the privilege record
        stored_privilege_update_records = (
            self.test_data_generator.query_privilege_update_records_for_given_record_from_database(
                test_privilege_record
            )
        )
        self.assertEqual(1, len(stored_privilege_update_records))

        update_data = stored_privilege_update_records[0]
        # the updateType should be homeJurisdictionChange
        self.assertEqual('homeJurisdictionChange', update_data.updateType)
        self.assertEqual('inactive', update_data.updatedValues['homeJurisdictionChangeStatus'])
        # we should not be updating the license jurisdiction or the data of expiration
        self.assertNotIn('licenseJurisdiction', update_data.updatedValues)
        self.assertNotIn('dateOfExpiration', update_data.updatedValues)

    def test_put_provider_home_jurisdiction_keeps_privilege_inactive_if_user_moves_back_to_jurisdiction_with_a_license(
        self,
    ):
        """
        In this test case, the user first moves to a non-member jurisdiction, and their privilege is deactivated. They
        then move back to a member state with a valid license. Because their privilege was previously deactivated, it
        should not be moved over even though there is a valid license.
        """
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.provider_users import provider_users_api_handler

        (test_provider_record, test_current_license_record, test_privilege_record) = (
            self._when_provider_has_one_license_and_privilege(privilege_jurisdiction=NEW_JURISDICTION)
        )

        # first move to a new jurisdiction where there is no license
        # this should deactivate the privilege
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('inactive', stored_privilege_data.homeJurisdictionChangeStatus)

        # now the user moves back to a member jurisdiction with a license
        event = self._when_testing_put_provider_home_jurisdiction(STARTING_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should still be inactive, since it was deactivated with the original license jurisdiction still
        # associated
        updated_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', updated_privilege_data.status)
        self.assertEqual(test_current_license_record.jurisdiction, updated_privilege_data.licenseJurisdiction)
        self.assertEqual(
            'inactive',
            updated_privilege_data.homeJurisdictionChangeStatus,
        )
