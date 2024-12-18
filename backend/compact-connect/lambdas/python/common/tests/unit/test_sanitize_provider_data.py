import json
from tests import TstLambdas


class TestSanitizeProviderData(TstLambdas):

    def when_expecting_full_provider_record_returned(self, scopes: set[str]):
        from cc_common.utils import sanitize_provider_data_based_on_caller_scopes
        with open('tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        test_provider = expected_provider.copy()

        resp = sanitize_provider_data_based_on_caller_scopes(compact='aslp', provider=test_provider,
                                                             scopes=scopes)

        self.assertEqual(resp, expected_provider)

    def test_full_provider_record_returned_if_caller_has_compact_read_private_permissions(self):
        self.when_expecting_full_provider_record_returned(scopes={'openid', 'email', 'aslp/readGeneral',
                                                              'aslp/aslp.readPrivate'})

    def test_full_provider_record_returned_if_caller_has_read_private_permissions_for_license_jurisdiction(self):
        self.when_expecting_full_provider_record_returned(scopes={'openid', 'email', 'aslp/readGeneral',
                                                              'aslp/oh.readPrivate'})

    def test_full_provider_record_returned_if_caller_has_read_private_permissions_for_privileges_jurisdiction(self):
        self.when_expecting_full_provider_record_returned(scopes={'openid', 'email', 'aslp/readGeneral',
                                                              'aslp/ne.readPrivate'})


    def when_testing_general_provider_info_returned(self, scopes: set[str]):
        from cc_common.utils import sanitize_provider_data_based_on_caller_scopes
        from cc_common.data_model.schema.provider import SanitizedProviderReadGeneralSchema

        with open('tests/resources/api/provider-detail-response.json') as f:
            full_provider = json.load(f)
            expected_provider = full_provider.copy()
            mock_ssn = full_provider['ssn']
            mock_dob = full_provider['dateOfBirth']
            mock_doc_keys = full_provider['militaryAffiliations'][0]['documentKeys']
            # simplest way to set up mock test user as returned from the db
            loaded_provider = SanitizedProviderReadGeneralSchema().load(full_provider)
            loaded_provider['ssn'] = mock_ssn
            loaded_provider['dateOfBirth'] = mock_dob
            loaded_provider['militaryAffiliations'][0]['documentKeys'] = mock_doc_keys
            loaded_provider['licenses'][0]['ssn'] = mock_ssn
            loaded_provider['licenses'][0]['dateOfBirth'] = mock_dob

        # test provider has a license in oh and privilege in ne
        resp = sanitize_provider_data_based_on_caller_scopes(compact='aslp', provider=loaded_provider,
                                                             scopes=scopes)

        # now create expected provider record with the ssn and dob removed
        expected_provider.pop('ssn')
        expected_provider.pop('dateOfBirth')
        # we do not return the military affiliation document keys if the caller does not have read private scope
        expected_provider['militaryAffiliations'][0].pop('documentKeys')
        # also remove the ssn from the license record
        expected_provider['licenses'][0].pop('ssn')
        expected_provider['licenses'][0].pop('dateOfBirth')
        # cast to set to match schema
        expected_provider['privilegeJurisdictions'] = set(expected_provider['privilegeJurisdictions'])

        self.assertEqual(expected_provider, resp)


    def test_sanitized_provider_record_returned_if_caller_does_not_have_read_private_permissions_for_jurisdiction(self):
        self.when_testing_general_provider_info_returned(scopes={'openid', 'email', 'aslp/readGeneral',
                                                                     'aslp/az.readPrivate'})

    def test_sanitized_provider_record_returned_if_caller_does_not_have_any_read_private_permissions(self):
        self.when_testing_general_provider_info_returned(scopes={'openid', 'email', 'aslp/readGeneral'})

