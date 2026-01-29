import json
from decimal import Decimal

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestHandleDataEvents(TstFunction):
    def test_handle_data_event(self):
        from handlers.data_events import handle_data_events

        with open('tests/resources/message.json') as f:
            message = f.read()

        event = {'Records': [{'messageId': '123', 'body': message}]}

        resp = handle_data_events(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)
        key = {
            'pk': 'COMPACT#cosm#JURISDICTION#oh',
            'sk': 'TYPE#license.validation-error#TIME#1730255454#EVENT#44ec3255-8d59-a6ae-0783-5563a9318a58',
        }
        saved_event = self._data_event_table.get_item(Key=key)['Item']
        # Drop dynamic value
        del saved_event['eventExpiry']

        self.assertEqual(
            {
                **key,
                'eventTime': '2024-10-30T02:30:54.586569+00:00',
                'eventType': 'license.validation-error',
                'compact': 'cosm',
                'jurisdiction': 'oh',
                'recordNumber': Decimal('4'),
                'errors': {'licenseType': ['Missing data for required field.']},
                'validData': {},
            },
            saved_event,
        )

    def test_handle_data_event_sanitizes_license_ingest_events(self):
        from handlers.data_events import handle_data_events

        # this test file represents a license.ingest event
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = f.read()

        event = {'Records': [{'messageId': '123', 'body': message}]}

        resp = handle_data_events(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)
        key = {
            'pk': 'COMPACT#cosm#JURISDICTION#oh',
            'sk': 'TYPE#license.ingest#TIME#1720727865#EVENT#44ec3255-8d59-a6ae-0783-5563a9318a58',
        }
        saved_event = self._data_event_table.get_item(Key=key)['Item']
        # Drop dynamic value
        del saved_event['eventExpiry']

        self.assertEqual(
            {
                **key,
                'eventTime': '2024-07-11T19:57:45+00:00',
                'eventType': 'license.ingest',
                'compact': 'cosm',
                'licenseType': 'cosmetologist',
                'jurisdiction': 'oh',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'dateOfExpiration': '2025-04-04',
                'dateOfIssuance': '2010-06-06',
                'dateOfRenewal': '2020-04-04',
            },
            saved_event,
        )

    def test_handle_data_event_with_empty_field(self):
        from handlers.data_events import handle_data_events

        with open('tests/resources/message.json') as f:
            message = json.load(f)
        # Set an error field with an empty string
        message['detail']['errors'] = {'': ['Unknown field.']}

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = handle_data_events(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)
        key = {
            'pk': 'COMPACT#cosm#JURISDICTION#oh',
            'sk': 'TYPE#license.validation-error#TIME#1730255454#EVENT#44ec3255-8d59-a6ae-0783-5563a9318a58',
        }
        saved_event = self._data_event_table.get_item(Key=key)['Item']
        # Drop dynamic value
        del saved_event['eventExpiry']

        self.assertEqual(
            {
                **key,
                'eventTime': '2024-10-30T02:30:54.586569+00:00',
                'eventType': 'license.validation-error',
                'compact': 'cosm',
                'jurisdiction': 'oh',
                'recordNumber': Decimal('4'),
                'errors': {'<EMPTY>': ['Unknown field.']},
                'validData': {},
            },
            saved_event,
        )
