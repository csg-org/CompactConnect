//
//  PageMainNav.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 11/20/2020.
//

import { reactive, computed } from 'vue';
import { Component, Vue, toNative } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import { Compact } from '@models/Compact/Compact.model';
import { CompactPermission } from '@models/StaffUser/StaffUser.model';

@Component({
    name: 'PageMainNav',
})
class PageMainNav extends Vue {
    //
    // Data
    //
    isMainNavToggled = false;

    //
    // Computed
    //
    get isDesktop(): boolean {
        return this.$matches.desktop.min;
    }

    get isMobile(): boolean {
        return !this.isDesktop;
    }

    get isMainNavVisible(): boolean {
        return this.isDesktop || this.isMainNavToggled;
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
        return this.isLoggedIn && this.$store.getters['user/highestPermissionAuthType']() === AuthTypes.STAFF;
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

    get mainLinks() {
        return reactive([
            {
                to: 'Licensing',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.licensing')),
                isEnabled: Boolean(this.currentCompact) && this.isLoggedInAsStaff,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'StateUpload',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.upload')),
                isEnabled: Boolean(this.currentCompact) && this.hasStateWritePermissions,
                isExternal: false,
                isExactActive: true,
            },
            {
                to: 'CompactSettings',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.compactSettings')),
                isEnabled: Boolean(this.currentCompact) && this.isCompactAdmin,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'LicenseeDashboard',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.dashboard')),
                isEnabled: Boolean(this.currentCompact) && !this.isLoggedInAsStaff,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'Account',
                label: computed(() => this.$t('navigation.account')),
                isEnabled: this.isLoggedIn,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'Users',
                params: { compact: this.currentCompact?.type },
                label: computed(() => this.$t('navigation.users')),
                isEnabled: this.isAnyTypeOfAdmin,
                isExternal: false,
                isExactActive: false,
            },
            {
                to: 'Logout',
                label: computed(() => this.$t('navigation.logout')),
                isEnabled: this.isLoggedIn,
                isExternal: false,
                isExactActive: true,
            },
        ].filter((link) => link.isEnabled));
    }

    //
    // Methods
    //
    toggleMainNav() {
        this.isMainNavToggled = !this.isMainNavToggled;
    }

    collapseMainNav() {
        this.isMainNavToggled = false;
    }
}

export default toNative(PageMainNav);

// export { PageMainNav };
