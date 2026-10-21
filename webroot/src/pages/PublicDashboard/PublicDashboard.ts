//
//  PublicDashboard.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue, Watch } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
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
import AppTypeSelector from '@components/AppTypeSelector/AppTypeSelector.vue';
import Card from '@components/Card/Card.vue';
import SearchIcon from '@components/Icons/Search/Search.vue';
import StaffUserIcon from '@components/Icons/StaffUser/StaffUser.vue';
import LicenseeUserIcon from '@components/Icons/LicenseeUser/LicenseeUser.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import { CompactConfig } from '@plugins/Compacts/compacts.plugin';
import { CompactSerializer, CompactType } from '@models/Compact/Compact.model';
import { FormInput } from '@models/FormInput/FormInput.model';

@Component({
    name: 'DashboardPublic',
    components: {
        AppTypeSelector,
        Card,
        SearchIcon,
        StaffUserIcon,
        LicenseeUserIcon,
        InputSelect,
    }
})
export default class DashboardPublic extends Vue {
    //
    // Data
    //
    csrfState = '';
    pkceChallenge = '';
    selectedCompactType: CompactType | null = null;
    formData: any = {};

    //
    // Lifecycle
    //
    async created(): Promise<void> {
        this.csrfState = createAuthCsrfState();
        this.pkceChallenge = await createPkceChallenge();

        const currentCompactType = this.$store.state.user.currentCompact?.type as CompactType | undefined;
        const isCurrentCompactAvailable = Boolean(
            currentCompactType && this.compactList.some((compact) => compact.type === currentCompactType)
        );

        if (this.$isAppModePsyPact) {
            await this.selectCompact(CompactType.PSYPACT);
        } else if (isCurrentCompactAvailable) {
            await this.selectCompact(currentCompactType as CompactType);
        }

        if (this.bypassQuery) {
            this.bypassRedirect();
        }
    }

    //
    // Computed
    //
    get appMode(): AppModes {
        return this.$appMode;
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

    get isUsingMockApi(): boolean {
        return this.$envConfig.isUsingMockApi || false;
    }

    get isAppTypeSelectorEnabled(): boolean {
        return Boolean(this.$envConfig.isAppLocal);
    }

    get compactList(): Array<CompactConfig> {
        let list: Array<CompactConfig> = [];

        if (this.$isAppModePsyPact) {
            list = this.$compactsEnabled.filter((compact) => compact.type === CompactType.PSYPACT);
        } else {
            list = [...this.$compactsEnabledCompactConnect];
        }

        list.sort((a, b) => this.getCompactDisplay(a).localeCompare(this.getCompactDisplay(b)));

        return list;
    }

    get compactSelectOptions(): Array<{ value: string, name: string }> {
        const options = this.compactList.map((compact) => ({
            value: compact.type,
            name: this.getCompactDisplay(compact),
        }));

        return options;
    }

    get selectedCompact(): CompactConfig | null {
        const selected = this.compactList.find((compact) => compact.type === this.selectedCompactType) || null;

        return selected;
    }

    get isCompactSelected(): boolean {
        return Boolean(this.selectedCompact);
    }

    get shouldShowCompactSelect(): boolean {
        return this.isCompactSelected && this.compactList.length > 1;
    }

    get selectedAppMode(): AppModes {
        return this.selectedCompact?.appMode || this.$appMode;
    }

    get hasPractitionerLogin(): boolean {
        const { selectedAppMode } = this;
        const hasLogin = selectedAppMode === AppModes.JCC || selectedAppMode === AppModes.PSYPACT;

        return hasLogin;
    }

    get publicLookupHeadingTag(): string {
        return (this.shouldShowCompactSelect) ? 'h2' : 'h1';
    }

    get publicLookupHeadingId(): string {
        return (this.shouldShowCompactSelect) ? 'public-lookup-heading' : 'dashboard-step-heading';
    }

    //
    // Methods
    //
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

    initCompactSelect(): void {
        this.formData = reactive({
            compact: new FormInput({
                id: 'compact-dashboard',
                name: 'compact-dashboard',
                label: computed(() => this.$t('navigation.selectYourCompact')),
                shouldHideLabel: true,
                shouldHideMargin: true,
                value: this.selectedCompactType,
                valueOptions: this.compactSelectOptions,
            }),
        });
    }

    async selectCompact(compactType: CompactType, shouldMoveFocus = false): Promise<void> {
        this.selectedCompactType = compactType;
        this.initCompactSelect();

        await this.$store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: compactType }));
        await this.$store.dispatch('license/setStoreSearch', {
            ...this.$store.state.license.search,
            compact: compactType,
        });

        if (shouldMoveFocus) {
            await this.$nextTick();

            this.focusStepHeading();
        }
    }

    focusStepHeading(): void {
        const heading = this.$el?.querySelector('#dashboard-step-heading') as HTMLElement | null;

        if (heading) {
            heading.focus();
        }
    }

    async handleCompactSelect(): Promise<void> {
        const selectedCompactType = this.formData.compact.value as CompactType;

        if (selectedCompactType && selectedCompactType !== this.selectedCompactType) {
            await this.selectCompact(selectedCompactType);
        }
    }

    handleStaffLoginClick(): void {
        if (this.selectedCompact) {
            this.setGotoCompact(this.selectedCompact.type);
        }
    }

    handlePractitionerLoginClick(): void {
        if (this.selectedCompact) {
            this.setGotoCompact(this.selectedCompact.type);
        }
    }

    handleMockStaffLogin(): void {
        this.bypassToStaffLogin(this.selectedAppMode, this.selectedCompact?.type);
    }

    handleMockPractitionerLogin(): void {
        this.bypassToLicenseeLogin(this.selectedAppMode, this.selectedCompact?.type);
    }

    setGotoCompact(compactType: CompactType): void {
        if (compactType) {
            authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, compactType);
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

    //
    // Watchers
    //
    @Watch('appMode')
    async appModeChanged(newMode: AppModes, oldMode: AppModes): Promise<void> {
        if (newMode === AppModes.PSYPACT && this.selectedCompactType !== CompactType.PSYPACT) {
            await this.selectCompact(CompactType.PSYPACT);
        } else if (oldMode === AppModes.PSYPACT) {
            this.selectedCompactType = null;
            this.formData = {};

            await this.$store.dispatch('user/setCurrentCompact', null);
        }
    }
}
