from enum import Enum


class ServicePrincipalName(Enum):
    CLOUD_FORMATION = 'cloudformation.amazonaws.com'
    CLOUD_TRAIL = 'cloudtrail.amazonaws.com'
    CLOUD_WATCH = 'cloudwatch.amazonaws.com'
    DYNAMODB = 'dynamodb.amazonaws.com'
    LAMBDA = 'lambda.amazonaws.com'
    LOGS_DELIVERY = 'delivery.logs.amazonaws.com'
    LOGS = 'logs.amazonaws.com'
    S3 = 's3.amazonaws.com'
