import * as crypto from 'crypto';
import { TReaderDocument } from '@csg-org/email-builder';
import { EnvironmentVariablesService } from '../environment-variables-service';

/**
 * Service for adding environment-specific banners and footers to email templates
 */
export class EnvironmentBannerService {
    private readonly environmentVariablesService = new EnvironmentVariablesService();

    /**
     * Inserts environment banner if current environment is non-production
     */
    public insertEnvironmentBannerIfNonProd(template: TReaderDocument): void {
        try {
            if (this.shouldShowBanner()) {
                this.insertBanner(template, this.getBannerText());
            }
        } catch (error) {
            // Log error but don't throw - email should still send without banner
            console.error('Error inserting environment banner:', error);
        }
    }

    /**
     * Inserts red "test email" footer if current environment is non-production
     */
    public insertTestEmailFooterIfNonProd(template: TReaderDocument): void {
        try {
            if (this.shouldShowBanner()) {
                this.insertTestWarningFooter(template);
            }
        } catch (error) {
            // Log error but don't throw - email should still send without footer
            console.error('Error inserting test email footer:', error);
        }
    }

    /**
     * Determines if banner/footer should be shown based on environment
     * Returns true for all environments except production
     */
    private shouldShowBanner(): boolean {
        try {
            const envName = this.environmentVariablesService.getEnvironmentName().toLowerCase().trim();

            // only show banner for non-production environments and if the environment is defined
            return envName !== 'prod' && envName !== '';
        } catch (error) {
            // If environment detection fails, default to not showing banner
            // (better to not show than to show the banner in a prod environment)
            console.error('Error detecting environment, defaulting to not showing banner:', error);
            return false;
        }
    }

    /**
     * Gets environment-specific banner text
     */
    private getBannerText(): string {
        return `⚠️ TEST: The info in this email is from a testing environment and is for testing purposes only.`;
    }

    /**
     * Inserts the environment banner at the top of the email template
     */
    private insertBanner(template: TReaderDocument, bannerText: string): void {
        const blockId = `block-environment-banner-${crypto.randomUUID()}`;

        template[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'backgroundColor': '#FFA726',
                    'color': '#000000',
                    'fontSize': 14,
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'padding': {
                        'top': 16,
                        'bottom': 16,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': `${bannerText}`,
                    'markdown': false
                }
            }
        };

        // Insert banner at the beginning of the email (before existing content)
        template['root']['data']['childrenIds'].unshift(blockId);
    }

    /**
     * Inserts the test email warning footer at the bottom of the email template
     */
    private insertTestWarningFooter(template: TReaderDocument): void {
        const blockId = `block-test-warning-footer-${crypto.randomUUID()}`;

        template[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': '#DA2525',
                    'fontSize': 13,
                    'fontWeight': 'normal',
                    'textAlign': 'center',
                    'padding': {
                        'top': 16,
                        'bottom': 24,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': 'You\'re viewing a test email.',
                    'markdown': false
                }
            }
        };

        // Insert footer at the end of the email (after existing content)
        template['root']['data']['childrenIds'].push(blockId);
    }
}
