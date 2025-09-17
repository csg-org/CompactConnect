from aws_cdk import Stack, aws_ssm
from constructs import Construct


class SynthSubstituteStack(Stack):
    """
    A lightweight stack used as a substitute during pipeline synthesis.

    This stack is used to optimize CDK pipeline synthesis by replacing
    heavyweight stacks with a minimal stack that contains just a dummy
    SSM parameter. This dramatically reduces synthesis time when only
    a specific pipeline's stacks need to be synthesized.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create a simple SSM parameter as a lightweight substitute
        self.dummy_parameter = aws_ssm.StringParameter(
            self,
            'DummyParameter',
            parameter_name=f'/compact-connect/{construct_id}/dummy-parameter',
            string_value='dummy parameter value',
            description='Dummy parameter used for CDK synthesis optimization',
        )
