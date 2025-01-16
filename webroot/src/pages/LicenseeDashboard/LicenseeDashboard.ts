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
import moment from 'moment';

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

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
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
        // From list of all privileges associated with user (independent of status),
        // returns only most recent privilege fetched associated with each state
        // to positively and most clearly display user's status in each state
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
        // From list of all licenses associated with user (independent of status),
        // returns only most recent license fetched associated with each state
        // to positively and most clearly display user's status in each state
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

    get pastPrivilegeList(): Array<License> {
        const privilegeList: Array<License> = [];

        this.licenseePrivileges.forEach((privilege) => {
            if (privilege.history) {
                (privilege.history as Array<any>).forEach((historyItem) => {
                    privilegeList.push(new License({
                        ...privilege,
                        expireDate: historyItem.previousValues?.dateOfExpiration || null,
                        issueDate: historyItem.previousValues?.dateOfIssuance || null,
                        statusState: LicenseStatus.INACTIVE
                    }));
                });
            }
        });

        return privilegeList;
    }

    get pastPrivilegesTitle(): string {
        return this.$t('licensing.pastPrivilegesTitle');
    }

    //
    // Methods
    //
    startPrivPurchaseFlow() {
        // The feature is stubbed off at this point, please
        // manually navigate to the select privilege screen
        console.log('Starting Privilege Purchase Flow!');
    }

    viewMilitaryStatus() {
        this.$router.push({
            name: 'MilitaryStatus',
            params: { compact: this.currentCompactType }
        });
    }

    checkIfLicenseActive(license: License) {
        let isLicenseActive = false;

        if (license && license.statusState === LicenseStatus.ACTIVE) {
            isLicenseActive = true;
        }

        return isLicenseActive;
    }

    togglePrivsCollapsed() {
        this.isPrivsCollapsed = !this.isPrivsCollapsed;
    }

    togglePastPrivsCollapsed() {
        this.isPastPrivsCollapsed = !this.isPastPrivsCollapsed;
    }
}
