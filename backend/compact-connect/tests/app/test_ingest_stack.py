import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_cloudwatch import CfnAlarm

from tests.app.base import TstAppABC


class TestIngestStack(TstAppABC, TestCase):
    """
    Test cases for the custom metrics and alarms that track how often states rely on the previousSSN
    last-resort SSN correction feature (see handlers/ingest.py::_perform_ssn_correction_migration).
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

    def _get_ssn_correction_alarm_properties(self, construct_id: str) -> dict:
        ingest_stack = self.app.sandbox_backend_stage.ingest_stack
        ingest_template = Template.from_stack(ingest_stack)
        alarms = ingest_template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)

        alarm_logical_id = ingest_stack.get_logical_id(
            ingest_stack.ingest_handler.node.find_child(construct_id).node.default_child
        )
        return self.get_resource_properties_by_logical_id(alarm_logical_id, resources=alarms)

    def test_full_migration_metric_alarm_configured(self):
        """The full-migration alarm should fire on any full migration within a rolling 24-hour period."""
        alarm = self._get_ssn_correction_alarm_properties('SsnCorrectionFullMigrationAlarm')

        self.assertEqual(alarm['Namespace'], 'compact-connect')
        self.assertEqual(alarm['MetricName'], 'ssn-correction-full-migration')
        self.assertEqual(alarm['Dimensions'], [{'Name': 'service', 'Value': 'common'}])
        self.assertEqual(alarm['Statistic'], 'Sum')
        # 24-hour period, so at most one alert per day for this category
        self.assertEqual(alarm['Period'], 86400)
        self.assertEqual(alarm['EvaluationPeriods'], 1)
        self.assertEqual(alarm['Threshold'], 1)
        self.assertEqual(alarm['ComparisonOperator'], 'GreaterThanOrEqualToThreshold')
        self.assertEqual(alarm['TreatMissingData'], 'notBreaching')

    def test_partial_migration_metric_alarm_configured(self):
        """The partial-migration alarm should fire on any partial migration within a rolling 24-hour period."""
        alarm = self._get_ssn_correction_alarm_properties('SsnCorrectionPartialMigrationAlarm')

        self.assertEqual(alarm['Namespace'], 'compact-connect')
        self.assertEqual(alarm['MetricName'], 'ssn-correction-partial-migration')
        self.assertEqual(alarm['Dimensions'], [{'Name': 'service', 'Value': 'common'}])
        self.assertEqual(alarm['Statistic'], 'Sum')
        # 24-hour period, so at most one alert per day for this category
        self.assertEqual(alarm['Period'], 86400)
        self.assertEqual(alarm['EvaluationPeriods'], 1)
        self.assertEqual(alarm['Threshold'], 1)
        self.assertEqual(alarm['ComparisonOperator'], 'GreaterThanOrEqualToThreshold')
        self.assertEqual(alarm['TreatMissingData'], 'notBreaching')

    def test_no_migration_metric_alarm_configured(self):
        """The no-migration alarm should fire when previousSSN yields no records to migrate within 24 hours."""
        alarm = self._get_ssn_correction_alarm_properties('SsnCorrectionNoMigrationAlarm')

        self.assertEqual(alarm['Namespace'], 'compact-connect')
        self.assertEqual(alarm['MetricName'], 'ssn-correction-no-migration')
        self.assertEqual(alarm['Dimensions'], [{'Name': 'service', 'Value': 'common'}])
        self.assertEqual(alarm['Statistic'], 'Sum')
        # 24-hour period, so at most one alert per day for this category
        self.assertEqual(alarm['Period'], 86400)
        self.assertEqual(alarm['EvaluationPeriods'], 1)
        self.assertEqual(alarm['Threshold'], 1)
        self.assertEqual(alarm['ComparisonOperator'], 'GreaterThanOrEqualToThreshold')
        self.assertEqual(alarm['TreatMissingData'], 'notBreaching')

    def test_migration_alarms_notify_the_shared_alarm_topic(self):
        """All three alarms should notify devops support via the shared alarm topic, at most 3 alerts/day total."""
        ingest_stack = self.app.sandbox_backend_stage.ingest_stack
        ingest_template = Template.from_stack(ingest_stack)
        alarms = ingest_template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)

        # The pre-existing V1IngestFailureAlarm already notifies the shared alarm topic; the SSN-correction
        # alarms should reference that exact same imported topic
        existing_alarm_logical_id = ingest_stack.get_logical_id(
            ingest_stack.node.find_child('V1IngestFailureAlarm').node.default_child
        )
        expected_actions = self.get_resource_properties_by_logical_id(existing_alarm_logical_id, resources=alarms)[
            'AlarmActions'
        ]
        self.assertTrue(expected_actions)

        full_migration_alarm = self._get_ssn_correction_alarm_properties('SsnCorrectionFullMigrationAlarm')
        partial_migration_alarm = self._get_ssn_correction_alarm_properties('SsnCorrectionPartialMigrationAlarm')
        no_migration_alarm = self._get_ssn_correction_alarm_properties('SsnCorrectionNoMigrationAlarm')

        self.assertEqual(expected_actions, full_migration_alarm['AlarmActions'])
        self.assertEqual(expected_actions, partial_migration_alarm['AlarmActions'])
        self.assertEqual(expected_actions, no_migration_alarm['AlarmActions'])
