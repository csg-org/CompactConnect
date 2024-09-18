# pylint: disable=invalid-name

from marshmallow import pre_dump, Schema, post_load
from marshmallow.fields import UUID, Nested, String, Dict
from marshmallow.validate import Length, OneOf

from config import config
from data_model.schema.base_record import BaseRecordSchema, Set


class CompactPermissionsSchema(Schema):
    actions = Set(String, required=False, allow_none=False)
    jurisdictions = Dict(
        keys=String(validate=OneOf(config.jurisdictions)),
        values=Set(String, required=False, allow_none=False),
        dump_default={},
        required=True,
        allow_none=False
    )


class UserAttributesSchema(Schema):
    email = String(required=True, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))


class UserRecordSchema(BaseRecordSchema):
    _record_type = 'user'

    # Provided fields
    userId = UUID(required=True, allow_none=False)
    attributes = Nested(UserAttributesSchema(), required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    permissions = Nested(
        CompactPermissionsSchema(),
        required=True,
        allow_none=False
    )

    # Generated fields
    famGiv = String(required=True, allow_none=False)

    @pre_dump
    def generate_pk(self, in_data, **kwargs):  # pylint: disable=unused-argument
        in_data['pk'] = f'USER#{in_data['userId']}'
        return in_data

    @pre_dump
    def generate_sk(self, in_data, **kwargs):  # pylint: disable=unused-argument
        in_data['sk'] = f'COMPACT#{in_data['compact']}'
        return in_data

    @pre_dump
    def generate_fam_giv(self, in_data, **kwargs):  # pylint: disable=unused-argument
        in_data['famGiv'] = '#'.join([
            in_data['attributes']['familyName'],
            in_data['attributes']['givenName']
        ])
        return in_data

    @post_load
    def drop_fam_giv(self, in_data, **kwargs):  # pylint: disable=unused-argument
        del in_data['famGiv']
        return in_data
