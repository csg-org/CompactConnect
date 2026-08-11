from collections import defaultdict
from collections.abc import Generator
from datetime import UTC, date

from cc_common.config import config, logger
from cc_common.data_model.schema.common import StaffUserStatus
from cc_common.data_model.schema.user import StaffUserData


class CompactStaffUserDirectory:
    """All staff users in a compact, loaded in a single pass over the famGiv GSI.

    Built once and queried repeatedly. The admin buckets are classified eagerly at construction;
    cohort selection is a query against the loaded set, so this class is usable by anything that
    needs to reach a compact's staff users or their admins.
    """

    def __init__(self, *, compact: str):
        self.compact = compact
        self._users: list[StaffUserData] = []
        self._compact_admins: list[StaffUserData] = []
        self._jurisdiction_admins: dict[str, list[StaffUserData]] = defaultdict(list)
        self._load()

    def _load(self) -> None:
        for user in config.user_client.iterate_all_users_in_compact(compact=self.compact):
            self._users.append(user)
            if user.isCompactAdmin:
                self._compact_admins.append(user)
            for jurisdiction in user.jurisdictions:
                if user.isJurisdictionAdmin(jurisdiction):
                    self._jurisdiction_admins[jurisdiction].append(user)

        logger.info('Loaded staff user directory', compact=self.compact, user_count=len(self._users))

    def users_last_seen_on(self, last_login_date: date) -> list[StaffUserData]:
        """Active users whose last sign-in was on this date."""
        return [user for user in self._candidates() if self._last_login_date(user) == last_login_date]

    def users_last_seen_on_or_before(self, last_login_date: date) -> list[StaffUserData]:
        """Active users whose last sign-in was on or before this date."""
        return [user for user in self._candidates() if self._last_login_date(user) <= last_login_date]

    def jurisdiction_admins(self, jurisdiction: str) -> list[StaffUserData]:
        """Users holding the admin action in this jurisdiction."""
        return list(self._jurisdiction_admins[jurisdiction])

    @property
    def compact_admins(self) -> list[StaffUserData]:
        """Users holding the admin action at the compact level."""
        return list(self._compact_admins)

    def _candidates(self) -> Generator[StaffUserData, None, None]:
        """Users eligible for an inactivity cohort.

        Users who are already inactive have been deactivated, and users with no lastLoginAt have not
        signed in since login tracking was introduced, so neither has an inactivity clock running.
        """
        return (
            user for user in self._users if user.status == StaffUserStatus.ACTIVE.value and user.lastLoginAt is not None
        )

    @staticmethod
    def _last_login_date(user: StaffUserData) -> date:
        # Timestamps are written in UTC, but normalize so the comparison cannot drift on an offset
        return user.lastLoginAt.astimezone(UTC).date()
