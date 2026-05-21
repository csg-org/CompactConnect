from unittest import TestCase

from common_constructs.constants import BETA_ENV_NAME, PROD_ENV_NAME


class TestConstants(TestCase):
    def test_prod_env_name(self):
        self.assertEqual('prod', PROD_ENV_NAME)

    def test_beta_env_name(self):
        self.assertEqual('beta', BETA_ENV_NAME)
