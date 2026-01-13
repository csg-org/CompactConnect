import json

from aws_cdk.aws_ssm import StringParameter
from constructs import Construct


class SSMContext:
    """
    Utility class for managing SSM Parameter context lookups with dummy value handling.

    This class abstracts the common pattern of:
    1. Creating a StringParameter reference from an existing parameter name
    2. Looking up the parameter value
    3. Handling CDK's dummy value pattern during initial synthesis
    4. Falling back to a context file when dummy values are detected

    :param scope: The CDK construct scope
    :param construct_id: The ID for the StringParameter construct
    :param parameter_name: The name of the SSM Parameter to look up
    :param fallback_context_file: Path to the context file to use when dummy values are detected
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        parameter_name: str,
        fallback_context_file: str,
    ):
        self._parameter = StringParameter.from_string_parameter_name(
            scope,
            construct_id,
            string_parameter_name=parameter_name,
        )
        value = StringParameter.value_from_lookup(scope, self._parameter.parameter_name)
        # When CDK runs for the first time, it synthesizes fully without actually retrieving the SSM Parameter
        # value. It, instead, populates parameters and other look-ups with dummy values, synthesizes, collects all
        # the look-ups together, populates them for real, then re-synthesizes with real values.
        # To accommodate this pattern, we have to replace this dummy value with one that will actually
        # let CDK complete its first round of synthesis, so that it can get to its second, real, synthesis.
        if value != f'dummy-value-for-{parameter_name}':
            self._context = json.loads(value)
        else:
            with open(fallback_context_file) as f:
                self._context = json.load(f)['ssm_context']

    @property
    def parameter(self) -> StringParameter:
        """Get the StringParameter construct."""
        return self._parameter

    @property
    def context(self) -> dict:
        """Get the parsed context dictionary from the SSM Parameter."""
        return self._context
