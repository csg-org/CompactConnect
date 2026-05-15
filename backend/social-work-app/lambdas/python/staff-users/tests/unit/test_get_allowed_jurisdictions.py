from tests import TstLambdas


class TestGetAllowedJurisdictions(TstLambdas):
    """Testing compact jurisdictions are identified correctly from request scopes"""

    def test_board_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='cosm',
            scopes={'openid', 'email', 'oh/cosm.admin'},
        )
        self.assertEqual(['oh'], resp)

    def test_compact_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='cosm',
            scopes={'openid', 'email', 'cosm/admin', 'oh/cosm.admin'},
        )
        self.assertEqual(None, resp)

    def test_multi_jurisdiction_board_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='cosm',
            scopes={'openid', 'email', 'oh/cosm.admin', 'ky/cosm.admin'},
        )
        self.assertEqual(sorted(['oh', 'ky']), sorted(resp))
