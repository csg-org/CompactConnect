# ruff: noqa: N801, N815  invalid-name

from marshmallow import Schema, post_dump, post_load, pre_dump
from marshmallow.fields import UUID, Dict, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.common import StaffUserStatus
from cc_common.data_model.schema.fields import Set


class CompactPermissionsRecordSchema(Schema):
    actions = Set(String, required=False, allow_none=False)
    jurisdictions = Dict(
        keys=String(validate=OneOf(config.jurisdictions)),
        values=Set(String, required=False, allow_none=False),
        dump_default={},
        required=True,
        allow_none=False,
    )

    @post_dump
    def drop_empty_actions(self, data, **kwargs):  # noqa: ARG002 unused-kwargs
        """
        DynamoDB doesn't like empty sets, so we will make a point to drop an actions field entirely,
        if it is empty.
        """
        if not data.get('actions', {}):
            data.pop('actions', None)
        empty_jurisdictions = [jurisdiction for jurisdiction, actions in data['jurisdictions'].items() if not actions]
        for jurisdiction in empty_jurisdictions:
            del data['jurisdictions'][jurisdiction]
        return data


class UserAttributesRecordSchema(Schema):
    email = String(required=True, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))


@BaseRecordSchema.register_schema('user')
class UserRecordSchema(BaseRecordSchema):
    _record_type = 'user'

    # Provided fields
    userId = UUID(required=True, allow_none=False)
    attributes = Nested(UserAttributesRecordSchema(), required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    permissions = Nested(CompactPermissionsRecordSchema(), required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([status.value for status in StaffUserStatus]))

    # Generated fields
    famGiv = String(required=True, allow_none=False)

    @pre_dump
    def generate_pk(self, in_data, **kwargs):  # noqa: ARG002 unused-kwargs
        in_data['pk'] = f'USER#{in_data["userId"]}'
        return in_data

    @pre_dump
    def generate_sk(self, in_data, **kwargs):  # noqa: ARG002 unused-kwargs
        in_data['sk'] = f'COMPACT#{in_data["compact"]}'
        return in_data

    @pre_dump
    def generate_fam_giv(self, in_data, **kwargs):  # noqa: ARG002 unused-kwargs
        in_data['famGiv'] = '#'.join([in_data['attributes']['familyName'], in_data['attributes']['givenName']])
        return in_data

    @post_load
    def drop_fam_giv(self, in_data, **kwargs):  # noqa: ARG002 unused-kwargs
        del in_data['famGiv']
        return in_data
