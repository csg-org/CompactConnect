import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_cloudwatch import CfnAlarm

from tests.app.base import TstAppABC

EXPECTED_ALARM_METRICS = {
    'ssn-correction-full-migration',
    'ssn-correction-partial-migration',
    'ssn-correction-no-migration',
    'ssn-correction-retired-cuid',
}


class TestSsnCorrectionAlarms(TstAppABC, TestCase):
    """
    The SSN-correction feature deletes records and can retire a public identifier, and there is no feature
    flag in front of it, so operator visibility is the only signal that it ran. Each outcome is alarmed on
    separately.
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

    def _ssn_correction_alarms(self) -> dict[str, dict]:
        ingest_stack = self.app.sandbox_backend_stage.ingest_stack
        alarms = Template.from_stack(ingest_stack).find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)
        return {
            properties['Properties']['MetricName']: properties['Properties']
            for properties in alarms.values()
            if properties['Properties'].get('MetricName') in EXPECTED_ALARM_METRICS
        }

    def test_every_ssn_correction_outcome_is_alarmed_on(self):
        self.assertEqual(EXPECTED_ALARM_METRICS, set(self._ssn_correction_alarms().keys()))

    def test_alarms_notify_the_alarm_topic(self):
        for metric_name, properties in self._ssn_correction_alarms().items():
            with self.subTest(metric_name=metric_name):
                self.assertTrue(properties['AlarmActions'], 'alarm must publish to the alarm topic')

    def test_alarms_fire_on_a_single_occurrence_per_day(self):
        """
        A threshold of 1 over a 24-hour period means devops sees at most one notification per category per
        day the feature is used, however many corrections that day contained.
        """
        for metric_name, properties in self._ssn_correction_alarms().items():
            with self.subTest(metric_name=metric_name):
                self.assertEqual(1, properties['Threshold'])
                self.assertEqual(1, properties['EvaluationPeriods'])
                self.assertEqual(86400, properties['Period'])
                self.assertEqual('GreaterThanOrEqualToThreshold', properties['ComparisonOperator'])
                self.assertEqual('notBreaching', properties['TreatMissingData'])

    def test_alarms_read_the_metrics_the_ingest_handler_emits(self):
        """
        The alarm namespace and dimensions have to match what the handler actually publishes, or the alarm
        sits permanently in INSUFFICIENT_DATA and the feature runs unobserved.
        """
        for metric_name, properties in self._ssn_correction_alarms().items():
            with self.subTest(metric_name=metric_name):
                self.assertEqual('compact-connect', properties['Namespace'])
                self.assertEqual([{'Name': 'service', 'Value': 'common'}], properties['Dimensions'])
                self.assertEqual('Sum', properties['Statistic'])

    def test_alarm_descriptions_tell_an_operator_what_to_do(self):
        for metric_name, properties in self._ssn_correction_alarms().items():
            with self.subTest(metric_name=metric_name):
                self.assertIn('previousSSN', properties['AlarmDescription'])
