import json
import os
from typing import Mapping
from unittest import TestCase

from app import CompactConnectApp


class TestApi(TestCase):
    """
    Base API test class with common methods for Compact Connect API resources.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = cls._when_testing_sandbox_stack_app()

    @classmethod
    def _when_testing_sandbox_stack_app(cls):
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        return app
    @staticmethod
    def _get_resource_properties_by_logical_id(logical_id: str, resources: Mapping[str, Mapping]) -> Mapping:
        """
        Helper function to retrieve a resource from a CloudFormation template by its logical ID.
        """""
        try:
            return resources[logical_id]['Properties']
        except KeyError as exc:
            raise RuntimeError(f'{logical_id} not found in resources!') from exc

    @staticmethod
    def _generate_expected_integration_object(handler_logical_id: str) -> dict:
        return {
            "Uri": {
                "Fn::Join": [
                    "",
                    [
                        "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/",
                        {
                            "Fn::GetAtt": [handler_logical_id, "Arn"]
                        },
                        "/invocations"
                    ]
                ]
            }
        }

    def compare_snapshot(self, actual: dict, snapshot_name: str, overwrite_snapshot: bool = False):
        """
        Compare the actual dictionary to the snapshot with the given name.
        If overwrite_snapshot is True, overwrite the snapshot with the actual data.
        """
        snapshot_path = os.path.join('tests', 'resources', 'snapshots', f'{snapshot_name}.json')

        if os.path.exists(snapshot_path):
            with open(snapshot_path, 'r') as f:
                snapshot = json.load(f)
        else:
            print(f"Snapshot at path '{snapshot_path}' does not exist.")
            snapshot = None

        if snapshot != actual and overwrite_snapshot:
            with open(snapshot_path, 'w') as f:
                json.dump(actual, f, indent=2)
            print(f"Snapshot '{snapshot_name}' has been overwritten.")
        else:
            self.maxDiff = None #pylint: disable=invalid-name
            self.assertEqual(snapshot, actual, f"Snapshot '{snapshot_name}' does not match the actual data. "
                                               "To overwrite the snapshot, set overwrite_snapshot=True.")
