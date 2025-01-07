//
//  PageContainer.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import PageHeader from '@components/Page/PageHeader/PageHeader.vue';
import PageNav from '@components/Page/PageNav/PageNav.vue';
import PageLoadingMask from '@components/Page/PageLoadingMask/PageLoadingMask.vue';
import PageFooter from '@components/Page/PageFooter/PageFooter.vue';

@Component({
    name: 'PageContainer',
    components: {
        PageHeader,
        PageNav,
        PageLoadingMask,
        PageFooter,
    }
})
class PageContainer extends Vue {
    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get isPhone(): boolean {
        return this.$matches.phone.only;
    }

    get includePageHeader(): boolean {
        const { isLoggedIn } = this.userStore;
        const currentRouteName: string = this.$route.name as string;
        const nonHeaderRouteNames: Array<string> = [
            'Login',
            'Logout',
        ];

        return (isLoggedIn && this.isPhone && !nonHeaderRouteNames.includes(currentRouteName));
    }

    get includePageFooter(): boolean {
        return false;
    }

    get isLoading(): boolean {
        return this.globalStore.isLoading
            || this.userStore.isLoadingAccount
            || this.userStore.isLoadingPrivilegePurchaseOptions;
    }
}

export default toNative(PageContainer);

// export { PageContainer };
