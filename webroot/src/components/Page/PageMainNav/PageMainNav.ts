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
                isEnabled: Boolean(this.currentCompact) && this.isLoggedInAsStaff,
                isExternal: false,
                isExactActive: true,
            },
            // { // @NOTE: Disable user-list nav while the user management feature is WIP
            //     to: 'Users',
            //     params: { compact: this.currentCompact?.type },
            //     label: computed(() => this.$t('navigation.users')),
            //     isEnabled: this.isLoggedIn && Boolean(this.currentCompact),
            //     isExternal: false,
            //     isExactActive: false,
            // },
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
