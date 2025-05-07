# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from datetime import datetime
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.military_affiliation.record import MilitaryAffiliationRecordSchema


class MilitaryAffiliationData(CCDataClass):
    """
    Class representing a Military Affiliation with read-only properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.

    Note: This class requires valid data when created - it cannot be instantiated empty
    and populated later.
    """

    # Define the record schema at the class level
    _record_schema = MilitaryAffiliationRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

    @property
    def providerId(self) -> UUID:
        return self._data.get('providerId')

    @property
    def compact(self) -> str:
        return self._data.get('compact')

    @property
    def documentKeys(self) -> list[str]:
        return self._data.get('documentKeys', [])

    @property
    def fileNames(self) -> list[str]:
        return self._data.get('fileNames', [])

    @property
    def affiliationType(self) -> str:
        return self._data.get('affiliationType')

    @property
    def dateOfUpload(self) -> datetime:
        return self._data.get('dateOfUpload')

    @property
    def status(self) -> str:
        return self._data.get('status')
