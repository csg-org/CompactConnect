import json
from functools import cached_property
from textwrap import dedent

from aws_cdk import Stack as CdkStack, Aspects
from aws_cdk.aws_route53 import HostedZone, IHostedZone
from cdk_nag import AwsSolutionsChecks, HIPAASecurityChecks, NagSuppressions


class StandardTags(dict):
    """
    Enforces four required tags for all stacks
    """
    def __init__(
            self, *,
            project: str,
            service: str,
            environment: str,
            **kwargs
    ):
        super().__init__(
            Project=project,
            Service=service,
            Environment=environment,
            **kwargs
        )


class Stack(CdkStack):
    def __init__(self, *args, standard_tags: StandardTags, **kwargs):
        super().__init__(*args, tags=standard_tags, **kwargs)
        # AWS-recommended rule sets for best practice and to help with (but not guarantee) HIPAA compliance
        Aspects.of(self).add(AwsSolutionsChecks())
        Aspects.of(self).add(HIPAASecurityChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-IAMNoInlinePolicy',
                    'reason': dedent('''
                        Prohibitions on inline policies are raised in favor of managed policies in order to support a
                        few goals:
                        - policy versioning
                        - reusability across resources that perform similar tasks
                        - rolling back on failures
                        - delegating permissions management

                        These goals are met differently in a CDK app. CDK itself allows for granular permissions crafting
                        that is attached to policies directly to each resource, by virtue of its Resource.grant_* methods.
                        This approach actually results in an improvement in the principle of least privilege, because each
                        resource in the app has permissions that are specifically crafted for that particular resource
                        and only allow exactly what it needs to do, rather than sharing, generally more coarse, managed
                        policies that approximate the access it needs to perform particular tasks. Those highly targeted
                        policies are appropriately attached to principals as inline policies. This approach leads to a
                        more maintainable and more secure implementation than the reusability and permissions delegation
                        that managed policies accomplish. Versioning of policies is accomplished through git itself as the
                        version control system that manages all of the infrastructure, runtime code, and policies for the
                        app, right here in this repository. Rolling back on failures is accomplished both through
                        CloudFormation as well as git again, as both have capabilities to perform much more cohesive
                        roll-backs than managed policies alone.
                        ''')
                },
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'The lambdas in this app will share account-wide concurrency limits'
                },
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'Temporarily turning off auth for OWASP Zap'
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'Temporarily turning off auth for OWASP Zap'
                }
            ]
        )

    @cached_property
    def license_types(self):
        """
        Flattened list of all license types across all compacts
        """
        return [
            typ
            for comp in self.node.get_context('license_types').values()
            for typ in comp
        ]

    @cached_property
    def common_env_vars(self):
        return {
            'DEBUG': 'true',
            'COMPACTS': json.dumps(self.node.get_context('compacts')),
            'JURISDICTIONS': json.dumps(self.node.get_context('jurisdictions')),
            'LICENSE_TYPES': json.dumps(self.node.get_context('license_types'))
        }


class AppStack(Stack):
    """
    A stack that is part of the main app deployment
    """
    def __init__(self, *args, environment_context: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self.environment_context = environment_context

    @cached_property
    def hosted_zone(self) -> IHostedZone | None:
        hosted_zone = None
        domain_name = self.environment_context.get('domain_name')
        if domain_name is not None:
            hosted_zone = HostedZone.from_lookup(
                self, 'HostedZone',
                domain_name=domain_name
            )
        return hosted_zone

    @property
    def api_domain_name(self) -> str | None:
        if self.hosted_zone is not None:
            return f'api.{self.hosted_zone.zone_name}'
        return None

    @property
    def ui_domain_name(self) -> str | None:
        if self.hosted_zone is not None:
            return f'app.{self.hosted_zone.zone_name}'
        return None
