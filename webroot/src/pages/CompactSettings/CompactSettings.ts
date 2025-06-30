//
//  CompactSettings.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/5/2024.
//

import { Component, Vue, Watch } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import Section from '@components/Section/Section.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import PaymentProcessorConfig from '@components/PaymentProcessorConfig/PaymentProcessorConfig.vue';
import CompactSettingsConfig from '@components/CompactSettingsConfig/CompactSettingsConfig.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { CompactPermission, StatePermission } from '@models/StaffUser/StaffUser.model';
import { State } from '@/models/State/State.model';
import { dataApi } from '@network/data.api';

@Component({
    name: 'CompactSettings',
    components: {
        Section,
        CompactSettingsConfig,
        PaymentProcessorConfig,
        LoadingSpinner,
    }
})
export default class CompactSettings extends Vue {
    //
    // Data
    //
    isCompactConfigLoading = false;
    compactConfigLoadingErrorMessage = '';
    compactConfigStates: Array<{abbrev: string, isLive: boolean}> = [];

    //
    // Lifecycle
    //
    created(): void {
        this.init();
    }

    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get authType(): string {
        return this.globalStore.authType;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get compactType(): CompactType | null {
        return this.currentCompact?.type || null;
    }

    get user() {
        return this.userStore.model;
    }

    get isLoggedIn(): boolean {
        return this.userStore.isLoggedIn;
    }

    get isLoggedInAsStaff(): boolean {
        return this.authType === AuthTypes.STAFF;
    }

    get staffPermission(): CompactPermission | null {
        const currentPermissions = this.user?.permissions;
        const compactPermission = currentPermissions?.find((currentPermission) =>
            currentPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get isCompactAdmin(): boolean {
        return this.isLoggedInAsStaff && Boolean(this.staffPermission?.isAdmin);
    }

    get statePermissionsAdmin(): Array<StatePermission> {
        return this.staffPermission?.states?.filter((statePermission) => statePermission.isAdmin) || [];
    }

    get isStateAdminAny(): boolean {
        return this.isLoggedInAsStaff && this.statePermissionsAdmin.length > 0;
    }

    get isStateAdminMultiple(): boolean {
        return this.isLoggedInAsStaff && this.statePermissionsAdmin.length > 1;
    }

    get isStateAdminExactlyOne(): boolean {
        return this.isLoggedInAsStaff && this.statePermissionsAdmin.length === 1;
    }

    get stateConfigRowPermissions(): Array<any> {
        const userCompactAdminStates = this.compactConfigStates;
        const userPermissionAdminStates = this.statePermissionsAdmin;
        let rowPermissions: Array<any> = [];

        // State row permissions are based on 2 different permission lists that we merge here

        // Compact-level admin states
        userCompactAdminStates.forEach((compactAdminState) => {
            rowPermissions.push({
                state: new State({ abbrev: compactAdminState.abbrev }),
                isLiveForCompact: compactAdminState.isLive,
                isCompactAdmin: true,
                isStateAdmin: false,
            });
        });

        // State-level admin states
        userPermissionAdminStates.forEach((permissionAdminState) => {
            const existing = rowPermissions.find((existingState) =>
                existingState.state.abbrev === permissionAdminState.state.abbrev);

            if (existing) {
                existing.isStateAdmin = true;
            } else {
                rowPermissions.push({
                    state: new State({ abbrev: permissionAdminState.state.abbrev }),
                    isLiveForCompact: false,
                    isCompactAdmin: false,
                    isStateAdmin: true,
                });
            }
        });

        // Sort the results for clarity
        rowPermissions = rowPermissions.sort((a, b) => {
            const stateNameA = a.state.name();
            const stateNameB = b.state.name();
            let sort = 0;

            if (stateNameA > stateNameB) {
                sort = 1;
            } else if (stateNameA < stateNameB) {
                sort = -1;
            }

            return sort;
        });

        return rowPermissions;
    }

    get shouldShowStateList(): boolean {
        return this.isCompactAdmin || this.isStateAdminMultiple;
    }

    //
    // Methods
    //
    init(): void {
        this.permissionRedirectCheck();
        this.initCompactConfig();
    }

    permissionRedirectCheck(): void {
        if (this.currentCompact && this.user && !this.isCompactAdmin) {
            if (!this.isStateAdminAny) {
                // Not compact or state admin, so redirect to home page
                this.$router.replace({ name: 'Home' });
            } else if (this.isStateAdminExactlyOne) {
                // Not compact admin and state admin for only 1 state, so redirect to state config page
                this.routeToStateConfig(this.statePermissionsAdmin[0]?.state?.abbrev || '', true);
            }
        }
    }

    routeToStateConfig(abbrev: string, isRouteReplace = false): void {
        if (this.currentCompact?.type) {
            const routeConfig = {
                name: 'StateSettings',
                params: {
                    compact: this.currentCompact?.type,
                    state: abbrev,
                },
            };

            if (isRouteReplace) {
                this.$router.replace(routeConfig);
            } else {
                this.$router.push(routeConfig);
            }
        }
    }

    async initCompactConfig(): Promise<void> {
        if (this.compactType && this.isCompactAdmin) {
            this.isCompactConfigLoading = true;

            const compact = this.compactType || '';
            const compactConfig: any = await dataApi.getCompactConfig(compact).catch((err) => {
                this.compactConfigLoadingErrorMessage = err?.message || this.$t('serverErrors.networkError');
            });

            if (Array.isArray(compactConfig.configuredStates)) {
                compactConfig.configuredStates.forEach((serverState) => {
                    this.compactConfigStates.push({
                        abbrev: serverState.postalAbbreviation || '',
                        isLive: serverState.isLive || false,
                    });
                });
            }

            this.isCompactConfigLoading = false;
        }
    }

    //
    // Watch
    //
    @Watch('currentCompact') currentCompactUpdate() {
        this.permissionRedirectCheck();
        this.initCompactConfig();
    }

    @Watch('user') userUpdate() {
        this.permissionRedirectCheck();
        this.initCompactConfig();
    }
}
