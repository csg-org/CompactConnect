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
import { Compact } from '@models/Compact/Compact.model';
import { CompactPermission, StatePermission } from '@models/StaffUser/StaffUser.model';

@Component({
    name: 'CompactSettings',
    components: {
        Section,
        PaymentProcessorConfig,
        CompactSettingsConfig,
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

    //
    // Methods
    //
    init(): void {
        this.permissionRedirectCheck();
    }

    permissionRedirectCheck(): void {
        if (this.currentCompact && this.user) {
            if (!this.isLoggedInAsStaff || (!this.isCompactAdmin && !this.isStateAdminAny)) {
                // Redirect user to home page
                this.$router.replace({ name: 'Home' });
            } else if (!this.isCompactAdmin && this.isStateAdminExactlyOne) {
                // Redirect user to state config page
                this.$router.replace({
                    name: 'StateSettings',
                    params: {
                        compact: this.currentCompact.type,
                        state: this.statePermissionsAdmin[0].state.abbrev,
                    },
                });
            }
        }
    }

    routeToStateConfig(abbrev: string): void {
        this.$router.push({
            name: 'StateSettings',
            params: {
                compact: this.currentCompact?.type,
                state: abbrev,
            },
        });
    }

    //
    // Watch
    //
    @Watch('isCompactAdmin') compactAdminUpdate() {
        this.permissionRedirectCheck();
    }

    @Watch('isStateAdminExactlyOne') stateAdminUpdate() {
        this.permissionRedirectCheck();
    }
}
