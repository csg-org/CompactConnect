from collections.abc import Iterable
from enum import StrEnum
from secrets import token_hex

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from cc_common.config import _Config, logger
from cc_common.data_model.query_paginator import paginated_query
from cc_common.data_model.schema.common import StaffUserStatus
from cc_common.data_model.schema.user.record import (
    CompactPermissionsRecordSchema,
    UserAttributesRecordSchema,
    UserRecordSchema,
)
from cc_common.exceptions import CCInternalException, CCInvalidRequestException, CCNotFoundException
from cc_common.utils import get_sub_from_user_attributes


class UserStatus(StrEnum):
    # These top four should not happen for our user clients
    ARCHIVED = 'ARCHIVED'  # Not explained in Cognito documentation
    UNCONFIRMED = 'UNCONFIRMED'  # User has been created but not confirmed.
    EXTERNAL_PROVIDER = 'EXTERNAL_PROVIDER'  # User signed in with a third-party IdP.
    UNKNOWN = 'UNKNOWN'  # User status is unknown.

    # User has been confirmed
    CONFIRMED = 'CONFIRMED'
    # User is confirmed, but the user must request a code and reset their password before they can sign in.
    RESET_REQUIRED = 'RESET_REQUIRED'
    # The user is confirmed and the user can sign in using a temporary password, but on first sign-in, the user must
    # change their password to a new value before doing anything else.
    FORCE_CHANGE_PASSWORD = 'FORCE_CHANGE_PASSWORD'  # noqa: S105


