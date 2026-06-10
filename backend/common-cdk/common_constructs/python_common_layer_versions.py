import os

from aws_cdk import RemovalPolicy, Stack
from aws_cdk.aws_lambda import IFunction, ILayerVersion, Runtime
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_ssm import StringParameter
from constructs import Construct


class PythonCommonLayerVersions(Construct):
    """
    Constructs and wraps the runtime-specific python common lambda layers to make accessing the correct layer
    via the correct referencing strategy more convenient across the app.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        compatible_runtimes: list[Runtime],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id)

        from common_constructs.python_function import PythonFunction

        PythonFunction.register_layer_versions(self)

        self._python_layers = {}

        for runtime in compatible_runtimes:
            # Add the common python lambda layer for use in all python lambdas
            # NOTE: this is to only be referenced directly in this stack!
            # All external references should use the ssm parameter to get the value of the layer arn.
            # attempting to reference this layer directly in another stack will cause this stack
            # to be stuck in an UPDATE_ROLLBACK_FAILED state which will require DELETION of stacks
            # that reference the layer directly. See https://github.com/aws/aws-cdk/issues/1972
            self._python_layers[runtime.name] = PythonLayerVersion(
                self,
                runtime.name,
                entry=os.path.join('lambdas', 'python', 'common'),
                # Compatible runtime(s) is a bit misleading - only the first runtime is used for bundling, so any
                # other 'compatible' types listed could be broken. We'll just make one layer per runtime we need.
                compatible_runtimes=[runtime],
                description='A layer for common code shared between python lambdas',
                # We retain the layer versions in our environments, to avoid a situation where a consuming stack is
                # unable to roll back because old versions are destroyed. This means that over time, these versions
                # will accumulate in prod, and given the AWS limit of 75 GB for all layer and lambda code storage
                # we will likely need to add a custom resource to track these versions, and clean up versions that are
                # older than a certain date. That is out of scope for our current effort, but we're leaving this comment
                # here to remind us that this will need to be addressed at a later date.
                removal_policy=RemovalPolicy.RETAIN,
                **kwargs,
            )

            # We Store the layer ARN in SSM Parameter Store
            # since lambda layers can't be shared across stacks
            # directly due to the fact that you can't update a CloudFormation
            # exported value that is being referenced by a resource in another stack
            StringParameter(
                self,
                f'{runtime.name}LayerArnParameter',
                # We link across stacks based on a predictable parameter name
                parameter_name=self._get_parameter_name_for_runtime(runtime),
                string_value=self._python_layers[runtime.name].layer_version_arn,
            )

    def get_common_layer(self, for_function: IFunction) -> ILayerVersion:
        layer_stack = Stack.of(self)
        function_stack = Stack.of(for_function)
        runtime = for_function.runtime

        # If we're in-stack, we can just return the reference directly
        if runtime.name not in self._python_layers.keys():
            raise ValueError(f'No common python layer exists for runtime {runtime.name}')

        # If we're in-stack, return a direct reference to the layer version
        if function_stack is layer_stack:
            return self._python_layers[runtime.name]

        # This doesn't create a cross-stack reference, but it does help CDK/CloudFormation
        # to sequence the stack deploys properly. Without this, CDK may attempt to deploy
        # stacks that depend on the parameters in parallel with `layer_stack`, which will fail.
        for_function.node.add_dependency(layer_stack)

        return self._get_ilayer_reference(for_function)

    def _get_ilayer_reference(self, for_function: IFunction):
        """
        For cross-stack, we need to build an ILayerVersion from the SSM parameter value to avoid a cross-stack
        dependency that will break with every rebuild of the lambda layer version
        """
        function_stack = Stack.of(for_function)
        runtime = for_function.runtime

        # We only want to do this look-up once per stack, so we'll first check if it's already been done for the
        # stack before creating a new one
        layer_construct_id = self._get_ilayer_construct_id_for_runtime(runtime)
        parameter_construct_id = f'{layer_construct_id}Parameter'
        common_layer_version: ILayerVersion = function_stack.node.try_find_child(layer_construct_id)
        if common_layer_version is not None:
            return common_layer_version

        # Fetch the value from SSM parameter
        common_python_lambda_layer_parameter = StringParameter.from_string_parameter_name(
            function_stack,
            parameter_construct_id,
            string_parameter_name=self._get_parameter_name_for_runtime(runtime),
        )
        return PythonLayerVersion.from_layer_version_arn(
            function_stack, layer_construct_id, common_python_lambda_layer_parameter.string_value
        )

    @staticmethod
    def _get_ilayer_construct_id_for_runtime(runtime: Runtime):
        return f'{runtime.name}CommonPythonLayer'

    @staticmethod
    def _get_parameter_name_for_runtime(runtime: Runtime):
        return f'/deployment/lambda/layers/{runtime.name}/common-python-layer-arn'
