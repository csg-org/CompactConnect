//
//  CompactSettings.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/5/2024.
//

import { Component, Vue, Watch } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import Section from '@components/Section/Section.vue';
import PaymentProcessorConfig from '@components/PaymentProcessorConfig/PaymentProcessorConfig.vue';
import CompactSettingsConfig from '@components/CompactSettingsConfig/CompactSettingsConfig.vue';
import StateSettingsList from '@components/StateSettingsList/StateSettingsList.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { CompactPermission, StatePermission } from '@models/StaffUser/StaffUser.model';

@Component({
    name: 'CompactSettings',
    components: {
        Section,
        CompactSettingsConfig,
        PaymentProcessorConfig,
        StateSettingsList,
    }
})
export default class CompactSettings extends Vue {
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

    get shouldShowStateList(): boolean {
        return this.isCompactAdmin || this.isStateAdminMultiple;
    }

    //
    // Methods
    //
    init(): void {
        this.permissionRedirectCheck();
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

    //
    // Watch
    //
    @Watch('currentCompact') currentCompactUpdate() {
        this.permissionRedirectCheck();
    }

    @Watch('user') userUpdate() {
        this.permissionRedirectCheck();
    }
}
