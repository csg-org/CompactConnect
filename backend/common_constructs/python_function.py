from typing import List

import jsii
from aws_cdk import Stack, Duration
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction as CdkPythonFunction, ICommandHooks, BundlingOptions
from cdk_nag import NagSuppressions
from constructs import Construct


class PythonFunction(CdkPythonFunction):
    """
    Standard Python lambda function that assumes unittest-compatible tests are written in the 'tests' directory.

    On bundling, this function will validate the lambda by temporarily installing dev dependencies in
    requirements-dev.txt, then executing and removing tests.
    """
    def __init__(
            self, scope: Construct, construct_id: str, **kwargs
    ):
        defaults = {
            'timeout': Duration.seconds(28),
        }
        defaults.update(kwargs)

        super().__init__(  # pylint: disable=missing-kwoa
            scope, construct_id,
            bundling=BundlingOptions(command_hooks=TestingHooks()),
            runtime=Runtime.PYTHON_3_12,
            **defaults
        )

        stack = Stack.of(self)
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': "These lambdas are synchronous and so don't require any DLQ configuration"
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'We may choose to move our lambdas into private VPC subnets in a future enhancement'
                }
            ]
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.node.path}/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'applies_to': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],
                    'reason': 'The BasicExecutionRole policy is appropriate for these lambdas'
                }
            ]
        )


@jsii.implements(ICommandHooks)
class TestingHooks:
    """
    Testing hooks that will automatically run the expected tests package to validate the lambda.

    This command hook will temporarily install dev dependencies, then execute unittest-compatible
    tests expected to be in the `tests` directory.
    """
    def after_bundling(self, input_dir: str, output_dir: str) -> List[str]:  # pylint: disable=unused-argument
        return [
            'mkdir _tmp_dev_deps',
            'python -m pip install -r requirements-dev.txt -t _tmp_dev_deps',
            'PYTHONPATH="$(pwd)/_tmp_dev_deps" python -m unittest discover -s tests',
            'rm -rf _tmp_dev_deps',
            'rm -rf tests'
        ]

    def before_bundling(self, input_dir: str, output_dir: str) -> List[str]:  # pylint: disable=unused-argument
        return []
