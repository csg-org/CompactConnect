import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SESv2Client } from '@aws-sdk/client-sesv2';
import { CognitoEmailService } from '../../../lib/email';
import { EmailTemplateCapture } from '../../utils/email-template-capture';
import { TReaderDocument } from '@csg-org/email-builder';
import { describe, it, beforeEach, beforeAll, afterAll, jest } from '@jest/globals';

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

describe('CognitoEmailService', () => {
    let emailService: CognitoEmailService;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeAll(() => {
        // Mock the renderTemplate method if template capture is enabled
        if (EmailTemplateCapture.isEnabled()) {
            const original = (CognitoEmailService.prototype as any).renderTemplate;

            jest.spyOn(CognitoEmailService.prototype as any, 'renderTemplate').mockImplementation(function (this: any, ...args: any[]) {
                const [template, options] = args as [TReaderDocument, any];

                EmailTemplateCapture.captureTemplate(template);
                const html = original.apply(this, args);

                EmailTemplateCapture.captureHtml(html, template, options);
                return html;
            });
        }
    });

    afterAll(() => {
        if (EmailTemplateCapture.isEnabled()) {
            jest.restoreAllMocks();
        }
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESv2Client);

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
                    '{####}',
                    'testuser'
                );

                expect(subject).toBe('Welcome to CompactConnect');
                expect(htmlContent).toContain('Your temporary password is:');
                expect(htmlContent).toContain('{####}');
                expect(htmlContent).toContain('Your username is:');
                expect(htmlContent).toContain('testuser');
                expect(htmlContent).toContain('This temporary password is valid for 24 hours');
                expect(htmlContent).toContain('within the next 24 hours');
                expect(htmlContent).toContain('<a href="https://app.test.compactconnect.org/Dashboard?bypass=login-practitioner" target="_blank">sign in</a>');
                expect(htmlContent).toContain('<a href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2" target="_blank">Android</a>');
            });

            it('should generate AdminCreateUser message for staff users with immediate login message', () => {
                process.env.USER_POOL_TYPE = 'staff';

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
                expect(htmlContent).toContain('Please immediately');
                expect(htmlContent).toContain('and change your password when prompted');
                expect(htmlContent).toContain('<a href="https://app.test.compactconnect.org/Dashboard?bypass=login-staff" target="_blank">sign in</a>');
            });

            it('should generate AdminCreateUser message for unknown user pool type with immediate login message', () => {
                process.env.USER_POOL_TYPE = 'unknown';

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
                expect(htmlContent).toContain('Please immediately');
                expect(htmlContent).toContain('and change your password when prompted');
                expect(htmlContent).toContain('<a href="https://app.test.compactconnect.org/Dashboard?bypass=login-staff" target="_blank">sign in</a>');
            });
        });

        it('should generate ForgotPassword message', () => {
            const { subject, htmlContent } = emailService.generateCognitoMessage(
                'CustomMessage_ForgotPassword',
                '{####}'
            );

            expect(subject).toBe('Reset your password');
            expect(htmlContent).toContain('You requested to reset your password');
            expect(htmlContent).toContain('{####}');
            expect(htmlContent).toContain('<strong>Important:</strong> If you have lost access to your multi-factor authentication (MFA), you will need to recover your account by visiting the following link instead:');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/mfarecoverystart');
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
