import jsii
from aws_cdk import CfnOutput
from aws_cdk.aws_iam import IGrantable, Role, FederatedPrincipal, OpenIdConnectProvider
from constructs import Construct


@jsii.implements(IGrantable)
class GitHubActionsAccess(Construct):
    def __init__(
        self, scope: Construct, construct_id: str, *,
        github_repo_string: str,
        sub_ref: str = None,
        role_name: str = None
    ):
        super().__init__(scope, construct_id)
        self.github_repo_string = github_repo_string
        if sub_ref is None:
            sub_ref = '*'

        github_idp = GitHubActionsOIDCProvider(
            self, 'OIDCProvider',
            client_ids=['sts.amazonaws.com']
        )

        self.github_role = Role(
            self, 'Role',
            assumed_by=FederatedPrincipal(
                github_idp.open_id_connect_provider_arn,
                conditions={
                    'StringLike': {
                        'token.actions.githubusercontent.com:sub': f'repo:{github_repo_string}:{sub_ref}',
                    },
                    'StringEquals': {
                        'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com'
                    }
                },
                assume_role_action='sts:AssumeRoleWithWebIdentity'
            ),
            role_name=role_name
        )
        self._grant_principal = self.github_role
        self.role_arn = self.github_role.role_arn

        CfnOutput(
            self, 'GitHubRoleArn',
            value=self.role_arn
        )

    @property
    def grant_principal(self):
        return self._grant_principal


class GitHubActionsOIDCProvider(OpenIdConnectProvider):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(
            scope, construct_id,
            url='https://token.actions.githubusercontent.com',
            # This thumbprint value is not actually used by AWS:
            # > AWS secures communication with this OIDC identity provider (IdP) using our library of trusted
            # > CAs rather than using a certificate thumbprint to verify the server certificate of your IdP.
            # > Your legacy thumbprint(s) will remain in your configuration but will no longer be needed for
            # > validation.
            #
            # This note is found in the AWS Console, IAM identity providers view, but not yet in their
            # documentation anywhere at the time of writing this.
            #
            # Manually collected for good measure:
            thumbprints=['1B511ABEAD59C6CE207077C0BF0E0043B1382612'],
            **kwargs
        )
