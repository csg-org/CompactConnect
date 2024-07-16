from aws_cdk import RemovalPolicy
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.bucket import Bucket
from common_constructs.github_actions_access import GitHubActionsAccess
from common_constructs.stack import Stack
from stacks.persistent_stack import PersistentStack
from stacks.ui_stack.distribution import UIDistribution


class UIStack(Stack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            github_repo_string: str,
            persistent_stack: PersistentStack,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)
        ui_bucket = Bucket(
            self, 'UIBucket',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            server_access_logs_bucket=persistent_stack.access_logs_bucket
        )
        NagSuppressions.add_resource_suppressions(
            ui_bucket,
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'This bucket contains built files that are replaced each deploy of the UI. We have no'
                    ' desire for the resilience of bucket replication for this data.'
                },
                {
                    'id': 'HIPAA.Security-S3DefaultEncryptionKMS',
                    'reason': 'The data in this bucket is public web app static files. Default S3 encryption is'
                    ' more than enough for protecting this data.'
                },
                {
                    'id': 'HIPAA.Security-S3BucketVersioningEnabled',
                    'reason': 'This bucket contains built files that are replaced each deploy. We have no '
                    'desire for the resilience of versioning'
                }
            ]
        )

        self.distribution = UIDistribution(
            self, 'UIDistribution',
            ui_bucket=ui_bucket,
            persistent_stack=persistent_stack
        )

        # Configure permission for GitHub Actions to deploy the UI
        github_actions = GitHubActionsAccess(
            self, 'GitHubActionsAccess',
            github_repo_string=github_repo_string,
            role_name='github_ui_push'
        )
        self.distribution.grant_create_invalidation(github_actions)
        self.distribution.grant(github_actions, 'cloudfront:GetInvalidation')
        ui_bucket.grant_read_write(github_actions)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            path=f'{github_actions.node.path}/Role/DefaultPolicy',
            suppressions=[{
                'id': 'AwsSolutions-IAM5',
                'reason': 'The wild-carded actions and resources in this policy are still scoped specifically to the'
                ' bucket and actions needed for this principal to deploy the UI to this infrastructure'
            }]
        )
