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
            'pk': 'COMPACT#aslp#JURISDICTION#oh',
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
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'recordNumber': Decimal('4'),
                'errors': {'licenseType': ['Missing data for required field.']},
                'validData': {},
            },
            saved_event,
        )
