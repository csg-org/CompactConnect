from datetime import date, datetime
from unittest.mock import patch

from tests import TstLambdas


class TestReportWindow(TstLambdas):
    def test_weekly_report_window_calculated_ranges(self):
        from report_window import ReportCycle, ReportWindow

        with (
            self.subTest('Monday morning'),
            patch(
                'cc_common.config._Config.current_standard_datetime',
                # A Monday morning, UTC
                datetime.fromisoformat('2025-10-13T06:00:00+00:00'),
            ),
        ):
            window = ReportWindow(ReportCycle.WEEKLY)
            self.assertEqual(
                window.query_window,
                (
                    # Saturdays at midnight
                    datetime.fromisoformat('2025-10-04T00:00:00+00:00'),
                    datetime.fromisoformat('2025-10-11T00:00:00+00:00'),
                ),
            )
            self.assertEqual(
                window.display_window,
                (
                    # Saturday - Friday
                    date.fromisoformat('2025-10-04'),
                    date.fromisoformat('2025-10-10'),
                ),
            )

        with (
            self.subTest('Saturday, midnight'),
            patch(
                'cc_common.config._Config.current_standard_datetime',
                # A Monday, midnight, UTC
                datetime.fromisoformat('2025-10-11T00:00:00+00:00'),
            ),
        ):
            window = ReportWindow(ReportCycle.WEEKLY)
            self.assertEqual(
                window.query_window,
                (
                    # Saturdays at midnight
                    datetime.fromisoformat('2025-10-04T00:00:00+00:00'),
                    datetime.fromisoformat('2025-10-11T00:00:00+00:00'),
                ),
            )
            self.assertEqual(
                window.display_window,
                (
                    # Saturday - Friday
                    date.fromisoformat('2025-10-04'),
                    date.fromisoformat('2025-10-10'),
                ),
            )

        with (
            self.subTest('Friday, very late'),
            patch(
                'cc_common.config._Config.current_standard_datetime',
                # Just before midnight, Friday night, UTC
                datetime.fromisoformat('2025-10-10T23:59:59.999999+00:00'),
            ),
        ):
            window = ReportWindow(ReportCycle.WEEKLY)
            self.assertEqual(
                window.query_window,
                (
                    # Saturdays at midnight, a week prior
                    datetime.fromisoformat('2025-09-27T00:00:00+00:00'),
                    datetime.fromisoformat('2025-10-04T00:00:00+00:00'),
                ),
            )
            self.assertEqual(
                window.display_window,
                (
                    # Saturday - Friday
                    date.fromisoformat('2025-09-27'),
                    date.fromisoformat('2025-10-03'),
                ),
            )

    def test_monthly_report_window(self):
        from report_window import ReportCycle, ReportWindow

        with (
            self.subTest('Mid month'),
            patch(
                'cc_common.config._Config.current_standard_datetime',
                datetime.fromisoformat('2025-10-13T06:00:00+00:00'),
            ),
        ):
            window = ReportWindow(ReportCycle.MONTHLY)
            self.assertEqual(
                window.query_window,
                (
                    # Beginning of each month
                    datetime.fromisoformat('2025-09-01T00:00:00+00:00'),
                    datetime.fromisoformat('2025-10-01T00:00:00+00:00'),
                ),
            )
            self.assertEqual(
                window.display_window,
                (
                    # 1st - 30th
                    date.fromisoformat('2025-09-01'),
                    date.fromisoformat('2025-09-30'),
                ),
            )

        with (
            self.subTest('Midnight on the 1st'),
            patch(
                'cc_common.config._Config.current_standard_datetime',
                datetime.fromisoformat('2025-10-01T00:00:00+00:00'),
            ),
        ):
            window = ReportWindow(ReportCycle.MONTHLY)
            self.assertEqual(
                window.query_window,
                (
                    # First of each month
                    datetime.fromisoformat('2025-09-01T00:00:00+00:00'),
                    datetime.fromisoformat('2025-10-01T00:00:00+00:00'),
                ),
            )
            self.assertEqual(
                window.display_window,
                (
                    # 1st - 30th
                    date.fromisoformat('2025-09-01'),
                    date.fromisoformat('2025-09-30'),
                ),
            )

        with (
            self.subTest('30th, very late'),
            patch(
                'cc_common.config._Config.current_standard_datetime',
                # A Monday afternoon, UTC
                datetime.fromisoformat('2025-09-30T23:59:59.999999+00:00'),
            ),
        ):
            window = ReportWindow(ReportCycle.MONTHLY)
            self.assertEqual(
                window.query_window,
                (
                    # First of each month, a month ago
                    datetime.fromisoformat('2025-08-01T00:00:00+00:00'),
                    datetime.fromisoformat('2025-09-01T00:00:00+00:00'),
                ),
            )
            self.assertEqual(
                window.display_window,
                (
                    # 1st - 31st
                    date.fromisoformat('2025-08-01'),
                    date.fromisoformat('2025-08-31'),
                ),
            )

    def test_display_properties(self):
        from report_window import ReportCycle, ReportWindow

        report_window = ReportWindow(
            ReportCycle.WEEKLY,
            _display_start_date=date.fromisoformat('2025-10-04'),
            _display_end_date=date.fromisoformat('2025-10-10'),
        )

        self.assertEqual(
            report_window.display_window,
            (
                date.fromisoformat('2025-10-04'),
                date.fromisoformat('2025-10-10'),
            ),
        )

        self.assertEqual(report_window.display_start, date.fromisoformat('2025-10-04'))
        self.assertEqual(report_window.display_start_text, '2025-10-04')

        self.assertEqual(report_window.display_end, date.fromisoformat('2025-10-10'))
        self.assertEqual(report_window.display_end_text, '2025-10-10')

        self.assertEqual(report_window.display_text, '2025-10-04--2025-10-10')

    def test_query_properties(self):
        from report_window import ReportCycle, ReportWindow

        report_window = ReportWindow(
            ReportCycle.WEEKLY,
            _display_start_date=date.fromisoformat('2025-10-04'),
            _display_end_date=date.fromisoformat('2025-10-10'),
        )

        expected_start = datetime.fromisoformat('2025-10-04T00:00:00+00:00')
        expected_end = datetime.fromisoformat('2025-10-11T00:00:00+00:00')

        self.assertEqual(
            report_window.query_window,
            (
                expected_start,
                expected_end,
            ),
        )

        self.assertEqual(report_window.start_epoch, int(expected_start.timestamp()))
        self.assertEqual(report_window.end_epoch, int(expected_end.timestamp()))
