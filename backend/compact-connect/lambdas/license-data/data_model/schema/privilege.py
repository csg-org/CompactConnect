# noqa: N801 invalid-name
from urllib.parse import quote

from marshmallow import post_load, pre_dump
from marshmallow.fields import UUID, Date, String
from marshmallow.validate import Length, OneOf, Regexp

from data_model.schema.base_record import BaseRecordSchema, ForgivingSchema, SocialSecurityNumber


class PrivilegePostSchema(ForgivingSchema):
    """Schema for privilege data as it may be posted by a board"""

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    licenseType = String(required=True, allow_none=False, validate=Length(1, 100))
    dateOfBirth = Date(required=True, allow_none=False)
    dateOfIssuance = Date(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
    homeJurisdiction = String(required=True, allow_none=False, validate=Length(1, 100))


@BaseRecordSchema.register_schema('license-privilege')
class PrivilegeRecordSchema(BaseRecordSchema, PrivilegePostSchema):
    """Schema for privilege records in the license data table"""

    _record_type = 'license-privilege'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)

    # Generated fields
    famGivMid = String(required=True, allow_none=False)
    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    @post_load
    def drop_index_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        del in_data['famGivMid']
        return in_data

    @pre_dump
    def populate_privilege_generated_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        in_data['birthMonthDay'] = in_data['dateOfBirth'].strftime('%m-%d')
        in_data['famGivMid'] = '/'.join(
            (
                quote(in_data['familyName'], safe=''),
                quote(in_data['givenName'], safe=''),
                quote(in_data.get('middleName', ''), safe=''),
            ),
        )
        return in_data
