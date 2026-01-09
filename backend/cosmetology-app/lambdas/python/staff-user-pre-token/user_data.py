from boto3.dynamodb.conditions import Key
from cc_common.config import config, logger
from cc_common.data_model.schema.common import CCPermissionsAction


class UserData:
    """Class that will populate itself based on the user's database record contents"""

    def __init__(self, sub: str):
        # Some auth flows (like Secure Remote Password) don't grant 'profile', so we'll make sure it's included by
        # default
        super().__init__()

        self.scopes = set(('profile',))
        self._get_scopes_from_db(sub)

    def _get_scopes_from_db(self, sub: str):
        """Parse the user's database record to calculate scopes.

        Note: See the accompanying unit tests for expected db record shape.
        :param sub: The `sub` field value from the Cognito Authorizer (which gets it from the JWT)
        """
        self._get_user_records(sub)
        permissions = {
            compact_record['compact']: {
                'actions': set(compact_record['permissions'].get('actions', [])),
                'jurisdictions': compact_record['permissions']['jurisdictions'],
            }
            for compact_record in self.records
        }

        # Ensure included compacts are limited to supported values
        disallowed_compacts = permissions.keys() - config.compacts
        if disallowed_compacts:
            raise ValueError(f'User permissions include disallowed compacts: {disallowed_compacts}')

        for compact_abbr, compact_permissions in permissions.items():
            self._process_compact_permissions(compact_abbr, compact_permissions)

    def _get_user_records(self, sub: str):
        self.records = config.users_table.query(KeyConditionExpression=Key('pk').eq(f'USER#{sub}')).get('Items', [])
        if not self.records:
            logger.error('Authenticated user not found!', sub=sub)
            raise RuntimeError('Authenticated user not found!')

    def _process_compact_permissions(self, compact_abbr, compact_permissions):
        # Compact-level permissions
        compact_actions = compact_permissions.get('actions', set())

        # Ensure included actions are limited to supported values
        # Note we are keeping in the 'read' permission for backwards compatibility
        # Though we are not using it in the codebase
        disallowed_actions = compact_actions - {
            CCPermissionsAction.READ,
            CCPermissionsAction.ADMIN,
            CCPermissionsAction.READ_PRIVATE,
            CCPermissionsAction.READ_SSN,
        }
        if disallowed_actions:
            raise ValueError(f'User {compact_abbr} permissions include disallowed actions: {disallowed_actions}')

        # readGeneral is always added an implicit permission granted to all staff users at the compact level
        self.scopes.add(f'{compact_abbr}/{CCPermissionsAction.READ_GENERAL}')

        if CCPermissionsAction.READ_PRIVATE in compact_actions:
            self.scopes.add(f'{compact_abbr}/{CCPermissionsAction.READ_PRIVATE}')

        if CCPermissionsAction.READ_SSN in compact_actions:
            self.scopes.add(f'{compact_abbr}/{CCPermissionsAction.READ_SSN}')

        if CCPermissionsAction.ADMIN in compact_actions:
            self.scopes.add(f'{compact_abbr}/{CCPermissionsAction.ADMIN}')

        # Ensure included jurisdictions are limited to supported values
        jurisdictions = compact_permissions['jurisdictions']
        disallowed_jurisdictions = jurisdictions.keys() - config.jurisdictions
        if disallowed_jurisdictions:
            raise ValueError(
                f'User {compact_abbr} permissions include disallowed jurisdictions: {disallowed_jurisdictions}',
            )

        for jurisdiction_name, jurisdiction_permissions in compact_permissions['jurisdictions'].items():
            self._process_jurisdiction_permissions(compact_abbr, jurisdiction_name, jurisdiction_permissions)

    def _process_jurisdiction_permissions(self, compact_abbr, jurisdiction_name, jurisdiction_actions):
        # Ensure included actions are limited to supported values
        disallowed_actions = jurisdiction_actions - {
            CCPermissionsAction.WRITE,
            CCPermissionsAction.ADMIN,
            CCPermissionsAction.READ_PRIVATE,
            CCPermissionsAction.READ_SSN,
        }
        if disallowed_actions:
            raise ValueError(
                f'User {jurisdiction_name}/{compact_abbr} permissions include disallowed actions: {disallowed_actions}',
            )
        for action in jurisdiction_actions:
            self.scopes.add(f'{jurisdiction_name}/{compact_abbr}.{action}')
