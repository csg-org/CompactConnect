# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition
from datetime import datetime
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.home_jurisdiction.record import (
    ProviderHomeJurisdictionSelectionRecordSchema,
)


# TODO - deprecated, this will be removed once the frontend is updated to # noqa: FIX002
#  read the 'currentHomeJurisdiction' field on the provider record as part of https://github.com/csg-org/CompactConnect/issues/763
class HomeJurisdictionSelectionData(CCDataClass):
    """
    Class representing a Home Jurisdiction Selection with properties and setters.
    """

    # Define record schema at the class level
    _record_schema = ProviderHomeJurisdictionSelectionRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

    @property
    def providerId(self) -> UUID:
        return self._data.get('providerId')

    @property
    def compact(self) -> str:
        return self._data.get('compact')

    @property
    def jurisdiction(self) -> str:
        return self._data.get('jurisdiction')

    @property
    def dateOfSelection(self) -> datetime:
        return self._data.get('dateOfSelection')
