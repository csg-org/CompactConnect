import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { S3Client } from '@aws-sdk/client-s3';
import { Lambda } from '../cognito-emails/lambda';
import { CognitoEmailService } from '../lib/email';
import { describe, it, expect, beforeAll, beforeEach, jest } from '@jest/globals';

const SAMPLE_COGNITO_EVENT = {
    version: '1',
    triggerSource: 'CustomMessage_AdminCreateUser',
    region: 'us-east-1',
    userPoolId: 'us-east-1_123456789',
    userName: 'testuser',
    callerContext: {
        awsSdkVersion: '1.0',
        clientId: 'test-client-id'
    },
    request: {
        userAttributes: {
            email: 'test@example.com'
        },
        codeParameter: 'TEST-CODE-123',
        usernameParameter: 'testuser',
        clientMetadata: {}
    },
    response: {
        smsMessage: 'unchanged',
        emailMessage: 'unchanged',
        emailSubject: 'unchanged'
    }
};

const SAMPLE_CONTEXT = {
    callbackWaitsForEmptyEventLoop: true,
    functionVersion: '$LATEST',
    functionName: 'cognito-emails-function',
    memoryLimitInMB: '128',
    logGroupName: '/aws/lambda/cognito-emails-function',
    logStreamName: '2024/03/09/[$LATEST]abcdef123456',
    invokedFunctionArn: 'arn:aws:lambda:us-east-1:123456789012:function:cognito-emails-function',
    awsRequestId: 'c6af9ac6-7b61-11e6-9a41-93e812345678',
    getRemainingTimeInMillis: () => 1234,
    done: () => console.log('Done!'),
    fail: () => console.log('Failed!'),
    succeed: () => console.log('Succeeded!')
};

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;
const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;
const asS3Client = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as S3Client;

describe('CognitoEmailsLambda', () => {
    let lambda: Lambda;
    let mockDynamoDBClient: ReturnType<typeof mockClient>;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockS3Client: ReturnType<typeof mockClient>;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.AWS_REGION = 'us-east-1';
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockDynamoDBClient = mockClient(DynamoDBClient);
        mockSESClient = mockClient(SESClient);
        mockS3Client = mockClient(S3Client);

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient),
            s3Client: asS3Client(mockS3Client)
        });
    });

    it('should process AdminCreateUser event for provider users with 24-hour message', async () => {
        process.env.USER_POOL_TYPE = 'provider';

        const response = await lambda.handler(SAMPLE_COGNITO_EVENT, SAMPLE_CONTEXT);

        expect(response.response.emailSubject).toBe('Welcome to CompactConnect');
        expect(response.response.emailMessage).toContain('Your temporary password is:');
        expect(response.response.emailMessage).toContain('TEST-CODE-123');
        expect(response.response.emailMessage).toContain('Your username is:');
        expect(response.response.emailMessage).toContain('testuser');
        expect(response.response.emailMessage).toContain('This temporary password is valid for 24 hours');
        expect(response.response.emailMessage).toContain('within the next 24 hours');


    });

    it('should process AdminCreateUser event for staff users without time constraint message', async () => {
        process.env.USER_POOL_TYPE = 'staff';

        const response = await lambda.handler(SAMPLE_COGNITO_EVENT, SAMPLE_CONTEXT);

        expect(response.response.emailSubject).toBe('Welcome to CompactConnect');
        expect(response.response.emailMessage).toContain('Your temporary password is:');
        expect(response.response.emailMessage).toContain('TEST-CODE-123');
        expect(response.response.emailMessage).toContain('Your username is:');
        expect(response.response.emailMessage).toContain('testuser');
        expect(response.response.emailMessage).not.toContain('24 hours');
        expect(response.response.emailMessage).toContain('Please sign in at');
        expect(response.response.emailMessage).toContain('and change your password when prompted');
    });

    it('should process AdminCreateUser event for unknown user pool type without time constraint message', async () => {
        process.env.USER_POOL_TYPE = 'unknown';

        const response = await lambda.handler(SAMPLE_COGNITO_EVENT, SAMPLE_CONTEXT);

        expect(response.response.emailSubject).toBe('Welcome to CompactConnect');
        expect(response.response.emailMessage).toContain('Your temporary password is:');
        expect(response.response.emailMessage).toContain('TEST-CODE-123');
        expect(response.response.emailMessage).toContain('Your username is:');
        expect(response.response.emailMessage).toContain('testuser');
        expect(response.response.emailMessage).not.toContain('24 hours');
        expect(response.response.emailMessage).toContain('Please sign in at');
        expect(response.response.emailMessage).toContain('and change your password when prompted');
    });

    it('should handle ForgotPassword event', async () => {
        const forgotPasswordEvent = {
            ...SAMPLE_COGNITO_EVENT,
            triggerSource: 'CustomMessage_ForgotPassword'
        };

        const response = await lambda.handler(forgotPasswordEvent, SAMPLE_CONTEXT);

        expect(response.response.emailSubject).toBe('Reset your password');
        expect(response.response.emailMessage).toContain('You requested to reset your password');
        expect(response.response.emailMessage).toContain('TEST-CODE-123');
    });

    it('should handle missing code parameter', async () => {
        process.env.USER_POOL_TYPE = 'provider';

        const eventWithoutCode = {
            ...SAMPLE_COGNITO_EVENT,
            request: {
                ...SAMPLE_COGNITO_EVENT.request,
                codeParameter: undefined
            }
        };

        const response = await lambda.handler(eventWithoutCode, SAMPLE_CONTEXT);

        expect(response.response.emailSubject).toBe('Welcome to CompactConnect');
        expect(response.response.emailMessage).toContain('Your temporary password is:');
        expect(response.response.emailMessage).toContain('undefined'); // Since codeParameter is undefined
        expect(response.response.emailMessage).toContain('Your username is:');
        expect(response.response.emailMessage).toContain('testuser');
        expect(response.response.emailMessage).toContain('This temporary password is valid for 24 hours');

    });

    it('should handle unsupported trigger source', async () => {
        const unsupportedEvent = {
            ...SAMPLE_COGNITO_EVENT,
            triggerSource: 'UnsupportedTrigger'
        };

        await expect(lambda.handler(unsupportedEvent, SAMPLE_CONTEXT))
            .rejects
            .toThrow('Unsupported Cognito trigger source: UnsupportedTrigger');
    });
});
