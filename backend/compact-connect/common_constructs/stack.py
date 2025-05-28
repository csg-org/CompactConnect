import json
from functools import cached_property
from textwrap import dedent

from aws_cdk import Aspects
from aws_cdk import Stack as CdkStack
from aws_cdk.aws_route53 import HostedZone, IHostedZone
from cdk_nag import AwsSolutionsChecks, HIPAASecurityChecks, NagSuppressions


class StandardTags(dict):
    """Enforces four required tags for all stacks"""

    def __init__(self, *, project: str, service: str, environment: str, **kwargs):
        super().__init__(Project=project, Service=service, Environment=environment, **kwargs)


class Stack(CdkStack):
    def __init__(self, *args, standard_tags: StandardTags, environment_name: str, **kwargs):
        super().__init__(*args, tags=standard_tags, **kwargs)
        self.environment_name = environment_name
        # AWS-recommended rule sets for best practice and to help with (but not guarantee) HIPAA compliance
        Aspects.of(self).add(AwsSolutionsChecks())
        Aspects.of(self).add(HIPAASecurityChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-IAMNoInlinePolicy',
                    'reason': dedent("""
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
                    """),
                },
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'The lambdas in this app will share account-wide concurrency limits',
                },
            ],
        )

    @cached_property
    def license_type_names(self):
        """Flattened list of all license type names across all compacts"""
        return [typ['name'] for compact in self.node.get_context('license_types').values() for typ in compact]

    @cached_property
    def license_type_abbreviations(self):
        """Flattened list of all license type names across all compacts"""
        return [
            typ['abbreviation']
            for compact_license_types in self.node.get_context('license_types').values()
            for typ in compact_license_types
        ]

    @cached_property
    def license_types(self):
        """Dictionary of license types by compact"""
        return self.node.get_context('license_types')

    @cached_property
    def common_env_vars(self):
        return {
            'DEBUG': 'true',
            'ALLOWED_ORIGINS': json.dumps(self.allowed_origins),
            'COMPACTS': json.dumps(self.node.get_context('compacts')),
            'JURISDICTIONS': json.dumps(self.node.get_context('jurisdictions')),
            'LICENSE_TYPES': json.dumps(self.node.get_context('license_types')),
            'ENVIRONMENT_NAME': self.environment_name,
        }


class AppStack(Stack):
    """A stack that is part of the main app deployment"""

    def __init__(self, *args, environment_context: dict, environment_name: str, **kwargs):
        super().__init__(*args, environment_name=environment_name, **kwargs)
        self.environment_context = environment_context
        self.environment_name = environment_name

    @cached_property
    def hosted_zone(self) -> IHostedZone | None:
        hosted_zone = None
        domain_name = self.environment_context.get('domain_name')
        if domain_name is not None:
            hosted_zone = HostedZone.from_lookup(self, 'HostedZone', domain_name=domain_name)
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

    @property
    def allowed_origins(self) -> list[str]:
        allowed_origins = []
        if self.hosted_zone is not None:
            allowed_origins.append(f'https://{self.ui_domain_name}')

        if self.environment_context.get('allow_local_ui', False):
            local_ui_port = self.environment_context.get('local_ui_port', '3018')
            allowed_origins.append(f'http://localhost:{local_ui_port}')

        if not allowed_origins:
            raise ValueError(
                'This app requires at least one allowed origin for its API CORS configuration. Either provide '
                "'domain_name' or set 'allow_local_ui' to true in this environment's context."
            )
        return allowed_origins
