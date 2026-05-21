from unittest import TestCase

from aws_cdk import App, Stack
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_backup import BackupPlan, BackupResource, BackupVault, CfnBackupPlan, CfnBackupSelection
from aws_cdk.aws_iam import Role, ServicePrincipal
from aws_cdk.aws_kms import Key

from common_constructs.backup_plan import CCBackupPlan


class TestCCBackupPlan(TestCase):
    def setUp(self):
        self.app = App()
        self.stack = Stack(self.app, 'TestStack')
        self.key = Key(self.stack, 'Key')
        self.local_vault = BackupVault(self.stack, 'LocalVault', encryption_key=self.key)
        self.cross_account_vault = BackupVault.from_backup_vault_arn(
            self.stack,
            'CrossAccountVault',
            backup_vault_arn='arn:aws:backup:us-east-1:999999999999:backup-vault:remote-vault',
        )
        self.backup_role = Role(
            self.stack,
            'BackupRole',
            assumed_by=ServicePrincipal('backup.amazonaws.com'),
        )
        self.backup_policy = {
            'schedule': {'hour': '5', 'minute': '0'},
            'delete_after_days': 180,
            'cold_storage_after_days': 30,
        }
        self.resource = BackupResource.from_dynamo_db_table(
            Stack.of(self.stack).node.try_find_child('Dummy')  # placeholder; works as construct reference
        ) if False else None  # Use arn-based resource instead

    def _make_plan(self, **kwargs):
        from aws_cdk.aws_dynamodb import Attribute, AttributeType, Table

        table = Table(
            self.stack,
            'Table',
            partition_key=Attribute(name='pk', type=AttributeType.STRING),
        )
        return CCBackupPlan(
            self.stack,
            'Plan',
            backup_plan_name_prefix='test-resource',
            backup_resources=[BackupResource.from_dynamo_db_table(table)],
            backup_vault=self.local_vault,
            backup_service_role=self.backup_role,
            cross_account_backup_vault=self.cross_account_vault,
            backup_policy=self.backup_policy,
            **kwargs,
        )

    def test_backup_plan_name_uses_prefix(self):
        self._make_plan()

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBackupPlan.CFN_RESOURCE_TYPE_NAME,
            {
                'BackupPlan': Match.object_like(
                    {'BackupPlanName': 'test-resource-BackupPlan'}
                )
            },
        )

    def test_rule_uses_delete_after_from_policy(self):
        self._make_plan()

        template = Template.from_stack(self.stack)
        (plan,) = template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME).values()
        rule = plan['Properties']['BackupPlan']['BackupPlanRule'][0]
        self.assertEqual(180, rule['Lifecycle']['DeleteAfterDays'])

    def test_rule_uses_cold_storage_after_from_policy(self):
        self._make_plan()

        template = Template.from_stack(self.stack)
        (plan,) = template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME).values()
        rule = plan['Properties']['BackupPlan']['BackupPlanRule'][0]
        self.assertEqual(30, rule['Lifecycle']['MoveToColdStorageAfterDays'])

    def test_cross_account_copy_action_is_present(self):
        self._make_plan()

        template = Template.from_stack(self.stack)
        (plan,) = template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME).values()
        rule = plan['Properties']['BackupPlan']['BackupPlanRule'][0]
        copy_actions = rule.get('CopyActions', [])
        self.assertEqual(1, len(copy_actions))
        self.assertIn('arn:aws:backup:us-east-1:999999999999:backup-vault:remote-vault', str(copy_actions[0]))

    def test_copy_action_lifecycle_matches_primary_rule(self):
        self._make_plan()

        template = Template.from_stack(self.stack)
        (plan,) = template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME).values()
        rule = plan['Properties']['BackupPlan']['BackupPlanRule'][0]
        copy_action = rule['CopyActions'][0]
        self.assertEqual(180, copy_action['Lifecycle']['DeleteAfterDays'])
        self.assertEqual(30, copy_action['Lifecycle']['MoveToColdStorageAfterDays'])

    def test_backup_selection_uses_provided_role(self):
        self._make_plan()

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBackupSelection.CFN_RESOURCE_TYPE_NAME,
            {
                'BackupSelection': Match.object_like(
                    {
                        'SelectionName': 'test-resource-Selection',
                        'IamRoleArn': {'Fn::GetAtt': [self.stack.get_logical_id(self.backup_role.node.default_child), 'Arn']},
                    }
                )
            },
        )

    def test_backup_selection_includes_provided_resources(self):
        self._make_plan()

        template = Template.from_stack(self.stack)
        selections = template.find_resources(CfnBackupSelection.CFN_RESOURCE_TYPE_NAME)
        self.assertEqual(1, len(selections))
