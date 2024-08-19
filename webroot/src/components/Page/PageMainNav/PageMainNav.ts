//
//  PageMainNav.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 11/20/2020.
//

import { reactive, computed } from 'vue';
import { Component, Vue, toNative } from 'vue-facing-decorator';

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

    get mainLinks() {
        return reactive([
            {
                to: 'Home',
                label: computed(() => this.$t('navigation.upload')),
                isEnabled: this.isLoggedIn,
                isExternal: false,
                isExactActive: true,
            },
            {
                to: 'Licensing',
                label: computed(() => this.$t('navigation.licensing')),
                isEnabled: this.isLoggedIn,
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
