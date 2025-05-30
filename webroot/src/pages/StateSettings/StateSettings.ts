//
//  StateSettings.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/20/2025.
//

import { Component, Vue, Watch } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import Section from '@components/Section/Section.vue';
import StateSettingsConfig from '@components/StateSettingsConfig/StateSettingsConfig.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import { Compact } from '@models/Compact/Compact.model';
import { CompactPermission, StatePermission } from '@models/StaffUser/StaffUser.model';

@Component({
    name: 'StateSettings',
    components: {
        Section,
        StateSettingsConfig,
        InputButton,
    },
})
export default class StateSettings extends Vue {
    //
    // Lifecycle
    //
    created(): void {
        this.init();
    }

    //
    // Computed
    //
    get stateAbbrev(): string {
        return (this.$route.params?.state as string) || '';
    }

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

    get statePermission(): StatePermission | null {
        return this.staffPermission?.states?.find((permission) => permission.state.abbrev === this.stateAbbrev) || null;
    }

    get isStateAdmin(): boolean {
        return Boolean(this.isLoggedInAsStaff && this.statePermission?.isAdmin);
    }

    get pageTitle(): string {
        const stateName = this.statePermission?.state?.name() || '';
        const compactName = this.currentCompact?.abbrev() || '';

        return `${stateName}-${compactName} ${(this.$t('compact.configuration') || '').toLowerCase()}`;
    }

    //
    // Methods
    //
    init(): void {
        this.permissionRedirectCheck();
    }

    permissionRedirectCheck(): void {
        if (this.currentCompact && this.user) {
            if (!this.isLoggedInAsStaff || !this.isStateAdmin) {
                // Redirect user to home page
                this.$router.replace({ name: 'Home' });
            }
        }
    }

    goBack() {
        this.$router.go(-1);
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
