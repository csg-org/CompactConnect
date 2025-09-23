import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';

const environmentVariableService = new EnvironmentVariablesService();

/**
 * Email service for handling Cognito custom messages
 */
export class CognitoEmailService extends BaseEmailService {
    // We don't want to show the environment banner for Cognito emails
    // so that users know the welcome email is valid and not a test email
    protected readonly shouldShowEnvironmentBannerIfNonProdEnvironment: boolean = false;
    /**
     * Generates the appropriate email template based on Cognito trigger source
     * @param triggerSource - The Cognito trigger source
     * @param codeParameter - The code parameter to include in the message (if applicable)
     * @param usernameParameter - The username parameter to include in the message (if applicable)
     * @returns An object containing the subject and HTML content for the email
     */
    public generateCognitoMessage(
        triggerSource: string,
        codeParameter?: string,
        usernameParameter?: string
    ): { subject: string; htmlContent: string } {
        /*
         * We don't actually anticipate using all of these triggers, but we're including them just to avoid breaking
         * any Cognito flows.
         */
        switch (triggerSource) {
        // Sent as an invite, after a user is created by our API.
        // Based on the triggerSource value, we know which parameters are defined, so we will
        // assert that they are defined for each particular template.
        case 'CustomMessage_AdminCreateUser':
            return this.generateAdminCreateUserTemplate(codeParameter!, usernameParameter!);
        // Sent if a user requests to reset their password
        case 'CustomMessage_ForgotPassword':
            return this.generateForgotPasswordTemplate(codeParameter!);
        // Sent if a user changes their email attribute
        case 'CustomMessage_UpdateUserAttribute':
            return this.generateUpdateUserAttributeTemplate(codeParameter!);
        // These next ones, we don't anticipate actually using
        case 'CustomMessage_VerifyUserAttribute':
            return this.generateVerifyUserAttributeTemplate(codeParameter!);
        case 'CustomMessage_ResendCode':
            return this.generateResendCodeTemplate(codeParameter!);
        case 'CustomMessage_SignUp':
            return this.generateSignUpTemplate(codeParameter!);
        default:
            throw new Error(`Unsupported Cognito trigger source: ${triggerSource}`);
        }
    }

    /**
     * Generates a template for when an admin creates a new user
     */
    private generateAdminCreateUserTemplate(
        codeParameter: string,
        usernameParameter: string
    ): { subject: string; htmlContent: string } {
        const subject = 'Welcome to CompactConnect';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        const userPoolType = environmentVariableService.getUserPoolType();

        let loginText: string;

        if (userPoolType === 'provider') {
            const loginUrl = `${environmentVariableService.getUiBasePathUrl()}/Dashboard?bypass=login-practitioner`;

            loginText = `This temporary password is valid for 24 hours. Please sign in at [${loginUrl}](${loginUrl}) within the next 24 hours and change your password when prompted.`;
        } else {
            const loginUrl = `${environmentVariableService.getUiBasePathUrl()}/Dashboard?bypass=login-staff`;

            loginText = `Please immediately sign in at [${loginUrl}](${loginUrl}) and change your password when prompted.`;
        }
        this.insertBody(template,
            `Your temporary password is: \n**${codeParameter}**\n\nYour username is: \n**${usernameParameter}**\n`,
            'center',
            true,
            {
                'padding': {
                    'top': '8',
                    'bottom': '8',
                    'right': '40',
                    'left': '40',
                }
            }
        );

        this.insertBody(template,
            loginText,
            'center',
            true,
            {
                'size': 14,
                'color': '#727272',
                'padding': {
                    'top': '8',
                    'bottom': '16',
                    'right': '40',
                    'left': '40',
                }
            }
        );

        // Add MFA instructions block
        this.insertStyledBlock(template, {
            blockType: 'warning',
            title: 'Multi-Factor Authentication (MFA) Required',
            content: `For security, you'll need to set up Multi-Factor Authentication (MFA) after you first login. MFA adds an extra layer of security by requiring a second form of verification.

**What is an Authenticator App?**
An authenticator app generates time-based codes that change every 30 seconds. You'll use these codes along with your password to sign in.

**Recommended Authenticator Apps:**
- **Google Authenticator** - [Android](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2) | [iOS](https://apps.apple.com/app/google-authenticator/id388497605)
- **Microsoft Authenticator** - [Android](https://play.google.com/store/apps/details?id=com.azure.authenticator) | [iOS](https://apps.apple.com/app/microsoft-authenticator/id983156458)
- **Authy** - [Android](https://play.google.com/store/apps/details?id=com.authy.authy) | [iOS](https://apps.apple.com/app/authy/id494168017)

**Setup Steps:**
1) Download one of the authenticator apps above
2) Click the sign-in link above to CompactConnect with your temporary credentials
3) Follow the MFA setup prompts when you first log in

**How to Login with MFA (After Setup):**
1) Go to ${environmentVariableService.getUiBasePathUrl()}
2) Enter your username and password as usual
3) When prompted, open your authenticator app
4) Find the "CompactConnect" entry you created during setup in your authenticator app
5) Enter the current 6-digit code (code refreshes every 30 seconds)
6) Click "Verify" to complete your login`
        });

        this.insertFooter(template);

        return {
            subject,
            htmlContent: this.renderTemplate(template)
        };
    }

    /**
     * Generates a template for password reset requests
     */
    private generateForgotPasswordTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Reset your password';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'You requested to reset your password. Enter the following code to proceed:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertBody(template,
            `**Important:** If you have lost access to your multi-factor authentication (MFA), you will need to recover your account by visiting the following link instead: ${environmentVariableService.getUiBasePathUrl()}/mfarecoverystart`,
            'center',
            true
        );
        this.insertFooter(template);

        return {
            subject,
            htmlContent: this.renderTemplate(template)
        };
    }

    /**
     * Generates a template for email attribute updates
     */
    private generateUpdateUserAttributeTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Verify your email';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Please verify your new email address by entering the following code:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: this.renderTemplate(template)
        };
    }

    /**
     * Generates a template for user attribute verification
     * Note: Not anticipated to be used in normal flows
     */
    private generateVerifyUserAttributeTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Verify your email';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Please verify your email address by entering the following code:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: this.renderTemplate(template)
        };
    }

    /**
     * Generates a template for code resend requests
     * Note: Not anticipated to be used in normal flows
     */
    private generateResendCodeTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'New verification code for CompactConnect';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Your new verification code is:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: this.renderTemplate(template)
        };
    }

    /**
     * Generates a template for new user sign-ups
     * Note: Not anticipated to be used in normal flows
     */
    private generateSignUpTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Welcome to CompactConnect';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Please verify your email address by entering the following code:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: this.renderTemplate(template)
        };
    }
}
