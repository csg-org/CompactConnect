from enum import Enum
from typing import List

from aws_cdk import Stack, Resource, IResolvable
from aws_cdk.aws_iam import PolicyDocument, PolicyStatement, Effect
from aws_cdk.aws_organizations import CfnPolicy
from constructs import Construct

from multi_account.bare_org_stack import BareOrgStack


class OrganizationalControlsStack(Stack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            bare_org_stack: BareOrgStack,
            **kwargs
    ):
        """
        We can declare organizational controls that can be maintained here
        """
        super().__init__(scope, construct_id, **kwargs)

        NoLeavingServiceControlPolicy(
            self, 'NoLeavingServiceControlPolicy',
            target_ids=[bare_org_stack.organization.attr_root_id]
        )


class OrganizationalPolicyType(Enum):
    SERVICE_CONTROL_POLICY = 'SERVICE_CONTROL_POLICY'
    AISERVICES_OPT_OUT_POLICY = 'AISERVICES_OPT_OUT_POLICY'
    BACKUP_POLICY = 'BACKUP_POLICY'
    TAG_POLICY = 'TAG_POLICY'


class ServiceControlPolicy(Resource):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            name: str,
            description: str,
            target_ids: List[str] | IResolvable
    ):
        super().__init__(scope, construct_id)
        self.name = name
        self.description = description
        self.target_ids = self.resolve_targets(target_ids)

    def resolve_targets(self, target_ids: List[str] | IResolvable) -> List[str]:
        stack = Stack.of(self)
        return [
            target_id if isinstance(target_id, str) else stack.resolve(target_id)
            for target_id in target_ids
        ]

    def _build_policy(self, policy_document: PolicyDocument):
        self.node.default_child = CfnPolicy(
            self, 'Resource',
            type=OrganizationalPolicyType.SERVICE_CONTROL_POLICY.value,
            name=self.name,
            content=policy_document.to_json(),
            description=self.description,
            target_ids=self.target_ids,
        )

    def assign_document(self, policy_document: PolicyDocument):
        if self.node.default_child is not None:
            raise RuntimeError('This policy statement can only be defined once!')
        self._build_policy(policy_document)


class NoLeavingServiceControlPolicy(ServiceControlPolicy):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            target_ids: List[str]
    ):
        super().__init__(
            scope, construct_id,
            name='NoLeaving',
            description='Denies accounts leaving the organization',
            target_ids=target_ids
        )
        self.assign_document(PolicyDocument(
            statements=[
                PolicyStatement(
                    effect=Effect.DENY,
                    actions=[
                        'organizations:LeaveOrganization'
                    ],
                    resources=[
                        '*'
                    ]
                )
            ]
        ))
