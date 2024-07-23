from __future__ import annotations

from aws_cdk.aws_route53 import HostedZone
from constructs import Construct

from common_constructs.stack import Stack
from stacks.api_stack.license_api import LicenseApi
from stacks import persistent_stack as ps


class ApiStack(Stack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            environment_name: str,
            environment_context: dict,
            persistent_stack: ps.PersistentStack,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        hosted_zone = None
        domain_name = environment_context.get('domain_name')
        if domain_name is not None:
            hosted_zone = HostedZone.from_lookup(
                self, 'HostedZone',
                domain_name=domain_name
            )

        self.license_api = LicenseApi(
            self, 'LicenseApi',
            environment_name=environment_name,
            hosted_zone=hosted_zone,
            persistent_stack=persistent_stack
        )
