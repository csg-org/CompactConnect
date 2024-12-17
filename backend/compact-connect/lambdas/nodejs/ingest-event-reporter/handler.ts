import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Lambda } from '../lib/lambda';


const lambda = new Lambda({
    dynamoDBClient: new DynamoDBClient(),
    sesClient: new SESClient(),
});

export const collectEvents = lambda.handler.bind(lambda);
