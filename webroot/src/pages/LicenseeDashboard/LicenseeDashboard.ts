//
//  LicenseeDashboard.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { reactive, nextTick } from 'vue';
import { FormInput } from '@/models/FormInput/FormInput.model';
import HomeStateBlock from '@/components/HomeStateBlock/HomeStateBlock.vue';
import LicenseCard from '@/components/LicenseCard/LicenseCard.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact } from '@models/Compact/Compact.model';
import { License, LicenseStatus } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import InfoCircle from '@/components/Icons/InfoCircle/InfoCircle.vue';

@Component({
    name: 'LicenseeDashboard',
    components: {
        HomeStateBlock,
        LicenseCard,
        PrivilegeCard,
        InputButton,
        InputSubmit,
        CollapseCaretButton,
        Modal,
        InfoCircle
    }
})
export default class LicenseeDashboard extends Vue {
    //
    // Data
    //
    isPrivsCollapsed = false;
    isPastPrivsCollapsed = false;
    isPurchaseUnavailableModalDisplayed = false;
    formData: any = {};

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get userFullName(): string {
        let name = '';

        if (this.user) {
            name = this.user.getFullName();
        }

        return name;
    }

    get licensee(): Licensee {
        return this.user?.licensee || new Licensee();
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee.licenses || [];
    }

    get licenseePrivileges(): Array<License> {
        return this.licensee.privileges || [];
    }

    get homeJurisdiction(): State | null {
        return this.licensee?.homeJurisdiction || null;
    }

    get isGenerateProofEnabled(): boolean {
        return this.licenseePrivileges.filter((privilege: License) =>
            privilege.status === LicenseStatus.ACTIVE).length > 0;
    }

    get isPrivilegePurchaseEnabled(): boolean {
        return this.licensee?.canPurchasePrivileges() || false;
    }

    get isMilitaryStatusInitializing(): boolean {
        return this.licensee?.isMilitaryStatusInitializing() || false;
    }

    //
    // Methods
    //
    startPrivPurchaseFlow() {
        this.$router.push({
            name: 'PrivilegePurchaseInformationConfirmation',
            params: { compact: this.currentCompactType }
        });
    }

    viewLicenseeProof() {
        this.$router.push({
            name: 'LicenseeVerification',
            params: { compact: this.currentCompactType }
        });
    }

    isLicenseActive(license: License): boolean {
        return license && license.status === LicenseStatus.ACTIVE;
    }

    togglePrivsCollapsed() {
        this.isPrivsCollapsed = !this.isPrivsCollapsed;
    }

    togglePastPrivsCollapsed() {
        this.isPastPrivsCollapsed = !this.isPastPrivsCollapsed;
    }

    async openPurchaseUnavailableModal(): Promise<void> {
        this.isPurchaseUnavailableModalDisplayed = true;
        await nextTick();
        document.getElementById('submit-close-purchase-unavailable')?.focus();
    }

    closePurchaseUnavailableModal(): void {
        this.isPurchaseUnavailableModalDisplayed = false;
    }

    initFormInputs(): void {
        this.formData = reactive({
            close: new FormInput({
                isSubmitInput: true,
                id: 'submit-close-purchase-unavailable',
            }),
        });
    }

    focusTrapPurchaseUnavailable(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('submit-close-purchase-unavailable');
        const lastTabIndex = document.getElementById('military-status-link');

        if (event.shiftKey) {
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
            } else {
                firstTabIndex?.focus();
            }
            event.preventDefault();
        } else {
            if (document.activeElement === lastTabIndex) {
                firstTabIndex?.focus();
            } else {
                lastTabIndex?.focus();
            }
            event.preventDefault();
        }
    }
}
