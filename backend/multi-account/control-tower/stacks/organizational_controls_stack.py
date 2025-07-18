from enum import Enum

from aws_cdk import IResolvable, Resource, Stack
from aws_cdk.aws_iam import Effect, PolicyDocument, PolicyStatement
from aws_cdk.aws_organizations import CfnPolicy
from constructs import Construct

from stacks.bare_org_stack import BareOrgStack


class OrganizationalControlsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, bare_org_stack: BareOrgStack, **kwargs):
        """We can declare organizational controls that can be maintained here"""
        super().__init__(scope, construct_id, **kwargs)

        NoLeavingServiceControlPolicy(
            self,
            'NoLeavingServiceControlPolicy',
            target_ids=[bare_org_stack.organization.attr_root_id],
        )

        NoCreatingIAMUsersControlPolicy(
            self,
            'NoCreatingIAMUsersControlPolicy',
            target_ids=[bare_org_stack.organization.attr_root_id],
        )


class OrganizationalPolicyType(Enum):
    SERVICE_CONTROL_POLICY = 'SERVICE_CONTROL_POLICY'
    AISERVICES_OPT_OUT_POLICY = 'AISERVICES_OPT_OUT_POLICY'
    BACKUP_POLICY = 'BACKUP_POLICY'
    TAG_POLICY = 'TAG_POLICY'


class ServiceControlPolicy(Resource):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        name: str,
        description: str,
        target_ids: list[str] | IResolvable,
    ):
        super().__init__(scope, construct_id)
        self.name = name
        self.description = description
        self.target_ids = self.resolve_targets(target_ids)

    def resolve_targets(self, target_ids: list[str] | IResolvable) -> list[str]:
        stack = Stack.of(self)
        return [target_id if isinstance(target_id, str) else stack.resolve(target_id) for target_id in target_ids]

    def _build_policy(self, policy_document: PolicyDocument):
        self.node.default_child = CfnPolicy(
            self,
            'Resource',
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
    def __init__(self, scope: Construct, construct_id: str, *, target_ids: list[str]):
        super().__init__(
            scope,
            construct_id,
            name='NoLeaving',
            description='Denies accounts leaving the organization',
            target_ids=target_ids,
        )
        self.assign_document(
            PolicyDocument(
                statements=[
                    PolicyStatement(effect=Effect.DENY, actions=['organizations:LeaveOrganization'], resources=['*']),
                ],
            ),
        )


class NoCreatingIAMUsersControlPolicy(ServiceControlPolicy):
    def __init__(self, scope: Construct, construct_id: str, *, target_ids: list[str]):
        super().__init__(
            scope,
            construct_id,
            name='NoCreatingIAMUsers',
            description='Denies the creation of IAM users',
            target_ids=target_ids,
        )
        self.assign_document(
            PolicyDocument(
                statements=[
                    PolicyStatement(effect=Effect.DENY, actions=['iam:CreateUser'], resources=['*']),
                ],
            ),
        )
