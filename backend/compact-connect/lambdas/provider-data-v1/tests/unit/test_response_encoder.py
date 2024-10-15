import json
from datetime import UTC, date, datetime
from decimal import Decimal

from tests import TstLambdas


class TestResponseEncoder(TstLambdas):
    def test_standard_fields(self):
        from handlers.utils import ResponseEncoder

        start_data = {
            'foo': 42,
            'bar': 'baz'
        }

        round_trip = json.loads(json.dumps(start_data, cls=ResponseEncoder))
        self.assertEqual(start_data, round_trip)

    def test_decimal(self):
        from handlers.utils import ResponseEncoder

        start_data = {
            'decimal': Decimal('4.1'),
            'integer': Decimal(4)
        }

        dumped = json.dumps(start_data, cls=ResponseEncoder)
        self.assertIn('"integer": 4', dumped)
        self.assertIn('"decimal": 4.1', dumped)

    def test_date(self):
        from handlers.utils import ResponseEncoder

        start_data = {
            'date': date(2024, 7, 21),
            'datetime': datetime(
                2024, 7, 21,
                17, 20, 12, 54321,
                tzinfo=UTC
            )
        }
        dumped = json.dumps(start_data, cls=ResponseEncoder)

        self.assertIn('"date": "2024-07-21"', dumped)
        self.assertIn('"datetime": "2024-07-21T17:20:12.054321+00:00"', dumped)
