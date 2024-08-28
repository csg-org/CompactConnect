from __future__ import annotations

import jsii
from aws_cdk import IAspect, Aspects
from aws_cdk.aws_apigateway import IResource, MethodOptions, AuthorizationType, Method
from cdk_nag import NagSuppressions

from stacks.api_stack.bulk_upload_url import BulkUploadUrl
from stacks.api_stack.post_license import PostLicenses
from stacks.api_stack.query_providers import QueryProviders
from stacks import persistent_stack as ps


@jsii.implements(IAspect)
class NagSuppressNotAuthorized:
    """
    This Aspect will be called over every node in the construct tree from where it is added, through all children:
    https://docs.aws.amazon.com/cdk/v2/guide/aspects.html

    This entire API portion is intentionally unauthenticated, so we will suppress those Nag findings en masse.
    """
    def visit(self, node: Method):
        if isinstance(node, Method):
            NagSuppressions.add_resource_suppressions(
                node,
                suppressions=[
                    {
                        'id': 'AwsSolutions-APIG4',
                        'reason': 'The mock API is intentionally unauthenticated'
                    },
                    {
                        'id': 'AwsSolutions-COG4',
                        'reason': 'The mock API is intentionally unauthenticated'
                    }
                ]
            )


class MockApi:
    """
    Deprecated - Mock API portion
    """
    def __init__(self, resource: IResource, persistent_stack: ps.PersistentStack):
        self.root = resource
        self._add_mock_api(persistent_stack=persistent_stack)

    def _add_mock_api(self, persistent_stack: ps.PersistentStack):
        mock_resource = self.root.add_resource('mock')
        Aspects.of(mock_resource).add(NagSuppressNotAuthorized())

        noauth_method_options = MethodOptions(
            authorization_type=AuthorizationType.NONE
        )

        # No auth mock endpoints
        # /mock/providers/query
        mock_providers_resource = mock_resource.add_resource('providers')
        QueryProviders(
            mock_providers_resource,
            method_options=noauth_method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            license_data_table=persistent_stack.mock_license_table
        )

        # /mock/licenses/{compact}/{jurisdiction}
        mock_jurisdiction_resource = mock_resource \
            .add_resource('licenses') \
            .add_resource('{compact}') \
            .add_resource('{jurisdiction}')
        PostLicenses(
            mock_resource=True,
            resource=mock_jurisdiction_resource,
            method_options=noauth_method_options,
            event_bus=persistent_stack.data_event_bus
        )
        BulkUploadUrl(
            mock_bucket=True,
            resource=mock_jurisdiction_resource,
            method_options=noauth_method_options,
            bulk_uploads_bucket=persistent_stack.mock_bulk_uploads_bucket
        )
