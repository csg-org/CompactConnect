import json
from unittest.mock import MagicMock, patch

from cc_common.exceptions import CCAmbiguousLicenseNumberException, CCInvalidRequestException

from tests import TstLambdas

COMPACT = 'cosm'
JURISDICTION = 'oh'
PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'
SSN_LAST_FOUR = '1234'
EVENT_TIME = '2024-11-08T23:59:59+00:00'


def _license(**overrides) -> dict:
    """A license record as it looks after LicensePostRequestSchema.dump()."""
    record = {
        'compact': COMPACT,
        'jurisdiction': JURISDICTION,
        'licenseNumber': 'A0608337260',
        'licenseType': 'cosmetologist',
        'licenseStatus': 'active',
        'compactEligibility': 'eligible',
        'givenName': 'Björk',
        'familyName': 'Guðmundsdóttir',
        'dateOfIssuance': '2010-06-06',
        'dateOfExpiration': '2025-04-04',
        'dateOfBirth': '1985-06-06',
        'homeAddressStreet1': '123 A St.',
        'homeAddressCity': 'Columbus',
        'homeAddressState': 'oh',
        'homeAddressPostalCode': '43004',
    }
    record.update(overrides)
    return record


def _resolve(license_record: dict, *, record_position: int = 0, seen_license_keys: dict | None = None) -> dict:
    """Call the resolver with the request-path values these tests always use."""
    from license_upload_without_ssn import resolve_license_without_ssn

    return resolve_license_without_ssn(
        compact=COMPACT,
        jurisdiction=JURISDICTION,
        license_record=license_record,
        record_position=record_position,
        seen_license_keys=seen_license_keys if seen_license_keys is not None else {},
    )


class TestPartitionLicensesBySsnPresence(TstLambdas):
    def test_splits_records_by_whether_they_carry_an_ssn(self):
        from license_upload_without_ssn import partition_licenses_by_ssn_presence

        with_ssn = _license(ssn='123-12-1234', licenseNumber='WITH')
        without_ssn = _license(licenseNumber='WITHOUT')

        ssn_licenses, ssnless_licenses = partition_licenses_by_ssn_presence([with_ssn, without_ssn])

        self.assertEqual([with_ssn], ssn_licenses)
        self.assertEqual([(1, without_ssn)], ssnless_licenses)

    def test_preserves_input_order_and_reports_request_position(self):
        """
        The index travels with each SSN-less record so a per-record error can be reported against the row
        the caller actually sent, even though the two paths are processed separately.
        """
        from license_upload_without_ssn import partition_licenses_by_ssn_presence

        licenses = [
            _license(licenseNumber='FIRST'),
            _license(ssn='123-12-1234', licenseNumber='SECOND'),
            _license(licenseNumber='THIRD'),
        ]

        ssn_licenses, ssnless_licenses = partition_licenses_by_ssn_presence(licenses)

        self.assertEqual(['SECOND'], [record['licenseNumber'] for record in ssn_licenses])
        self.assertEqual([(0, 'FIRST'), (2, 'THIRD')], [(i, r['licenseNumber']) for i, r in ssnless_licenses])

    def test_returns_lists_independent_of_the_input_list(self):
        from license_upload_without_ssn import partition_licenses_by_ssn_presence

        licenses = [_license(licenseNumber='ONLY')]

        _, ssnless_licenses = partition_licenses_by_ssn_presence(licenses)
        licenses.clear()

        self.assertEqual(1, len(ssnless_licenses))


class TestLicenseNumberDedupeKey(TstLambdas):
    def test_key_distinguishes_license_type(self):
        """
        A state may legitimately hold one license number across license types for one practitioner, so
        the key must not treat those rows as duplicates of each other.
        """
        from license_upload_without_ssn import license_number_dedupe_key

        self.assertNotEqual(
            license_number_dedupe_key(_license(licenseType='cosmetologist')),
            license_number_dedupe_key(_license(licenseType='esthetician')),
        )

    def test_key_matches_for_the_same_number_and_license_type(self):
        from license_upload_without_ssn import license_number_dedupe_key

        self.assertEqual(license_number_dedupe_key(_license()), license_number_dedupe_key(_license()))

    def test_key_distinguishes_license_number(self):
        from license_upload_without_ssn import license_number_dedupe_key

        self.assertNotEqual(
            license_number_dedupe_key(_license(licenseNumber='ONE')),
            license_number_dedupe_key(_license(licenseNumber='TWO')),
        )


