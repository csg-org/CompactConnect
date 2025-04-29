import json
import os

import yaml
from aws_cdk import CustomResource, Duration
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
from constructs import Construct

from .compact_configuration_table import CompactConfigurationTable


class CompactConfigurationUpload(Construct):
    """Custom resource to upload compact configuration data to the compact configuration table."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: CompactConfigurationTable,
        master_key: IKey,
        environment_name: str,
        environment_context: dict,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        stack: Stack = Stack.of(self)

        self.compact_configuration_upload_function = PythonFunction(
            scope,
            'CompactConfigurationUploadFunction',
            lambda_dir='custom-resources',
            index=os.path.join('handlers', 'compact_config_uploader.py'),
            handler='on_event',
            description='Uploads contents of compact-config directory to the compact configuration Dynamo table',
            timeout=Duration.minutes(10),
            log_retention=RetentionDays.THREE_MONTHS,
            environment={'COMPACT_CONFIGURATION_TABLE_NAME': table.table_name, **stack.common_env_vars},
        )

        # grant lambda access to the compact configuration table
        table.grant_read_write_data(self.compact_configuration_upload_function)
        # grant lambda access to the KMS key
        master_key.grant_encrypt_decrypt(self.compact_configuration_upload_function)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )

        self.compact_configuration_upload_provider = Provider(
            scope,
            'CompactConfigurationUploadProvider',
            on_event_handler=self.compact_configuration_upload_function,
            log_retention=RetentionDays.ONE_DAY,
        )
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            f'{self.compact_configuration_upload_provider.node.path}/framework-onEvent/Resource',
            [
                {'id': 'AwsSolutions-L1', 'reason': 'We do not control this runtime'},
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'This function is only run at deploy time, by CloudFormation and has no need for '
                    'concurrency limits.',
                },
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This is a synchronous function run at deploy time. It does not need a DLQ',
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'We may choose to move our lambdas into private VPC subnets in a future enhancement',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_provider.node.path}'
            f'/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_provider.node.path}/framework-onEvent/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],  # noqa: E501 line-too-long
                    'reason': 'This policy is appropriate for the log retention lambda',
                },
            ],
        )

        self.compact_configuration_uploader_custom_resource = CustomResource(
            scope,
            'CompactConfigurationUploadCustomResource',
            resource_type='Custom::CompactConfigurationUpload',
            service_token=self.compact_configuration_upload_provider.service_token,
            properties={
                # passing this as a property to the custom resource so that the lambda can access it
                'compact_configuration': self._generate_compact_configuration_json_string(
                    environment_name, environment_context
                ),
            },
        )

    def _is_sandbox_environment(self) -> bool:
        """Check if the current environment is a sandbox environment."""
        return self.node.try_get_context('sandbox') is True

    def _configuration_is_active_for_environment(self, environment_name: str, active_environments: list[str]) -> bool:
        """Check if the compact configuration is active in the given environment."""
        return environment_name in active_environments or self._is_sandbox_environment()

    def _generate_compact_configuration_json_string(self, environment_name: str, environment_context: dict) -> str:
        """Currently, all configuration for compacts and jurisdictions is hardcoded in the compact-config directory.
        This reads the YAML configuration files and generates a JSON string of all the configuration objects that
        should be uploaded into the provider table.
        """
        stack = Stack.of(self)
        # This object consists of two attributes: compacts and jurisdictions.
        # 'compacts' is a list of top level compact configuration files converted into JSON.
        # 'jurisdictions' is a dictionary of jurisdiction configuration files for a specific
        # compact, converted into JSON.
        uploader_input = {'compacts': [], 'jurisdictions': {}}

        # Read all compact configuration YAML files from top level compact-config directory
        for compact_config_file in os.listdir('compact-config'):
            if compact_config_file.endswith('.yml'):
                with open(os.path.join('compact-config', compact_config_file)) as f:
                    # convert YAML to JSON
                    formatted_compact = yaml.safe_load(f)
                    # if running in sandbox, add the environment name to the registration list
                    # so registration is enabled by default
                    if self._is_sandbox_environment():
                        formatted_compact['licenseeRegistrationEnabledForEnvironments'].append(environment_name)
                    # only include the compact configuration if it is active in the environment
                    if self._configuration_is_active_for_environment(
                        environment_name,
                        formatted_compact['activeEnvironments'],
                    ):
                        uploader_input['compacts'].append(formatted_compact)

        # Read all jurisdiction configuration YAML files from each active compact directory
        for compact in uploader_input['compacts']:
            compact_abbr = compact['compactAbbr']
            uploader_input['jurisdictions'][compact_abbr] = []
            for jurisdiction_config_file in os.listdir(os.path.join('compact-config', compact_abbr)):
                if jurisdiction_config_file.endswith('.yml'):
                    with open(os.path.join('compact-config', compact_abbr, jurisdiction_config_file)) as f:
                        # convert YAML to JSON
                        formatted_jurisdiction = yaml.safe_load(f)
                        # if running in sandbox, add the environment name to the registration list
                        # so registration is enabled by default
                        if self._is_sandbox_environment():
                            formatted_jurisdiction['licenseeRegistrationEnabledForEnvironments'].append(
                                environment_name
                            )
                        # only include the jurisdiction configuration if it is active in the environment
                        if self._configuration_is_active_for_environment(
                            environment_name,
                            formatted_jurisdiction['activeEnvironments'],
                        ):
                            formatted_jurisdiction = self._apply_jurisdiction_configuration_overrides(
                                formatted_jurisdiction, environment_context
                            )
                            self._validate_jurisdiction_configuration(
                                compact_abbr=compact_abbr,
                                jurisdiction=formatted_jurisdiction,
                                license_types_for_compact=stack.license_types[compact_abbr],
                            )
                            uploader_input['jurisdictions'][compact_abbr].append(formatted_jurisdiction)

        return json.dumps(uploader_input)

    def _apply_jurisdiction_configuration_overrides(self, jurisdiction: dict, environment_context: dict) -> dict:
        """Apply overrides to the jurisdiction configuration, based on any overrides set in environment context"""
        if 'jurisdiction_configuration_overrides' in environment_context.keys():
            jurisdiction.update(environment_context['jurisdiction_configuration_overrides'])
        return jurisdiction

    def _validate_jurisdiction_configuration(
        self, compact_abbr: str, jurisdiction: dict, license_types_for_compact: list[dict]
    ):
        """Do some basic jurisdiction configuration validation to catch some easy mistakes early"""
        if not jurisdiction.get('jurisdictionOperationsTeamEmails', []):
            raise ValueError(
                f'jurisdictionOperationsTeamEmails is required for jurisdiction {jurisdiction["postalAbbreviation"]}'
            )

        # Ensure all license types are covered
        if jurisdiction.get('privilegeFees'):
            defined_license_types_list = [fee['licenseTypeAbbreviation'] for fee in jurisdiction['privilegeFees']]
            defined_license_types_set = set(defined_license_types_list)
            compact_license_type_abbreviations = set([lt['abbreviation'] for lt in license_types_for_compact])

            missing_license_types = compact_license_type_abbreviations - defined_license_types_set
            if missing_license_types:
                raise ValueError(
                    f'Jurisdiction {jurisdiction["postalAbbreviation"]} in Compact {compact_abbr} '
                    f'is missing license fees for the following license types: {", ".join(missing_license_types)}'
                )

            # Check for duplicate license types
            if len(defined_license_types_list) != len(defined_license_types_set):
                raise ValueError(
                    f'Jurisdiction {jurisdiction["postalAbbreviation"]} in Compact {compact_abbr} '
                    f'has duplicate license type fees'
                )

            # Check for unknown license types
            unknown_license_types = defined_license_types_set - compact_license_type_abbreviations
            if unknown_license_types:
                raise ValueError(
                    f'Jurisdiction {jurisdiction["postalAbbreviation"]} in Compact {compact_abbr} '
                    f'defines fees for unknown license types: {", ".join(unknown_license_types)}'
                )
        else:
            # Neither privilegeFees nor jurisdictionFee is defined
            raise ValueError(
                f'Jurisdiction {jurisdiction["postalAbbreviation"]} in compact {compact_abbr} must define privilegeFees'
            )
