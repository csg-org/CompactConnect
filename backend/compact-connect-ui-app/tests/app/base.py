import json
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from unittest.mock import patch

from aws_cdk.assertions import Annotations, Match, Template
from aws_cdk.aws_cloudfront import CfnDistribution
from aws_cdk.aws_lambda import CfnFunction
from aws_cdk.aws_s3 import CfnBucket
from common_constructs.stack import Stack

from app import CompactConnectApp
from pipeline import FrontendStage
from stacks.frontend_deployment_stack import FrontendDeploymentStack


class _AppSynthesizer:
    """
    A helper class to cache apps based on context.
    This is useful to avoid re-synthesizing the app for each test.
    """

    def __init__(self):
        super().__init__()
        self._cached_apps: dict[int, CompactConnectApp] = {}

    def get_app(self, context: Mapping) -> CompactConnectApp:
        context_hash = self._get_context_hash(context)
        if context_hash not in self._cached_apps.keys():
            self._cached_apps[context_hash] = CompactConnectApp(context=context)
        return self._cached_apps[context_hash]

    def _get_context_hash(self, context: Mapping) -> int:
        return hash(json.dumps(context, sort_keys=True))


_app_synthesizer = _AppSynthesizer()


class TstAppABC(ABC):
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
        cls.app = _app_synthesizer.get_app(cls.context)

    @staticmethod
    def get_resource_properties_by_logical_id(logical_id: str, resources: Mapping[str, Mapping]) -> Mapping:
        """
        Helper function to retrieve a resource from a CloudFormation template by its logical ID.
        """
        try:
            return resources[logical_id]['Properties']
        except KeyError as exc:
            raise RuntimeError(f'{logical_id} not found in resources!') from exc

    def _inspect_frontend_deployment_stack(self, ui_stack: FrontendDeploymentStack):
        with self.subTest(ui_stack.stack_name):
            ui_stack_template = Template.from_stack(ui_stack)
            # Ensure we have a CloudFront distribution
            ui_stack_template.resource_count_is('AWS::CloudFront::Distribution', 1)
            # This stack is not anticipated to do much changing, so we'll just snapshot-test key resources
            ui_bucket = ui_stack_template.find_resources(CfnBucket.CFN_RESOURCE_TYPE_NAME)[
                ui_stack.get_logical_id(ui_stack.ui_bucket.node.default_child)
            ]
            self.compare_snapshot(ui_bucket, snapshot_name=f'{ui_stack.stack_name}-UI_BUCKET', overwrite_snapshot=False)
            distribution = ui_stack_template.find_resources(CfnDistribution.CFN_RESOURCE_TYPE_NAME)
            self.assertEqual(len(distribution), 1)
            self.compare_snapshot(distribution, f'{ui_stack.stack_name}-UI_DISTRIBUTION', overwrite_snapshot=False)
            # take a snapshot of the lambda@edge code to ensure placeholder values are being injected
            distribution_function = ui_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME)[
                ui_stack.get_logical_id(ui_stack.distribution.csp_function.node.default_child)
            ]
            self.compare_snapshot(
                distribution_function,
                f'{ui_stack.stack_name}-UI_DISTRIBUTION_LAMBDA_FUNCTION',
                overwrite_snapshot=False,
            )

    def _check_no_stack_annotations(self, stack: Stack):
        with self.subTest(f'Security Rules: {stack.stack_name}'):
            errors = Annotations.from_stack(stack).find_error('*', Match.string_like_regexp('.*'))
            self.assertEqual(0, len(errors), msg='\n'.join(f'{err.id}: {err.entry.data.strip()}' for err in errors))

            warnings = Annotations.from_stack(stack).find_warning('*', Match.string_like_regexp('.*'))
            self.assertEqual(
                0, len(warnings), msg='\n'.join(f'{warn.id}: {warn.entry.data.strip()}' for warn in warnings)
            )

    def _check_no_frontend_stage_annotations(self, stage: FrontendStage):
        self._check_no_stack_annotations(stage.frontend_deployment_stack)

    def _count_stack_resources(self, stack: Stack) -> int:
        """
        Count the number of resources in a CloudFormation stack.

        :param stack: The CDK Stack to analyze
        :returns: Number of resources in the stack
        """
        template = Template.from_stack(stack)
        # Get template as dictionary and count resources
        template_dict = template.to_json()
        resources = template_dict.get('Resources', {})
        return len(resources)

    def compare_snapshot(self, actual: Mapping | list, snapshot_name: str, overwrite_snapshot: bool = False):
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
                # So the data files will end with a newline
                f.write('\n')
            sys.stdout.write(f"Snapshot '{snapshot_name}' has been overwritten.")
        else:
            self.maxDiff = None  # pylint: disable=invalid-name,attribute-defined-outside-init
            self.assertEqual(
                snapshot,
                actual,
                f"Snapshot '{snapshot_name}' does not match the actual data. "
                'To overwrite the snapshot, set overwrite_snapshot=True.',
            )
