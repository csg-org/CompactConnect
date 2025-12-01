from moto import mock_aws

from . import TstFunction


@mock_aws
class TestOpenSearchIndexManager(TstFunction):
    """Test suite for OpenSearchIndexManager custom resource."""

    def setUp(self):
        super().setUp()

    # TODO - add test cases for checking api calls
