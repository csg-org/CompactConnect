import os
import json
import yaml

from aws_cdk import Duration, Stack, CustomResource
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from aws_cdk.aws_kms import IKey
from common_constructs.python_function import PythonFunction

from constructs import Construct


from .provider_table import ProviderTable


class CompactConfigurationUpload(Construct):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            table: ProviderTable,
            master_key: IKey,
            environment_name: str,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.compact_configuration_upload_function = PythonFunction(
            scope, 'CompactConfigurationUploadFunction',
            entry=os.path.join('lambdas', 'custom-resources', 'handlers'),
            index='compact_config_uploader.py',
            handler='on_event',
            description='Uploads contents of compact-config directory to the provider Dynamo table',
            timeout=Duration.minutes(10),
            log_retention=RetentionDays.THREE_MONTHS,
            environment={
                'PROVIDER_TABLE_NAME': table.table_name,
            }
        )

        # grant lambda access to the provider table
        table.grant_read_write_data(self.compact_configuration_upload_function)
        # grant lambda access to the KMS key
        master_key.grant_encrypt_decrypt(self.compact_configuration_upload_function)


        compact_configuration_upload_provider = Provider(
            scope, 'CompactConfigurationUploadProvider',
            on_event_handler=self.compact_configuration_upload_function,
            log_retention=RetentionDays.ONE_DAY
        )
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            f'{compact_configuration_upload_provider.node.path}/framework-onEvent/Resource', [
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
                }
            ]
        )

        self.compact_configuration_uploader_custom_resource = CustomResource(
            scope, 'CompactConfigurationUploadCustomResource',
            resource_type='Custom::CompactConfigurationUpload',
            service_token=compact_configuration_upload_provider.service_token,
            properties={
                # passing this as a property to the custom resource so that the lambda can access it
                'compact_configuration': self._generate_compact_configuration_json_string(),
                # this defines the environment that the lambda is running in so it only uploads configuration
                # which is active in that environment
                'environment_name': environment_name
            }
        )

    def _generate_compact_configuration_json_string(self):
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
                    uploader_input['compacts'].append(yaml.safe_load(f))

        # Read all jurisdiction configuration YAML files from each compact directory
        for compact in uploader_input['compacts']:
            uploader_input['jurisdictions'][compact['compactName']] = []
            for jurisdiction_config_file in os.listdir(os.path.join('compact-config', compact['compactName'])):
                if jurisdiction_config_file.endswith('.yml'):
                    with open(os.path.join('compact-config', compact['compactName'], jurisdiction_config_file), 'r') as f:
                        # convert YAML to JSON
                        uploader_input['jurisdictions'][compact['compactName']].append(yaml.safe_load(f))


        return json.dumps(uploader_input)
