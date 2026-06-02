from __future__ import annotations

from aws_cdk.aws_logs import QueryDefinition, QueryString
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps

from .bulk_upload_url import BulkUploadUrlLambdas
from .compact_configuration_api import CompactConfigurationApiLambdas
from .feature_flags import FeatureFlagsLambdas
from .post_licenses import PostLicensesLambdas
from .provider_management import ProviderManagementLambdas
from .public_lookup_api import PublicLookupApiLambdas
from .staff_users import StaffUsersLambdas


class ApiLambdaStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ) -> None:
        super().__init__(
            scope,
            construct_id,
            environment_name=environment_name,
            environment_context=environment_context,
            **kwargs,
        )

        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(self)

        # Initialize log groups list for QueryDefinition
        self.log_groups = []

        # we only pass the API_BASE_URL env var if the API_DOMAIN_NAME is set
        # this is because the API_BASE_URL is used by the feature flag client to call the flag check endpoint
        if persistent_stack.api_domain_name:
            self.common_env_vars.update({'API_BASE_URL': f'https://{persistent_stack.api_domain_name}'})

        # Feature Flags related API lambdas
        self.feature_flags_lambdas = FeatureFlagsLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

        # Bulk upload url lambdas
        self.bulk_upload_url_lambdas = BulkUploadUrlLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            api_lambda_stack=self,
        )

        # Compact configuration lambdas
        self.compact_configuration_lambdas = CompactConfigurationApiLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            api_lambda_stack=self,
        )

        # Post licenses lambdas
        self.post_licenses_lambdas = PostLicensesLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            api_lambda_stack=self,
        )

        # Provider Management lambdas
        self.provider_management_lambdas = ProviderManagementLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            api_lambda_stack=self,
        )

        # Public lookup lambdas
        self.public_lookup_lambdas = PublicLookupApiLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            api_lambda_stack=self,
        )

        # The public GET provider route is wired to get_provider_handler and is not deployed in the
        # beta environment (see api_stack/v1_api/api.py). Removing that route removes the API stack's
        # cross-stack import of this lambda ARN, which would otherwise delete the auto-generated
        # CloudFormation export created here. CloudFormation refuses to delete an export while another
        # stack still imports it during the same deployment ("deadly embrace"), so we retain it.
        # TODO: remove this export once the API stack no longer imports it in every environment.  # noqa: FIX002
        self.export_value(self.public_lookup_lambdas.get_provider_handler.function_arn)

        # query_providers_handler is no longer wired to the API (the public query providers route now
        # uses SearchPersistentStack.search_handler.public_handler). We retain its export to avoid the
        # same deadly embrace while the old cross-stack import is removed from already-deployed stacks.
        # TODO: remove this export (and the unused lambda) once it is deployed to all environments.  # noqa: FIX002
        self.export_value(self.public_lookup_lambdas.query_providers_handler.function_arn)

        # Staff user lambdas
        self.staff_users_lambdas = StaffUsersLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            api_lambda_stack=self,
        )

        # Create the QueryDefinition after all lambda modules have been initialized and added their log groups
        self._create_runtime_query_definition()

    def _create_runtime_query_definition(self):
        """Create the QueryDefinition for runtime logs after all lambda modules have been initialized."""
        QueryDefinition(
            self,
            'RuntimeQuery',
            query_definition_name=f'{self.node.id}/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', 'level', 'status', 'message', 'method', 'path', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=self.log_groups,
        )
