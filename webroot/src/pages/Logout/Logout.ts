//
//  Logout.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import {
    authStorage,
    AUTH_LOGIN_GOTO_PATH,
    AuthTypes,
    tokens
} from '@/app.config';

@Component({
    name: 'Logout',
    components: {}
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
    get userStore() {
        return this.$store.state.user;
    }

    get workingUri(): string {
        return this.$route.query?.goto?.toString() || '';
    }

    get hostedLogoutUriStaff(): string {
        const { domain, cognitoAuthDomainStaff, cognitoClientIdStaff } = this.$envConfig;
        const logoutLink = encodeURIComponent(`${(domain as string)}/Logout`);
        const logoutUriQuery = [
            `?client_id=${cognitoClientIdStaff}`,
            `&logout_uri=${logoutLink}`
        ].join('');
        const idpPath = '/logout';
        const logoutUri = `${cognitoAuthDomainStaff}${idpPath}${logoutUriQuery}`;

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
            window.location.replace(this.loginURL);
        }
    }

    async logoutChecklist(isRemoteLoggedInAsLicenseeOnly): Promise<void> {
        const authType = isRemoteLoggedInAsLicenseeOnly ? AuthTypes.LICENSEE : AuthTypes.STAFF;

        this.$store.dispatch('user/clearRefreshTokenTimeout');
        this.stashWorkingUri();
        await this.$store.dispatch('user/logoutRequest', authType);
    }

    stashWorkingUri(): void {
        const { workingUri } = this;

        if (workingUri) {
            authStorage.setItem(AUTH_LOGIN_GOTO_PATH, workingUri);
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