@patch('license_upload_without_ssn.config')
class TestResolveLicenseWithoutSsn(TstLambdas):
    @staticmethod
    def _mock_lookup_result(mock_config, provider_id=PROVIDER_ID, ssn_last_four=SSN_LAST_FOUR):
        result = MagicMock()
        result.provider_id = provider_id
        result.ssn_last_four = ssn_last_four
        mock_config.data_client.find_provider_by_license_number.return_value = result

    def test_returns_a_copy_enriched_with_provider_id_and_ssn_last_four(self, mock_config):
        self._mock_lookup_result(mock_config)
        license_record = _license()

        resolved = _resolve(license_record)

        self.assertEqual(PROVIDER_ID, resolved['providerId'])
        self.assertEqual(SSN_LAST_FOUR, resolved['ssnLastFour'])
        self.assertNotIn('ssn', resolved)
        # the caller's record must not be mutated
        self.assertNotIn('providerId', license_record)

    def test_looks_the_license_up_within_the_path_compact_and_jurisdiction(self, mock_config):
        """
        The compact and jurisdiction come from the request path, never from the record body, so a state
        cannot resolve a license number belonging to another jurisdiction.
        """
        self._mock_lookup_result(mock_config)

        _resolve(_license(compact='octp', jurisdiction='ne'))

        mock_config.data_client.find_provider_by_license_number.assert_called_once_with(
            compact=COMPACT,
            jurisdiction=JURISDICTION,
            license_number='A0608337260',
        )

    def test_raises_invalid_request_when_the_license_number_is_unknown(self, mock_config):
        from license_upload_without_ssn import LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE

        mock_config.data_client.find_provider_by_license_number.return_value = None

        with self.assertRaises(CCInvalidRequestException) as context:
            _resolve(_license())

        self.assertEqual(LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE, context.exception.message)

    def test_propagates_ambiguous_license_number(self, mock_config):
        mock_config.data_client.find_provider_by_license_number.side_effect = CCAmbiguousLicenseNumberException('boom')

        with self.assertRaises(CCAmbiguousLicenseNumberException):
            _resolve(_license())

    def test_rejects_a_license_already_seen_in_this_upload_and_names_the_earlier_record(self, mock_config):
        self._mock_lookup_result(mock_config)
        seen_license_keys = {}

        _resolve(_license(), record_position=3, seen_license_keys=seen_license_keys)

        with self.assertRaises(CCInvalidRequestException) as context:
            _resolve(_license(), record_position=7, seen_license_keys=seen_license_keys)

        # the state needs to know which earlier record it collided with in order to fix either one
        self.assertIn('matches with record 3', context.exception.message)

    def test_registers_the_license_before_resolving_it(self, mock_config):
        """
        A row that fails to resolve still claims its license number, so a later row carrying the same
        number is reported as the duplicate it is rather than repeating the first row's error.
        """
        mock_config.data_client.find_provider_by_license_number.return_value = None
        seen_license_keys = {}

        with self.assertRaises(CCInvalidRequestException):
            _resolve(_license(), record_position=1, seen_license_keys=seen_license_keys)

        with self.assertRaises(CCInvalidRequestException) as context:
            _resolve(_license(), record_position=2, seen_license_keys=seen_license_keys)

        self.assertIn('matches with record 1', context.exception.message)

    def test_allows_the_same_license_number_for_a_different_license_type(self, mock_config):
        self._mock_lookup_result(mock_config)
        seen_license_keys = {}

        _resolve(_license(), record_position=1, seen_license_keys=seen_license_keys)
        resolved = _resolve(_license(licenseType='esthetician'), record_position=2, seen_license_keys=seen_license_keys)

        self.assertEqual(PROVIDER_ID, resolved['providerId'])


@patch('license_upload_without_ssn.metrics')
@patch('license_upload_without_ssn.config')
class TestResolutionMetrics(TstLambdas):
    """
    These metrics are how we watch adoption and spot trouble after release. They are for observability
    only -- no alarms are wired to them.
    """

    def test_counts_a_resolved_license(self, mock_config, mock_metrics):
        from license_upload_without_ssn import LICENSE_UPLOAD_WITHOUT_SSN_RESOLVED_METRIC

        result = MagicMock()
        result.provider_id = PROVIDER_ID
        result.ssn_last_four = SSN_LAST_FOUR
        mock_config.data_client.find_provider_by_license_number.return_value = result

        _resolve(_license())

        self.assertEqual(
            [LICENSE_UPLOAD_WITHOUT_SSN_RESOLVED_METRIC],
            [call.kwargs['name'] for call in mock_metrics.add_metric.call_args_list],
        )

    def test_counts_an_unknown_license_number(self, mock_config, mock_metrics):
        from license_upload_without_ssn import LICENSE_UPLOAD_WITHOUT_SSN_NOT_FOUND_METRIC

        mock_config.data_client.find_provider_by_license_number.return_value = None

        with self.assertRaises(CCInvalidRequestException):
            _resolve(_license())

        self.assertEqual(
            [LICENSE_UPLOAD_WITHOUT_SSN_NOT_FOUND_METRIC],
            [call.kwargs['name'] for call in mock_metrics.add_metric.call_args_list],
        )

    def test_counts_an_ambiguous_license_number(self, mock_config, mock_metrics):
        from license_upload_without_ssn import LICENSE_UPLOAD_WITHOUT_SSN_AMBIGUOUS_METRIC

        mock_config.data_client.find_provider_by_license_number.side_effect = CCAmbiguousLicenseNumberException('boom')

        with self.assertRaises(CCAmbiguousLicenseNumberException):
            _resolve(_license())

        self.assertEqual(
            [LICENSE_UPLOAD_WITHOUT_SSN_AMBIGUOUS_METRIC],
            [call.kwargs['name'] for call in mock_metrics.add_metric.call_args_list],
        )


