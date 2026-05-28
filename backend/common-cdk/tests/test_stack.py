from unittest import TestCase

from aws_cdk import App, Environment

from common_constructs.stack import AppStack, Stack, StandardTags

_TEST_ENV = Environment(account='111122223333', region='us-east-1')

_CDK_CONTEXT = {
    'compacts': ['aslp', 'octp', 'coun'],
    'jurisdictions': ['al', 'ak', 'az'],
    'license_types': {
        'aslp': [{'name': 'audiologist', 'abbreviation': 'aud'}],
        'octp': [{'name': 'occupational therapist', 'abbreviation': 'ot'}],
        'coun': [{'name': 'licensed professional counselor', 'abbreviation': 'lpc'}],
    },
    'hosted-zone:account=111122223333:domainName=example.com:region=us-east-1': {
        'Id': 'Z1234567890',
        'Name': 'example.com.',
    },
}

_STANDARD_TAGS = StandardTags(project='test', service='test', environment='test')


class TestStackLicenseContext(TestCase):
    def setUp(self):
        self.app = App(context=_CDK_CONTEXT)
        self.stack = Stack(self.app, 'BaseStack', standard_tags=_STANDARD_TAGS, environment_name='sandbox')

    def test_license_type_names_flattens_all_compacts(self):
        self.assertEqual(
            ['audiologist', 'occupational therapist', 'licensed professional counselor'], self.stack.license_type_names
        )

    def test_license_type_abbreviations_flattens_all_compacts(self):
        self.assertEqual(['aud', 'ot', 'lpc'], self.stack.license_type_abbreviations)

    def test_license_types_returns_context_dict(self):
        self.assertEqual(_CDK_CONTEXT['license_types'], self.stack.license_types)


class TestAppStack(TestCase):
    def setUp(self):
        self.app = App(context=_CDK_CONTEXT)

    def test_prod_environment_requires_domain_name(self):
        with self.assertRaises(ValueError):
            AppStack(
                self.app,
                'ProdStack',
                standard_tags=_STANDARD_TAGS,
                environment_name='prod',
                environment_context={},
                env=_TEST_ENV,
            )

    def test_domain_properties_derived_from_hosted_zone(self):
        stack = AppStack(
            self.app,
            'DomainStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context={'domain_name': 'example.com'},
            env=_TEST_ENV,
        )
        self.assertEqual('api.example.com', stack.api_domain_name)
        self.assertEqual('state-api.example.com', stack.state_api_domain_name)
        self.assertEqual('search.example.com', stack.search_api_domain_name)
        self.assertEqual('app.example.com', stack.ui_domain_name)

    def test_ui_domain_name_override_takes_precedence(self):
        stack = AppStack(
            self.app,
            'OverrideStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context={
                'domain_name': 'example.com',
                'ui_domain_name_override': 'custom.example.com',
            },
            env=_TEST_ENV,
        )
        self.assertEqual('custom.example.com', stack.ui_domain_name)

    def test_allowed_origins_includes_ui_and_local_when_configured(self):
        stack = AppStack(
            self.app,
            'CorsStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context={
                'domain_name': 'example.com',
                'allow_local_ui': True,
                'local_ui_port': '3018',
            },
            env=_TEST_ENV,
        )
        self.assertEqual(
            ['https://app.example.com', 'http://localhost:3018'],
            stack.allowed_origins,
        )

    def test_common_env_vars_includes_api_base_url_when_domain_configured(self):
        stack = AppStack(
            self.app,
            'EnvStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context={'domain_name': 'example.com'},
            env=_TEST_ENV,
        )
        self.assertEqual('https://api.example.com', stack.common_env_vars['API_BASE_URL'])
