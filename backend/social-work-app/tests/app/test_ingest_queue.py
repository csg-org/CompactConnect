import json
from unittest import TestCase

from aws_cdk.assertions import Template

from tests.app.base import TstAppABC

INGEST_HANDLER_DESCRIPTION = 'Ingest license data handler'
PREPROCESS_HANDLER_DESCRIPTION = (
    'Preprocess license data to create SSN Dynamo records before sending licenses to the event bus'
)


class TestIngestQueue(TstAppABC, TestCase):
    """
    The ingest queue's timing settings, which have to hold together as a set.

    An SSN correction is far more expensive per message than an ordinary ingest - it reads both providers'
    partitions and rewrites a whole partition in a single transaction - and a batch may contain up to
    batch_size of them. That drives the handler timeout up, and the queue's visibility timeout has to stay
    ahead of the handler timeout or SQS redelivers a message to a second worker while the first is still
    processing it, so the same correction runs twice concurrently.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    @property
    def _template(self) -> Template:
        return Template.from_stack(self.app.sandbox_backend_stage.ingest_stack)

    @property
    def _persistent_template(self) -> Template:
        """The preprocess stage lives with the SSN table, in the persistent stack."""
        return Template.from_stack(self.app.sandbox_backend_stage.persistent_stack)

    def _handler_properties(self, template: Template, description: str) -> dict:
        functions = template.find_resources('AWS::Lambda::Function')
        handlers = [
            resource['Properties']
            for resource in functions.values()
            if resource['Properties'].get('Description') == description
        ]
        self.assertEqual(1, len(handlers), f'expected exactly one handler described as {description!r}')
        return handlers[0]

    def _ingest_handler_properties(self) -> dict:
        return self._handler_properties(self._template, INGEST_HANDLER_DESCRIPTION)

    def _preprocess_handler_properties(self) -> dict:
        return self._handler_properties(self._persistent_template, PREPROCESS_HANDLER_DESCRIPTION)

    def _queue_properties(self, template: Template, construct_id_fragment: str) -> dict:
        """The queue a handler reads from, found via its event source mapping."""
        mappings = template.find_resources('AWS::Lambda::EventSourceMapping')
        queues = template.find_resources('AWS::SQS::Queue')

        matching = [
            resource['Properties']
            for resource in mappings.values()
            if construct_id_fragment in json.dumps(resource['Properties'].get('EventSourceArn', {}))
        ]
        self.assertEqual(1, len(matching), f'expected exactly one event source mapping for {construct_id_fragment}')

        # The mapping references the queue by Arn/GetAtt, whose logical id names the queue resource
        queue_logical_id = matching[0]['EventSourceArn']['Fn::GetAtt'][0]
        return queues[queue_logical_id]['Properties']

    def _ingest_queue_properties(self) -> dict:
        return self._queue_properties(self._template, 'V1Ingest')

    def _preprocess_queue_properties(self) -> dict:
        return self._queue_properties(self._persistent_template, 'LicenseQueuePreprocessor')

    def test_visibility_timeout_exceeds_the_handler_timeout_at_every_stage(self):
        """
        The invariant that matters, rather than the specific numbers: if a message becomes visible again
        while the handler still holds it, a second worker picks up the same SSN correction concurrently.

        License ingest runs through two SQS stages - preprocess, then ingest - and the invariant has to hold
        at both, so a correction is not replayed at the stage that resolves its two SSNs either.
        """
        stages = {
            'preprocess': (self._preprocess_handler_properties(), self._preprocess_queue_properties()),
            'ingest': (self._ingest_handler_properties(), self._ingest_queue_properties()),
        }
        for stage, (handler, queue) in stages.items():
            with self.subTest(stage=stage):
                self.assertGreater(queue['VisibilityTimeout'], handler['Timeout'])

    def test_timings_match_the_compact_connect_ingest_queue(self):
        """
        These apps are per-compact replicas of one deployment, so the ingest timings are pinned to the same
        values compact-connect uses rather than derived independently. A change here should be a deliberate
        change in both, not a drift in one.

        The 20-minute visibility timeout is four times the handler timeout, below the six times AWS suggests
        as a rule of thumb, but comfortably above the invariant that actually matters above.
        """
        self.assertEqual(120, self._preprocess_handler_properties()['Timeout'])
        self.assertEqual(480, self._preprocess_queue_properties()['VisibilityTimeout'])
        self.assertEqual(300, self._ingest_handler_properties()['Timeout'])
        self.assertEqual(1200, self._ingest_queue_properties()['VisibilityTimeout'])

    def test_failed_messages_land_on_a_dead_letter_queue_at_every_stage(self):
        for stage, queue in (
            ('preprocess', self._preprocess_queue_properties()),
            ('ingest', self._ingest_queue_properties()),
        ):
            with self.subTest(stage=stage):
                redrive_policy = queue.get('RedrivePolicy')
                self.assertIsNotNone(redrive_policy, f'the {stage} queue must have a dead letter queue')
                self.assertEqual(3, redrive_policy['maxReceiveCount'])
