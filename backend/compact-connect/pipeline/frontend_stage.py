from aws_cdk import Environment, Stage
from common_constructs.stack import StandardTags
from constructs import Construct
from stacks.frontend_deployment_stack import FrontendDeploymentStack


class FrontendStage(Stage):
    """
    Stage for deploying Frontend Resources
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        standard_tags = StandardTags(**self.node.get_context('tags'), environment=environment_name)
        environment = Environment(account=environment_context['account_id'], region=environment_context['region'])

        self.frontend_deployment_stack = FrontendDeploymentStack(
            self,
            'FrontendDeploymentStack',
            env=environment,
            environment_context=environment_context,
            environment_name=environment_name,
            standard_tags=standard_tags,
        )
