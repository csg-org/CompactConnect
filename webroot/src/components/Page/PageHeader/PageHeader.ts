//
//  PageHeader.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';

@Component({
    name: 'PageHeader',
    components: {}
})
class PageHeader extends Vue {
    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get isMenuTouchToggle(): boolean {
        const { $matches } = this;

        return $matches.phone.only || $matches.hover === 'none';
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
}

export default toNative(PageHeader);

// export { PageHeader };
