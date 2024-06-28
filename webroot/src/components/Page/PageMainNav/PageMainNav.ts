//
//  PageMainNav.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 11/20/2020.
//

import { reactive } from 'vue';
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

    get mainLinks() {
        return reactive([{} as any
            // {
            //     to: '/',
            //     label: computed(() => this.$t('navigation.home')),
            //     isEnabled: true,
            //     isExternal: false,
            //     isExactActive: true,
            // },
            // {
            //     to: '/styleguide',
            //     label: computed(() => this.$t('navigation.styleGuide')),
            //     isEnabled: true,
            //     isExternal: false,
            //     isExactActive: false,
            // },
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
