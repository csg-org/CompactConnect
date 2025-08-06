# ruff: noqa: E501 line-too-long
import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestCopyRecords(TstFunction):
    """Test suite for get compact jurisdiction endpoints."""

    def _generate_test_event(self) -> dict:
        return {
            'sourceTableArn': self.mock_source_table_arn,
            'destinationTableArn': self.mock_destination_table_arn
        }

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_http_method(self):
        """Test getting an empty list if no jurisdictions configured."""
        from handlers.copy_records import copy_records

        event = self._generate_test_event()

        response = copy_records(event, self.mock_context)

        self.assertEqual(
            {
                'copyStatus': 'COMPLETE'
            },
            response,
        )

