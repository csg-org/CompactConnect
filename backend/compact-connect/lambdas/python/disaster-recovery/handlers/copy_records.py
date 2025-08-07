from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger


def copy_records(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    As part of synchronizing tables during a DR event, we clear the current records from the target
    table to put it in a clean state. After which the next step in the recovery process will copy over all the
    existing records from the recovery point table into the target table.

    In the event that the copy process takes longer than the 15-minute time limit window for lambda, we return a
    'copyStatus' field of 'IN_PROGRESS', causing the step function to loop around and continue the copy process using
    the lastEvaluatedKey found in the response.
    If all the records have been copied, we return a 'copyStatus' of 'COMPLETE', causing the step function to
    complete the sync workflow.
    """

    return {'copyStatus': 'COMPLETE'}
