from aws_cdk import Stage, Environment
from constructs import Construct

from common_constructs.stack import StandardTags
from stacks.api_stack import ApiStack
from stacks.persistent_stack import PersistentStack
from stacks.ui_stack import UIStack


class BackendStage(Stage):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            app_name: str,
            environment_name: str,
            environment_context: dict,
            github_repo_string: str,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        standard_tags = StandardTags(
            **self.node.get_context('tags'),
            environment=environment_name
        )

        environment = Environment(
            account=environment_context['account_id'],
            region=environment_context['region']
        )

        self.persistent_stack = PersistentStack(
            self, 'PersistentStack',
            env=environment,
            standard_tags=standard_tags,
            app_name=app_name,
            environment_name=environment_name
        )

        self.ui_stack = UIStack(
            self, 'UIStack',
            env=environment,
            standard_tags=standard_tags,
            github_repo_string=github_repo_string,
            persistent_stack=self.persistent_stack
        )

        self.api_stack = ApiStack(
            self, 'APIStack',
            env=environment,
            standard_tags=standard_tags,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack
        )
