from boto3.dynamodb.conditions import Key

from config import config, logger


class UserScopes(set):
    """
    Custom Set that will populate itself based on the user's database record contents
    """
    def __init__(self, sub: str):
        super().__init__()
        self._get_scopes_from_db(sub)

    def _get_scopes_from_db(self, sub: str):
        """
        Parse the user's database record to calculate scopes.

        Note: See the accompanying unit tests for expected db record shape.
        :param sub: The `sub` field value from the Cognito Authorizer (which gets it from the JWT)
        """
        user_data = self._get_user_data(sub)
        permissions = {
            compact_record['compact']: {
                'actions': set(compact_record['permissions']['actions']),
                'jurisdictions': compact_record['permissions']['jurisdictions']
            }
            for compact_record in user_data
        }

        # Ensure included compacts are limited to supported values
        disallowed_compacts = permissions.keys() - config.compacts
        if disallowed_compacts:
            raise ValueError(f'User permissions include disallowed compacts: {disallowed_compacts}')

        for compact_name, compact_permissions in permissions.items():
            self._process_compact_permissions(compact_name, compact_permissions)

    @staticmethod
    def _get_user_data(sub: str):
        user_data = config.users_table.query(
            KeyConditionExpression=Key('pk').eq(f'USER#{sub}')
        ).get('Items', [])
        if not user_data:
            logger.error('Authenticated user not found!', sub=sub)
            raise RuntimeError('Authenticated user not found!')
        return user_data

    def _process_compact_permissions(self, compact_name, compact_permissions):
        # Compact-level permissions
        compact_actions = compact_permissions.get('actions', set())

        # Ensure included actions are limited to supported values
        disallowed_actions = compact_actions - {'read', 'admin'}
        if disallowed_actions:
            raise ValueError(f'User {compact_name} permissions include disallowed actions: {disallowed_actions}')

        # Read is the only truly compact-level permission
        if 'read' in compact_actions:
            self.add(f'{compact_name}/read')

        if 'admin' in compact_actions:
            # Two levels of authz for admin
            self.add(f'{compact_name}/admin')
            self.add(f'{compact_name}/{compact_name}.admin')

        # Ensure included jurisdictions are limited to supported values
        jurisdictions = compact_permissions['jurisdictions']
        disallowed_jurisdictions = jurisdictions.keys() - config.jurisdictions
        if disallowed_jurisdictions:
            raise ValueError(
                f'User {compact_name} permissions include disallowed jurisdictions: {disallowed_jurisdictions}'
            )

        for jurisdiction_name, jurisdiction_permissions in compact_permissions['jurisdictions'].items():
            self._process_jurisdiction_permissions(compact_name, jurisdiction_name, jurisdiction_permissions)

    def _process_jurisdiction_permissions(self, compact_name, jurisdiction_name, jurisdiction_actions):
        # Ensure included actions are limited to supported values
        disallowed_actions = jurisdiction_actions - {'write', 'admin'}
        if disallowed_actions:
            raise ValueError(
                f'User {compact_name}/{jurisdiction_name} permissions include disallowed actions: '
                f'{disallowed_actions}'
            )
        for action in jurisdiction_actions:
            # Two levels of authz
            self.add(f'{compact_name}/{action}')
            self.add(f'{compact_name}/{jurisdiction_name}.{action}')
