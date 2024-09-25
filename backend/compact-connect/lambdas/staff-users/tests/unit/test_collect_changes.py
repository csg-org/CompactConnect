from tests import TstLambdas


class TestCollectChanges(TstLambdas):
    """
    Testing that permissions changes are parsed correctly from the API
    """

    def test_compact_changes(self):
        from utils import collect_changes

        resp = collect_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'aslp/aslp.admin'},
            compact_changes={
                'actions': {
                    'admin': True,
                    'read': False
                },
                'jurisdictions': {}
            }
        )
        self.assertEqual(
            {
                'compact_action_additions': {'admin'},
                'compact_action_removals': {'read'},
                'jurisdiction_action_additions': {},
                'jurisdiction_action_removals': {}
            },
            resp
        )

    def test_jurisdiction_changes(self):
        from utils import collect_changes

        resp = collect_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'aslp/oh.admin'},
            compact_changes={
                'jurisdictions': {
                    'oh': {
                        'actions': {
                            'admin': True,
                            'write': False
                        }
                    }
                }
            }
        )
        self.assertEqual(
            {
                'compact_action_additions': set(),
                'compact_action_removals': set(),
                'jurisdiction_action_additions': {
                    'oh': {'admin'}
                },
                'jurisdiction_action_removals': {
                    'oh': {'write'}
                }
            },
            resp
        )

    def test_disallowed_jurisdiction_changes(self):
        from exceptions import CCAccessDeniedException
        from utils import collect_changes

        with self.assertRaises(CCAccessDeniedException):
            collect_changes(
                path_compact='aslp',
                scopes={'openid', 'email', 'aslp/admin', 'aslp/oh.admin'},
                compact_changes={
                    'jurisdictions': {
                        'ne': {
                            'actions': {
                                'admin': True,
                                'write': False
                            }
                        }
                    }
                }
            )

    def test_jurisdiction_admin_disallowed_compact_changes(self):
        from exceptions import CCAccessDeniedException
        from utils import collect_changes

        with self.assertRaises(CCAccessDeniedException):
            collect_changes(
                path_compact='aslp',
                scopes={'openid', 'email', 'aslp/admin', 'aslp/oh.admin'},
                compact_changes={
                    'actions': {
                        'admin': True
                    },
                    'jurisdictions': {}
                }
            )

    def test_compact_and_jurisdiction_changes(self):
        from utils import collect_changes

        resp = collect_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'aslp/aslp.admin'},
            compact_changes={
                'actions': {
                    'admin': True,
                    'read': False
                },
                'jurisdictions': {
                    'oh': {
                        'actions': {
                            'admin': True,
                            'write': False
                        }
                    }
                }
            }
        )
        self.assertEqual(
            {
                'compact_action_additions': {'admin'},
                'compact_action_removals': {'read'},
                'jurisdiction_action_additions': {
                    'oh':  {'admin'}
                },
                'jurisdiction_action_removals': {
                    'oh': {'write'}
                }
            },
            resp
        )

    def test_jurisdiction_add_only(self):
        from utils import collect_changes

        resp = collect_changes(
            path_compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'aslp/oh.admin'},
            compact_changes={
                'jurisdictions': {
                    'oh': {
                        'actions': {
                            'admin': True
                        }
                    }
                }
            }
        )
        self.assertEqual(
            {
                'compact_action_additions': set(),
                'compact_action_removals': set(),
                'jurisdiction_action_additions': {
                    'oh': {'admin'}
                },
                'jurisdiction_action_removals': {}
            },
            resp
        )
