from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

from cc_common.config import config


class ReportCycle(StrEnum):
    """Report cycles."""

    WEEKLY = 'weekly'
    MONTHLY = 'monthly'


class ReportWindow:
    """
    Manages reporting window start/end times for both query and display

    All windows start and end at midnight.
    """

    def __init__(self, report_cycle: ReportCycle, *, _display_start_date: date = None, _display_end_date: date = None):
        """
        :param report_cycle: The ReportCycle this report will run for (weekly or monthly)
        :param _display_start_date: Optional override of start date. Required with _display_end_date.
        :param _display_end_date: Optional override of end date. Required with _display_start_date.
        """
        super().__init__()
        self._report_cycle = report_cycle
        if _display_start_date and _display_end_date:
            self._start_time = datetime.combine(
                _display_start_date, time(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
            )
            self._end_time = datetime.combine(
                # Add 1 to convert display day to query datetime
                _display_end_date + timedelta(days=1),
                time(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC),
            )
        else:
            self._start_time, self._end_time = self._get_query_date_range()

    @property
    def query_window(self) -> tuple[datetime, datetime]:
        """Get the query window for DynamoDB queries.

        :return: (start_time, end_time)
        """
        return self._start_time, self._end_time

    @property
    def start_epoch(self) -> int:
        """
        The POSIX timestamp marking the beginning (inclusive) of the reporting window
        """
        return int(self._start_time.timestamp())

    @property
    def end_epoch(self) -> int:
        """
        The POSIX timestamp marking the end (exclusive) of the reporting window
        """
        return int(self._end_time.timestamp())

    @property
    def display_start(self) -> date:
        return self._start_time.date()

    @property
    def display_end(self) -> date:
        return (self._end_time - timedelta(seconds=1)).date()

    @property
    def display_window(self) -> tuple[date, date]:
        """Get the display window for report dates.

        :return: (start_date, end_date)
        """
        return self.display_start, self.display_end

    @property
    def display_start_text(self) -> str:
        return self.display_start.strftime('%Y-%m-%d')

    @property
    def display_end_text(self) -> str:
        return self.display_end.strftime('%Y-%m-%d')

    @property
    def display_text(self) -> str:
        return f'{self.display_start_text}--{self.display_end_text}'

    def _get_query_date_range(self) -> tuple[datetime, datetime]:
        """Get the query date range for DynamoDB queries.

        :return: (start_time, end_time)

        Our Sort Key format for transactions includes additional components after the timestamp
        (COMPACT#name#TIME#timestamp#BATCH#id#TX#id), So the DynamoDB BETWEEN condition is INCLUSIVE for the beginning
        range and EXCLUSIVE at the end range. This is because DynamoDB performs lexicographical comparison on the entire
        sort key string. When the sort key continues beyond the comparison value:

        - For the lower bound: Additional characters after the comparison point make the full key "greater than" the
          bound, satisfying the >= condition
        - For the upper bound: Additional characters after the comparison point make the full key "greater than" the
          bound, failing the <= condition

        We need to adjust our timestamps accordingly to ensure we capture all settled transactions exactly once.

        :return: Tuple of (start_time, end_time) for DynamoDB queries
        """
        if self._report_cycle == ReportCycle.WEEKLY:
            # Reports exclude anything before the most recent Midnight on Saturday
            end_time = self._get_most_recent_saturday_midnight(config.current_standard_datetime)
            # Go back 7 days to capture the full week
            start_time = end_time - timedelta(days=7)
            return start_time, end_time

        if self._report_cycle == ReportCycle.MONTHLY:
            # Reports run on the first day of the month
            # End time is midnight, since that will be excluded from the BETWEEN key condition
            end_time = config.current_standard_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Start time is midnight of the previous month
            start_time = (end_time - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return start_time, end_time

        raise ValueError(f'Invalid report cycle: {self._report_cycle}')

    @staticmethod
    def _get_most_recent_saturday_midnight(now: datetime) -> datetime:
        """
        Returns the most recent Saturday midnight (00:00:00)
        given a timezone-aware datetime object.
        """
        # weekday() returns 0=Monday, 1=Tuesday, ..., 5=Saturday, 6=Sunday
        days_since_saturday = (now.weekday() - 5) % 7

        # If it's currently Saturday, days_since_saturday is 0
        # If it's Sunday, days_since_saturday is 1, etc.
        saturday = now - timedelta(days=days_since_saturday)

        # Replace time with midnight, keeping the timezone info
        return saturday.replace(hour=0, minute=0, second=0, microsecond=0)
