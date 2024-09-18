from tests import TstLambdas


class TestTransformUserPermissions(TstLambdas):
    """
    Testing that permissions are transformed correctly for the API
    """

    def test_basic_transformation(self):
        from utils import transform_user_permissions

        resp = transform_user_permissions(
            compact='aslp',
            compact_permissions={
                'actions': {'read', 'admin'},
                'jurisdictions': {
                    'ky': {'write', 'admin'}
                }
            }
        )
        self.assertEqual(
            {
                'aslp': {
                    'actions': {
                        'read': True,
                        'admin': True
                    },
                    'jurisdictions': {
                        'ky': {
                            'actions': {
                                'write': True,
                                'admin': True
                            }
                        }
                    }
                }
            },
            resp
        )
