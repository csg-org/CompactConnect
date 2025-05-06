//
//  LicenseeDashboard.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import HomeStateBlock from '@/components/HomeStateBlock/HomeStateBlock.vue';
import LicenseCard from '@/components/LicenseCard/LicenseCard.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import { Compact } from '@models/Compact/Compact.model';
import { License, LicenseStatus } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';

@Component({
    name: 'LicenseeDashboard',
    components: {
        HomeStateBlock,
        LicenseCard,
        PrivilegeCard,
        InputButton,
        CollapseCaretButton
    }
})
export default class LicenseeDashboard extends Vue {
    //
    // Data
    //
    isPrivsCollapsed = false;
    isPastPrivsCollapsed = false;

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

    //
    // Methods
    //
    startPrivPurchaseFlow() {
        this.$router.push({
            name: 'PrivilegePurchaseInformationConfirmation',
            params: { compact: this.currentCompactType }
        });
    }

    viewMilitaryStatus() {
        this.$router.push({
            name: 'MilitaryStatus',
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
}
