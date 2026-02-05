//
//  PublicDashboard.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import {
    authStorage,
    AppModes,
    AuthTypes,
    getHostedLoginUri,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE
} from '@/app.config';
import SearchIcon from '@components/Icons/Search/Search.vue';
import RegisterIcon from '@components/Icons/RegisterAlt/RegisterAlt.vue';
import StaffUserIcon from '@components/Icons/StaffUser/StaffUser.vue';
import LicenseeUserIcon from '@components/Icons/LicenseeUser/LicenseeUser.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'DashboardPublic',
    components: {
        SearchIcon,
        RegisterIcon,
        StaffUserIcon,
        LicenseeUserIcon,
        InputButton,
    }
})
export default class DashboardPublic extends Vue {
    //
    // Lifecycle
    //
    created(): void {
        if (this.bypassQuery) {
            this.bypassRedirect();
        }
    }

    //
    // Computed
    //
    get appMode(): AppModes {
        return this.$store.state.appMode;
    }

    get bypassQuery(): string {
        const bypass: string = (this.$route.query?.bypass as string) || '';

        return bypass.toLowerCase();
    }

    get shouldRemoteLogout(): boolean {
        const logoutQuery: string = (this.$route.query?.logout as string) || '';

        return logoutQuery.toLowerCase() === 'true';
    }

    get hostedLoginUriPath(): string {
        return (this.shouldRemoteLogout) ? '/logout' : '/login';
    }

    get hostedLoginUriStaff(): string {
        return getHostedLoginUri(AppModes.JCC, AuthTypes.STAFF, this.hostedLoginUriPath);
    }

    get hostedLoginUriStaffCosmo(): string {
        return getHostedLoginUri(AppModes.COSMETOLOGY, AuthTypes.STAFF, this.hostedLoginUriPath);
    }

    get hostedLoginUriLicensee(): string {
        return getHostedLoginUri(AppModes.JCC, AuthTypes.LICENSEE, this.hostedLoginUriPath);
    }

    get isUsingMockApi(): boolean {
        return this.$envConfig.isUsingMockApi || false;
    }

    //
    // Methods
    //
    bypassRedirect(): void {
        switch (this.bypassQuery) {
        case 'login-staff':
            this.bypassToStaffLogin();
            break;
        case 'login-staff-cosmo':
            this.bypassToStaffLoginCosmo();
            break;
        case 'login-practitioner':
            this.bypassToLicenseeLogin();
            break;
        case 'recovery-practitioner':
            this.bypassToLicenseeMfaRecovery();
            break;
        default:
            // Continue
        }
    }

    bypassToStaffLogin(): void {
        if (this.isUsingMockApi) {
            this.mockStaffLogin();
        } else {
            this.$store.dispatch('startLoading');
            window.location.replace(this.hostedLoginUriStaff);
        }
    }

    bypassToStaffLoginCosmo(): void {
        if (this.isUsingMockApi) {
            this.mockStaffLogin(AppModes.COSMETOLOGY);
        } else {
            this.$store.dispatch('startLoading');
            window.location.replace(this.hostedLoginUriStaffCosmo);
        }
    }

    bypassToLicenseeLogin(): void {
        if (this.isUsingMockApi) {
            this.mockLicenseeLogin();
        } else {
            this.$store.dispatch('startLoading');
            window.location.replace(this.hostedLoginUriLicensee);
        }
    }

    bypassToLicenseeMfaRecovery(): void {
        const { compact, providerId, recoveryId } = this.$route.query;

        this.$router.replace({
            name: 'MfaResetConfirmLicensee',
            query: {
                compact,
                providerId,
                recoveryId,
            },
        });
    }

    async mockStaffLogin(appMode = AppModes.JCC): Promise<void> {
        const goto = authStorage.getItem(AUTH_LOGIN_GOTO_PATH);
        const gotoAuthType = authStorage.getItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        const data = {
            access_token: 'mock_access_token',
            token_type: 'Bearer',
            expires_in: '100000000',
            id_token: 'mock_id_token',
            refresh_token: 'mock_refresh_token'
        };

        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        await this.$store.dispatch('user/updateAuthTokens', { tokenResponse: data, authType: AuthTypes.STAFF });
        this.$store.dispatch('user/loginSuccess', AuthTypes.STAFF);
        this.$store.dispatch('setAppMode', appMode);

        if (goto && (!gotoAuthType || gotoAuthType === AuthTypes.STAFF)) {
            this.$router.push({ path: goto });
        } else {
            this.$router.push({ name: 'Home' });
        }
    }

    async mockLicenseeLogin(): Promise<void> {
        const goto = authStorage.getItem(AUTH_LOGIN_GOTO_PATH);
        const gotoAuthType = authStorage.getItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        const data = {
            access_token: 'mock_access_token',
            token_type: 'Bearer',
            expires_in: '100000000',
            id_token: 'mock_id_token',
            refresh_token: 'mock_refresh_token'
        };

        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        await this.$store.dispatch('user/updateAuthTokens', { tokenResponse: data, authType: AuthTypes.LICENSEE });
        this.$store.dispatch('user/loginSuccess', AuthTypes.LICENSEE);

        if (goto && (!gotoAuthType || gotoAuthType === AuthTypes.LICENSEE)) {
            this.$router.push({ path: goto });
        } else {
            this.$router.push({ name: 'Home' });
        }
    }
}
