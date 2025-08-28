//
//  MfaResetConfirmLicensee.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/22/2025.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import { AuthTypes, getHostedLoginUri } from '@/app.config';
import Section from '@components/Section/Section.vue';
import Card from '@components/Card/Card.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import CheckCircle from '@components/Icons/CheckCircle/CheckCircle.vue';
import AlertTriangle from '@components/Icons/AlertTriangle/AlertTriangle.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'MfaResetConfirmLicensee',
    components: {
        Section,
        Card,
        LoadingSpinner,
        CheckCircle,
        AlertTriangle,
        InputButton,
    },
})
class MfaResetConfirmLicensee extends Vue {
    //
    // Data
    //
    isLoading = true;
    isSuccess = false;
    serverMessage = 'Sample message from server';

    //
    // Lifecycle
    //
    created(): void {
        this.initiateRecoveryConfirmation();
    }

    //
    // Computed
    //
    get compactQuery(): string {
        const compact: string = (this.$route.query?.compact as string) || '';

        return compact.toLowerCase();
    }

    get providerIdQuery(): string {
        return (this.$route.query?.providerId as string) || '';
    }

    get recoveryIdQuery(): string {
        return (this.$route.query?.recoveryId as string) || '';
    }

    get hostedLoginUriLicensee(): string {
        return getHostedLoginUri(AuthTypes.LICENSEE, '/login');
    }

    get isUsingMockApi(): boolean {
        return this.$envConfig.isUsingMockApi || false;
    }

    //
    // Methods
    //
    async initiateRecoveryConfirmation(): Promise<void> {
        const { compactQuery, providerIdQuery, recoveryIdQuery } = this;

        if (compactQuery && providerIdQuery && recoveryIdQuery) {
            this.isSuccess = true;
        }

        if (this.isUsingMockApi) {
            await new Promise((resolve) => setTimeout(() => { resolve(true); }, 2000));
        }

        this.isLoading = false;
    }

    goToLogin(): void {
        window.location.replace(this.hostedLoginUriLicensee);
    }

    goToDashboard(): void {
        this.$router.replace({ name: 'DashboardPublic' });
    }
}

export default toNative(MfaResetConfirmLicensee);

// export default MfaResetConfirmLicensee;
