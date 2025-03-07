//
//  PageMainNav.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 11/20/2020.
//

import {
    reactive,
    computed,
    ComputedRef,
    markRaw,
    Raw
} from 'vue';
import { Component, Vue, toNative } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import RegisterIcon from '@components/Icons/Register/Register.vue';
import UploadIcon from '@components/Icons/Upload/Upload.vue';
import UsersIcon from '@components/Icons/Users/Users.vue';
import LicenseSearchIcon from '@components/Icons/LicenseSearch/LicenseSearch.vue';
import SettingsIcon from '@components/Icons/Settings/Settings.vue';
import DashboardIcon from '@components/Icons/Dashboard/Dashboard.vue';
import PurchaseIcon from '@components/Icons/Purchase/Purchase.vue';
import AccountIcon from '@components/Icons/Account/Account.vue';
import LogoutIcon from '@components/Icons/Logout/Logout.vue';
import CompactSelector from '@components/CompactSelector/CompactSelector.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { CompactPermission } from '@models/StaffUser/StaffUser.model';

export interface NavLink {
    to: string;
    params?: {
        compact?: CompactType | null,
    };
    label?: string | ComputedRef,
    iconComponent?: Raw<any>,
    isEnabled?: boolean,
    isExternal?: boolean,
    isExactActive?: boolean,
}

@Component({
    name: 'PageMainNav',
    components: {
        RegisterIcon,
        UploadIcon,
        UsersIcon,
        LicenseSearchIcon,
        SettingsIcon,
        DashboardIcon,
        PurchaseIcon,
        AccountIcon,
        LogoutIcon,
        CompactSelector,
    }
})
class PageMainNav extends Vue {
    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get authType(): string {
        return this.globalStore.authType;
    }

    get isNavExpanded(): boolean {
        return this.globalStore.isNavExpanded;
    }

    get userStore() {
        return this.$store.state.user;
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

    get isLoggedInAsLicensee(): boolean {
        return this.authType === AuthTypes.LICENSEE;
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

    get isAnyTypeOfAdmin(): boolean {
        return this.isCompactAdmin || this.isStateAdmin;
    }

    get hasStateWritePermissions(): boolean {
        let hasWritePermissions = false;

        if (this.isLoggedInAsStaff) {
            const { staffPermission } = this;

            if (staffPermission?.states?.some((statePermission) =>
                statePermission.isAdmin || statePermission.isWrite)) {
                hasWritePermissions = true;
            }
        }

        return hasWritePermissions;
    }

    get mainLinks(): Array<NavLink> {
        return reactive([
            {
                to: 'DashboardPublic',
                label: computed(() => this.$t('navigation.dashboard')),
                iconComponent: markRaw(DashboardIcon),
                isEnabled: !this.isLoggedIn,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'LicneseeSearchPublic',
                label: computed(() => this.$t('navigation.licensing')),
                iconComponent: markRaw(LicenseSearchIcon),
                isEnabled: !this.isLoggedIn,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'RegisterLicensee',
                label: computed(() => this.$t('navigation.register')),
                iconComponent: markRaw(RegisterIcon),
                isEnabled: !this.isLoggedIn,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'StateUpload',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.upload')),
                iconComponent: markRaw(UploadIcon),
                isEnabled: Boolean(this.currentCompact) && this.hasStateWritePermissions,
                isExternal: false,
                isExactActive: true,
            },
            {
                to: 'Users',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.users')),
                iconComponent: markRaw(UsersIcon),
                isEnabled: this.isAnyTypeOfAdmin,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'Licensing',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.licensing')),
                iconComponent: markRaw(LicenseSearchIcon),
                isEnabled: Boolean(this.currentCompact) && this.isLoggedInAsStaff,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'CompactSettings',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.compactSettings')),
                iconComponent: markRaw(SettingsIcon),
                isEnabled: Boolean(this.currentCompact) && this.isCompactAdmin,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'LicenseeDashboard',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.dashboard')),
                iconComponent: markRaw(DashboardIcon),
                isEnabled: Boolean(this.currentCompact) && this.isLoggedInAsLicensee,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'PrivilegePurchase',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.purchasePrivileges')),
                iconComponent: markRaw(PurchaseIcon),
                isEnabled: Boolean(this.currentCompact) && !this.isLoggedInAsStaff,
                isExternal: false,
                isExactActive: false,
            },
        ].filter((link) => link.isEnabled));
    }

    get myLinks(): Array<NavLink> {
        return reactive([
            {
                to: 'Account',
                label: computed(() => this.$t('navigation.account')),
                iconComponent: markRaw(AccountIcon),
                isEnabled: this.isLoggedIn,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'Logout',
                label: computed(() => this.$t('navigation.logout')),
                iconComponent: markRaw(LogoutIcon),
                isEnabled: this.isLoggedIn,
                isExternal: false,
                isExactActive: true,
            },
        ].filter((link) => link.isEnabled));
    }

    //
    // Methods
    //
    logoClick(): void {
        this.$router.push({ name: 'Home' });
    }

    navToggle(): void {
        if (this.globalStore.isNavExpanded) {
            this.$store.dispatch('collapseNavMenu');
        } else {
            this.$store.dispatch('expandNavMenu');
        }
    }

    navExpand(): void {
        this.$store.dispatch('expandNavMenu');
    }

    navCollapse(): void {
        this.$store.dispatch('collapseNavMenu');
    }

    clickOutside(event): void {
        if (!event.target.closest('.main-nav-container, .nav-toggle')) {
            this.navCollapse();
        }
    }
}

export default toNative(PageMainNav);

// export { PageMainNav };
