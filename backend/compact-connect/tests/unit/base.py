import json
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from unittest.mock import patch

from app import CompactConnectApp
from aws_cdk.assertions import Annotations, Match, Template
from aws_cdk.aws_apigateway import CfnMethod
from aws_cdk.aws_cognito import CfnUserPool, CfnUserPoolClient
from common_constructs.stack import Stack
from pipeline import BackendStage
from stacks.api_stack import ApiStack
from stacks.persistent_stack import PersistentStack


class TstCompactConnectABC(ABC):
    """
    Base class for common test elements across configurations.

    Note: Concrete classes must also inherit from TestCase
    """

    @classmethod
    @abstractmethod
    def get_context(cls) -> Mapping:
        pass

    @classmethod
    @patch.dict(os.environ, {'CDK_DEFAULT_ACCOUNT': '000000000000', 'CDK_DEFAULT_REGION': 'us-east-1'})
    def setUpClass(cls):  # pylint: disable=invalid-name
        """
        We build the app once per TestCase, to save compute time in the test suite
        """
        cls.context = cls.get_context()
        cls.app = CompactConnectApp(context=cls.context)

    def test_no_compact_jurisdiction_name_clash(self):
        """
        Because compact and jurisdiction abbreviations share space in access token scopes, we need to ensure that
        there are no naming clashes between the two.
        """
        jurisdictions = set(self.context['jurisdictions'])
        compacts = set(self.context['compacts'])
        # The '#' character is used in the composite identifiers in the database. In order to prevent confusion in
        # parsing the identifiers, we either have to carefully escape all '#' characters that might show up in compact
        # or jurisdiction abbreviations or simply not allow them. Since the abbreviations seem unlikely to include a #
        # character, the latter seems reasonable.
        for jurisdiction in jurisdictions:
            self.assertNotIn('#', jurisdiction, "'#' not allowed in jurisdiction abbreviations!")
        for compact in compacts:
            self.assertNotIn('#', compact, "'#' not allowed in compact abbreviations!")
        self.assertFalse(jurisdictions.intersection(compacts), 'Compact vs jurisdiction name clash!')

    @staticmethod
    def get_resource_properties_by_logical_id(logical_id: str, resources: Mapping[str, Mapping]) -> Mapping:
        """
        Helper function to retrieve a resource from a CloudFormation template by its logical ID.
        """
        try:
            return resources[logical_id]['Properties']
        except KeyError as exc:
            raise RuntimeError(f'{logical_id} not found in resources!') from exc

    def _inspect_persistent_stack(
        self,
        persistent_stack: PersistentStack,
        *,
        domain_name: str = None,
        allow_local_ui: bool = False,
        local_ui_port: str = None,
    ):
        with self.subTest(persistent_stack.stack_name):
            # Make sure our local port ui setting overrides the default
            persistent_stack_template = Template.from_stack(persistent_stack)

            callbacks = []
            if domain_name is not None:
                callbacks.append(f'https://{domain_name}/auth/callback')
            if allow_local_ui:
                # 3018 is default
                local_ui_port = '3018' if not local_ui_port else local_ui_port
                callbacks.append(f'http://localhost:{local_ui_port}/auth/callback')

            # ensure we have two user pools, one for staff users and one for providers
            persistent_stack_template.resource_count_is(CfnUserPool.CFN_RESOURCE_TYPE_NAME, 2)

            # Ensure our provider user pool is created with expected custom attributes
            provider_users_user_pool = self.get_resource_properties_by_logical_id(
                persistent_stack.get_logical_id(persistent_stack.provider_users.node.default_child),
                persistent_stack_template.find_resources(CfnUserPool.CFN_RESOURCE_TYPE_NAME),
            )

            # assert that both custom attributes are in schema
            self.assertIn(
                {'AttributeDataType': 'String', 'Mutable': False, 'Name': 'providerId'},
                provider_users_user_pool['Schema'],
            )
            self.assertIn(
                {'AttributeDataType': 'String', 'Mutable': False, 'Name': 'compact'}, provider_users_user_pool['Schema']
            )
            # Ensure our Staff user pool app client is configured with the expected callbacks and read/write attributes
            staff_users_user_pool_app_client = self.get_resource_properties_by_logical_id(
                persistent_stack.get_logical_id(persistent_stack.staff_users.ui_client.node.default_child),
                persistent_stack_template.find_resources(CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME),
            )
            self.assertEqual(staff_users_user_pool_app_client['CallbackURLs'], callbacks)
            self.assertEqual(staff_users_user_pool_app_client['ReadAttributes'], ['email'])
            self.assertEqual(staff_users_user_pool_app_client['WriteAttributes'], ['email'])

            # Ensure our Provider user pool app client is created with expected values
            provider_users_user_pool_app_client = self.get_resource_properties_by_logical_id(
                persistent_stack.get_logical_id(persistent_stack.provider_users.ui_client.node.default_child),
                persistent_stack_template.find_resources(CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME),
            )

            self.assertEqual(provider_users_user_pool_app_client['CallbackURLs'], callbacks)
            self.assertEqual(
                provider_users_user_pool_app_client['ReadAttributes'],
                ['custom:compact', 'custom:providerId', 'email', 'family_name', 'given_name'],
            )
            self.assertEqual(
                provider_users_user_pool_app_client['WriteAttributes'], ['email', 'family_name', 'given_name']
            )

    def _inspect_api_stack(self, api_stack: ApiStack):
        with self.subTest(api_stack.stack_name):
            api_template = Template.from_stack(api_stack)

            with self.assertRaises(RuntimeError):
                # This is an indicator of unintentional (and invalid) authorizer configuration in the API.
                # Not matching is desired in this case and raises a RuntimeError.
                api_template.has_resource(
                    type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
                    props={'Properties': {'AuthorizationScopes': Match.any_value(), 'AuthorizationType': 'NONE'}},
                )

    def _check_no_stack_annotations(self, stack: Stack):
        with self.subTest(f'Security Rules: {stack.stack_name}'):
            errors = Annotations.from_stack(stack).find_error('*', Match.string_like_regexp('.*'))
            self.assertEqual(0, len(errors), msg='\n'.join(f'{err.id}: {err.entry.data.strip()}' for err in errors))

            warnings = Annotations.from_stack(stack).find_warning('*', Match.string_like_regexp('.*'))
            self.assertEqual(
                0, len(warnings), msg='\n'.join(f'{warn.id}: {warn.entry.data.strip()}' for warn in warnings)
            )

    def _check_no_stage_annotations(self, stage: BackendStage):
        self._check_no_stack_annotations(stage.persistent_stack)
        self._check_no_stack_annotations(stage.ui_stack)
        self._check_no_stack_annotations(stage.api_stack)
        self._check_no_stack_annotations(stage.ingest_stack)

    def compare_snapshot(self, actual: dict, snapshot_name: str, overwrite_snapshot: bool = False):
        """
        Compare the actual dictionary to the snapshot with the given name.
        If overwrite_snapshot is True, overwrite the snapshot with the actual data.
        """
        snapshot_path = os.path.join('tests', 'resources', 'snapshots', f'{snapshot_name}.json')

        if os.path.exists(snapshot_path):
            with open(snapshot_path) as f:
                snapshot = json.load(f)
        else:
            sys.stdout.write(f"Snapshot at path '{snapshot_path}' does not exist.")
            snapshot = None

        if snapshot != actual and overwrite_snapshot:
            with open(snapshot_path, 'w') as f:
                json.dump(actual, f, indent=2)
            sys.stdout.write(f"Snapshot '{snapshot_name}' has been overwritten.")
        else:
            self.maxDiff = None  # pylint: disable=invalid-name,attribute-defined-outside-init
            self.assertEqual(
                snapshot,
                actual,
                f"Snapshot '{snapshot_name}' does not match the actual data. "
                'To overwrite the snapshot, set overwrite_snapshot=True.',
            )
