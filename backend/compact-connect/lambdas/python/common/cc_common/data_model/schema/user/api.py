# ruff: noqa: N801, N815  invalid-name

from marshmallow import Schema, post_dump, pre_load
from marshmallow.fields import Boolean, Dict, Nested, Raw, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.common import StaffUserStatus


class UserAttributesAPISchema(Schema):
    email = String(required=True, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))


class CompactActionPermissionAPISchema(Schema):
    actions = Dict(
        keys=String(),  # Keys are actions
        values=Boolean(),
        required=False,
        allow_none=False,
    )


class CompactPermissionsAPISchema(CompactActionPermissionAPISchema):
    jurisdictions = Dict(
        keys=String(validate=OneOf(config.jurisdictions)),  # Keys are jurisdictions
        values=Nested(CompactActionPermissionAPISchema(), required=True, allow_none=False),
        dump_default={},
        required=True,
        allow_none=False,
    )


class UserAPISchema(Schema):
    """Schema to transform from the API-facing user data format (load) to the internal format (dump) that is ready for
    serialization to the DynamoDB table.

    Note: This schema is not intended for actual validation, only serialization/deserialization.
    """

    type = String(required=True, allow_none=False, validate=OneOf(['user']))
    userId = Raw(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([status.value for status in StaffUserStatus]))
    dateOfUpdate = Raw(required=True, allow_none=False)
    attributes = Nested(UserAttributesAPISchema(), required=True, allow_none=False)
    permissions = Dict(
        keys=String(validate=OneOf(config.compacts)),  # Key is one compact
        values=Nested(CompactPermissionsAPISchema(), required=True, allow_none=False),
        validate=Length(equal=1),
    )

    @pre_load
    def transform_to_api_permissions(self, data, **kwargs):  # noqa: ARG002 unused-kwargs
        """Transform compact permissions from database format into API format"""
        compact = data.pop('compact')
        compact_permissions = data['permissions']

        user_permissions = {compact: {}}

        compact_actions = compact_permissions.get('actions')
        if compact_actions is not None:
            # Set to dict of '{action}: True' items
            user_permissions[compact]['actions'] = {action: True for action in compact_permissions['actions']}
        jurisdictions = compact_permissions['jurisdictions']
        if jurisdictions is not None:
            # Transform jurisdiction permissions
            user_permissions[compact]['jurisdictions'] = {}
            for jurisdiction, jurisdiction_permissions in jurisdictions.items():
                # Set to dict of '{action}: True' items
                user_permissions[compact]['jurisdictions'][jurisdiction] = {
                    'actions': {action: True for action in jurisdiction_permissions},
                }
        data['permissions'] = user_permissions

        return data

    @post_dump  # Note _post_ dump, so after any type conversions happen, in this case
    def transform_to_dynamo_permissions(self, data, **kwargs):  # noqa: ARG002 unused-kwargs
        # { "permissions": { "aslp": { ... } } } -> { "compact": "aslp", "permissions": { ... } }
        for compact, compact_permissions in data['permissions'].items():
            data['permissions'] = compact_permissions
            data['compact'] = compact

        # { "actions": { "read": True } } -> { "actions": { "read" } }
        data['permissions']['actions'] = {
            key for key, value in data['permissions'].get('actions', {}).items() if value is True
        }

        # { "oh": { "actions": { "write": True } } } -> { "oh": { "write" } }
        for jurisdiction, jurisdiction_permissions in data['permissions']['jurisdictions'].items():
            data['permissions']['jurisdictions'][jurisdiction] = {
                key for key, value in jurisdiction_permissions.get('actions', {}).items() if value is True
            }

        return data
