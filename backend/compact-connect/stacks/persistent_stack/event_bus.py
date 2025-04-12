from aws_cdk import Duration, Stack
from aws_cdk.aws_events import EventBus as CdkEventBus
from aws_cdk.aws_events import EventPattern
from constructs import Construct

DEFAULT_ARCHIVE_RETENTION_DURATION = Duration.days(180)


class EventBus(CdkEventBus):
    def __init__(
        self,
        scope: Construct,
        construct_id,
        archive_retention: Duration = DEFAULT_ARCHIVE_RETENTION_DURATION,
        **kwargs,
    ):
        # we explicitly name this resource, so that any future pipeline migrations will not change the namespace
        super().__init__(scope, construct_id, **kwargs)
        self.archive(
            f'{construct_id}Archive',
            description=f'{construct_id} event archive',
            retention=archive_retention,
            event_pattern=EventPattern(account=[Stack.of(self).account]),
        )
