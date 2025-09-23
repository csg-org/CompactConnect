import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SESClient } from '@aws-sdk/client-ses';
import { CognitoEmailService } from '../../../lib/email';
import { EmailTemplateCapture } from '../../utils/email-template-capture';
import { describe, it, expect, beforeEach, beforeAll, jest } from '@jest/globals';

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

describe('CognitoEmailService', () => {
    let emailService: CognitoEmailService;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeAll(() => {
        // Mock the renderTemplate method if template capture is enabled
        if (EmailTemplateCapture.isEnabled()) {
            jest.spyOn(CognitoEmailService.prototype as any, 'renderTemplate')
                .mockImplementation(EmailTemplateCapture.mockRenderTemplate);
        }
    });

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
        describe('AdminCreateUser template', () => {
            it('should generate AdminCreateUser message for provider users with 24-hour message', () => {
                process.env.USER_POOL_TYPE = 'provider';

                const { subject, htmlContent } = emailService.generateCognitoMessage(
                    'CustomMessage_AdminCreateUser',
                    'TEST-CODE-123',
                    'testuser'
                );

                expect(subject).toBe('Welcome to CompactConnect');
                expect(htmlContent).toContain('Your temporary password is:');
                expect(htmlContent).toContain('TEST-CODE-123');
                expect(htmlContent).toContain('Your username is:');
                expect(htmlContent).toContain('testuser');
                expect(htmlContent).toContain('This temporary password is valid for 24 hours');
                expect(htmlContent).toContain('within the next 24 hours');
                expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard?bypass=login-practitioner');
            });

            it('should generate AdminCreateUser message for staff users with immediate login message', () => {
                process.env.USER_POOL_TYPE = 'staff';

                const { subject, htmlContent } = emailService.generateCognitoMessage(
                    'CustomMessage_AdminCreateUser',
                    'TEST-CODE-123',
                    'testuser'
                );

                expect(subject).toBe('Welcome to CompactConnect');
                expect(htmlContent).toContain('Your temporary password is:');
                expect(htmlContent).toContain('TEST-CODE-123');
                expect(htmlContent).toContain('Your username is:');
                expect(htmlContent).toContain('testuser');
                expect(htmlContent).toContain('Please immediately sign in at');
                expect(htmlContent).toContain('and change your password when prompted');
                expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard?bypass=login-staff');
            });

            it('should generate AdminCreateUser message for unknown user pool type with immediate login message', () => {
                process.env.USER_POOL_TYPE = 'unknown';

                const { subject, htmlContent } = emailService.generateCognitoMessage(
                    'CustomMessage_AdminCreateUser',
                    'TEST-CODE-123',
                    'testuser'
                );

                expect(subject).toBe('Welcome to CompactConnect');
                expect(htmlContent).toContain('Your temporary password is:');
                expect(htmlContent).toContain('TEST-CODE-123');
                expect(htmlContent).toContain('Your username is:');
                expect(htmlContent).toContain('testuser');
                expect(htmlContent).toContain('Please immediately sign in at');
                expect(htmlContent).toContain('and change your password when prompted');
                expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard?bypass=login-staff');
            });
        });

        it('should generate ForgotPassword message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_ForgotPassword',
                'TEST-CODE-123'
            );

            expect(subject).toBe('Reset your password');
            expect(htmlContent).toContain('You requested to reset your password');
            expect(htmlContent).toContain('TEST-CODE-123');
            expect(htmlContent).toContain('<strong>Important:</strong> If you have lost access to your multi-factor authentication (MFA), you will need to recover your account by visiting the following link instead:');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/mfarecoverystart');
        });

        it('should generate UpdateUserAttribute message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_UpdateUserAttribute',
                'TEST-CODE-123'
            );

            expect(subject).toBe('Verify your email');
            expect(htmlContent).toContain('Please verify your new email address by entering the following code:');
            expect(htmlContent).toContain('TEST-CODE-123');
        });

        it('should generate VerifyUserAttribute message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_VerifyUserAttribute',
                'TEST-CODE-123'
            );

            expect(subject).toBe('Verify your email');
            expect(htmlContent).toContain('Please verify your email address by entering the following code:');
            expect(htmlContent).toContain('TEST-CODE-123');
        });

        it('should generate ResendCode message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_ResendCode',
                'TEST-CODE-123'
            );

            expect(subject).toBe('New verification code for CompactConnect');
            expect(htmlContent).toContain('Your new verification code is:');
            expect(htmlContent).toContain('TEST-CODE-123');
        });

        it('should generate SignUp message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_SignUp',
                'TEST-CODE-123'
            );

            expect(subject).toBe('Welcome to CompactConnect');
            expect(htmlContent).toContain('Please verify your email address by entering the following code:');
            expect(htmlContent).toContain('TEST-CODE-123');
        });

        it('should throw error for unsupported trigger source', () => {
            expect(() => emailService.generateCognitoMessage('UnsupportedTrigger'))
                .toThrow('Unsupported Cognito trigger source: UnsupportedTrigger');
        });
    });
});
