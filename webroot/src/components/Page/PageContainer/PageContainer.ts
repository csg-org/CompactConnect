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

    get licenseStore() {
        return this.$store.state.license;
    }

    get currentRouteName(): string {
        return this.$route?.name as string || '';
    }

    get isPhone(): boolean {
        return this.$matches.phone.only;
    }

    get includePageHeader(): boolean {
        const nonHeaderRouteNames: Array<string> = [
            'Logout',
        ];

        return (this.isPhone && !nonHeaderRouteNames.includes(this.currentRouteName));
    }

    get shouldPadTop(): boolean {
        const nonPadTopRouteNames: Array<string> = [
            'LicensingDetail',
            'LicenseeDetailPublic',
            'LicenseeVerification',
        ];

        return !nonPadTopRouteNames.includes(this.currentRouteName);
    }

    get includeMainNav(): boolean {
        const nonMainNavRouteNames: Array<string> = [
            'LicenseeVerification', // This is a printer-friendly page
        ];

        return !nonMainNavRouteNames.includes(this.currentRouteName);
    }

    get includePageFooter(): boolean {
        return false;
    }

    get isLoading(): boolean {
        return this.globalStore.isLoading
            || this.userStore.isLoadingAccount
            || this.userStore.isLoadingCompactStates
            || this.userStore.isLoadingPrivilegePurchaseOptions;
    }
}

export default toNative(PageContainer);

// export { PageContainer };