class UserClient:
    """Client interface for license data dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.schema = UserRecordSchema()
        self.user_attributes_schema = UserAttributesRecordSchema()
        self.compact_permissions_schema = CompactPermissionsRecordSchema()

    @paginated_query
    def get_user(self, *, user_id: str, dynamo_pagination: dict, scan_forward: bool = True) -> list[dict]:
        resp = self.config.users_table.query(
            KeyConditionExpression=Key('pk').eq(f'USER#{user_id}'),
            ScanIndexForward=scan_forward,
            **dynamo_pagination,
        )
        if not resp.get('Items', []):
            raise CCNotFoundException('User not found')
        return resp

    def get_user_in_compact(self, *, compact: str, user_id: str):
        user = self.config.users_table.get_item(Key={'pk': f'USER#{user_id}', 'sk': f'COMPACT#{compact}'}).get('Item')

        if user is None:
            raise CCNotFoundException('User not found')
        return self.schema.load(user)

    @paginated_query
    def get_users_sorted_by_family_name(
        self,
        *,
        compact: str,
        dynamo_pagination: dict,
        jurisdictions: Iterable[str] = None,
        scan_forward: bool = True,
    ):
        """Get users with permissions in the provided compact, sorted by family name
        :param compact: The compact to filter by
        :param dynamo_pagination: DynamoDB query pagination fields
        :param jurisdictions: List of jurisdiction codes to filter by
        :param scan_forward: Whether to scan forward (True) or backward (False)
        """
        logger.info('Getting staff users by family name')

        filter_expression = None
        if jurisdictions:
            # Form an attribute_exists(<attr>) OR attribute_exists(<attr>) OR ... expression for each jurisdiction
            iter_jurisdictions = iter(jurisdictions)
            jurisdiction = next(iter_jurisdictions)
            filter_expression = Attr(f'permissions.jurisdictions.{jurisdiction}').exists()
            for jurisdiction in iter_jurisdictions:
                filter_expression = filter_expression | Attr(f'permissions.jurisdictions.{jurisdiction}').exists()
        return self.config.users_table.query(
            IndexName=self.config.fam_giv_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('sk').eq(f'COMPACT#{compact}'),
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
            **dynamo_pagination,
        )

    def update_user_permissions(
        self,
        *,
        compact: str,
        user_id: str,
        compact_action_additions: set = None,
        compact_action_removals: set = None,
        jurisdiction_action_additions: dict = None,
        jurisdiction_action_removals: dict = None,
    ):
        """Update the provided user's permissions
        :param str compact: The compact the user's permissions are within
        :param str user_id: The user to update
        :param set compact_action_additions: Set of compact actions to add to the user ('read' or 'admin')
        :param set compact_action_removals: Set of compact actions to remove from the user ('read' or 'admin')
        :param dict jurisdiction_action_additions: Dict of jurisdiction actions to add to the user.
        Keys are the jurisdiction codes, values are sets of actions to add ('write' or 'admin')
        :param dict jurisdiction_action_removals: Dict of jurisdiction actions to remove from the user.
        Keys are the jurisdiction codes, values are sets of actions to remove ('write' or 'admin')

        A given compact's permissions record looks something like:

        ```json
        {
          "permissions": {
            "actions": { "admin", "readPrivate" },
            "jurisdictions": {
              "oh": {
                "actions": { "admin", "write", "readPrivate" }
              }
            }
          }
        }
        ```
        """
        logger.info('Updating staff user permissions', user_id=user_id)

        # Creating a mutable collection so the handlers can add their collected changes
        update_expression_parts = {'add': [], 'delete': []}

        # DynamoDB does not support both ADD and DELETE on the same String Set in a single UpdateItem call, so we will
        # split additions and removals into two calls to prevent a conflict.
        resp = self._handle_user_permission_additions(
            user_id=user_id,
            compact=compact,
            update_expression_parts=update_expression_parts['add'],
            compact_action_additions=compact_action_additions,
            jurisdiction_action_additions=jurisdiction_action_additions,
        )
        resp = (
            self._handle_user_permission_removals(
                user_id=user_id,
                compact=compact,
                update_expression_parts=update_expression_parts['delete'],
                compact_action_removals=compact_action_removals,
                jurisdiction_action_removals=jurisdiction_action_removals,
            )
            or resp
        )

        if not (update_expression_parts['add'] or update_expression_parts['delete']):
            logger.warning('No changes provided for update_user_permissions')
            raise CCInvalidRequestException('No changes requested')

        return self.schema.load(resp['Attributes'])

    def _handle_user_permission_additions(
        self,
        *,
        user_id: str,
        compact: str,
        update_expression_parts: list,
        compact_action_additions: set,
        jurisdiction_action_additions: dict,
    ) -> dict | None:
        expression_attribute_names = {}
        expression_attribute_values = {}

        if compact_action_additions:
            update_expression_parts.append('#permissions.#actions :addActions')
            expression_attribute_names['#permissions'] = 'permissions'
            expression_attribute_names['#actions'] = 'actions'
            expression_attribute_values[':addActions'] = compact_action_additions

        if jurisdiction_action_additions:
            for jurisdiction, actions in jurisdiction_action_additions.items():
                expression_attribute_names['#permissions'] = 'permissions'
                expression_attribute_names['#jurisdictions'] = 'jurisdictions'
                expression_attribute_names[f'#{jurisdiction}'] = jurisdiction

                # If this is not their first action, we simply add to the set
                update_expression_parts.append(
                    f'#permissions.#jurisdictions.#{jurisdiction}  :{jurisdiction}AddActions',
                )
                expression_attribute_values[f':{jurisdiction}AddActions'] = actions

        if update_expression_parts:
            update_expression = 'ADD ' + ', '.join(update_expression_parts)

            try:
                return self.config.users_table.update_item(
                    Key={'pk': f'USER#{user_id}', 'sk': f'COMPACT#{compact}'},
                    UpdateExpression=update_expression,
                    ExpressionAttributeNames=expression_attribute_names,
                    ExpressionAttributeValues=expression_attribute_values,
                    ReturnValues='ALL_NEW',
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    # This error occurs when the document path is invalid, which happens when the user doesn't exist
                    raise CCNotFoundException('User not found') from e
                raise

        return None

    def _handle_user_permission_removals(
        self,
        *,
        user_id: str,
        compact: str,
        update_expression_parts: list,
        compact_action_removals: set,
        jurisdiction_action_removals: dict,
    ) -> dict | None:
        expression_attribute_names = {}
        expression_attribute_values = {}

        if compact_action_removals:
            update_expression_parts.append('#permissions.#actions :deleteActions')
            expression_attribute_names['#permissions'] = 'permissions'
            expression_attribute_names['#actions'] = 'actions'
            expression_attribute_values[':deleteActions'] = compact_action_removals

        if jurisdiction_action_removals:
            for jurisdiction, actions in jurisdiction_action_removals.items():
                update_expression_parts.append(
                    f'#permissions.#jurisdictions.#{jurisdiction} :{jurisdiction}DeleteActions',
                )
                expression_attribute_names['#permissions'] = 'permissions'
                expression_attribute_names['#jurisdictions'] = 'jurisdictions'
                expression_attribute_names[f'#{jurisdiction}'] = jurisdiction
                expression_attribute_values[f':{jurisdiction}DeleteActions'] = actions

        if update_expression_parts:
            update_expression = 'DELETE ' + ', '.join(update_expression_parts)

            return self.config.users_table.update_item(
                Key={'pk': f'USER#{user_id}', 'sk': f'COMPACT#{compact}'},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues='ALL_NEW',
            )

        return None

    def update_user_attributes(self, *, user_id: str, attributes: dict):
        """Update the provided user's attributes
        :param str user_id: The user to update
        :param dict attributes: Dict of user attributes to update.
        Keys are the attribute names, values are the attribute values
        ```json
        {
          "attributes": {
            "email": "justin@example.com",
            "familyName": "Justin",
            "givenName": "Case"
          }
        }
        ```
        """
        logger.info('Updating staff user attributes', user_id=user_id)

        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}

        for attr_name, attr_value in attributes.items():
            update_expression_parts.append(f'attributes.#{attr_name} = :{attr_name}')
            expression_attribute_names[f'#{attr_name}'] = attr_name
            expression_attribute_values[f':{attr_name}'] = attr_value

        update_expression = 'SET ' + ', '.join(update_expression_parts)

        records = self.get_user(user_id=user_id)['items']
        compacts = {record['compact'] for record in records}

        # We'll just serially update each of the user's records, since we realistically only
        # expect users to have two or three. If latency gets excessive, we can refactor.
        records = []
        for compact in compacts:
            resp = self.config.users_table.update_item(
                Key={'pk': f'USER#{user_id}', 'sk': f'COMPACT#{compact}'},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues='ALL_NEW',
            )
            records.append(resp['Attributes'])
        return self.schema.load(records, many=True)

    def create_user(self, compact: str, attributes: dict, permissions: dict):
        """Create a new Cognito user and DB record with the given attributes and permissions
        :param str compact: The compact the user will have permissions in
        :param dict attributes: The user attributes
        :param dict permissions: The permissions for the user
        :return:
        """
        logger.info('Creating staff user', attributes=attributes)
        attributes = self.user_attributes_schema.load(attributes)
        permissions = self.compact_permissions_schema.load(permissions)

        try:
            resp = self.config.cognito_client.admin_create_user(
                UserPoolId=self.config.user_pool_id,
                Username=attributes['email'],
                # Email will be the only attribute we actually manage in Cognito
                UserAttributes=[
                    {'Name': 'email', 'Value': attributes['email']},
                    {'Name': 'email_verified', 'Value': 'True'},
                ],
                DesiredDeliveryMediums=['EMAIL'],
            )
            user_id = get_sub_from_user_attributes(resp['User']['Attributes'])
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                # If the user already exists, look them up
                resp = self.config.cognito_client.admin_get_user(
                    UserPoolId=self.config.user_pool_id,
                    Username=attributes['email'],
                )
                user_id = get_sub_from_user_attributes(resp['UserAttributes'])
            else:
                raise

        try:
            user = self.schema.dump(
                {
                    'userId': user_id,
                    'compact': compact,
                    'attributes': attributes,
                    'permissions': permissions,
                    'status': StaffUserStatus.INACTIVE.value,
                },
            )
            # If the user doesn't already exist, add them
            self.config.users_table.put_item(
                Item=user,
                ConditionExpression=Attr('pk').not_exists() & Attr('sk').not_exists(),
            )
            user = self.schema.load(user)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # The user record already exists - we'll update the existing record permissions and ignore attributes
                compact_permissions = permissions.get('actions', set())
                jurisdiction_permissions = permissions.get('jurisdictions', {})
                user = self.update_user_permissions(
                    compact=compact,
                    user_id=user_id,
                    compact_action_additions=compact_permissions,
                    jurisdiction_action_additions=jurisdiction_permissions,
                )
            else:
                raise
        return user

    def delete_user(self, *, compact: str, user_id: str) -> None:
        """
        Delete a staff user's compact permissions record from DynamoDB
        :param str compact: The compact the user has permissions in
        :param str user_id: The user's ID
        """
        try:
            # We add a ConditionExpression to force this operation to _not_ be idempotent. We want an exception
            # if the user's record doesn't exist.
            self.config.users_table.delete_item(
                Key={'pk': f'USER#{user_id}', 'sk': f'COMPACT#{compact}'}, ConditionExpression=Attr('pk').exists()
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise CCNotFoundException('User not found') from e
        return

    def reinvite_user(self, *, email: str) -> None:
        """
        Reinvite a staff user by resetting their password and resending their invite email
        :param str email: The user's email address
        """
        try:
            # Check their current status
            user_data = self.config.cognito_client.admin_get_user(
                UserPoolId=self.config.user_pool_id,
                Username=email,
            )

            # If they're in CONFIRMED state, we need to reset their password first
            if user_data['UserStatus'] in (UserStatus.CONFIRMED, UserStatus.RESET_REQUIRED):
                self.config.cognito_client.admin_set_user_password(
                    UserPoolId=self.config.user_pool_id,
                    Username=email,
                    # We need to reset their password, but they will never use it, so we
                    # just need to set it to something random. Note that this value should not be referenced
                    # outside of this function, as it is a real password and we want it to be cleaned up
                    # by the garbage collector, as soon as possible.
                    # These passwords require at least one number, one uppercase, and one lowercase letter, so we add
                    # the prefix to meet these requirements
                    Password='!1Ha' + token_hex(45),
                    Permanent=False,
                )
            # If the user is in any unexpected state, we'll raise an exception
            elif user_data['UserStatus'] != UserStatus.FORCE_CHANGE_PASSWORD:
                logger.error(
                    'User is in unexpected state',
                    user_id=get_sub_from_user_attributes(user_data['UserAttributes']),
                    user_status=user_data['UserStatus'],
                    email=email,
                    user_data=user_data,
                )
                raise CCInternalException(f'User is in unexpected state: {user_data["UserStatus"]}')
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                raise CCNotFoundException('User not found') from e
            raise

        # Now resend the invite
        try:
            self.config.cognito_client.admin_create_user(
                UserPoolId=self.config.user_pool_id,
                Username=email,
                MessageAction='RESEND',
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                raise CCNotFoundException('User not found') from e
            raise
