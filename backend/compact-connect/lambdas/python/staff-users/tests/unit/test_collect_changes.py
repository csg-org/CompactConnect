from unittest.mock import patch

from tests import TstLambdas


class TestCollectChanges(TstLambdas):
    """Testing that permissions changes are parsed correctly from the API"""

    def _when_testing_collect_and_authorize_changes_with_valid_jurisdiction(self, mock_compact_configuration_client):
        mock_compact_configuration_client.get_active_compact_jurisdictions.return_value = [{'postalAbbreviation': 'OH'}]

    def test_compact_changes(self):
        from cc_common.utils import collect_and_authorize_changes

        resp = collect_and_authorize_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'aslp/admin'},
            compact_changes={'actions': {'admin': True, 'readPrivate': False}, 'jurisdictions': {}},
        )
        self.assertEqual(
            {
                'compact_action_additions': {'admin'},
                'compact_action_removals': {'readPrivate'},
                'jurisdiction_action_additions': {},
                'jurisdiction_action_removals': {},
            },
            resp,
        )

    @patch('cc_common.utils.config.compact_configuration_client')
    def test_jurisdiction_changes(self, mock_compact_configuration_client):
        from cc_common.utils import collect_and_authorize_changes

        self._when_testing_collect_and_authorize_changes_with_valid_jurisdiction(mock_compact_configuration_client)

        resp = collect_and_authorize_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'oh/aslp.admin'},
            compact_changes={'jurisdictions': {'oh': {'actions': {'admin': True, 'write': False}}}},
        )
        self.assertEqual(
            {
                'compact_action_additions': set(),
                'compact_action_removals': set(),
                'jurisdiction_action_additions': {'oh': {'admin'}},
                'jurisdiction_action_removals': {'oh': {'write'}},
            },
            resp,
        )

    def test_disallowed_jurisdiction_changes(self):
        from cc_common.exceptions import CCAccessDeniedException
        from cc_common.utils import collect_and_authorize_changes

        with self.assertRaises(CCAccessDeniedException):
            collect_and_authorize_changes(
                path_compact='aslp',
                scopes={'openid', 'email', 'oh/aslp.admin'},
                compact_changes={'jurisdictions': {'ne': {'actions': {'admin': True, 'write': False}}}},
            )

    def test_jurisdiction_admin_disallowed_compact_changes(self):
        from cc_common.exceptions import CCAccessDeniedException
        from cc_common.utils import collect_and_authorize_changes

        with self.assertRaises(CCAccessDeniedException):
            collect_and_authorize_changes(
                path_compact='aslp',
                scopes={'openid', 'email', 'oh/aslp.admin'},
                compact_changes={'actions': {'admin': True}, 'jurisdictions': {}},
            )

    @patch('cc_common.utils.config.compact_configuration_client')
    def test_compact_and_jurisdiction_changes(self, mock_compact_configuration_client):
        from cc_common.utils import collect_and_authorize_changes

        self._when_testing_collect_and_authorize_changes_with_valid_jurisdiction(mock_compact_configuration_client)

        resp = collect_and_authorize_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'aslp/admin'},
            compact_changes={
                'actions': {'admin': True, 'readPrivate': False},
                'jurisdictions': {'oh': {'actions': {'admin': True, 'write': False}}},
            },
        )
        self.assertEqual(
            {
                'compact_action_additions': {'admin'},
                'compact_action_removals': {'readPrivate'},
                'jurisdiction_action_additions': {'oh': {'admin'}},
                'jurisdiction_action_removals': {'oh': {'write'}},
            },
            resp,
        )

    @patch('cc_common.utils.config.compact_configuration_client')
    def test_jurisdiction_add_only(self, mock_compact_configuration_client):
        from cc_common.utils import collect_and_authorize_changes

        self._when_testing_collect_and_authorize_changes_with_valid_jurisdiction(mock_compact_configuration_client)

        resp = collect_and_authorize_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'oh/aslp.admin'},
            compact_changes={'jurisdictions': {'oh': {'actions': {'admin': True}}}},
        )
        self.assertEqual(
            {
                'compact_action_additions': set(),
                'compact_action_removals': set(),
                'jurisdiction_action_additions': {'oh': {'admin'}},
                'jurisdiction_action_removals': {},
            },
            resp,
        )
