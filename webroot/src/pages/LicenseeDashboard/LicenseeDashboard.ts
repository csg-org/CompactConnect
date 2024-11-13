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
import { License, LicenseStatus } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import moment from 'moment';

@Component({
    name: 'LicenseeDashboard',
    components: {
        HomeStateBlock,
        LicenseCard,
        PrivilegeCard,
        InputButton
    }
})
export default class LicenseeDashboard extends Vue {
    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee {
        return this.user?.licensee || new Licensee();
    }

    get licenseePrivileges(): Array<License> {
        return this.licensee.privileges || [];
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee.licenses || [];
    }

    get userFullName(): string {
        let name = '';

        if (this.user) {
            name = this.user.getFullName();
        }

        return name;
    }

    get homeStateList(): Array<State> {
        const stateList: Array<State> = [];

        this.activeLicenses.forEach((license) => {
            const { issueState } = license;

            if (issueState) {
                stateList.push(issueState);
            }
        });

        return stateList;
    }

    get privilegeList(): Array<License> {
        const privilegeList: Array<License> = [];

        this.licenseePrivileges.forEach((privilege) => {
            const previousEntryOfStateIndex = privilegeList.findIndex((state) =>
                state?.issueState?.abbrev === privilege?.issueState?.abbrev);
            const previousEntryOfState = privilegeList[previousEntryOfStateIndex];

            // If no existing entry of state add to array
            if (previousEntryOfStateIndex === -1) {
                privilegeList.push(privilege);
            // If currently observed privilege is newer than saved entry replace existing entry
            } else if (
                privilege.renewalDate
                && previousEntryOfState.renewalDate
                && moment(privilege.renewalDate).isAfter(moment(previousEntryOfState.renewalDate))
            ) {
                privilegeList[previousEntryOfStateIndex] = privilege;
            }
        });

        return privilegeList;
    }

    get licenseList(): Array<License> {
        const licenseList: Array<License> = [];

        this.licenseeLicenses.forEach((license) => {
            const previousEntryOfStateIndex = licenseList.findIndex((state) =>
                state?.issueState?.abbrev === license?.issueState?.abbrev);
            const previousEntryOfState = licenseList[previousEntryOfStateIndex];

            // If no existing entry of state add to array
            if (previousEntryOfStateIndex === -1) {
                licenseList.push(license);
            // If currently observed license is newer than saved entry replace existing entry
            } else if (
                license.renewalDate
                && previousEntryOfState.renewalDate
                && moment(license.renewalDate).isAfter(moment(previousEntryOfState.renewalDate))
            ) {
                licenseList[previousEntryOfStateIndex] = license;
            }
        });

        return licenseList;
    }

    get obtainPrivButtonLabel(): string {
        return `+ ${this.$t('licensing.obtainPrivileges')}`;
    }

    get privilegeTitle(): string {
        return this.$t('licensing.privileges');
    }

    get welcomeText(): string {
        return this.$t('common.welcome');
    }

    get activeLicenses(): Array<License> {
        return this.licenseList.filter((license) => (license.statusState === 'active'));
    }

    get hasMoreThanOneActiveLicense(): boolean {
        return this.activeLicenses.length > 1;
    }

    get isPrivilegePurchaseDisabled(): boolean {
        return this.hasMoreThanOneActiveLicense || !this.hasActiveLicense;
    }

    get hasActiveLicense(): boolean {
        return this.activeLicenses.length > 0;
    }

    get twoHomeStateErrorText(): string {
        return this.$t('licensing.twoHomeStateErrorMessage');
    }

    get licenseExpiredMessage(): string {
        return this.$t('licensing.licenseExpiredMessage');
    }

    //
    // Methods
    //
    startPrivPurchaseFlow() {
        // The feature is stubbed off at this point, please
        // manually navigate to the select privilege screen
        console.log('Starting Privilege Purchase Flow!');
    }

    checkIfLicenseActive(license: License) {
        let isLicenseActive = false;

        if (license && license.statusState === LicenseStatus.ACTIVE) {
            isLicenseActive = true;
        }

        return isLicenseActive;
    }
}
