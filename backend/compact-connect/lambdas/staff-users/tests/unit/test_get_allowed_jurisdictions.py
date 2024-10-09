from tests import TstLambdas


class TestGetAllowedJurisdictions(TstLambdas):
    """
    Testing compact jurisdictions are identified correctly from request scopes
    """

    def test_board_admin(self):
        from utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'aslp/oh.admin', 'octp/admin', 'octp/ne.admin'}
        )
        self.assertEqual(
            ['oh'],
            resp
        )

    def test_compact_admin(self):
        from utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'aslp/aslp.admin', 'aslp/oh.admin'}
        )
        self.assertEqual(None, resp)

    def test_multi_jurisdiction_board_admin(self):
        from utils import get_allowed_jurisdictions

        resp = get_allowed_jurisdictions(
            compact='aslp',
            scopes={'openid', 'email', 'aslp/admin', 'aslp/oh.admin', 'aslp/ky.admin', 'octp/admin', 'octp/ne.admin'}
        )
        self.assertEqual(
            sorted(['oh', 'ky']),
            sorted(resp)
        )
