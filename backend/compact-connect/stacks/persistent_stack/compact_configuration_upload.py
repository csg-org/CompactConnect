import os
import json
import yaml

from aws_cdk import Duration, Stack, CustomResource
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.custom_resources import Provider
from aws_cdk.aws_kms import IKey
from common_constructs.python_function import PythonFunction
from cdk_nag import NagSuppressions

from constructs import Construct

from .compact_configuration_table import CompactConfigurationTable


class CompactConfigurationUpload(Construct):
    """
    Custom resource to upload compact configuration data to the compact configuration table.
    """
    def __init__(
            self, scope: Construct, construct_id: str, *,
            table: CompactConfigurationTable,
            master_key: IKey,
            environment_name: str,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.compact_configuration_upload_function = PythonFunction(
            scope, 'CompactConfigurationUploadFunction',
            entry=os.path.join('lambdas', 'custom-resources'),
            index=os.path.join('handlers', 'compact_config_uploader.py'),
            handler='on_event',
            description='Uploads contents of compact-config directory to the compact configuration Dynamo table',
            timeout=Duration.minutes(10),
            log_retention=RetentionDays.THREE_MONTHS,
            environment={
                'COMPACT_CONFIGURATION_TABLE_NAME': table.table_name,
            }
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
                              'and is scoped to one table and encryption key.'
                }
            ]
        )


        self.compact_configuration_upload_provider = Provider(
            scope, 'CompactConfigurationUploadProvider',
            on_event_handler=self.compact_configuration_upload_function,
            log_retention=RetentionDays.ONE_DAY
        )
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            f'{self.compact_configuration_upload_provider.node.path}/framework-onEvent/Resource', [
                {
                    'id': 'AwsSolutions-L1',
                    'reason': 'We do not control this runtime'
                },
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'This function is only run at deploy time, by CloudFormation and has no need for '
                              'concurrency limits.'
                },
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This is a synchronous function run at deploy time. It does not need a DLQ'
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'We may choose to move our lambdas into private VPC subnets in a future enhancement'
                },
            ]
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_provider.node.path}'
                 f'/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_provider.node.path}/framework-onEvent/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'applies_to':
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
                    'reason': 'This policy is appropriate for the log retention lambda'
                }
            ]
        )

        self.compact_configuration_uploader_custom_resource = CustomResource(
            scope, 'CompactConfigurationUploadCustomResource',
            resource_type='Custom::CompactConfigurationUpload',
            service_token=self.compact_configuration_upload_provider.service_token,
            properties={
                # passing this as a property to the custom resource so that the lambda can access it
                'compact_configuration': self._generate_compact_configuration_json_string(environment_name)
            }
        )

    def _configuration_is_active_for_environment(self, environment_name: str, active_environments: list[str]) -> bool:
        """
        Check if the compact configuration is active in the given environment.
        """
        return environment_name in active_environments or self.node.try_get_context('sandbox') == 'true'

    def _generate_compact_configuration_json_string(self, environment_name: str) -> str:
        """
        Currently, all configuration for compacts and jurisdictions is hardcoded in the compact-config directory.
        This reads the YAML configuration files and generates a JSON string of all the configuration objects that
        should be uploaded into the provider table.
        """

        # This object consists of two attributes: compacts and jurisdictions.
        # 'compacts' is a list of top level compact configuration files converted into JSON.
        # 'jurisdictions' is a dictionary of jurisdiction configuration files for a specific
        # compact, converted into JSON.
        uploader_input = {
            "compacts": [],
            "jurisdictions": {}
        }

        # Read all compact configuration YAML files from top level compact-config directory
        for compact_config_file in os.listdir('compact-config'):
            if compact_config_file.endswith('.yml'):
                with open(os.path.join('compact-config', compact_config_file), 'r') as f:
                    # convert YAML to JSON
                    formatted_compact = yaml.safe_load(f)
                    # only include the compact configuration if it is active in the environment
                    if self._configuration_is_active_for_environment(environment_name,
                                                                     formatted_compact['activeEnvironments']):
                        uploader_input['compacts'].append(formatted_compact)

        # Read all jurisdiction configuration YAML files from each active compact directory
        for compact in uploader_input['compacts']:
            compact_name = compact['compactName']
            uploader_input['jurisdictions'][compact_name] = []
            for jurisdiction_config_file in os.listdir(os.path.join('compact-config', compact['compactName'])):
                if jurisdiction_config_file.endswith('.yml'):
                    with open(os.path.join('compact-config', compact_name, jurisdiction_config_file), 'r') as f:
                        # convert YAML to JSON
                        formatted_jurisdiction = yaml.safe_load(f)
                        # only include the jurisdiction configuration if it is active in the environment
                        if self._configuration_is_active_for_environment(environment_name,
                                                                         formatted_jurisdiction['activeEnvironments']):
                            uploader_input['jurisdictions'][compact_name].append(formatted_jurisdiction)


        return json.dumps(uploader_input)
