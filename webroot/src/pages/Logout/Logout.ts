//
//  Logout.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { AppModes } from '@/app.config';
import {
    authStorage,
    tokens,
    AuthTypes,
    AUTH_TYPE,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE,
    revokeCognitoRefreshToken
} from '@utils/auth';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';

@Component({
    name: 'Logout',
    components: {
        LoadingSpinner,
    },
})
export default class Logout extends Vue {
    //
    // Lifecycle
    //
    async created() {
        await this.logout();
    }

    //
    // Computed
    //
    get appMode(): AppModes {
        return this.$store.state.appMode;
    }

    get appGroupMode() {
        return this.$store.state.appGroupMode;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get workingUri(): string {
        return this.$route.query?.goto?.toString() || '';
    }

    get hostedLogoutUriStaff(): string {
        const {
            domain,
            cognitoAuthDomainStaff,
            cognitoClientIdStaff,
            cognitoAuthDomainStaffCosmo,
            cognitoClientIdStaffCosmo,
            cognitoAuthDomainStaffSw,
            cognitoClientIdStaffSw
        } = this.$envConfig;
        let cognitoAuthDomain = cognitoAuthDomainStaff;
        let cognitoClientId = cognitoClientIdStaff;

        // Adjust cognito params based on app mode
        if (this.appMode === AppModes.COSMETOLOGY) {
            cognitoAuthDomain = cognitoAuthDomainStaffCosmo;
            cognitoClientId = cognitoClientIdStaffCosmo;
        } else if (this.appMode === AppModes.SOCIAL_WORK) {
            cognitoAuthDomain = cognitoAuthDomainStaffSw;
            cognitoClientId = cognitoClientIdStaffSw;
        }

        // Create the logout URI
        const logoutLink = encodeURIComponent(`${(domain as string)}/Logout`);
        const logoutUriQuery = [
            `?client_id=${cognitoClientId}`,
            `&logout_uri=${logoutLink}`
        ].join('');
        const idpPath = '/logout';
        const logoutUri = `${cognitoAuthDomain}${idpPath}${logoutUriQuery}`;

        return logoutUri;
    }

    get loginURL(): string {
        const { domain } = this.$envConfig;

        return `${(domain as string)}/Dashboard`;
    }

    get hostedLogoutUriLicensee(): string {
        const { cognitoAuthDomainLicensee, cognitoClientIdLicensee } = this.$envConfig;
        const logoutUriQuery = [
            `?client_id=${cognitoClientIdLicensee}`,
            `&logout_uri=${encodeURIComponent(this.loginURL)}`
        ].join('');
        const idpPath = '/logout';
        const logoutUri = `${cognitoAuthDomainLicensee}${idpPath}${logoutUriQuery}`;

        return logoutUri;
    }

    get isLoggedIn(): boolean {
        return this.userStore.isLoggedIn;
    }

    //
    // Methods
    //
    async logout(): Promise<void> {
        if (this.isLoggedIn) {
            const isRemoteLoggedInAsLicenseeOnly = !authStorage.getItem(tokens.staff.AUTH_TOKEN);

            await this.logoutChecklist(isRemoteLoggedInAsLicenseeOnly);
            this.beginLogoutRedirectChain(isRemoteLoggedInAsLicenseeOnly);
        } else {
            await this.logoutChecklist(false);
            window.location.replace(this.loginURL);
        }
    }

    async logoutChecklist(isRemoteLoggedInAsLicenseeOnly): Promise<void> {
        const authType = (isRemoteLoggedInAsLicenseeOnly) ? AuthTypes.LICENSEE : AuthTypes.STAFF;

        this.stashWorkingUri();
        this.$store.dispatch('user/clearRefreshTokenTimeout');
        await this.revokeTokens(authType);
        this.unsetAnalyticsUser(); // Not awaiting analytics so it doesn't block other critical steps
        await this.$store.dispatch('user/logoutRequest', authType);
    }

    async revokeTokens(authType: AuthTypes): Promise<void> {
        await revokeCognitoRefreshToken(this.appMode, authType).catch((err) => Promise.resolve().then(() => {
            // https://console.statsig.com/3KcYv8LC2YCc1vsTkVi3Fb/metrics/metrics_catalog/Cognito%20Token%20Revocation%20Failure/event_count_custom?unitType=overall
            this.$analytics.logEvent('cognito_token_revoke_failed', 1, {
                authType,
                appMode: this.appMode,
                appGroupMode: this.appGroupMode,
                errorName: err?.name,
                errorCode: err?.code,
                httpStatus: err?.response?.status,
            });
        }).catch(() => {
            // Continue — analytics failures must never block logout
        }));
    }

    async unsetAnalyticsUser(): Promise<void> {
        await this.$analytics.updateUserAsync({}).catch(() => {
            // Continue
        });
    }

    stashWorkingUri(): void {
        const { workingUri } = this;
        const authType = authStorage.getItem(AUTH_TYPE);

        if (workingUri) {
            authStorage.setItem(AUTH_LOGIN_GOTO_PATH, workingUri);
            if (authType) {
                authStorage.setItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE, authType);
            }
        }
    }

    beginLogoutRedirectChain(isRemoteLoggedInAsLicenseeOnly): void {
        let logOutUrl = this.hostedLogoutUriStaff;

        if (isRemoteLoggedInAsLicenseeOnly) {
            logOutUrl = this.hostedLogoutUriLicensee;
        }

        window.location.replace(logOutUrl);
    }
}
