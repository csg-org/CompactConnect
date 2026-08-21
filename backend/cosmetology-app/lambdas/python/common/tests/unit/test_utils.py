import json
from unittest.mock import patch

from tests import TstLambdas


class TestUtils(TstLambdas):
    @patch('cc_common.utils.config.license_preprocessing_queue')
    def test_send_licenses_to_preprocessing_queue_handles_failures(self, mock_preprocessing_queue):
        from cc_common.utils import send_licenses_to_preprocessing_queue

        def mock_send_messages(Entries):  # noqa N803 AWS defines the kwargs
            failed_entries = [
                {'Id': entry['Id'], 'SenderFault': False, 'Code': '1234', 'Message': 'Something went wrong'}
                for entry in Entries
            ]
            return {'Successful': [], 'Failed': failed_entries}

        # we have to mock the SQS queue to force a failure scenario
        mock_preprocessing_queue.send_messages.side_effect = mock_send_messages

        with open('tests/resources/api/license-post.json') as f:
            license_record = json.load(f)
            license_record['compact'] = 'cosm'
            license_record['jurisdiction'] = 'oh'

        # generate 5 records and ensure the system processes all the failures
        licenses_data = []
        for i in range(5):
            with open('tests/resources/api/license-post.json') as f:
                license_record = json.load(f)
                license_record['compact'] = 'cosm'
                license_record['jurisdiction'] = 'oh'
                license_record['licenseNumber'] = f'licenseNumber-{i}'
                licenses_data.append(license_record)

        failed_license_numbers = send_licenses_to_preprocessing_queue(
            licenses_data=licenses_data, event_time='2024-12-04T08:08:08+00:00'
        )

        self.assertEqual([f'licenseNumber-{i}' for i in range(5)], failed_license_numbers)


class TestLoggerInjectKwargs(TstLambdas):
    """
    Guards the logging context that decorated methods share with their callers.

    Powertools' append_context_keys removes every key it set when it exits, including keys the caller had
    already set under the same name. Since nearly every decorated method injects 'compact' and 'provider_id'
    - the same names handlers wrap their work in - returning from one used to silently delete the caller's
    context, leaving every later log line in that handler unsearchable by those keys.
    """

    @staticmethod
    def _context_keys(logger, *names):
        current_keys = logger.get_current_keys()
        return {name: current_keys[name] for name in names if name in current_keys}

    def test_decorated_call_preserves_context_keys_the_caller_already_set(self):
        from aws_lambda_powertools import Logger
        from cc_common.utils import logger_inject_kwargs

        logger = Logger(service='test_logger_inject_kwargs')

        @logger_inject_kwargs(logger, 'compact', 'provider_id')
        def decorated(*, compact, provider_id):  # noqa: ARG001 read from kwargs by the decorator
            return 'done'

        with logger.append_context_keys(compact='aslp', provider_id='caller-provider-id'):
            decorated(compact='aslp', provider_id='callee-provider-id')

            self.assertEqual(
                {'compact': 'aslp', 'provider_id': 'caller-provider-id'},
                self._context_keys(logger, 'compact', 'provider_id'),
                "The caller's context keys must survive a call into a decorated method",
            )

    def test_decorated_call_restores_the_caller_value_not_the_injected_one(self):
        """The caller's value has to come back, not whatever the decorated method was called with."""
        from aws_lambda_powertools import Logger
        from cc_common.utils import logger_inject_kwargs

        logger = Logger(service='test_logger_inject_kwargs_value')

        @logger_inject_kwargs(logger, 'provider_id')
        def decorated(*, provider_id):
            return provider_id

        with logger.append_context_keys(provider_id='previous-provider-id'):
            decorated(provider_id='new-provider-id')

            self.assertEqual(
                {'provider_id': 'previous-provider-id'},
                self._context_keys(logger, 'provider_id'),
            )

    def test_decorated_call_preserves_context_keys_when_it_raises(self):
        """A method that blows up must not take the caller's logging context down with it."""
        from aws_lambda_powertools import Logger
        from cc_common.utils import logger_inject_kwargs

        logger = Logger(service='test_logger_inject_kwargs_raises')

        @logger_inject_kwargs(logger, 'compact')
        def decorated(*, compact):  # noqa: ARG001 read from kwargs by the decorator
            raise ValueError('boom')

        with logger.append_context_keys(compact='aslp'):
            with self.assertRaises(ValueError):
                decorated(compact='aslp')

            self.assertEqual({'compact': 'aslp'}, self._context_keys(logger, 'compact'))

    def test_injected_keys_are_still_removed_when_the_caller_never_set_them(self):
        """Keys the caller did not own must not leak out of the decorated call."""
        from aws_lambda_powertools import Logger
        from cc_common.utils import logger_inject_kwargs

        logger = Logger(service='test_logger_inject_kwargs_leak')

        @logger_inject_kwargs(logger, 'compact')
        def decorated(*, compact):
            return compact

        decorated(compact='aslp')

        self.assertEqual({}, self._context_keys(logger, 'compact'))

    def test_injected_keys_are_visible_inside_the_decorated_method(self):
        """The decorator's original purpose still has to work."""
        from aws_lambda_powertools import Logger
        from cc_common.utils import logger_inject_kwargs

        logger = Logger(service='test_logger_inject_kwargs_inside')
        observed = {}

        @logger_inject_kwargs(logger, 'compact', 'provider_id')
        def decorated(*, compact, provider_id):  # noqa: ARG001 read from kwargs by the decorator
            observed.update(self._context_keys(logger, 'compact', 'provider_id'))

        with logger.append_context_keys(compact='aslp', provider_id='caller-provider-id'):
            decorated(compact='aslp', provider_id='callee-provider-id')

        self.assertEqual({'compact': 'aslp', 'provider_id': 'callee-provider-id'}, observed)
