//
//  CompactSettings.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/5/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import Section from '@components/Section/Section.vue';
import PaymentProcessorConfig from '@components/PaymentProcessorConfig/PaymentProcessorConfig.vue';
import CompactSettingsConfig from '@components/CompactSettingsConfig/CompactSettingsConfig.vue';
import { Compact } from '@models/Compact/Compact.model';
import { CompactPermission } from '@models/StaffUser/StaffUser.model';

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

    get user() {
        return this.userStore.model;
    }

    get isLoggedIn(): boolean {
        return this.userStore.isLoggedIn;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get isLoggedInAsStaff(): boolean {
        return this.authType === AuthTypes.STAFF;
    }

    get staffPermission(): CompactPermission | null {
        const { model: user } = this.userStore;
        const currentPermissions = user?.permissions;
        const compactPermission = currentPermissions?.find((currentPermission) =>
            currentPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get isCompactAdmin(): boolean {
        return this.isLoggedInAsStaff && Boolean(this.staffPermission?.isAdmin);
    }

    get isStateAdmin(): boolean {
        const { isLoggedInAsStaff, staffPermission } = this;
        const isAdmin = Boolean(staffPermission?.states?.some((statePermission) => statePermission.isAdmin));

        return isLoggedInAsStaff && isAdmin;
    }
}
