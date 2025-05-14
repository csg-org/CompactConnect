from aws_cdk import Environment, Stage
from constructs import Construct
from pipeline.synth_substitute_stack import SynthSubstituteStack


class SynthSubstituteStage(Stage):
    """
    A lightweight stage used as a substitute during pipeline synthesis.

    This stage is used to optimize CDK pipeline synthesis by replacing
    heavyweight stages with a minimal stage that contains just a single
    SynthSubstituteStack. This dramatically reduces synthesis time when
    only a specific pipeline's stages need to be synthesized.

    Using a separate stage rather than conditional logic within existing
    stages provides an additional safety layer - preventing accidental
    deletion of production resources due to typos in pipeline names.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_context: dict,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        environment = Environment(account=environment_context['account_id'], region=environment_context['region'])

        # Create a simple substitute stack
        self.substitute_stack = SynthSubstituteStack(
            self,
            'SubstituteStack',
            env=environment,
        )
