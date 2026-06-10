from unittest import TestCase

from common_constructs.service_principal_name import ServicePrincipalName


class TestServicePrincipalName(TestCase):
    def test_lambda_principal_value(self):
        self.assertEqual('lambda.amazonaws.com', ServicePrincipalName.LAMBDA.value)

    def test_dynamodb_principal_value(self):
        self.assertEqual('dynamodb.amazonaws.com', ServicePrincipalName.DYNAMODB.value)

    def test_logs_delivery_principal_value(self):
        self.assertEqual('delivery.logs.amazonaws.com', ServicePrincipalName.LOGS_DELIVERY.value)

    def test_s3_principal_value(self):
        self.assertEqual('s3.amazonaws.com', ServicePrincipalName.S3.value)

    def test_all_members_have_expected_service_arn_suffix(self):
        for member in ServicePrincipalName:
            self.assertTrue(
                member.value.endswith('.amazonaws.com'),
                f'{member.name} value should be an AWS service principal: {member.value}',
            )
