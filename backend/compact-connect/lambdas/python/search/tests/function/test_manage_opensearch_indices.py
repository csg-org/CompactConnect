from moto import mock_aws

from . import TstFunction


@mock_aws
class TestOpenSearchIndexManager(TstFunction):
    """Test suite for ManageFeatureFlagHandler custom resource."""

    def setUp(self):
        super().setUp()
