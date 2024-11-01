from decimal import Decimal

from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestHandleDataEvents(TstFunction):
    def test_handle_data_event(self):
        from handlers import handle_data_events

        with open('tests/resources/message.json') as f:
            message = f.read()

        event = {'Records': [{'messageId': '123', 'body': message}]}

        resp = handle_data_events(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)
        key = {
            'pk': 'COMPACT#aslp#TYPE#license.validation-error',
            'sk': 'TIME#1730255454#EVENT#44ec3255-8d59-a6ae-0783-5563a9318a58',
        }
        resp = self._data_event_table.scan()
        saved_event = self._data_event_table.get_item(Key=key)['Item']
        self.assertEqual(
            {
                **key,
                'eventType': 'license.validation-error',
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'record_number': Decimal('4'),
                'errors': {'licenseType': ['Missing data for required field.']},
                'ingestTime': '2024-10-30T02:30:54.586569+00:00',
                'valid_data': {},
            },
            saved_event,
        )
