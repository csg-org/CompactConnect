from tests import TstLambdas


class TestGetAllowedJurisdictions(TstLambdas):
    """Testing compact jurisdictions are identified correctly from request scopes"""

    def test_board_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='aslp',
            scopes={'openid', 'email', 'oh/aslp.admin', 'ne/octp.admin'},
        )
        self.assertEqual(['oh'], resp)

    def test_compact_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'oh/aslp.admin'},
        )
        self.assertEqual(None, resp)

    def test_multi_jurisdiction_board_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='aslp',
            scopes={'openid', 'email', 'oh/aslp.admin', 'ky/aslp.admin', 'ne/octp.admin'},
        )
        self.assertEqual(sorted(['oh', 'ky']), sorted(resp))
