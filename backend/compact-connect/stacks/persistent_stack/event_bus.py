from aws_cdk import Duration, Stack
from aws_cdk.aws_events import EventBus, EventPattern
from constructs import Construct


class DataEventBus(EventBus):
    def __init__(
            self, scope: Construct, construct_id,
            archive_retention: Duration = Duration.days(180),
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)
        self.archive(
            f'{construct_id}Archive',
            description=f'{construct_id} event archive',
            retention=archive_retention,
            event_pattern=EventPattern(
                account=[Stack.of(self).account]
            )
        )
