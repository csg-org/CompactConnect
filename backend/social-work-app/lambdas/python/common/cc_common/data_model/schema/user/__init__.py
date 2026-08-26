# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from datetime import datetime
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass, CCPermissionsAction
from cc_common.data_model.schema.user.record import UserRecordSchema


class StaffUserData(CCDataClass):
    """
    Class representing a Staff User with getters for all properties.
    """

    # Define record schema at the class level
    _record_schema = UserRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

    @property
    def userId(self) -> UUID:
        return self._data['userId']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def status(self) -> str:
        return self._data['status']

    @property
    def lastLoginAt(self) -> datetime | None:
        """Absent for users who have not signed in since login tracking was introduced."""
        return self._data.get('lastLoginAt')

    # The attributes field is flattened here, since its nesting is a storage detail
    @property
    def email(self) -> str:
        return self._data['attributes']['email']

    @property
    def givenName(self) -> str:
        return self._data['attributes']['givenName']

    @property
    def familyName(self) -> str:
        return self._data['attributes']['familyName']

    @property
    def compactActions(self) -> set[str]:
        """Compact-level actions. Empty if the user only has jurisdiction permissions."""
        return self._data['permissions'].get('actions', set())

    @property
    def jurisdictions(self) -> set[str]:
        """Jurisdiction codes where this user holds any permission."""
        return set(self._data['permissions']['jurisdictions'].keys())

    def jurisdictionActions(self, jurisdiction: str) -> set[str]:
        """The user's actions in one jurisdiction. Empty if they hold no permissions there."""
        return self._data['permissions']['jurisdictions'].get(jurisdiction, set())

    @property
    def isCompactAdmin(self) -> bool:
        return CCPermissionsAction.ADMIN in self.compactActions

    def isJurisdictionAdmin(self, jurisdiction: str) -> bool:
        return CCPermissionsAction.ADMIN in self.jurisdictionActions(jurisdiction)
