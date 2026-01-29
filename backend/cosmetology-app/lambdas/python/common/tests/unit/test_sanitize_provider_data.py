import json

from tests import TstLambdas


class TestSanitizeProviderData(TstLambdas):
    def when_expecting_full_provider_record_returned(self, scopes: set[str]):
        from cc_common.utils import sanitize_provider_data_based_on_caller_scopes

        with open('tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        test_provider = expected_provider.copy()

        resp = sanitize_provider_data_based_on_caller_scopes(compact='cosm', provider=test_provider, scopes=scopes)

        # cast to set to match schema
        expected_provider['privilegeJurisdictions'] = set(expected_provider['privilegeJurisdictions'])

        self.assertEqual(expected_provider, resp)

    def test_full_provider_record_returned_if_caller_has_compact_read_private_permissions(self):
        self.when_expecting_full_provider_record_returned(
            scopes={'openid', 'email', 'cosm/readGeneral', 'cosm/readPrivate'}
        )

    def test_full_provider_record_returned_if_caller_has_read_private_permissions_for_license_jurisdiction(self):
        self.when_expecting_full_provider_record_returned(
            scopes={'openid', 'email', 'cosm/readGeneral', 'oh/cosm.readPrivate'}
        )

    def test_full_provider_record_returned_if_caller_has_read_private_permissions_for_privileges_jurisdiction(self):
        self.when_expecting_full_provider_record_returned(
            scopes={'openid', 'email', 'cosm/readGeneral', 'ne/cosm.readPrivate'}
        )

    def when_testing_general_provider_info_returned(self, scopes: set[str]):
        from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
        from cc_common.utils import sanitize_provider_data_based_on_caller_scopes

        with open('tests/resources/api/provider-detail-response.json') as f:
            full_provider = json.load(f)
            # Re-read data from file to have an independent second copy
            f.seek(0)
            expected_provider = json.load(f)
        mock_ssn = full_provider['ssnLastFour']
        mock_dob = full_provider['dateOfBirth']
        # simplest way to set up mock test user as returned from the db
        loaded_provider = ProviderGeneralResponseSchema().load(full_provider)
        loaded_provider['ssnLastFour'] = mock_ssn
        loaded_provider['dateOfBirth'] = mock_dob
        loaded_provider['licenses'][0]['ssnLastFour'] = mock_ssn
        loaded_provider['licenses'][0]['dateOfBirth'] = mock_dob

        # test provider has a license in oh and privilege in ne
        resp = sanitize_provider_data_based_on_caller_scopes(compact='cosm', provider=loaded_provider, scopes=scopes)

        # now create expected provider record with the ssn and dob removed
        del expected_provider['ssnLastFour']
        del expected_provider['dateOfBirth']
        # also remove the ssn from the license record
        del expected_provider['licenses'][0]['ssnLastFour']
        del expected_provider['licenses'][0]['dateOfBirth']
        # cast to set to match schema
        expected_provider['privilegeJurisdictions'] = set(expected_provider['privilegeJurisdictions'])

        self.assertEqual(expected_provider, resp)

    def test_sanitized_provider_record_returned_if_caller_does_not_have_read_private_permissions_for_jurisdiction(self):
        self.when_testing_general_provider_info_returned(
            scopes={'openid', 'email', 'cosm/readGeneral', 'az/cosm.readPrivate'}
        )

    def test_sanitized_provider_record_returned_if_caller_does_not_have_any_read_private_permissions(self):
        self.when_testing_general_provider_info_returned(scopes={'openid', 'email', 'cosm/readGeneral'})
