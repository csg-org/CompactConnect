import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SESClient } from '@aws-sdk/client-ses';
import { CognitoEmailService } from '../../../lib/email';
import { describe, it, expect, beforeEach, jest } from '@jest/globals';

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

describe('CognitoEmailService', () => {
    let emailService: CognitoEmailService;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESClient);

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';
        process.env.USER_POOL_TYPE = 'provider'; // Set default for tests

        emailService = new CognitoEmailService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            s3Client: {} as any,
            compactConfigurationClient: {} as any,
            jurisdictionClient: {} as any
        });
    });

    describe('generateCognitoMessage', () => {
        it('should generate AdminCreateUser message for provider users', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_AdminCreateUser',
                '{####}',
                'testuser'
            );

            expect(subject).toBe('Welcome to CompactConnect');
            expect(htmlContent).toContain('Your temporary password is:');
            expect(htmlContent).toContain('{####}');
            expect(htmlContent).toContain('Your username is:');
            expect(htmlContent).toContain('testuser');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard?bypass=login-practitioner');

        });

        it('should generate AdminCreateUser message for staff users', () => {
            // Set up for staff user type
            process.env.USER_POOL_TYPE = 'staff';
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_AdminCreateUser',
                '{####}',
                'staffuser'
            );

            expect(subject).toBe('Welcome to CompactConnect');
            expect(htmlContent).toContain('Your temporary password is:');
            expect(htmlContent).toContain('{####}');
            expect(htmlContent).toContain('Your username is:');
            expect(htmlContent).toContain('staffuser');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard?bypass=login-staff');
        });

        it('should generate ForgotPassword message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_ForgotPassword',
                '{####}'
            );

            expect(subject).toBe('Reset your password');
            expect(htmlContent).toContain('Enter the following code to proceed:');
            expect(htmlContent).toContain('{####}');
        });

        it('should generate UpdateUserAttribute message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_UpdateUserAttribute',
                '{####}'
            );

            expect(subject).toBe('Verify your email');
            expect(htmlContent).toContain('Please verify your new email address by entering the following code:');
            expect(htmlContent).toContain('{####}');
        });

        it('should generate VerifyUserAttribute message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_VerifyUserAttribute',
                '{####}'
            );

            expect(subject).toBe('Verify your email');
            expect(htmlContent).toContain('Please verify your email address by entering the following code:');
            expect(htmlContent).toContain('{####}');
        });

        it('should generate ResendCode message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_ResendCode',
                '{####}'
            );

            expect(subject).toBe('New verification code for CompactConnect');
            expect(htmlContent).toContain('Your new verification code is:');
            expect(htmlContent).toContain('{####}');
        });

        it('should generate SignUp message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_SignUp',
                '{####}'
            );

            expect(subject).toBe('Welcome to CompactConnect');
            expect(htmlContent).toContain('Please verify your email address by entering the following code:');
            expect(htmlContent).toContain('{####}');
        });

        it('should throw error for unsupported trigger source', () => {
            expect(() => emailService.generateCognitoMessage('UnsupportedTrigger'))
                .toThrow('Unsupported Cognito trigger source: UnsupportedTrigger');
        });
    });
});
