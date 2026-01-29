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

            self.assertEqual([r['providerId'] for r in results], ['p1', 'p2', 'p3'])

            # Verify pagination: second call includes search_after from last hit in page 1
            first_call_kwargs = mock_client.search.call_args_list[0].kwargs
            second_call_kwargs = mock_client.search.call_args_list[1].kwargs

            self.assertEqual(first_call_kwargs['index_name'], 'compact_aslp_providers')
            self.assertNotIn('search_after', first_call_kwargs['body'])

            self.assertEqual(second_call_kwargs['index_name'], 'compact_aslp_providers')
            self.assertEqual(second_call_kwargs['body']['search_after'], ['p2'])

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

            provider_doc = next(
                iterate_privileges_by_expiration_date(
                    compact='aslp',
                    expiration_date=date(2026, 2, 16),
                    page_size=100,
                )
            )

            self.assertEqual(provider_doc['providerId'], 'p1')
            self.assertEqual(provider_doc['privileges'], full_privileges)


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

    def _make_event(self, days_before: int = 30) -> dict:
        """Helper to create a valid event for testing."""
        return {
            'targetDate': '2026-02-16',
            'daysBefore': days_before,
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

            mock_iter.return_value = iter([self._make_provider_doc()])

            from handlers.expiration_reminders import process_expiration_reminders

            resp = process_expiration_reminders(self._make_event(days_before=30), self.mock_context)

            self.assertEqual(resp['metrics']['sent'], 1)
            self.assertEqual(resp['metrics']['failed'], 0)
            self.assertEqual(resp['daysBefore'], 30)
            mock_email_client.send_privilege_expiration_reminder_email.assert_called_once()
            call_kwargs = mock_email_client.send_privilege_expiration_reminder_email.call_args.kwargs
            tv = call_kwargs['template_variables']
            self.assertEqual(tv.provider_first_name, 'John')
            self.assertEqual(tv.expiration_date.isoformat(), '2026-02-16')
            self.assertEqual(len(tv.privileges), 1)
            priv = tv.privileges[0]
            self.assertEqual(priv['jurisdiction'], 'Ohio', 'jurisdiction must be full state name')
            self.assertEqual(priv['licenseType'], 'aud')
            self.assertEqual(priv['privilegeId'], 'a')
            self.assertEqual(priv['dateOfExpiration'], '2026-02-16', 'dateOfExpiration must be ISO 8601')
            mock_tracker_instance.record_success.assert_called_once()

            # Verify tracker was created with correct event_type
            from expiration_reminder_tracker import ExpirationEventType

            mock_tracker_class.assert_called_once()
            tracker_call = mock_tracker_class.call_args.kwargs
            self.assertEqual(tracker_call['event_type'], ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY)

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

            mock_iter.return_value = iter([self._make_provider_doc()])

            from handlers.expiration_reminders import process_expiration_reminders

            resp = process_expiration_reminders(self._make_event(days_before=7), self.mock_context)

            self.assertEqual(resp['metrics']['sent'], 0)
            self.assertEqual(resp['metrics']['alreadySent'], 1)
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
            mock_iter.return_value = iter([self._make_provider_doc(email=None)])

            from handlers.expiration_reminders import process_expiration_reminders

            resp = process_expiration_reminders(self._make_event(days_before=0), self.mock_context)

            self.assertEqual(resp['metrics']['sent'], 0)
            self.assertEqual(resp['metrics']['noEmail'], 1)
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

            mock_iter.return_value = iter([self._make_provider_doc()])

            from handlers.expiration_reminders import process_expiration_reminders

            resp = process_expiration_reminders(self._make_event(), self.mock_context)

            self.assertEqual(resp['metrics']['sent'], 0)
            self.assertEqual(resp['metrics']['failed'], 1)
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
            doc = self._make_provider_doc()
            doc['privileges'][0]['jurisdiction'] = 'xx'
            mock_iter.return_value = iter([doc])

            from handlers.expiration_reminders import process_expiration_reminders

            resp = process_expiration_reminders(self._make_event(), self.mock_context)

            self.assertEqual(resp['metrics']['sent'], 0)
            self.assertEqual(resp['metrics']['failed'], 1)
            mock_tracker_instance.record_failure.assert_called_once()
            failure_msg = mock_tracker_instance.record_failure.call_args.kwargs['error_message']
            self.assertIn('Unknown jurisdiction', failure_msg)

    def test_handler_validates_days_before_value(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders(
                {'targetDate': '2026-02-16', 'daysBefore': 15, 'scheduledTime': '2026-01-17T10:00:00Z'},
                self.mock_context,
            )

        self.assertIn('15', str(ctx.exception))
        self.assertIn('Must be 30, 7, or 0', str(ctx.exception))

    def test_handler_requires_days_before_field(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.expiration_reminders import process_expiration_reminders

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_expiration_reminders(
                {'targetDate': '2026-02-16', 'scheduledTime': '2026-01-17T10:00:00Z'},
                self.mock_context,
            )

        self.assertIn('daysBefore', str(ctx.exception))

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

            mock_iter.return_value = iter([provider_doc])

            from handlers.expiration_reminders import process_expiration_reminders

            # Event with only daysBefore (no targetDate)
            event = {'daysBefore': 30}
            resp = process_expiration_reminders(event, self.mock_context)

            # Verify it calculated the correct target date
            expected_target_date = (today + timedelta(days=30)).isoformat()
            self.assertEqual(resp['targetDate'], expected_target_date)
            self.assertEqual(resp['daysBefore'], 30)

            # Verify the generator was called with the calculated date
            mock_iter.assert_called_once()
            call_kwargs = mock_iter.call_args.kwargs
            self.assertEqual(call_kwargs['expiration_date'], target_date)
