import json
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from unittest.mock import patch

from app import CompactConnectApp
from aws_cdk.assertions import Annotations, Match, Template
from aws_cdk.aws_apigateway import CfnGatewayResponse, CfnMethod
from aws_cdk.aws_cloudfront import CfnDistribution
from aws_cdk.aws_cognito import CfnUserPool, CfnUserPoolClient
from aws_cdk.aws_dynamodb import CfnTable
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_kms import CfnKey
from aws_cdk.aws_lambda import CfnEventSourceMapping, CfnFunction
from aws_cdk.aws_s3 import CfnBucket
from aws_cdk.aws_sqs import CfnQueue
from common_constructs.stack import Stack
from pipeline import BackendStage, FrontendStage
from stacks.api_stack import ApiStack
from stacks.frontend_deployment_stack import FrontendDeploymentStack
from stacks.persistent_stack import PersistentStack
from stacks.provider_users import ProviderUsersStack


class _AppSynthesizer:
    """
    A helper class to cache apps based on context.
    This is useful to avoid re-synthesizing the app for each test.
    """

    def __init__(self):
        super().__init__()
        self._cached_apps: dict[str, CompactConnectApp] = {}

    def get_app(self, context: Mapping) -> CompactConnectApp:
        context_hash = self._get_context_hash(context)
        if context_hash not in self._cached_apps.keys():
            self._cached_apps[context_hash] = CompactConnectApp(context=context)
        return self._cached_apps[context_hash]

    def _get_context_hash(self, context: Mapping) -> str:
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

    def _inspect_provider_users_stack(
        self,
        provider_users_stack: ProviderUsersStack,
        *,
        domain_name: str = None,
        allow_local_ui: bool = False,
        local_ui_port: str = None,
    ):
        with self.subTest(provider_users_stack.stack_name):
            # Make sure our local port ui setting overrides the default
            provider_users_stack_template = Template.from_stack(provider_users_stack)
            callbacks = []
            if domain_name is not None:
                callbacks.append(f'https://{domain_name}/auth/callback')
            if allow_local_ui:
                # 3018 is default
                local_ui_port = '3018' if not local_ui_port else local_ui_port
                callbacks.append(f'http://localhost:{local_ui_port}/auth/callback')

            # Ensure our provider user pool is created with expected custom attributes
            provider_users_user_pool = self.get_resource_properties_by_logical_id(
                provider_users_stack.get_logical_id(provider_users_stack.provider_users.node.default_child),
                provider_users_stack_template.find_resources(CfnUserPool.CFN_RESOURCE_TYPE_NAME),
            )

            # assert that both custom attributes are in schema
            self.assertIn(
                {'AttributeDataType': 'String', 'Mutable': False, 'Name': 'providerId'},
                provider_users_user_pool['Schema'],
            )
            self.assertIn(
                {'AttributeDataType': 'String', 'Mutable': False, 'Name': 'compact'}, provider_users_user_pool['Schema']
            )

            # ensure we have one user pool for providers
            provider_users_stack_template.resource_count_is(CfnUserPool.CFN_RESOURCE_TYPE_NAME, 1)

            # Ensure our Provider user pool app client is created with expected values
            provider_users_user_pool_app_client = self.get_resource_properties_by_logical_id(
                provider_users_stack.get_logical_id(provider_users_stack.provider_users.ui_client.node.default_child),
                provider_users_stack_template.find_resources(CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME),
            )

            self.assertEqual(provider_users_user_pool_app_client['CallbackURLs'], callbacks)
            self.assertEqual(
                provider_users_user_pool_app_client['ReadAttributes'],
                ['custom:compact', 'custom:providerId', 'email'],
            )
            self.assertEqual(provider_users_user_pool_app_client['WriteAttributes'], ['email'])

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
            # TODO - this will go down to one when we finish provider user migration  # noqa: FIX002
            persistent_stack_template.resource_count_is(CfnUserPool.CFN_RESOURCE_TYPE_NAME, 2)

            # Ensure our Staff user pool app client is configured with the expected callbacks and read/write attributes
            staff_users_user_pool_app_client = self.get_resource_properties_by_logical_id(
                persistent_stack.get_logical_id(persistent_stack.staff_users.ui_client.node.default_child),
                persistent_stack_template.find_resources(CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME),
            )
            self.assertEqual(staff_users_user_pool_app_client['CallbackURLs'], callbacks)
            self.assertEqual(staff_users_user_pool_app_client['ReadAttributes'], ['email'])
            self.assertEqual(staff_users_user_pool_app_client['WriteAttributes'], ['email'])

        self._inspect_data_events_table(persistent_stack, persistent_stack_template)
        self._inspect_ssn_table(persistent_stack, persistent_stack_template)
        self._inspect_backup_resources(persistent_stack, persistent_stack_template)

    def _inspect_ssn_table(self, persistent_stack: PersistentStack, persistent_stack_template: Template):
        ssn_key_logical_id = persistent_stack.get_logical_id(persistent_stack.ssn_table.key.node.default_child)
        ingest_role_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.ingest_role.node.default_child
        )
        license_upload_role_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.license_upload_role.node.default_child
        )
        api_query_role_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.api_query_role.node.default_child
        )
        ssn_backup_role_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.backup_service_role.node.default_child
        )
        ssn_table_template = self.get_resource_properties_by_logical_id(
            persistent_stack.get_logical_id(persistent_stack.ssn_table.node.default_child),
            persistent_stack_template.find_resources(CfnTable.CFN_RESOURCE_TYPE_NAME),
        )
        ssn_key_template = self.get_resource_properties_by_logical_id(
            ssn_key_logical_id, persistent_stack_template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
        )
        # This naming convention is important for opting into future CloudTrail organization access logging
        self.assertTrue(ssn_table_template['TableName'].endswith('-DataEventsLog'))
        # Ensure our SSN Key is locked down by resource policy
        # Note: SSN backup role reference may be a nested stack output, so we use Match.any_value() for flexibility
        expected_policy = {
            'Statement': [
                {
                    'Action': 'kms:*',
                    'Effect': 'Allow',
                    'Principal': {'AWS': f'arn:aws:iam::{persistent_stack.account}:root'},
                    'Resource': '*',
                },
                {
                    'Action': ['kms:Decrypt', 'kms:Encrypt', 'kms:GenerateDataKey*', 'kms:ReEncrypt*'],
                    'Condition': {
                        'StringNotEquals': {
                            'aws:PrincipalArn': [
                                {'Fn::GetAtt': [ingest_role_logical_id, 'Arn']},
                                {'Fn::GetAtt': [license_upload_role_logical_id, 'Arn']},
                                {'Fn::GetAtt': [api_query_role_logical_id, 'Arn']},
                                Match.any_value(),  # SSN backup role reference (may be nested stack output)
                            ],
                            'aws:PrincipalServiceName': ['dynamodb.amazonaws.com', 'events.amazonaws.com'],
                        }
                    },
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Resource': '*',
                },
            ],
            'Version': '2012-10-17',
        }

        # Validate the key policy structure matches our expected pattern
        actual_policy = ssn_key_template['KeyPolicy']
        self.assertEqual(len(expected_policy['Statement']), len(actual_policy['Statement']))

        # Check first statement (admin access) exactly
        self.assertEqual(expected_policy['Statement'][0], actual_policy['Statement'][0])

        # Check second statement structure (with flexible backup role reference)
        actual_second_stmt = actual_policy['Statement'][1]
        self.assertEqual(expected_policy['Statement'][1]['Action'], actual_second_stmt['Action'])
        self.assertEqual(expected_policy['Statement'][1]['Effect'], actual_second_stmt['Effect'])
        self.assertEqual(expected_policy['Statement'][1]['Principal'], actual_second_stmt['Principal'])
        self.assertEqual(expected_policy['Statement'][1]['Resource'], actual_second_stmt['Resource'])

        # Check condition structure but allow flexible backup role reference
        self.assertIn('StringNotEquals', actual_second_stmt['Condition'])
        self.assertIn('aws:PrincipalArn', actual_second_stmt['Condition']['StringNotEquals'])
        self.assertEqual(4, len(actual_second_stmt['Condition']['StringNotEquals']['aws:PrincipalArn']))
        self.assertEqual(
            expected_policy['Statement'][1]['Condition']['StringNotEquals']['aws:PrincipalServiceName'],
            actual_second_stmt['Condition']['StringNotEquals']['aws:PrincipalServiceName'],
        )
        # Ensure we're using our locked down KMS key for encryption
        self.assertEqual(
            ssn_table_template['SSESpecification'],
            {'KMSMasterKeyId': {'Fn::GetAtt': [ssn_key_logical_id, 'Arn']}, 'SSEEnabled': True, 'SSEType': 'KMS'},
        )
        self.compare_snapshot(
            ssn_table_template['ResourcePolicy']['PolicyDocument'],
            'SSN_TABLE_RESOURCE_POLICY',
            overwrite_snapshot=False,
        )

    def _inspect_backup_resources(self, persistent_stack: PersistentStack, persistent_stack_template: Template):
        """Validate that backup resources are created for tables with backup plans."""
        from aws_cdk.aws_backup import CfnBackupPlan, CfnBackupSelection

        # Should have 6 backup plans (provider, SSN, compact config, transaction history, data event, staff users)
        persistent_stack_template.resource_count_is(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME, 6)

        # Should have 6 backup selections (provider, SSN, compact config, transaction history, data event, staff users)
        persistent_stack_template.resource_count_is(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME, 6)

        # Validate provider table backup plan exists
        provider_backup_plan_logical_id = persistent_stack.get_logical_id(
            persistent_stack.provider_table.backup_plan.backup_plan.node.default_child
        )
        provider_backup_selection_logical_id = persistent_stack.get_logical_id(
            persistent_stack.provider_table.backup_plan.backup_selection.node.default_child
        )

        # Validate SSN table backup plan exists
        ssn_backup_plan_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.backup_plan.backup_plan.node.default_child
        )
        ssn_backup_selection_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.backup_plan.backup_selection.node.default_child
        )

        # Validate compact configuration table backup plan exists
        compact_config_backup_plan_logical_id = persistent_stack.get_logical_id(
            persistent_stack.compact_configuration_table.backup_plan.backup_plan.node.default_child
        )
        compact_config_backup_selection_logical_id = persistent_stack.get_logical_id(
            persistent_stack.compact_configuration_table.backup_plan.backup_selection.node.default_child
        )

        # Validate transaction history table backup plan exists
        transaction_history_backup_plan_logical_id = persistent_stack.get_logical_id(
            persistent_stack.transaction_history_table.backup_plan.backup_plan.node.default_child
        )
        transaction_history_backup_selection_logical_id = persistent_stack.get_logical_id(
            persistent_stack.transaction_history_table.backup_plan.backup_selection.node.default_child
        )

        # Validate data event table backup plan exists
        data_event_backup_plan_logical_id = persistent_stack.get_logical_id(
            persistent_stack.data_event_table.backup_plan.backup_plan.node.default_child
        )
        data_event_backup_selection_logical_id = persistent_stack.get_logical_id(
            persistent_stack.data_event_table.backup_plan.backup_selection.node.default_child
        )

        # Validate staff users table backup plan exists
        staff_users_backup_plan_logical_id = persistent_stack.get_logical_id(
            persistent_stack.staff_users.user_table.backup_plan.backup_plan.node.default_child
        )
        staff_users_backup_selection_logical_id = persistent_stack.get_logical_id(
            persistent_stack.staff_users.user_table.backup_plan.backup_selection.node.default_child
        )

        # Verify backup plan configurations exist
        provider_backup_plan = self.get_resource_properties_by_logical_id(
            provider_backup_plan_logical_id,
            persistent_stack_template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME),
        )
        ssn_backup_plan = self.get_resource_properties_by_logical_id(
            ssn_backup_plan_logical_id,
            persistent_stack_template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME),
        )
        compact_config_backup_plan = self.get_resource_properties_by_logical_id(
            compact_config_backup_plan_logical_id,
            persistent_stack_template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME),
        )
        transaction_history_backup_plan = self.get_resource_properties_by_logical_id(
            transaction_history_backup_plan_logical_id,
            persistent_stack_template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME),
        )
        data_event_backup_plan = self.get_resource_properties_by_logical_id(
            data_event_backup_plan_logical_id,
            persistent_stack_template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME),
        )
        staff_users_backup_plan = self.get_resource_properties_by_logical_id(
            staff_users_backup_plan_logical_id,
            persistent_stack_template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME),
        )

        # Verify backup selection configurations reference the correct tables
        provider_backup_selection = self.get_resource_properties_by_logical_id(
            provider_backup_selection_logical_id,
            persistent_stack_template.find_resources(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME),
        )
        ssn_backup_selection = self.get_resource_properties_by_logical_id(
            ssn_backup_selection_logical_id,
            persistent_stack_template.find_resources(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME),
        )
        compact_config_backup_selection = self.get_resource_properties_by_logical_id(
            compact_config_backup_selection_logical_id,
            persistent_stack_template.find_resources(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME),
        )
        transaction_history_backup_selection = self.get_resource_properties_by_logical_id(
            transaction_history_backup_selection_logical_id,
            persistent_stack_template.find_resources(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME),
        )
        data_event_backup_selection = self.get_resource_properties_by_logical_id(
            data_event_backup_selection_logical_id,
            persistent_stack_template.find_resources(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME),
        )
        staff_users_backup_selection = self.get_resource_properties_by_logical_id(
            staff_users_backup_selection_logical_id,
            persistent_stack_template.find_resources(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME),
        )

        # Validate that backup selections reference DynamoDB resources
        for selection_name, selection in [
            ('provider', provider_backup_selection),
            ('SSN', ssn_backup_selection),
            ('compact_config', compact_config_backup_selection),
            ('transaction_history', transaction_history_backup_selection),
            ('data_event', data_event_backup_selection),
            ('staff_users', staff_users_backup_selection),
        ]:
            self.assertIn(
                'BackupSelection', selection, f'{selection_name} backup selection should have BackupSelection'
            )
            self.assertIn(
                'Resources', selection['BackupSelection'], f'{selection_name} backup selection should have Resources'
            )

        # Verify backup plans have proper structure (environment-agnostic validation)
        for backup_plan, table_name in [
            (provider_backup_plan, 'provider'),
            (ssn_backup_plan, 'SSN'),
            (compact_config_backup_plan, 'compact_config'),
            (transaction_history_backup_plan, 'transaction_history'),
            (data_event_backup_plan, 'data_event'),
            (staff_users_backup_plan, 'staff_users'),
        ]:
            self.assertIn('BackupPlan', backup_plan)
            self.assertIn('BackupPlanRule', backup_plan['BackupPlan'])
            rules = backup_plan['BackupPlan']['BackupPlanRule']
            self.assertEqual(len(rules), 1, f'{table_name} table should have exactly one backup rule')

            rule = rules[0]
            # Verify basic structure without checking specific values (since they vary by environment)
            self.assertIn('ScheduleExpression', rule, f'{table_name} table backup rule should have a schedule')
            self.assertIn('Lifecycle', rule, f'{table_name} table backup rule should have lifecycle configuration')
            self.assertIn(
                'DeleteAfterDays', rule['Lifecycle'], f'{table_name} table backup should have retention period'
            )
            self.assertIn(
                'MoveToColdStorageAfterDays',
                rule['Lifecycle'],
                f'{table_name} table backup should have cold storage transition',
            )

            # Verify copy actions exist for cross-account replication
            self.assertIn(
                'CopyActions', rule, f'{table_name} table backup should have copy actions for cross-account replication'
            )
            self.assertEqual(len(rule['CopyActions']), 1, f'{table_name} table should have one copy action')

    def _inspect_data_events_table(self, persistent_stack: PersistentStack, persistent_stack_template: Template):
        # Ensure our DataEventTable and queues are created
        event_bus_logical_id = persistent_stack.get_logical_id(persistent_stack._data_event_bus.node.default_child)  # noqa: SLF001 private_member_access
        queue_logical_id = persistent_stack.get_logical_id(
            persistent_stack.data_event_table.event_processor.queue.node.default_child
        )
        dlq_logical_id = persistent_stack.get_logical_id(
            persistent_stack.data_event_table.event_processor.dlq.node.default_child
        )

        self.get_resource_properties_by_logical_id(
            persistent_stack.get_logical_id(persistent_stack.data_event_table.node.default_child),
            persistent_stack_template.find_resources(CfnTable.CFN_RESOURCE_TYPE_NAME),
        )
        self.get_resource_properties_by_logical_id(
            queue_logical_id,
            persistent_stack_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
        )
        self.get_resource_properties_by_logical_id(
            dlq_logical_id,
            persistent_stack_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
        )
        # Events from bus to queue
        rules = persistent_stack_template.find_resources(
            type=CfnRule.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'EventBusName': {'Ref': event_bus_logical_id},
                    'Targets': [
                        {
                            'Arn': {
                                'Fn::GetAtt': [
                                    queue_logical_id,
                                    'Arn',
                                ]
                            }
                        }
                    ],
                }
            },
        )
        self.assertEqual(1, len(rules))
        rule = [rule for rule in rules.values()][0]
        self.compare_snapshot(rule, 'DATA_EVENT_RULE', overwrite_snapshot=False)

        # Events from queue to lambda
        persistent_stack_template.has_resource(
            type=CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'EventSourceArn': {
                        'Fn::GetAtt': [
                            queue_logical_id,
                            'Arn',
                        ]
                    },
                    'FunctionName': {
                        'Ref': persistent_stack.get_logical_id(
                            persistent_stack.data_event_table.event_handler.node.default_child
                        )
                    },
                    'FunctionResponseTypes': ['ReportBatchItemFailures'],
                },
            },
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

            # This is what the auto-generated preflight CORS OPTIONS methods looks like. If we have one match
            # we probably have a ton, so we'll just check for the presence of one method that looks like this.
            api_template.has_resource(
                type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
                props={
                    'Properties': {
                        'HttpMethod': 'OPTIONS',
                        'Integration': {
                            'IntegrationResponses': [
                                {
                                    'ResponseParameters': {
                                        'method.response.header.Access-Control-Allow-Headers': (
                                            "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,"
                                            "X-Amz-User-Agent,cache-control'"
                                        ),
                                        'method.response.header.Access-Control-Allow-Origin': (
                                            f"'{api_stack.allowed_origins[0]}'"
                                        ),
                                        'method.response.header.Vary': "'Origin'",
                                        'method.response.header.Access-Control-Allow-Methods': (
                                            "'OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD'"
                                        ),
                                    },
                                    'StatusCode': '204',
                                }
                            ],
                            'RequestTemplates': {'application/json': '{ statusCode: 200 }'},
                            'Type': 'MOCK',
                        },
                        'MethodResponses': [
                            {
                                'ResponseParameters': {
                                    'method.response.header.Access-Control-Allow-Headers': True,
                                    'method.response.header.Access-Control-Allow-Origin': True,
                                    'method.response.header.Vary': True,
                                    'method.response.header.Access-Control-Allow-Methods': True,
                                },
                                'StatusCode': '204',
                            }
                        ],
                        'RestApiId': {'Ref': api_stack.get_logical_id(api_stack.api.node.default_child)},
                    }
                },
            )

        # The GatewayResponses we configure should have a single specific origin, unless we have more than one origin
        # in which case we should have the catch-all '*' origin.
        if len(api_stack.allowed_origins) > 1:
            api_template.has_resource(
                CfnGatewayResponse.CFN_RESOURCE_TYPE_NAME,
                props={
                    'Properties': {
                        'ResponseParameters': {'gatewayresponse.header.Access-Control-Allow-Origin': "'*'"},
                        'RestApiId': {'Ref': api_stack.get_logical_id(api_stack.api.node.default_child)},
                    },
                },
            )
        else:
            api_template.has_resource(
                CfnGatewayResponse.CFN_RESOURCE_TYPE_NAME,
                props={
                    'Properties': {
                        'ResponseParameters': {
                            'gatewayresponse.header.Access-Control-Allow-Origin': f"'{api_stack.allowed_origins[0]}'"
                        },
                        'RestApiId': {'Ref': api_stack.get_logical_id(api_stack.api.node.default_child)},
                    },
                },
            )

    def _check_no_stack_annotations(self, stack: Stack):
        with self.subTest(f'Security Rules: {stack.stack_name}'):
            errors = Annotations.from_stack(stack).find_error('*', Match.string_like_regexp('.*'))
            self.assertEqual(0, len(errors), msg='\n'.join(f'{err.id}: {err.entry.data.strip()}' for err in errors))

            warnings = Annotations.from_stack(stack).find_warning('*', Match.string_like_regexp('.*'))
            self.assertEqual(
                0, len(warnings), msg='\n'.join(f'{warn.id}: {warn.entry.data.strip()}' for warn in warnings)
            )

    def _check_no_backend_stage_annotations(self, stage: BackendStage):
        self._check_no_stack_annotations(stage.persistent_stack)
        self._check_no_stack_annotations(stage.api_stack)
        self._check_no_stack_annotations(stage.ingest_stack)
        self._check_no_stack_annotations(stage.transaction_monitoring_stack)
        # There is on reporting stack if no hosted zone is configured
        if stage.persistent_stack.hosted_zone:
            self._check_no_stack_annotations(stage.reporting_stack)

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

    def _check_backend_stage_resource_counts(self, stage: BackendStage):
        """
        Check resource counts for all stacks in a BackendStage and emit warnings/errors.

        Emits a warning if any stack has more than 400 resources.
        Fails the test if any stack has more than 475 resources.

        :param stage: The BackendStage containing stacks to check
        """
        stacks_to_check = [
            ('persistent_stack', stage.persistent_stack),
            ('api_stack', stage.api_stack),
            ('ingest_stack', stage.ingest_stack),
            ('transaction_monitoring_stack', stage.transaction_monitoring_stack),
        ]

        # Add reporting stack if it exists (only when hosted zone is configured)
        if stage.persistent_stack.hosted_zone:
            stacks_to_check.append(('reporting_stack', stage.reporting_stack))

        for stack_name, stack in stacks_to_check:
            with self.subTest(f'Resource Count: {stack.stack_name}'):
                resource_count = self._count_stack_resources(stack)

                if resource_count > 475:
                    self.fail(
                        f'{stack.stack_name} has {resource_count} resources, which exceeds the '
                        'error threshold of 475. Consider splitting this stack or reducing resource count.'
                    )
                elif resource_count > 400:
                    sys.stderr.write(
                        f'WARNING: {stack.stack_name} has {resource_count} resources, which exceeds the '
                        'warning threshold of 400. Consider monitoring for future growth.\n'
                    )

                # Also log the count for visibility in test output
                sys.stdout.write(f'INFO: {stack.stack_name} has {resource_count} resources\n')

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
