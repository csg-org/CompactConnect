from tests import TstLambdas


class TestGetAllowedJurisdictions(TstLambdas):
    """Testing compact jurisdictions are identified correctly from request scopes"""

    def test_board_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='diet',
            scopes={'openid', 'email', 'oh/diet.admin', 'ne/diet.admin'},
        )
        self.assertEqual(['ne', 'oh'], sorted(resp))

    def test_compact_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='diet',
            scopes={'openid', 'email', 'diet/admin', 'oh/diet.admin'},
        )
        self.assertEqual(None, resp)

    def test_multi_jurisdiction_board_admin(self):
        from cc_common.utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='diet',
            scopes={'openid', 'email', 'oh/diet.admin', 'ky/diet.admin', 'ne/diet.admin'},
        )
        self.assertEqual(['ky', 'ne', 'oh'], sorted(resp))
