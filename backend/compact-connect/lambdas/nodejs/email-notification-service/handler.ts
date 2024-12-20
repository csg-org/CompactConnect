import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Lambda } from './email-notification-service-lambda';


const lambda = new Lambda({
    dynamoDBClient: new DynamoDBClient(),
    sesClient: new SESClient(),
});

export const sendEmail = lambda.handler.bind(lambda);
