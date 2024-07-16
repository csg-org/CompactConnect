from aws_cdk import RemovalPolicy, Stack
from aws_cdk.aws_organizations import CfnOrganization, CfnAccount
from constructs import Construct


class BareOrgStack(Stack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            account_name_prefix: str,
            email_domain: str,
            **kwargs
    ):
        """
        Creates an AWS Organization with the minimum accounts needed
        to create a ControlTower LandingZone

        This stack must be deployed in the Management AWS account. Before deploying this stack, matching email
        addresses must be created for:
        - '{account_name_prefix}-logs@{email_domain}' and
        - '{account_name_prefix}-audit@{email_domain}'

        :param scope:
        :param construct_id:
        :param account_name_prefix: A string prefix to use in logging and audit account names
        :param email_domain: The email domain associated with AWS account email addresses.
        """
        super().__init__(scope, construct_id, **kwargs)

        self.organization = CfnOrganization(
            self, 'Organization',
            feature_set='ALL'
        )
        self.organization.apply_removal_policy(RemovalPolicy.RETAIN)

        logging_account_name = f'{account_name_prefix}-logs'
        logging_account_email = f'{logging_account_name}@{email_domain}'
        self.logging_account = CfnAccount(
            self, 'LoggingAccount',
            account_name=logging_account_name,
            email=logging_account_email,
            parent_ids=[self.organization.attr_root_id]
        )
        self.logging_account.apply_removal_policy(RemovalPolicy.RETAIN)

        audit_account_name = f'{account_name_prefix}-audit'
        audit_account_email = f'{audit_account_name}@{email_domain}'
        self.audit_account = CfnAccount(
            self, 'AuditAcount',
            account_name=audit_account_name,
            email=audit_account_email,
            parent_ids=[self.organization.attr_root_id]
        )
        self.audit_account.apply_removal_policy(RemovalPolicy.RETAIN)
        self.audit_account.add_dependency(self.logging_account)
