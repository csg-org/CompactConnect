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
        permissions = user_data.get('permissions', {})

        # Ensure included compacts are limited to supported values
        disallowed_compcats = permissions.keys() - config.compacts
        if disallowed_compcats:
            raise ValueError(f'User permissions include disallowed compacts: {disallowed_compcats}')

        for compact_name, compact_permissions in permissions.items():
            self._process_compact_permissions(compact_name, compact_permissions)

    @staticmethod
    def _get_user_data(sub: str):
        try:
            user_data = config.users_table.get_item(Key={'pk': sub})['Item']
        except KeyError as e:
            logger.error('Authenticated user not found!', exc_info=e, sub=sub)
            raise RuntimeError('Authenticated user not found!') from e
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

    def _process_jurisdiction_permissions(self, compact_name, jurisdiction_name, jurisdiction_permissions):
        # Jurisdiction-level permissions
        jurisdiction_actions = jurisdiction_permissions.get('actions', set())

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
