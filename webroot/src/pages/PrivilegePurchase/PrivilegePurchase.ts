//
//  PrivilegePurchase.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/31/2025.
//

import { Component, Vue, Watch } from 'vue-facing-decorator';
import PrivilegePurchaseAttestation from '@components/PrivilegePurchaseAttestation/PrivilegePurchaseAttestation.vue';
import PrivilegePurchaseInformationConfirmation from '@components/PrivilegePurchaseInformationConfirmation/PrivilegePurchaseInformationConfirmation.vue';
import PrivilegePurchaseSelect from '@components/PrivilegePurchaseSelect/PrivilegePurchaseSelect.vue';
import PrivilegePurchaseFinalize from '@components/PrivilegePurchaseFinalize/PrivilegePurchaseFinalize.vue';
import PrivilegePurchaseSuccessful from '@components/PrivilegePurchaseSuccessful/PrivilegePurchaseSuccessful.vue';
import PrivilegePurchaseLicense from '@components/PrivilegePurchaseLicense/PrivilegePurchaseLicense.vue';
import ProgressBar from '@components/ProgressBar/ProgressBar.vue';
import { Compact } from '@models/Compact/Compact.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { PurchaseFlowState } from '@/models/PurchaseFlowState/PurchaseFlowState.model';

@Component({
    name: 'PrivilegePurchase',
    components: {
        PrivilegePurchaseLicense,
        PrivilegePurchaseInformationConfirmation,
        PrivilegePurchaseSelect,
        PrivilegePurchaseAttestation,
        PrivilegePurchaseFinalize,
        PrivilegePurchaseSuccessful,
        ProgressBar
    }
})
export default class PrivilegePurchase extends Vue {
    //
    // Data
    //
    flowOrder = [
        'PrivilegePurchaseSelectLicense',
        'PrivilegePurchaseInformationConfirmation',
        'PrivilegePurchaseSelect',
        'PrivilegePurchaseAttestation',
        'PrivilegePurchaseFinalize',
        'PrivilegePurchaseSuccessful'
    ]

    //
    // Lifecycle
    //
    created() {
        if (this.licensee?.canPurchasePrivileges() && this.currentCompactType) {
            this.handlePurchaseFlowState();
        } else {
            this.$router.push({
                name: 'Home',
            });
        }
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get routeName(): string {
        return this.$route?.name?.toString() || '';
    }

    get purchaseFlowState(): PurchaseFlowState {
        return this.userStore.purchase;
    }

    get isSelectLicenseRoute(): boolean {
        return this.routeName === 'PrivilegePurchaseSelectLicense';
    }

    get isConfirmInfoRoute(): boolean {
        return this.routeName === 'PrivilegePurchaseInformationConfirmation';
    }

    get isSelectPrivilegesRoute(): boolean {
        return this.routeName === 'PrivilegePurchaseSelect';
    }

    get isAttestationRoute(): boolean {
        return this.routeName === 'PrivilegePurchaseAttestation';
    }

    get isFinalizeRoute(): boolean {
        return this.routeName === 'PrivilegePurchaseFinalize';
    }

    get isPurchaseSuccessfulRoute(): boolean {
        return this.routeName === 'PrivilegePurchaseSuccessful';
    }

    get currentFlowStep(): number {
        const {
            routeName,
            flowOrder
        } = this;

        return flowOrder.findIndex((flowRouteName) => (flowRouteName === routeName));
    }

    get numFlowSteps(): number {
        return this.flowOrder.length;
    }

    get progressPercent(): number {
        return Math.round(((this.currentFlowStep + 1) / this.numFlowSteps) * 100);
    }

    //
    // Methods
    //
    handlePurchaseFlowState() {
        const { $store, $router, currentFlowStep } = this;
        const nextStepNeeded = $store.getters['user/getNextNeededPurchaseFlowStep']();

        if (nextStepNeeded < currentFlowStep || currentFlowStep === -1) {
            $router.push({
                name: this.flowOrder[nextStepNeeded],
                params: { compact: this.currentCompactType }
            });
        } else {
            $store.dispatch('user/resetToPurchaseFlowStep', currentFlowStep);
        }
    }

    //
    // Watchers
    //
    @Watch('routeName') handlePurchaseFlowNavigation() {
        this.handlePurchaseFlowState();
    }
}
