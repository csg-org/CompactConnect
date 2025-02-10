import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { S3Client } from '@aws-sdk/client-s3';
import { Lambda } from './email-notification-service-lambda';


const lambda = new Lambda({
    dynamoDBClient: new DynamoDBClient(),
    s3Client: new S3Client(),
    sesClient: new SESClient(),
});

export const sendEmail = lambda.handler.bind(lambda);
