import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESv2Client } from '@aws-sdk/client-sesv2';
import { S3Client } from '@aws-sdk/client-s3';
import { Lambda } from './lambda';
const lambda = new Lambda({
    dynamoDBClient: new DynamoDBClient(),
    s3Client: new S3Client(),
    sesClient: new SESv2Client(),
});
export const customMessage = lambda.handler.bind(lambda);
//# sourceMappingURL=handler.js.map