import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { Lambda } from '../lib/lambda';

const lambda = new Lambda({ dynamoDBClient: new DynamoDBClient() });

export const collectEvents = lambda.handler.bind(lambda); //
