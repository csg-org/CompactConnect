import json
from datetime import datetime, date
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

    def test_get_provider_does_not_return_home_jurisdiction_selection_key_if_not_present(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()
        # delete the homeJurisdictionSelection key from the provider dynamodb record
        self.config.provider_table.delete_item(
            Key={
                'pk': f'{TEST_COMPACT}#PROVIDER#{event["requestContext"]["authorizer"]["claims"]["custom:providerId"]}',
                'sk': f'{TEST_COMPACT}#PROVIDER#home-jurisdiction#',
            },
        )

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        expected_provider = self.test_data_generator.generate_default_provider_detail_response()
        del expected_provider['homeJurisdictionSelection']

        self.assertEqual(expected_provider, provider_data)

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
NEW_JURISDICTION = 'ne'
NEW_LICENSE_VALID_EXPIRATION_DATE = '2026-12-12'
NEW_LICENSE_EXPIRED_EXPIRATION_DATE = '2023-12-12'
# this other keyword is used for jurisdictions not listed in the system.
OTHER_NON_MEMBER_JURISDICTION = 'other'

@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPutProviderHomeJurisdiction(TstFunction):


    def _when_provider_has_one_license_and_privilege(self, license_encumbered: bool=False):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum, PrivilegeEncumberedStatusEnum
        test_provider_record = self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': STARTING_JURISDICTION,
                'compact': TEST_COMPACT,
            }
        )


        test_current_license_record = self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': STARTING_JURISDICTION,
                'compact': TEST_COMPACT,
                'licenseType': TEST_LICENSE_TYPE,
                'encumberedStatus': LicenseEncumberedStatusEnum.ENCUMBERED
                if license_encumbered else LicenseEncumberedStatusEnum.UNENCUMBERED
            }
        )

        # add privilege in Kentucky for the current license
        test_privilege_record = self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'compact': TEST_COMPACT,
                'jurisdiction': PRIVILEGE_JURISDICTION,
                'licenseJurisdiction': test_current_license_record.jurisdiction,
                'licenseType': TEST_LICENSE_TYPE,
                'encumberedStatus': PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED if license_encumbered else
                PrivilegeEncumberedStatusEnum.UNENCUMBERED
            }
        )

        return test_provider_record, test_current_license_record, test_privilege_record


    def _when_provider_has_license_in_new_home_state(self, license_encumbered: bool = False,
                                                     license_expired: bool = False,
                                                     license_compact_eligible: bool = True):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum

        return self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': NEW_JURISDICTION,
                'compact': TEST_COMPACT,
                'licenseType': TEST_LICENSE_TYPE,
                'dateOfExpiration': date.fromisoformat(NEW_LICENSE_EXPIRED_EXPIRATION_DATE)
                if license_expired else date.fromisoformat(NEW_LICENSE_VALID_EXPIRATION_DATE),
                'encumberedStatus': LicenseEncumberedStatusEnum.ENCUMBERED
                if license_encumbered else LicenseEncumberedStatusEnum.UNENCUMBERED,
                'jurisdictionUploadedCompactEligibility': 'eligible' if license_compact_eligible else 'ineligible'

            }
        )

    def _when_provider_has_no_license_in_new_selected_jurisdiction(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have a license, and they move to Nebraska,
        where they don't have a license. They also have one privilege for this license
        """
        (
            test_provider_record,
            test_current_license_record,
            test_privilege_record
        ) = self._when_provider_has_one_license_and_privilege()

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record

    def _when_provider_moves_to_non_member_jurisdiction(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have a license and a privilege in KY.
        They move to an international location, which is not a member of the compact.
        """
        (
            test_provider_record,
            test_current_license_record,
            test_privilege_record
        ) = self._when_provider_has_one_license_and_privilege()

        event = self._when_testing_put_provider_home_jurisdiction(OTHER_NON_MEMBER_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record

    def _when_original_home_state_license_is_encumbered(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an encumbered license and a privilege in KY.
        They move to a new state with an unencumbered license with a new expiration date.
        """
        (
            test_provider_record,
            test_current_license_record,
            test_privilege_record
        ) = self._when_provider_has_one_license_and_privilege(license_encumbered=True)

        # add unencumbered license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(license_encumbered=False)

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record, new_jurisdiction_license_record

    def _when_new_home_state_license_is_encumbered(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an active license and a privilege in KY.
        They move to a new state with an encumbered license.
        """
        (
            test_provider_record,
            test_current_license_record,
            test_privilege_record
        ) = self._when_provider_has_one_license_and_privilege(license_encumbered=False)

        # add encumbered license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(license_encumbered=True)

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record, new_jurisdiction_license_record

    def _when_new_home_state_license_is_expired(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an active license and a privilege in KY.
        They move to a new state with an expired license.
        """
        (
            test_provider_record,
            test_current_license_record,
            test_privilege_record
        ) = self._when_provider_has_one_license_and_privilege(license_encumbered=False)

        # add expired license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(license_expired=True)

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record, new_jurisdiction_license_record

    def _when_new_home_state_license_is_not_compact_eligible(self):
        """
        In this setup, we have a provider which starts in Ohio, where they have an active license and a privilege in KY.
        They move to a new state with a license that is not compact eligible.
        """
        (
            test_provider_record,
            test_current_license_record,
            test_privilege_record
        ) = self._when_provider_has_one_license_and_privilege(license_encumbered=False)

        # add compact ineligible license in new jurisdiction
        new_jurisdiction_license_record = self._when_provider_has_license_in_new_home_state(license_compact_eligible=False)

        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        return event, test_provider_record, test_current_license_record, test_privilege_record, new_jurisdiction_license_record


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

        event = self._when_testing_put_provider_home_jurisdiction()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        resp_body = json.loads(resp['body'])

        self.assertEqual({'message': 'ok'}, resp_body)

    def test_put_provider_home_jurisdiction_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_put_provider_home_jurisdiction()

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_put_provider_home_jurisdiction_deactivates_privileges_if_no_license_in_new_jurisdiction(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record
         ) = self._when_provider_has_no_license_in_new_selected_jurisdiction()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('noLicenseInJurisdiction', stored_privilege_data.homeJurisdictionChangeDeactivationStatus)

    def test_put_provider_home_jurisdiction_sets_deactivation_status_on_provider_record_if_no_license_in_new_jurisdiction(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.provider import ProviderData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record
         ) = self._when_provider_has_no_license_in_new_selected_jurisdiction()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the provider record should show provider is in a jurisdiction that is not a member of the compact
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )
        self.assertEqual('inactive', stored_provider_data.licenseStatus)
        self.assertEqual('ineligible', stored_provider_data.compactEligibility)
        self.assertEqual('noLicenseInJurisdiction', stored_provider_data.homeJurisdictionChangeDeactivationStatus)

    def test_put_provider_home_jurisdiction_deactivates_privileges_if_new_jurisdiction_non_member(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record
         ) = self._when_provider_moves_to_non_member_jurisdiction()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there new jurisdiction is not a member of the compact
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('nonMemberJurisdiction', stored_privilege_data.homeJurisdictionChangeDeactivationStatus)

    def test_put_provider_home_jurisdiction_sets_deactivation_status_on_provider_record_if_new_jurisdiction_non_member(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.provider import ProviderData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record
         ) = self._when_provider_moves_to_non_member_jurisdiction()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the provider record should show provider is in a jurisdiction that is not a member of the compact
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )
        self.assertEqual('inactive', stored_provider_data.licenseStatus)
        self.assertEqual('ineligible', stored_provider_data.compactEligibility)
        self.assertEqual('nonMemberJurisdiction', stored_provider_data.homeJurisdictionChangeDeactivationStatus)

    def test_put_provider_home_jurisdiction_does_not_update_privileges_if_starting_home_state_license_is_encumbered(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record,
         test_new_license_record
         ) = self._when_original_home_state_license_is_encumbered()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        # this field should not be added, since the privilege is already encumbered, it should not be deactivated
        # by this operation
        self.assertNotIn('homeJurisdictionChangeDeactivationStatus', stored_privilege_data.to_dict())
        # these values should remain the same since it was previously encumbered, and we do not update privileges to
        # new license information if they are encumbered
        self.assertEqual('licenseEncumbered', stored_privilege_data.encumberedStatus)
        self.assertEqual(test_current_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)

    def test_put_provider_home_jurisdiction_deactivates_privileges_if_new_home_state_license_is_encumbered(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record,
         test_new_license_record
         ) = self._when_new_home_state_license_is_encumbered()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        # this field should not be added, since the privilege is going to be encumbered, not deactivated
        self.assertNotIn('homeJurisdictionChangeDeactivationStatus', stored_privilege_data.to_dict())
        # these values should be set since the new license is encumbered
        self.assertEqual('licenseEncumbered', stored_privilege_data.encumberedStatus)
        self.assertEqual(test_new_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)

    def test_put_provider_home_jurisdiction_expires_privileges_if_new_home_state_license_is_expired(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record,
         test_new_license_record
         ) = self._when_new_home_state_license_is_expired()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        # this field should not be added, since the privilege is going to be encumbered, not deactivated
        self.assertNotIn('homeJurisdictionChangeDeactivationStatus', stored_privilege_data.to_dict())
        # verify the expiration dates match on the new license and privilege record
        self.assertEqual(test_new_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)

    def test_put_provider_home_jurisdiction_activates_privileges_if_new_home_state_license_is_not_expired(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record,
         test_new_license_record
         ) = self._when_new_home_state_license_is_expired()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        # this field should not be added, since the privilege is going to be encumbered, not deactivated
        self.assertNotIn('homeJurisdictionChangeDeactivationStatus', stored_privilege_data.to_dict())
        # verify the expiration dates match on the new license and privilege record
        self.assertEqual(test_new_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)


    def test_put_provider_home_jurisdiction_deactivates_privileges_if_new_home_state_license_is_not_compact_eligible(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         event,
         test_provider_record,
         test_current_license_record,
         test_privilege_record,
         test_new_license_record
         ) = self._when_new_home_state_license_is_not_compact_eligible()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be deactivated because there is no license in the new jurisdiction
        stored_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('inactive', stored_privilege_data.status)
        self.assertEqual('licenseCompactIneligible', stored_privilege_data.homeJurisdictionChangeDeactivationStatus)

        # verify the expiration dates match on the new license and privilege record
        self.assertEqual(test_new_license_record.dateOfExpiration, stored_privilege_data.dateOfExpiration)

    def test_put_provider_home_jurisdiction_does_not_update_expiration_on_privileges_if_they_are_encumbered(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.privilege import PrivilegeData

        (
         test_provider_record,
         test_current_license_record,
         test_privilege_record
         ) = self._when_provider_has_one_license_and_privilege()

        new_license_record = self._when_provider_has_license_in_new_home_state()
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        # add one more privilege record in ne that is encumbered
        encumbered_privilege = self.test_data_generator.put_default_privilege_record_in_provider_table(value_overrides={
                'compact': TEST_COMPACT,
                'jurisdiction': 'ne',
                'licenseJurisdiction': test_current_license_record.jurisdiction,
                'licenseType': TEST_LICENSE_TYPE,
                'encumberedStatus': 'encumbered'
            })

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # the privilege should be successfully moved over since it is not encumbered
        stored_unencumbered_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_privilege_record)
        )
        self.assertEqual('active', stored_unencumbered_privilege_data.status)
        # this field should not be added, since the privilege is going to be moved over to a valid license
        self.assertNotIn('homeJurisdictionChangeDeactivationStatus', stored_unencumbered_privilege_data.to_dict())

        # verify these match on the new license and privilege record
        self.assertEqual(new_license_record.dateOfExpiration, stored_unencumbered_privilege_data.dateOfExpiration)
        self.assertEqual(new_license_record.jurisdiction, stored_unencumbered_privilege_data.licenseJurisdiction)

        # now check the values on the encumbered privilege to ensure they were not updated to the new license
        stored_encumbered_privilege_data = PrivilegeData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(encumbered_privilege)
        )
        self.assertEqual('inactive', stored_encumbered_privilege_data.status)
        self.assertEqual('encumbered', stored_encumbered_privilege_data.encumberedStatus)
        # this field should not be added here either, since the privilege is encumbered, not deactivated by this operation
        self.assertNotIn('homeJurisdictionChangeDeactivationStatus', stored_encumbered_privilege_data.to_dict())

        # verify these match the old license record for the encumbered privilege
        self.assertEqual(test_current_license_record.dateOfExpiration, stored_encumbered_privilege_data.dateOfExpiration)
        self.assertEqual(test_current_license_record.jurisdiction, stored_encumbered_privilege_data.licenseJurisdiction)

    def test_put_provider_home_jurisdiction_updates_provider_record_with_new_license_information(self):
        from handlers.provider_users import provider_users_api_handler
        from cc_common.data_model.schema.provider import ProviderData

        (
         test_provider_record,
         test_current_license_record,
         test_privilege_record
         ) = self._when_provider_has_one_license_and_privilege()
        new_license_record = self._when_provider_has_license_in_new_home_state()
        event = self._when_testing_put_provider_home_jurisdiction(NEW_JURISDICTION, test_provider_record)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )
        self.assertEqual('active', stored_provider_data.licenseStatus)
        self.assertEqual('eligible', stored_provider_data.compactEligibility)
        # this field should not be added, since the provider has a valid license in the new state
        self.assertNotIn('homeJurisdictionChangeDeactivationStatus', stored_provider_data.to_dict())

        # verify these match on the new license and privilege record
        self.assertEqual(new_license_record.dateOfExpiration, stored_provider_data.dateOfExpiration)
        self.assertEqual(new_license_record.jurisdiction, stored_provider_data.licenseJurisdiction)
