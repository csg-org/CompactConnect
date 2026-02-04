import json
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from moto import mock_aws

from tests import TstLambdas


@mock_aws
class TestExpirationRemindersOpenSearch(TstLambdas):
    """Tests for OpenSearch query and data extraction."""

    @patch('handlers.expiration_reminders.ProviderGeneralResponseSchema')
    @patch('handlers.expiration_reminders.opensearch_client')
    def test_iterate_privileges_by_expiration_date_paginates_with_search_after_and_yields_in_order(
        self, mock_client, mock_schema_class
    ):
        mock_client.search = MagicMock()
        mock_schema_class.return_value.load.side_effect = lambda doc: doc

        # Page 1: p1, p2
        mock_client.search.side_effect = [
            {
                'hits': {
                    'total': {'value': 3, 'relation': 'eq'},
                    'hits': [
                        {
                            '_source': {'providerId': 'p1', 'privileges': []},
                            'sort': ['p1'],
                        },
                        {
                            '_source': {'providerId': 'p2', 'privileges': []},
                            'sort': ['p2'],
                        },
                    ],
                }
            },
            # Page 2: p3
            {
                'hits': {
                    'total': {'value': 3, 'relation': 'eq'},
                    'hits': [
                        {
                            '_source': {'providerId': 'p3', 'privileges': []},
                            'sort': ['p3'],
                        }
                    ],
                }
            },
        ]

        from handlers.expiration_reminders import iterate_privileges_by_expiration_date

        results = list(
            iterate_privileges_by_expiration_date(
                compact='aslp',
                expiration_date=date(2026, 2, 16),
                page_size=2,
            )
        )

        self.assertEqual([r.provider_doc['providerId'] for r in results], ['p1', 'p2', 'p3'])
        self.assertEqual([r.search_after for r in results], [['p1'], ['p2'], ['p3']])

        # Verify pagination: second call includes search_after from last hit in page 1
        first_call_kwargs = mock_client.search.call_args_list[0].kwargs
        second_call_kwargs = mock_client.search.call_args_list[1].kwargs

        self.assertEqual('compact_aslp_providers', first_call_kwargs['index_name'])
        self.assertNotIn('search_after', first_call_kwargs['body'])

        self.assertEqual('compact_aslp_providers', second_call_kwargs['index_name'])
        self.assertEqual(['p2'], second_call_kwargs['body']['search_after'])

    @patch('handlers.expiration_reminders.ProviderGeneralResponseSchema')
    @patch('handlers.expiration_reminders.opensearch_client')
    def test_iterate_privileges_by_expiration_date_resumes_with_initial_search_after(
        self, mock_client, mock_schema_class
    ):
        """When initial_search_after is provided, first OpenSearch query uses it."""
        mock_client.search = MagicMock(
            return_value={
                'hits': {
                    'total': {'value': 1, 'relation': 'eq'},
                    'hits': [
                        {
                            '_source': {'providerId': 'p2', 'privileges': []},
                            'sort': ['p2'],
                        }
                    ],
                }
            }
        )
        mock_schema_class.return_value.load.side_effect = lambda doc: doc

        from handlers.expiration_reminders import iterate_privileges_by_expiration_date

        results = list(
            iterate_privileges_by_expiration_date(
                compact='aslp',
                expiration_date=date(2026, 2, 16),
                page_size=2,
                initial_search_after=['p1'],
            )
        )

        self.assertEqual(1, len(results))
        self.assertEqual('p2', results[0].provider_doc['providerId'])
        mock_client.search.assert_called_once()
        self.assertEqual(['p1'], mock_client.search.call_args.kwargs['body']['search_after'])

    @patch('handlers.expiration_reminders.ProviderGeneralResponseSchema')
    @patch('handlers.expiration_reminders.opensearch_client')
    def test_iterate_privileges_by_expiration_date_returns_full_provider_document(self, mock_client, mock_schema_class):
        """Provider document includes full privileges list from _source (no inner_hits filtering)."""
        full_privileges = [
            {
                'privilegeId': 'a',
                'jurisdiction': 'oh',
                'licenseType': 'aud',
                'dateOfExpiration': '2026-02-16',
                'status': 'active',
            },
            {
                'privilegeId': 'b',
                'jurisdiction': 'ky',
                'licenseType': 'slp',
                'dateOfExpiration': '2026-03-01',
                'status': 'active',
            },
        ]
        mock_client.search = MagicMock(
            return_value={
                'hits': {
                    'total': {'value': 1, 'relation': 'eq'},
                    'hits': [
                        {
                            '_source': {
                                'providerId': 'p1',
                                'privileges': full_privileges,
                            },
                            'sort': ['p1'],
                        }
                    ],
                }
            }
        )
        mock_schema_class.return_value.load.side_effect = lambda doc: doc

        from handlers.expiration_reminders import iterate_privileges_by_expiration_date

        result = next(
            iterate_privileges_by_expiration_date(
                compact='aslp',
                expiration_date=date(2026, 2, 16),
                page_size=100,
            )
        )

        self.assertEqual('p1', result.provider_doc['providerId'])
        self.assertEqual(full_privileges, result.provider_doc['privileges'])


