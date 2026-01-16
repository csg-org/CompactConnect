import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESv2Client } from '@aws-sdk/client-sesv2';
import { Lambda } from './lambda';


const lambda = new Lambda({
    dynamoDBClient: new DynamoDBClient(),
    sesClient: new SESv2Client(),
});

export const sendEmail = lambda.handler.bind(lambda);
