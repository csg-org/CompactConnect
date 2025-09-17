from __future__ import annotations

import json

from constructs import Construct

from common_constructs.stack import AppStack
from stacks import persistent_stack as ps

from .transaction_history_processing_workflow import TransactionHistoryProcessingWorkflow


class TransactionMonitoringStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        self.compact_state_machines = {}
        # we create a state machine for each compact in order to keep permissions separate
        # and to prevent errors with one compact's transaction account impacting others.
        for compact in json.loads(self.common_env_vars['COMPACTS']):
            self.compact_state_machines[compact] = TransactionHistoryProcessingWorkflow(
                self,
                f'{compact}-TransactionHistoryProcessingWorkflow',
                compact=compact,
                environment_name=environment_name,
                persistent_stack=persistent_stack,
            )
