import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SESClient } from '@aws-sdk/client-ses';
import { S3Client } from '@aws-sdk/client-s3';
import { BaseEmailService } from '../../../lib/email/base-email-service';
import { describe, it, expect, beforeEach, jest } from '@jest/globals';

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

const asS3Client = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as S3Client;

// Create a concrete test implementation of BaseEmailService
class TestEmailService extends BaseEmailService {
    public generateTestEmail(): string {
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, 'Test Email');
        this.insertFooter(template);

        // Return the template for inspection
        return JSON.stringify(template);
    }
}

describe('BaseEmailService Environment Banner', () => {
    let emailService: TestEmailService;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockS3Client: ReturnType<typeof mockClient>;

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESClient);
        mockS3Client = mockClient(S3Client);

        // Reset environment variables
        delete process.env.ENVIRONMENT_NAME;
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';

        emailService = new TestEmailService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            s3Client: asS3Client(mockS3Client),
            compactConfigurationClient: {} as any,
            jurisdictionClient: {} as any
        });
    });

    // Helper methods to reduce test duplication
    const expectBannerPresent = (template: any) => {
        const childrenIds = template.root.data.childrenIds;

        expect(childrenIds.length).toBeGreaterThan(0);

        // Find banner block (should be first element)
        const bannerBlockId = childrenIds[0];
        const bannerBlock = template[bannerBlockId];

        expect(bannerBlock).toBeDefined();
        expect(bannerBlock.type).toBe('Text');
        expect(bannerBlock.data.style.backgroundColor).toBe('#FFA726');
        expect(bannerBlock.data.style.color).toBe('#000000');
        expect(bannerBlock.data.props.text).toContain('⚠️ TEST: The info in this email is from a testing environment');
    };

    const expectFooterPresent = (template: any) => {
        const childrenIds = template.root.data.childrenIds;

        // Find footer warning block (should be last element)
        const footerWarningBlockId = childrenIds[childrenIds.length - 1];
        const footerWarningBlock = template[footerWarningBlockId];

        expect(footerWarningBlock).toBeDefined();
        expect(footerWarningBlock.type).toBe('Text');
        expect(footerWarningBlock.data.props.text).toBe('You\'re viewing a test email.');
    };

    const expectNoBannerOrFooter = (templateJson: string) => {
        // Simply check that the banner text doesn't appear anywhere in the email content
        expect(templateJson).not.toContain('⚠️ TEST: The info in this email is from a testing environment');
        expect(templateJson).not.toContain('You\'re viewing a test email.');
    };

    const testEnvironment = (environmentName: string | undefined, shouldShowBanner: boolean, description: string) => {
        it(description, () => {
            // Set environment
            if (environmentName === undefined) {
                delete process.env.ENVIRONMENT_NAME;
            } else {
                process.env.ENVIRONMENT_NAME = environmentName;
            }

            const templateJson = emailService.generateTestEmail();
            const template = JSON.parse(templateJson);

            if (shouldShowBanner) {
                expectBannerPresent(template);
                expectFooterPresent(template);
            } else {
                expectNoBannerOrFooter(templateJson);
            }
        });
    };

    describe('Environment Banner Behavior', () => {
        // Test cases: [environmentName, shouldShowBanner, description]
        testEnvironment('beta', true, 'should include environment banner and footer in beta environment');
        testEnvironment('test', true, 'should include environment banner and footer in test environment');
        testEnvironment('prod', false, 'should NOT include environment banner and footer in production environment');
        testEnvironment(undefined, false, 'should NOT include environment banner and footer when environment name is undefined');
    });
});
