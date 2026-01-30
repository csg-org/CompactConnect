import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from tests import TstLambdas


class TestExpirationRemindersOpenSearch(TstLambdas):
    """Tests for OpenSearch query and data extraction."""

    def test_iterate_privileges_by_expiration_date_paginates_with_search_after_and_yields_in_order(self):
        # Patch the module-level opensearch_client and schema load (validation would require full fixture)
        with (
            patch('handlers.expiration_reminders.opensearch_client') as mock_client,
            patch('handlers.expiration_reminders.ProviderGeneralResponseSchema') as mock_schema_class,
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

    def test_iterate_privileges_by_expiration_date_resumes_with_initial_search_after(self):
        """When initial_search_after is provided, first OpenSearch query uses it."""
        with (
            patch('handlers.expiration_reminders.opensearch_client') as mock_client,
            patch('handlers.expiration_reminders.ProviderGeneralResponseSchema') as mock_schema_class,
        ):
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

    def test_iterate_privileges_by_expiration_date_returns_full_provider_document(self):
        """Provider document includes full privileges list from _source (no inner_hits filtering)."""
        with (
            patch('handlers.expiration_reminders.opensearch_client') as mock_client,
            patch('handlers.expiration_reminders.ProviderGeneralResponseSchema') as mock_schema_class,
        ):
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

            self.assertEqual(result.provider_doc['providerId'], 'p1')
            self.assertEqual(result.provider_doc['privileges'], full_privileges)
            self.assertEqual(result.search_after, ['p1'])


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
            'privileges': privileges or [
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

    def test_handler_sends_email_and_records_success(self):
        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
        ):
            mock_config.compacts = ['aslp']
            mock_email_client = MagicMock()
            mock_config.email_service_client = mock_email_client

            mock_tracker_instance = MagicMock()
            mock_tracker_instance.was_already_sent.return_value = False
            mock_tracker_class.return_value = mock_tracker_instance

            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            mock_iter.return_value = iter([
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ])

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

    def test_handler_skips_when_already_sent(self):
        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
        ):
            mock_config.compacts = ['aslp']
            mock_email_client = MagicMock()
            mock_config.email_service_client = mock_email_client

            mock_tracker_instance = MagicMock()
            mock_tracker_instance.was_already_sent.return_value = True
            mock_tracker_class.return_value = mock_tracker_instance

            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            mock_iter.return_value = iter([
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ])

            resp = process_expiration_reminders(self._make_event(days_before=7), self.mock_context)

            self.assertEqual('complete', resp['status'])
            self.assertEqual(0, resp['metrics']['sent'])
            self.assertEqual(1, resp['metrics']['alreadySent'])
            mock_email_client.send_privilege_expiration_reminder_email.assert_not_called()

    def test_handler_logs_error_for_provider_without_email(self):
        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
            patch('handlers.expiration_reminders.logger') as mock_logger,
        ):
            mock_config.compacts = ['aslp']
            mock_email_client = MagicMock()
            mock_config.email_service_client = mock_email_client

            # Provider without email
            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            mock_iter.return_value = iter([
                PaginatedProviderResult(
                    provider_doc=self._make_provider_doc(email=None),
                    search_after=['cursor1'],
                ),
            ])

            resp = process_expiration_reminders(self._make_event(days_before=0), self.mock_context)

            self.assertEqual('complete', resp['status'])
            self.assertEqual(0, resp['metrics']['sent'])
            self.assertEqual(1, resp['metrics']['noEmail'])
            mock_email_client.send_privilege_expiration_reminder_email.assert_not_called()
            mock_tracker_class.assert_not_called()
            # Verify error was logged (not just debug)
            mock_logger.error.assert_called()

    def test_handler_records_failure_on_email_error(self):
        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
        ):
            mock_config.compacts = ['aslp']
            mock_email_client = MagicMock()
            mock_email_client.send_privilege_expiration_reminder_email.side_effect = Exception('Email service down')
            mock_config.email_service_client = mock_email_client

            mock_tracker_instance = MagicMock()
            mock_tracker_instance.was_already_sent.return_value = False
            mock_tracker_class.return_value = mock_tracker_instance

            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            mock_iter.return_value = iter([
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ])

            resp = process_expiration_reminders(self._make_event(), self.mock_context)

            self.assertEqual('complete', resp['status'])
            self.assertEqual(0, resp['metrics']['sent'])
            self.assertEqual(1, resp['metrics']['failed'])
            mock_tracker_instance.record_failure.assert_called_once()
            self.assertIn('Email service down', mock_tracker_instance.record_failure.call_args.kwargs['error_message'])

    def test_handler_records_failure_when_privilege_has_unknown_jurisdiction(self):
        """Unknown jurisdiction code raises when building template; handler records failure."""
        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
        ):
            mock_config.compacts = ['aslp']
            mock_email_client = MagicMock()
            mock_config.email_service_client = mock_email_client

            mock_tracker_instance = MagicMock()
            mock_tracker_instance.was_already_sent.return_value = False
            mock_tracker_class.return_value = mock_tracker_instance

            # Privilege with jurisdiction not in CompactConfigUtility.JURISDICTION_NAME_MAPPING
            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            doc = self._make_provider_doc()
            doc['privileges'][0]['jurisdiction'] = 'xx'
            mock_iter.return_value = iter([
                PaginatedProviderResult(provider_doc=doc, search_after=['cursor1']),
            ])

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
                    'daysBefore': 15,
                    'compact': 'aslp',
                    'scheduledTime': '2026-01-17T10:00:00Z',
                },
                self.mock_context,
            )

        self.assertIn('15', str(ctx.exception))
        self.assertIn('Must be 30, 7, or 0', str(ctx.exception))

    def test_handler_requires_days_before_field(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders(
                {'targetDate': '2026-02-16', 'compact': 'aslp', 'scheduledTime': '2026-01-17T10:00:00Z'},
                self.mock_context,
            )

        self.assertIn('daysBefore', str(ctx.exception))

    def test_handler_requires_compact_field(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders(
                {'targetDate': '2026-02-16', 'daysBefore': 30, 'scheduledTime': '2026-01-17T10:00:00Z'},
                self.mock_context,
            )

        self.assertIn('compact', str(ctx.exception))

    def test_handler_validates_compact_value(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with (
            patch('handlers.expiration_reminders.config') as mock_config,
        ):
            mock_config.compacts = ['aslp', 'coun']

            with self.assertRaises(CCInvalidRequestException) as ctx:
                process_expiration_reminders(
                    self._make_event(compact='invalid'),
                    self.mock_context,
                )

            self.assertIn('invalid', str(ctx.exception))
            self.assertIn('Must be one of', str(ctx.exception))

    def test_handler_calculates_target_date_from_days_before_when_not_provided(self):
        """Test that handler calculates targetDate from daysBefore when targetDate is not provided."""

        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
        ):
            mock_config.compacts = ['aslp']
            mock_email_client = MagicMock()
            mock_config.email_service_client = mock_email_client

            mock_tracker_instance = MagicMock()
            mock_tracker_instance.was_already_sent.return_value = False
            mock_tracker_class.return_value = mock_tracker_instance

            # Create provider doc with expiration date = today + 30 days
            today = datetime.now(UTC).date()
            target_date = today + timedelta(days=30)
            provider_doc = self._make_provider_doc()
            provider_doc['privileges'][0]['dateOfExpiration'] = target_date.isoformat()

            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            mock_iter.return_value = iter([
                PaginatedProviderResult(provider_doc=provider_doc, search_after=['cursor1']),
            ])

            # Event with only daysBefore and compact (no targetDate)
            event = {'daysBefore': 30, 'compact': 'aslp'}
            resp = process_expiration_reminders(event, self.mock_context)

            # Verify it calculated the correct target date
            expected_target_date = (today + timedelta(days=30)).isoformat()
            self.assertEqual(expected_target_date, resp['targetDate'])
            self.assertEqual(30, resp['daysBefore'])

            # Verify the generator was called with the calculated date and no initial_search_after
            mock_iter.assert_called_once()
            call_kwargs = mock_iter.call_args.kwargs
            self.assertEqual(target_date, call_kwargs['expiration_date'])
            self.assertIsNone(call_kwargs.get('initial_search_after'))

    def test_handler_continuation_parses_accumulated_metrics_and_search_after(self):
        """Continuation event restores metrics and passes initial_search_after to generator."""
        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
        ):
            mock_config.compacts = ['aslp']
            mock_config.email_service_client = MagicMock()

            mock_tracker_instance = MagicMock()
            mock_tracker_instance.was_already_sent.return_value = False
            mock_tracker_class.return_value = mock_tracker_instance

            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            mock_iter.return_value = iter([
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor2']),
            ])

            event = {
                'targetDate': '2026-02-16',
                'daysBefore': 30,
                'compact': 'aslp',
                '_continuation': {
                    'searchAfter': ['cursor1'],
                    'depth': 1,
                    'accumulatedMetrics': {
                        'sent': 100,
                        'skipped': 2,
                        'failed': 1,
                        'alreadySent': 5,
                        'noEmail': 0,
                        'matchedPrivileges': 108,
                        'providersWithMatches': 108,
                    },
                },
            }
            resp = process_expiration_reminders(event, self.mock_context)

            self.assertEqual('complete', resp['status'])
            self.assertEqual(101, resp['metrics']['sent'])
            self.assertEqual(2, resp['metrics']['skipped'])
            self.assertEqual(5, resp['metrics']['alreadySent'])
            self.assertEqual(2, resp['totalInvocations'])
            mock_iter.assert_called_once()
            call_kwargs = mock_iter.call_args.kwargs
            self.assertEqual(['cursor1'], call_kwargs['initial_search_after'])

    def test_handler_invokes_itself_with_pagination_values_when_reaching_limit(self):
        """When remaining time is below threshold, handler invokes self and returns continued."""
        with (
            patch('handlers.expiration_reminders.iterate_privileges_by_expiration_date') as mock_iter,
            patch('handlers.expiration_reminders.config') as mock_config,
            patch('handlers.expiration_reminders.ExpirationReminderTracker') as mock_tracker_class,
        ):
            mock_config.compacts = ['aslp']
            mock_config.email_service_client = MagicMock()
            mock_lambda_client = MagicMock()
            mock_config.lambda_client = mock_lambda_client

            mock_tracker_instance = MagicMock()
            mock_tracker_instance.was_already_sent.return_value = False
            mock_tracker_class.return_value = mock_tracker_instance

            from handlers.expiration_reminders import PaginatedProviderResult, process_expiration_reminders

            mock_iter.return_value = iter([
                PaginatedProviderResult(provider_doc=self._make_provider_doc(), search_after=['cursor1']),
            ])

            mock_context = MagicMock()
            mock_context.get_remaining_time_in_millis.return_value = 60_000  # 1 minute left

            resp = process_expiration_reminders(self._make_event(), mock_context)

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