class TestBuildLicenseIngestEventEntry(TstLambdas):
    def test_entry_targets_the_ingest_detail_type(self):
        from license_upload_without_ssn import build_license_ingest_event_entry

        entry = build_license_ingest_event_entry(
            license_record=_license(providerId=PROVIDER_ID, ssnLastFour=SSN_LAST_FOUR),
            event_time=EVENT_TIME,
        )

        self.assertEqual('license.ingest', entry['DetailType'])
        self.assertEqual('org.compactconnect.provider-data', entry['Source'])

    def test_detail_carries_the_event_time_the_ingest_handler_expects(self):
        from license_upload_without_ssn import build_license_ingest_event_entry

        entry = build_license_ingest_event_entry(
            license_record=_license(providerId=PROVIDER_ID, ssnLastFour=SSN_LAST_FOUR),
            event_time=EVENT_TIME,
        )

        self.assertEqual(EVENT_TIME, json.loads(entry['Detail'])['eventTime'])

    def test_detail_never_carries_an_ssn(self):
        """The whole point of this path is that no full SSN reaches the event bus."""
        from license_upload_without_ssn import build_license_ingest_event_entry

        entry = build_license_ingest_event_entry(
            license_record=_license(
                ssn='123-12-1234',
                previousSSN='123-12-9876',
                providerId=PROVIDER_ID,
                ssnLastFour=SSN_LAST_FOUR,
            ),
            event_time=EVENT_TIME,
        )

        detail = json.loads(entry['Detail'])
        self.assertNotIn('ssn', detail)
        self.assertNotIn('previousSSN', detail)
        self.assertNotIn('123-12-1234', entry['Detail'])
        self.assertNotIn('123-12-9876', entry['Detail'])

    def test_detail_loads_cleanly_through_the_ingest_schema(self):
        """
        Contract test: this path publishes straight to the ingest handler, bypassing the SSN
        preprocessor. If the detail did not satisfy LicenseIngestSchema, records would fail on the far
        side of the event bus where the state never sees the error.
        """
        from cc_common.data_model.schema.license.ingest import LicenseIngestSchema
        from license_upload_without_ssn import build_license_ingest_event_entry

        entry = build_license_ingest_event_entry(
            license_record=_license(providerId=PROVIDER_ID, ssnLastFour=SSN_LAST_FOUR),
            event_time=EVENT_TIME,
        )

        detail = json.loads(entry['Detail'])
        del detail['eventTime']

        loaded = LicenseIngestSchema().load(detail)

        self.assertEqual(SSN_LAST_FOUR, loaded['ssnLastFour'])
        self.assertEqual('active', loaded['jurisdictionUploadedLicenseStatus'])
        self.assertEqual('eligible', loaded['jurisdictionUploadedCompactEligibility'])


@patch('license_upload_without_ssn.config')
class TestPublishResolvedLicensesToEventBus(TstLambdas):
    def test_publishes_every_record(self, mock_config):
        from license_upload_without_ssn import publish_resolved_licenses_to_event_bus

        mock_config.events_client.put_events.return_value = {'FailedEntryCount': 0}

        failed_count = publish_resolved_licenses_to_event_bus(
            licenses=[
                _license(providerId=PROVIDER_ID, ssnLastFour=SSN_LAST_FOUR, licenseNumber=str(i)) for i in range(3)
            ],
            event_time=EVENT_TIME,
        )

        self.assertEqual(0, failed_count)
        published = [
            entry for call in mock_config.events_client.put_events.call_args_list for entry in call.kwargs['Entries']
        ]
        self.assertEqual(3, len(published))

    def test_batches_puts_within_the_event_bridge_limit(self, mock_config):
        """EventBridge accepts at most 10 entries per PutEvents call."""
        from license_upload_without_ssn import publish_resolved_licenses_to_event_bus

        mock_config.events_client.put_events.return_value = {'FailedEntryCount': 0}

        publish_resolved_licenses_to_event_bus(
            licenses=[
                _license(providerId=PROVIDER_ID, ssnLastFour=SSN_LAST_FOUR, licenseNumber=str(i)) for i in range(23)
            ],
            event_time=EVENT_TIME,
        )

        batch_sizes = [len(call.kwargs['Entries']) for call in mock_config.events_client.put_events.call_args_list]
        self.assertEqual([10, 10, 3], batch_sizes)

    def test_reports_failed_entries(self, mock_config):
        from license_upload_without_ssn import publish_resolved_licenses_to_event_bus

        mock_config.events_client.put_events.return_value = {
            'FailedEntryCount': 1,
            'Entries': [{'ErrorCode': 'InternalException'}],
        }

        failed_count = publish_resolved_licenses_to_event_bus(
            licenses=[_license(providerId=PROVIDER_ID, ssnLastFour=SSN_LAST_FOUR)],
            event_time=EVENT_TIME,
        )

        self.assertEqual(1, failed_count)
