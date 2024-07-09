from urllib.parse import quote

from marshmallow import pre_dump, post_load
from marshmallow.fields import String, Date, UUID
from marshmallow.validate import Regexp, Length, OneOf

from data_model.schema.base_record import BaseRecordSchema, SocialSecurityNumber, ForgivingSchema


class PrivilegePostSchema(ForgivingSchema):
    """
    Schema for privilege data as it may be posted by a board
    """
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    given_name = String(required=True, allow_none=False, validate=Length(1, 100))
    middle_name = String(required=False, allow_none=False, validate=Length(1, 100))
    family_name = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    license_type = String(required=True, allow_none=False, validate=Length(1, 100))
    date_of_birth = Date(required=True, allow_none=False)
    date_of_issuance = Date(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
    home_jurisdiction = String(required=True, allow_none=False, validate=Length(1, 100))


@BaseRecordSchema.register_schema('license-privilege')
class PrivilegeRecordSchema(BaseRecordSchema, PrivilegePostSchema):
    """
    Schema for privilege records in the license data table
    """
    _record_type = 'license-privilege'

    # Provided fields
    provider_id = UUID(required=True, allow_none=False)

    # Generated fields
    fam_giv_mid = String(required=True, allow_none=False)
    birth_month_day = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    @post_load
    def drop_index_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        del in_data['fam_giv_mid']
        return in_data

    @pre_dump
    def populate_priv_gen_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        in_data['birth_month_day'] = in_data['date_of_birth'].strftime('%m-%d')
        in_data['fam_giv_mid'] = '/'.join((
            quote(in_data['family_name'], safe=''),
            quote(in_data['given_name'], safe=''),
            quote(in_data.get('middle_name', ''), safe='')
        ))
        return in_data
