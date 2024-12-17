//
//  PageContainer.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import PageHeader from '@components/Page/PageHeader/PageHeader.vue';
import PageLoadingMask from '@components/Page/PageLoadingMask/PageLoadingMask.vue';
import PageFooter from '@components/Page/PageFooter/PageFooter.vue';

@Component({
    name: 'PageContainer',
    components: {
        PageHeader,
        PageLoadingMask,
        PageFooter,
    }
})
class PageContainer extends Vue {
    //
    // Data
    //
    globalStore: any = {};
    userStore: any = {};

    //
    // Lifecycle
    //
    created() {
        this.globalStore = this.$store.state;
        this.userStore = this.$store.state.user;
    }

    //
    // Computed
    //
    get includePageHeader(): boolean {
        const currentRouteName = this.$route.name;
        const nonHeaderRouteNames: Array<string> = [];

        return (!nonHeaderRouteNames.includes((currentRouteName as string)));
    }

    get includePageFooter(): boolean {
        const currentRouteName = this.$route.name;
        const nonFooterRouteNames: Array<string> = [];

        if (this.isPhone) {
            nonFooterRouteNames.push('SelectPrivileges');
        }

        return (!nonFooterRouteNames.includes((currentRouteName as string)));
    }

    get isPhone(): boolean {
        return this.$matches.phone.only;
    }

    get isLoading(): boolean {
        return this.globalStore.isLoading
            || this.userStore.isLoadingAccount
            || this.userStore.isLoadingPrivilegePurchaseOptions;
    }
}

export default toNative(PageContainer);

// export { PageContainer };
