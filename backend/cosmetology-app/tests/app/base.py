import json
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from unittest.mock import patch

from aws_cdk.assertions import Annotations, Match, Template
from aws_cdk.aws_apigateway import CfnGatewayResponse, CfnMethod
from aws_cdk.aws_cognito import CfnUserPool, CfnUserPoolClient, CfnUserPoolDomain, CfnUserPoolResourceServer
from aws_cdk.aws_dynamodb import CfnTable
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_kms import CfnKey
from aws_cdk.aws_lambda import CfnEventSourceMapping
from aws_cdk.aws_sqs import CfnQueue
from common_constructs.stack import Stack

from app import CompactConnectApp
from common_constructs.backup_plan import CCBackupPlan
from pipeline import BackendStage
from stacks.api_stack import ApiStack
from stacks.persistent_stack import PersistentStack
from stacks.state_auth import StateAuthStack


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
        cls._overwrite_snapshots = False
        cls.set_overwrite_snapshots()

        cls.context = cls.get_context()
        cls.app = _app_synthesizer.get_app(cls.context)

    @classmethod
    def set_overwrite_snapshots(cls):
        """
        Allow environment variable to force snapshot comparisons to overwrite the snapshot

        ```
        OVERWRITE_SNAPSHOTS=true pytest tests
        ```
        """
        cls._overwrite_snapshots = os.environ.get('OVERWRITE_SNAPSHOTS', 'false').lower() == 'true'

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

    def _inspect_state_auth_stack(
        self,
        state_auth_stack: StateAuthStack,
    ):
        with self.subTest(state_auth_stack.stack_name):
            state_auth_stack_template = Template.from_stack(state_auth_stack)

            # Basic resource count validation
            state_auth_stack_template.resource_count_is(CfnUserPool.CFN_RESOURCE_TYPE_NAME, 1)
            state_auth_stack_template.resource_count_is(
                CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME, 0
            )  # Manual provisioning
            state_auth_stack_template.resource_count_is('AWS::Cognito::UserPoolDomain', 1)

            # Fundamental security configuration
            state_auth_stack_template.has_resource_properties(
                CfnUserPool.CFN_RESOURCE_TYPE_NAME,
                {
                    'AdminCreateUserConfig': {
                        'AllowAdminCreateUserOnly': True,
                    },
                    'Policies': {
                        'PasswordPolicy': {
                            'MinimumLength': 32,
                            'RequireNumbers': True,
                            'RequireLowercase': True,
                            'RequireUppercase': True,
                            'RequireSymbols': True,
                            'TemporaryPasswordValidityDays': 1,
                        },
                    },
                },
            )
            state_auth_stack_template.has_resource(CfnUserPoolDomain.CFN_RESOURCE_TYPE_NAME, {})
            state_auth_stack_template.has_resource(CfnUserPoolResourceServer.CFN_RESOURCE_TYPE_NAME, {})

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

            # ensure we have one user pool defined in persistent stack for staff users
            persistent_stack_template.resource_count_is(CfnUserPool.CFN_RESOURCE_TYPE_NAME, 1)

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
        disaster_recovery_lambda_role_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.disaster_recovery_lambda_role.node.default_child
        )
        disaster_recovery_step_function_role_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.disaster_recovery_step_function_role.node.default_child
        )

        # Build the expected PrincipalArn array - always includes 5 roles, plus optional backup role
        # Note: SSN backup role reference may be a nested stack output, so we use Match.any_value() for flexibility
        principal_arn_array = [
            {'Fn::GetAtt': [ingest_role_logical_id, 'Arn']},
            {'Fn::GetAtt': [license_upload_role_logical_id, 'Arn']},
            {'Fn::GetAtt': [api_query_role_logical_id, 'Arn']},
            {'Fn::GetAtt': [disaster_recovery_lambda_role_logical_id, 'Arn']},
            {'Fn::GetAtt': [disaster_recovery_step_function_role_logical_id, 'Arn']},
        ]
        if persistent_stack.environment_context['backup_enabled']:
            # if backup is enabled, we add an additional principal arn for the backup role to the SSN policy to
            # perform backups on data
            principal_arn_array.append(Match.any_value())  # SSN backup role reference (may be nested stack output)

        # Ensure our SSN Key is locked down by resource policy
        persistent_stack_template.has_resource(
            CfnKey.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'KeyPolicy': {
                        'Statement': Match.array_with(
                            [
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
                                            'aws:PrincipalArn': principal_arn_array,
                                            'aws:PrincipalServiceName': [
                                                'dynamodb.amazonaws.com',
                                                'events.amazonaws.com',
                                            ],
                                        }
                                    },
                                    'Effect': 'Deny',
                                    'Principal': '*',
                                    'Resource': '*',
                                },
                            ]
                        ),
                        'Version': '2012-10-17',
                    }
                }
            },
        )

        persistent_stack_template.has_resource(
            CfnTable.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    # This naming convention is important for opting into future CloudTrail organization access logging
                    # don't remove the -DateEventsLog suffix
                    'TableName': 'ssn-table-DataEventsLog',
                    'ResourcePolicy': {
                        'PolicyDocument': {
                            'Statement': Match.array_with(
                                [
                                    {
                                        'Effect': 'Deny',
                                        'Principal': '*',
                                        'Resource': '*',
                                        'Action': 'dynamodb:CreateBackup',
                                        'Condition': {
                                            'StringNotEquals': {'aws:PrincipalServiceName': 'dynamodb.amazonaws.com'}
                                        },
                                    },
                                    {
                                        'Effect': 'Deny',
                                        'Principal': '*',
                                        'Resource': '*',
                                        'Action': [
                                            'dynamodb:BatchGetItem',
                                            'dynamodb:BatchWriteItem',
                                            'dynamodb:PartiQL*',
                                            'dynamodb:Scan',
                                        ],
                                        'Condition': {
                                            'StringNotEquals': {
                                                'aws:PrincipalServiceName': 'dynamodb.amazonaws.com',
                                                'aws:PrincipalArn': Match.any_value(),
                                            }
                                        },
                                    },
                                    {
                                        'Action': ['dynamodb:ConditionCheckItem', 'dynamodb:GetItem', 'dynamodb:Query'],
                                        'Effect': 'Deny',
                                        'Principal': '*',
                                        'NotResource': Match.string_like_regexp(
                                            f'arn:aws:dynamodb:{persistent_stack.region}:{persistent_stack.account}:table/ssn-table-DataEventsLog/index/ssnIndex'
                                        ),
                                    },
                                ]
                            )
                        }
                    },
                    'SSESpecification': {
                        'KMSMasterKeyId': {'Fn::GetAtt': [ssn_key_logical_id, 'Arn']},
                        'SSEEnabled': True,
                        'SSEType': 'KMS',
                    },
                }
            },
        )

    def _inspect_backup_resources(self, persistent_stack: PersistentStack, persistent_stack_template: Template):
        """Validate that backup resources are created for tables and buckets with backup plans."""
        from aws_cdk.aws_backup import CfnBackupPlan, CfnBackupSelection

        # if in env with backup_enabled, Should have 6 backup plans, 6 backup selections:
        # - provider table
        # - SSN table
        # - compact config table
        # - data event table
        # - staff users table
        # - staff cognito user backup
        # Every other environment should be 0

        if persistent_stack.environment_context['backup_enabled']:
            persistent_stack_template.resource_count_is(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME, 6)
            persistent_stack_template.resource_count_is(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME, 6)

            for plan in [
                persistent_stack.provider_table.backup_plan,
                persistent_stack.ssn_table.backup_plan,
                persistent_stack.compact_configuration_table.backup_plan,
                persistent_stack.data_event_table.backup_plan,
                persistent_stack.staff_users.user_table.backup_plan,
                persistent_stack.staff_users.backup_system.backup_plan,
            ]:
                self.assertIsInstance(plan, CCBackupPlan)
        else:
            persistent_stack_template.resource_count_is(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME, 0)
            persistent_stack_template.resource_count_is(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME, 0)

            # Verify that backup plans are None when backups are disabled
            self.assertIsNone(persistent_stack.provider_table.backup_plan)
            self.assertIsNone(persistent_stack.ssn_table.backup_plan)
            self.assertIsNone(persistent_stack.compact_configuration_table.backup_plan)
            self.assertIsNone(persistent_stack.data_event_table.backup_plan)
            self.assertIsNone(persistent_stack.staff_users.user_table.backup_plan)
            self.assertIsNone(persistent_stack.staff_users.backup_system)

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
        self._check_no_stack_annotations(stage.api_lambda_stack)
        self._check_no_stack_annotations(stage.api_stack)
        self._check_no_stack_annotations(stage.disaster_recovery_stack)
        self._check_no_stack_annotations(stage.event_listener_stack)
        self._check_no_stack_annotations(stage.feature_flag_stack)
        self._check_no_stack_annotations(stage.ingest_stack)
        self._check_no_stack_annotations(stage.managed_login_stack)
        self._check_no_stack_annotations(stage.persistent_stack)
        self._check_no_stack_annotations(stage.state_api_stack)
        self._check_no_stack_annotations(stage.state_auth_stack)
        # These are only present if a hosted zone is configured
        if stage.persistent_stack.hosted_zone:
            self._check_no_stack_annotations(stage.notification_stack)
            self._check_no_stack_annotations(stage.reporting_stack)
        # No backup stack here, because nexted stack annotations are checked in the parent stack

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
            ('api_lambda_stack', stage.api_lambda_stack),
            ('api_stack', stage.api_stack),
            ('backup_infrastructure_stack', stage.backup_infrastructure_stack),
            ('disaster_recovery_stack', stage.disaster_recovery_stack),
            ('event_listener_stack', stage.event_listener_stack),
            ('feature_flag_stack', stage.feature_flag_stack),
            ('ingest_stack', stage.ingest_stack),
            ('managed_login_stack', stage.managed_login_stack),
            ('persistent_stack', stage.persistent_stack),
            ('state_api_stack', stage.state_api_stack),
            ('state_auth_stack', stage.state_auth_stack),
        ]
        if stage.persistent_stack.hosted_zone:
            stacks_to_check.extend(
                [
                    ('notification_stack', stage.notification_stack),
                    ('reporting_stack', stage.reporting_stack),
                ]
            )

        for _stack_name, stack in stacks_to_check:
            if stack is None:
                continue
            with self.subTest(f'Resource Count: {stack.stack_name}'):
                resource_count = self._count_stack_resources(stack)

                if resource_count > 475:
                    self.fail(
                        f'{_stack_name} has {resource_count} resources, which exceeds the '
                        'error threshold of 475. Consider splitting this stack or reducing resource count.'
                    )
                elif resource_count > 400:
                    sys.stderr.write(
                        f'WARNING: {_stack_name} has {resource_count} resources, which exceeds the '
                        'warning threshold of 400. Consider monitoring for future growth.\n'
                    )

                # Also log the count for visibility in test output
                sys.stdout.write(f'INFO: {_stack_name} has {resource_count} resources\n')

    def compare_snapshot(self, actual: Mapping | list, snapshot_name: str, overwrite_snapshot: bool = False):
        """
        Compare the actual dictionary to the snapshot with the given name.
        If overwrite_snapshot is True, overwrite the snapshot with the actual data.
        """
        # Let class attribute force true
        overwrite_snapshot = overwrite_snapshot or self._overwrite_snapshots

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