@mock_aws
class TestProcessExpirationReminders(TstLambdas):
    """Tests for the main handler with email sending and idempotency."""

    def _make_provider_doc(
        self,
        *,
        provider_id: str | None = None,
        email: str | None = 'test@example.com',
        given_name: str = 'John',
        privileges: list | None = None,
    ) -> dict:
        """Helper to create a provider document for testing."""
        doc = {
            'providerId': provider_id or str(uuid4()),
            'givenName': given_name,
            'privileges': privileges
            or [
                {
                    'privilegeId': 'a',
                    'dateOfExpiration': '2026-02-16',
                    'status': 'active',
                    'jurisdiction': 'oh',
                    'licenseType': 'aud',
                },
            ],
        }
        if email:
            doc['compactConnectRegisteredEmailAddress'] = email
        return doc

    def _make_event(self, days_before: int = 30, compact: str = 'aslp') -> dict:
        """Helper to create a valid event for testing."""
        return {
            'targetDate': '2026-02-16',
            'daysBefore': days_before,
            'compact': compact,
            'scheduledTime': '2026-01-17T10:00:00Z',
        }

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_sends_email_and_records_success(self, mock_iter, mock_email_service_client, mock_tracker_class):
        mock_email_client = mock_email_service_client

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = False
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ]
        )

        resp = process_expiration_reminders(self._make_event(days_before=30), self.mock_context)

        self.assertEqual('complete', resp['status'])
        self.assertEqual(1, resp['metrics']['sent'])
        self.assertEqual(0, resp['metrics']['failed'])
        self.assertEqual(30, resp['daysBefore'])
        self.assertEqual('aslp', resp['compact'])
        mock_email_client.send_privilege_expiration_reminder_email.assert_called_once()
        call_kwargs = mock_email_client.send_privilege_expiration_reminder_email.call_args.kwargs
        tv = call_kwargs['template_variables']
        self.assertEqual('John', tv.provider_first_name)
        self.assertEqual('2026-02-16', tv.expiration_date.isoformat())
        self.assertEqual(1, len(tv.privileges))
        priv = tv.privileges[0]
        self.assertEqual('Ohio', priv['jurisdiction'], 'jurisdiction must be full state name')
        self.assertEqual('aud', priv['licenseType'])
        self.assertEqual('a', priv['privilegeId'])
        self.assertEqual('2026-02-16', priv['dateOfExpiration'], 'dateOfExpiration must be ISO 8601')
        mock_tracker_instance.record_success.assert_called_once()

        # Verify tracker was created with correct event_type
        from expiration_reminder_tracker import ExpirationEventType

        mock_tracker_class.assert_called_once()
        tracker_call = mock_tracker_class.call_args.kwargs
        self.assertEqual(ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY, tracker_call['event_type'])

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_skips_when_already_sent(self, mock_iter, mock_email_service_client, mock_tracker_class):
        mock_email_client = mock_email_service_client

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = True
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ]
        )

        resp = process_expiration_reminders(self._make_event(days_before=7), self.mock_context)

        self.assertEqual('complete', resp['status'])
        self.assertEqual(0, resp['metrics']['sent'])
        self.assertEqual(1, resp['metrics']['alreadySent'])
        mock_email_client.send_privilege_expiration_reminder_email.assert_not_called()

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_logs_error_for_provider_without_email(self, mock_iter, mock_email_service_client, mock_tracker_class):
        """Provider without email address is skipped and logged as noEmail."""
        mock_email_client = mock_email_service_client

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = False
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=self._make_provider_doc(email=None), search_after=['cursor1']),
            ]
        )

        resp = process_expiration_reminders(self._make_event(days_before=0), self.mock_context)

        self.assertEqual('complete', resp['status'])
        self.assertEqual(0, resp['metrics']['sent'])
        self.assertEqual(1, resp['metrics']['noEmail'])
        mock_email_client.send_privilege_expiration_reminder_email.assert_not_called()

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_records_failure_on_email_error(self, mock_iter, mock_email_client, mock_tracker_class):
        """Email service raises exception; handler records failure."""
        mock_email_client.send_privilege_expiration_reminder_email.side_effect = Exception('Email service down')

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = False
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ]
        )

        resp = process_expiration_reminders(self._make_event(), self.mock_context)

        self.assertEqual('complete', resp['status'])
        self.assertEqual(0, resp['metrics']['sent'])
        self.assertEqual(1, resp['metrics']['failed'])
        mock_tracker_instance.record_failure.assert_called_once()
        self.assertIn('Email service down', mock_tracker_instance.record_failure.call_args.kwargs['error_message'])

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_records_failure_when_privilege_has_unknown_jurisdiction(
        self, mock_iter, mock_email_client, mock_tracker_class
    ):
        """Unknown jurisdiction code raises when building template; handler records failure."""

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = False
        mock_tracker_class.return_value = mock_tracker_instance

        # Privilege with jurisdiction not in CompactConfigUtility.JURISDICTION_NAME_MAPPING
        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        doc = self._make_provider_doc()
        doc['privileges'][0]['jurisdiction'] = 'xx'
        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=doc, search_after=['cursor1']),
            ]
        )

        resp = process_expiration_reminders(self._make_event(), self.mock_context)

        self.assertEqual('complete', resp['status'])
        self.assertEqual(0, resp['metrics']['sent'])
        self.assertEqual(1, resp['metrics']['failed'])
        mock_tracker_instance.record_failure.assert_called_once()
        failure_msg = mock_tracker_instance.record_failure.call_args.kwargs['error_message']
        self.assertIn('Unknown jurisdiction', failure_msg)

    def test_handler_validates_days_before_value(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders(
                {
                    'targetDate': '2026-02-16',
                    'daysBefore': 999,  # Invalid
                    'compact': 'aslp',
                },
                self.mock_context,
            )
        self.assertIn('daysBefore', str(ctx.exception))

    def test_handler_requires_days_before_field(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders({'targetDate': '2026-02-16', 'compact': 'aslp'}, self.mock_context)
        self.assertIn('daysBefore', str(ctx.exception))

    def test_handler_requires_compact_field(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders({'targetDate': '2026-02-16', 'daysBefore': 30}, self.mock_context)
        self.assertIn('compact', str(ctx.exception))

    def test_handler_validates_compact_value(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders(
                {'targetDate': '2026-02-16', 'daysBefore': 30, 'compact': 'invalid'}, self.mock_context
            )
        self.assertIn('compact', str(ctx.exception))

    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2026-01-17T12:00:00+00:00'))
    def test_handler_calculates_target_date_from_days_before_when_not_provided(
        self, mock_iter, mock_tracker_class, mock_email_client
    ):
        """When targetDate is not provided, handler calculates it based on daysBefore."""
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = False
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import process_expiration_reminders

        mock_iter.return_value = iter([])

        resp = process_expiration_reminders({'daysBefore': 30, 'compact': 'aslp'}, self.mock_context)

        self.assertEqual('complete', resp['status'])
        # Verify it calculated the correct target date (2026-01-17 + 30 days = 2026-02-16)
        self.assertEqual('2026-02-16', resp['targetDate'])
        self.assertEqual(30, resp['daysBefore'])

        # Verify the generator was called with the calculated date and no initial_search_after
        mock_iter.assert_called_once()
        call_kwargs = mock_iter.call_args.kwargs
        self.assertEqual(date(2026, 2, 16), call_kwargs['expiration_date'])
        self.assertIsNone(call_kwargs.get('initial_search_after'))

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_continuation_parses_accumulated_metrics_and_search_after(
        self, mock_iter, mock_email_client, mock_tracker_class
    ):
        """Continuation event with _continuation state merges accumulated metrics and resumes from searchAfter."""

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.side_effect = [False, True, True, False, False]
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        # Simulate a continuation invocation
        event_with_continuation = {
            'targetDate': '2026-02-16',
            'daysBefore': 30,
            'compact': 'aslp',
            '_continuation': {
                'searchAfter': ['cursor1'],
                'depth': 1,
                'accumulatedMetrics': {'sent': 100, 'skipped': 2, 'alreadySent': 5},
            },
        }

        # This invocation processes 1 new email, 2 already sent
        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor2']),
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor3']),
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor4']),
            ]
        )

        resp = process_expiration_reminders(event_with_continuation, self.mock_context)

        self.assertEqual('complete', resp['status'])
        self.assertEqual(101, resp['metrics']['sent'])
        self.assertEqual(2, resp['metrics']['skipped'])
        self.assertEqual(7, resp['metrics']['alreadySent'])
        self.assertEqual(2, resp['totalInvocations'])
        mock_iter.assert_called_once()
        call_kwargs = mock_iter.call_args.kwargs
        self.assertEqual(['cursor1'], call_kwargs['initial_search_after'])

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('cc_common.config._Config.lambda_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_invokes_itself_with_pagination_values_when_reaching_limit(
        self, mock_iter, mock_lambda_client, mock_email_client, mock_tracker_class
    ):
        """Handler detects remaining time is low, invokes itself with continuation state."""

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = False
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        # Return one provider doc
        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ]
        )

        # Mock the context to simulate approaching timeout
        # TIMEOUT_BUFFER_MS is 120,000 (2 minutes), so set remaining time to 100,000 (< buffer)
        mock_context_below_time_threshold = MagicMock()
        mock_context_below_time_threshold.get_remaining_time_in_millis.return_value = 100_000
        mock_context_below_time_threshold.function_name = 'test-expiration-reminders'

        resp = process_expiration_reminders(self._make_event(), mock_context_below_time_threshold)

        self.assertEqual('continued', resp['status'])
        self.assertEqual(1, resp['nextInvocationDepth'])
        self.assertEqual(['cursor1'], resp['resumeFrom']['searchAfter'])
        self.assertEqual(1, resp['metricsAtContinuation']['sent'])

        mock_lambda_client.invoke.assert_called_once()
        call_kwargs = mock_lambda_client.invoke.call_args.kwargs
        self.assertEqual('Event', call_kwargs['InvocationType'])
        payload = json.loads(call_kwargs['Payload'])
        self.assertEqual(30, payload['daysBefore'])
        self.assertEqual('aslp', payload['compact'])
        self.assertEqual(['cursor1'], payload['_continuation']['searchAfter'])
        self.assertEqual(1, payload['_continuation']['depth'])
        self.assertEqual(1, payload['_continuation']['accumulatedMetrics']['sent'])

    def test_handler_max_continuation_depth_raises(self):
        """When continuation depth >= MAX_CONTINUATION_DEPTH, handler raises RuntimeError."""
        from handlers.expiration_reminders import MAX_CONTINUATION_DEPTH, process_expiration_reminders

        event = {
            'targetDate': '2026-02-16',
            'daysBefore': 30,
            'compact': 'aslp',
            '_continuation': {
                'searchAfter': ['cursor1'],
                'depth': MAX_CONTINUATION_DEPTH,
                'accumulatedMetrics': {},
            },
        }
        with self.assertRaises(RuntimeError) as ctx:
            process_expiration_reminders(event, self.mock_context)
        self.assertIn(str(MAX_CONTINUATION_DEPTH), str(ctx.exception))

    @patch('handlers.expiration_reminders.ExpirationReminderTracker')
    @patch('cc_common.config._Config.email_service_client')
    @patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date')
    def test_handler_only_includes_active_privileges_in_email(self, mock_iter, mock_email_client, mock_tracker_class):
        """
        Only active privileges are included in the email; inactive privileges are filtered out.
        """

        mock_tracker_instance = MagicMock()
        mock_tracker_instance.was_already_sent.return_value = False
        mock_tracker_class.return_value = mock_tracker_instance

        from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

        # Create provider with three privileges:
        # 1. Inactive (encumbered)
        # 2. Inactive (was stale-expired in OpenSearch, schema corrected status to inactive)
        # 3. Active and expiring on target date
        privileges = [
            {
                'privilegeId': 'encumbered-priv',
                'dateOfExpiration': '2026-02-16',
                'status': 'inactive',  # Encumbered - results in inactive status
                'jurisdiction': 'oh',
                'licenseType': 'aud',
            },
            {
                'privilegeId': 'active-expiring-priv',
                'dateOfExpiration': '2026-02-16',
                'status': 'active',  # Active privilege expiring on target date
                'jurisdiction': 'ne',
                'licenseType': 'aud',
            },
        ]
        provider_doc = self._make_provider_doc(privileges=privileges)

        mock_iter.return_value = iter(
            [
                PaginatedProviderResult(provider_doc=provider_doc, search_after=['cursor1']),
            ]
        )

        # Use daysBefore=0 to simulate day-of expiration notification
        resp = process_expiration_reminders(self._make_event(days_before=0), self.mock_context)

        self.assertEqual('complete', resp['status'])
        self.assertEqual(1, resp['metrics']['sent'])

        # Verify only the active privilege was passed to the email client
        mock_email_client.send_privilege_expiration_reminder_email.assert_called_once()
        call_kwargs = mock_email_client.send_privilege_expiration_reminder_email.call_args.kwargs
        tv = call_kwargs['template_variables']

        # Should only have 1 privilege (the active one)
        self.assertEqual(1, len(tv.privileges), 'Only active privileges should be included in email')

        # Verify it's the correct privilege
        priv = tv.privileges[0]
        self.assertEqual('active-expiring-priv', priv['privilegeId'])
        self.assertEqual('Nebraska', priv['jurisdiction'])
        self.assertEqual('aud', priv['licenseType'])
        self.assertEqual('2026-02-16', priv['dateOfExpiration'])
