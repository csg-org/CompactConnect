//
//  PublicDashboard.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import { AppModes } from '@/app.config';
import {
    authStorage,
    AuthTypes,
    getHostedLoginUri,
    createAuthCsrfState,
    createPkceChallenge,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE,
    AUTH_LOGIN_GOTO_COMPACT
} from '@utils/auth';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import Card from '@components/Card/Card.vue';
import SearchIcon from '@components/Icons/Search/Search.vue';
import RegisterIcon from '@components/Icons/RegisterAlt/RegisterAlt.vue';
import StaffUserIcon from '@components/Icons/StaffUser/StaffUser.vue';
import LicenseeUserIcon from '@components/Icons/LicenseeUser/LicenseeUser.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import { CompactConfig } from '@plugins/Compacts/compacts.plugin';
import { CompactType } from '@models/Compact/Compact.model';
import { FormInput } from '@models/FormInput/FormInput.model';

@Component({
    name: 'DashboardPublic',
    components: {
        InputSelect,
        Card,
        SearchIcon,
        RegisterIcon,
        StaffUserIcon,
        LicenseeUserIcon,
        InputButton,
    }
})
export default class DashboardPublic extends mixins(MixinForm) {
    //
    // Data
    //
    csrfState = '';
    pkceChallenge = '';

    //
    // Lifecycle
    //
    async created(): Promise<void> {
        this.csrfState = createAuthCsrfState();
        this.pkceChallenge = await createPkceChallenge();

        if (this.bypassQuery) {
            this.bypassRedirect();
        } else if (this.isAppTypeSelectorEnabled) {
            this.initAppTypeFormInputs();
        }
    }

    //
    // Computed
    //
    get compactTypes(): typeof CompactType {
        return CompactType;
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

    get appTypeOptions(): Array<{ value: string, name: string | ComputedRef }> {
        return [
            { value: 'compactconnect', name: computed(() => this.$t('common.appName')) },
            { value: 'psypact', name: 'PSYPACT' },
        ];
    }

    get isUsingMockApi(): boolean {
        return this.$envConfig.isUsingMockApi || false;
    }

    get isAppTypeSelectorEnabled(): boolean {
        return Boolean(this.$envConfig.isAppLocal);
    }

    //
    // Methods
    //
    initAppTypeFormInputs(): void {
        this.formData = reactive({
            appType: new FormInput({
                id: 'app-type-global',
                name: 'app-type-global',
                label: computed(() => this.$t('common.appTypeLabel')),
                shouldHideLabel: true,
                value: (this.$isAppModePsyPact) ? 'psypact' : 'compactconnect',
                valueOptions: this.appTypeOptions,
            }),
        });
    }

    bypassRedirect(): void {
        switch (this.bypassQuery) {
        case 'login-staff':
            this.bypassToStaffLogin(AppModes.JCC);
            break;
        case 'login-staff-cosmo':
            this.bypassToStaffLogin(AppModes.COSMETOLOGY);
            break;
        case 'login-staff-sw':
            this.bypassToStaffLogin(AppModes.SOCIAL_WORK);
            break;
        case 'login-staff-psypact':
            this.bypassToStaffLogin(AppModes.PSYPACT);
            break;
        case 'login-practitioner':
            this.bypassToLicenseeLogin(AppModes.JCC);
            break;
        case 'login-practitioner-psypact':
            this.bypassToLicenseeLogin(AppModes.PSYPACT);
            break;
        case 'recovery-practitioner':
            this.bypassToLicenseeMfaRecovery();
            break;
        default:
            // Continue
        }
    }

    staffLoginUri(appMode: AppModes): string {
        return getHostedLoginUri(
            appMode,
            AuthTypes.STAFF,
            this.hostedLoginUriPath,
            this.csrfState,
            this.pkceChallenge
        );
    }

    licenseeLoginUri(appMode: AppModes): string {
        return getHostedLoginUri(
            appMode,
            AuthTypes.LICENSEE,
            this.hostedLoginUriPath,
            this.csrfState,
            this.pkceChallenge
        );
    }

    bypassToStaffLogin(appMode: AppModes, compactType?: CompactType): void {
        if (this.isUsingMockApi) {
            if (compactType) {
                this.setGotoCompact(compactType);
            }
            this.mockStaffLogin(appMode);
        } else {
            this.$store.dispatch('startLoading');
            window.location.replace(this.staffLoginUri(appMode));
        }
    }

    bypassToLicenseeLogin(appMode: AppModes, compactType?: CompactType): void {
        if (this.isUsingMockApi) {
            if (compactType) {
                this.setGotoCompact(compactType);
            }
            this.mockLicenseeLogin(appMode);
        } else {
            this.$store.dispatch('startLoading');
            window.location.replace(this.licenseeLoginUri(appMode));
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

    getCompactDisplay(compact: CompactConfig): string {
        const shouldAddAbbrev = [
            CompactType.ASLP,
            CompactType.OT,
        ].includes(compact.type);
        let compactDisplay = compact.name || '';

        if (shouldAddAbbrev && compact.abbrev) {
            compactDisplay += ` (${compact.abbrev})`;
        }

        return compactDisplay.trim();
    }

    setGotoCompact(compactType: CompactType): void {
        if (compactType) {
            authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, compactType);
        }
    }

    async handleAppTypeSelect(): Promise<void> {
        const { appType } = this.formData || {};

        if (appType?.value === 'psypact') {
            await this.$store.dispatch('setAppMode', AppModes.PSYPACT);
        } else {
            await this.$store.dispatch('setAppMode', AppModes.JCC);
            await this.$store.dispatch('user/setCurrentCompact', null);
        }
    }

    async mockStaffLogin(appMode: AppModes): Promise<void> {
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
        this.$store.dispatch('setAppMode', appMode);
        await this.$store.dispatch('user/updateAuthTokens', { tokenResponse: data, authType: AuthTypes.STAFF });
        this.$store.dispatch('user/loginSuccess', AuthTypes.STAFF);

        if (goto && (!gotoAuthType || gotoAuthType === AuthTypes.STAFF)) {
            this.$router.push({ path: goto });
        } else {
            this.$router.push({ name: 'Home' });
        }
    }

    async mockLicenseeLogin(appMode: AppModes): Promise<void> {
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
        this.$store.dispatch('setAppMode', appMode);
        await this.$store.dispatch('user/updateAuthTokens', { tokenResponse: data, authType: AuthTypes.LICENSEE });
        this.$store.dispatch('user/loginSuccess', AuthTypes.LICENSEE);

        if (goto && (!gotoAuthType || gotoAuthType === AuthTypes.LICENSEE)) {
            this.$router.push({ path: goto });
        } else {
            this.$router.push({ name: 'Home' });
        }
    }
}
